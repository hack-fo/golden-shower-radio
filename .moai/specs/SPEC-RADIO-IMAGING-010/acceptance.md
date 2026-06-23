# SPEC-RADIO-IMAGING-010 — Acceptance Criteria

<!-- version: 0.3.1 (matches spec.md) -->
<!-- 2026-06-23 (v0.3.1): Audit convergence fixes — rewrote AC-NFR-I-5 to scope the
     no-fully-autonomous-generation prohibition to Suno only (VERIFY the LOCAL Group IG path is
     described as fully autonomous) and AC-NFR-I-7 to name the local-gen music-gen.server sidecar
     as the one sanctioned additive external GPU service (replacing the stale "no on-GPU generative
     model" wording). No requirement/parity change; 1:1 REQ↔AC preserved (38 REQ + 10 NFR = 48). -->

Acceptance criteria for SPEC-RADIO-IMAGING-010 (Station/Show Imaging Production — local-primary
autonomous generation, autonomous post-production, hosted breaks). Section A lists one acceptance
entry per requirement (1:1 REQ↔AC). Section B gives detailed Given-When-Then scenarios for the
load-bearing requirements. Section C is the Definition of Done. Parity: 38 REQ + 10 NFR = 48
specified items → 48 acceptance entries. (Group IG — AC-IG-001…007 — is the PRIMARY local-gen path;
Group IH — AC-IH-001…005 — is the hosted-break composer; Group IX — AC-IX-001…005 — is
EXPERIMENTAL / OPT-IN / OFF BY DEFAULT.)

---

## Section A — Acceptance entries (1:1 with requirements)

### Group IB — Imaging Beds & Licensing

**AC-IB-001 (REQ-IB-001 — no Suno API; no third-party wrapper ever; optional Suno seed is human-only) [HARD]**
- VERIFY no code path constructs or calls a Suno API endpoint, a third-party "Suno API" wrapper,
  or any third-party / network music-generation API (a source/dependency scan finds no such
  client/URL); the third-party-wrapper prohibition is absolute on ANY path.
- VERIFY the PRIMARY/default bed source is the LOCAL self-hosted `music-gen.server` sidecar
  (Group IG) — a FIRST-PARTY local service the brain POSTs to, which is NOT a third-party API and
  does not violate this prohibition (cross-checks AC-IG-001/004).
- VERIFY the optional Suno-seed path enters beds ONLY as human-downloaded local files via the
  drop-dir ingest (REQ-IB-002); the SPEC/docs describe the SUNO seed as human-seeded (off-loop) and
  describe LOCAL generation honestly as fully autonomous (cross-checks AC-NFR-I-5).

**AC-IB-002 (REQ-IB-002 — watched drop-dir ingest of local files) [HARD]**
- GIVEN bed files placed in the watched ingest drop dir, WHEN ingest runs, THEN each is read as a
  LOCAL file, validated as decodable audio, and recorded in the library + ledger; 12-track WAV
  stems and 2-bus mixdowns are both accepted (stems preferred).
- VERIFY ingest never fetches from a network music source; a non-audio/corrupt file is logged +
  skipped (not aired); re-running ingest does not re-ingest an already-known bed (idempotent).

**AC-IB-003 (REQ-IB-003 — paid-tier-only beds; free-tier forbidden) [HARD]**
- VERIFY only paid-tier (commercial-rights, no-attribution) beds generated while subscribed are
  marked airable; a free-tier/Basic bed is NOT aired.
- VERIFY beds are treated as non-exclusive, non-indemnified (no reliance on owning/enforcing); the
  "generate only while subscribed" reminder is recorded with the ledger (AC-IB-004).

**AC-IB-004 (REQ-IB-004 — paid-tier-licensed ledger class extends OPS-004 REQ-OE-010) [HARD]**
- GIVEN an ingested Suno bed, WHEN it is recorded, THEN its OPS-004 license-ledger entry carries
  the paid-tier-licensed class (`source: suno-paid`, `commercial_rights: true`, `exclusive: false`,
  `indemnified: false`, `attribution_required: false`, `generated_while_subscribed: true`,
  `ai_generated: true`, `bed_id`, `ingested_at`).
- VERIFY the OE-010 ledger store + gate are NOT forked or weakened; the gate RECOGNIZES the
  paid-tier-licensed class as a permitted-to-air basis alongside procedural/CC0; a murkier/free-tier
  bed is quarantined.

### Group IP — Autonomous Production Pipeline

**AC-IP-001 (REQ-IP-001 — fully autonomous after ingest) [HARD]**
- GIVEN an ingested bed + a jingle-spec recipe, WHEN production runs, THEN cut → loop → TTS-layer →
  duck → master → catalog → serve complete with ZERO human input.
- VERIFY no production stage prompts for or blocks on a human; the only non-autonomous step is bed
  generation (REQ-IB-001), which is outside the run loop.

**AC-IP-002 (REQ-IP-002 — cut/trim, phrase-snap, fades, honor `[End]`) [HARD]**
- GIVEN a bed + a target ident length, WHEN cut, THEN the clip is `atrim`'d to the target length on
  a musical phrase boundary with `afade` in/out (and optional `silenceremove`), and any Suno `[End]`
  hard-stop is honored.
- VERIFY the cut fades rather than hard-cuts unless an `[End]` sting is intended.

**AC-IP-003 (REQ-IP-003 — loop/extend to fit) [HARD]**
- GIVEN a bed shorter than the target length, WHEN extended, THEN `aloop`/`acrossfade` produce a
  seamless bed of the needed duration (verified: a 2s bed → exactly 6.0s) with no audible seam at
  the loop point.

**AC-IP-004 (REQ-IP-004 — TTS-layer + sidechain duck, `asplit=2` gotcha) [HARD]**
- GIVEN a voiced ident, WHEN mixed, THEN the TTS line (Kokoro/Piper) is positioned with
  `adelay`/`apad` and the bed is ducked ~8-12 dB under the voice via `sidechaincompress` with the
  VOICE as the sidechain key, then `amix`'d, with a smooth attack/release.
- VERIFY the delayed voice is `asplit=2`-fanned (one branch to the duck trigger, one to the `amix`
  bus) so ffmpeg does NOT fail "matches no streams"; a non-voiced sting skips this stage (music
  only).

**AC-IP-005 (REQ-IP-005 — two-pass loudnorm master to shared target) [HARD]**
- GIVEN a mixed ident, WHEN mastered, THEN two-pass `loudnorm` (pyloudnorm measure pass + apply
  pass) lands it within ~0.3 LU of -16 LUFS / -1.5 dBTP / LRA 11 (`config.py`), encoded
  `libmp3lame` 192k @ 44.1kHz.
- VERIFY the measured integrated loudness of a produced ident is within tolerance of the shared
  target (fulfills OPS-004 REQ-OE-005).

**AC-IP-006 (REQ-IP-006 — anti-dramatic master discipline) [HARD]**
- VERIFY produced idents are NOT brick-walled/over-limited (dynamics preserved; the two-pass target
  is reached without aggressive limiting); the duck keeps the bed audible under the voice rather
  than slammed away; cuts fade rather than slam.
- VERIFY the imaging register is understated/musical (BBC6/NTS/KEXP), not loud news-bed (an ear-test
  pass confirms; the limiter/dynamics targets are TUNABLE).

**AC-IP-007 (REQ-IP-007 — verified toolchain, no new infra) [HARD]**
- VERIFY production uses only ffmpeg (the host-verified filter set), pyloudnorm, and the existing
  Kokoro/Piper providers — no new dependency and no new service is introduced.
- VERIFY the production module parallels `produce_talk_clip` at the `voice.py:340-342` seam and
  returns the same clip contract; the GPU is not required for the audio stage.

**AC-IP-008 (REQ-IP-008 — catalog the finished ident) [HARD]**
- GIVEN a mastered ident, WHEN cataloged, THEN it is written to the clips dir (mirroring the
  talk-clips dir / OPS-004 CLIPS_DIR) with metadata (type, show/segment, duration, lufs, voiced
  flag, bed_id, license class, created_at), available for serving.
- VERIFY re-producing the ident replaces (not duplicates) its catalog entry; the clip-library store
  is not forked (fulfills OPS-004 REQ-OE-006).

### Group IL — Per-Show Imaging Library

**AC-IL-001 (REQ-IL-001 — jingle-spec table) [HARD]**
- VERIFY a per-show/segment jingle-spec table maps show/segment → bed(s) + bump text/template +
  duck params + target length + ident type, keyed against the PROGRAMMING-007 roster.
- VERIFY a show's idents are produced from its row; a show with no row falls back to a
  station-default recipe; the table is config-tunable.

**AC-IL-002 (REQ-IL-002 — ident taxonomy + durations) [HARD]**
- VERIFY the taxonomy supports STING (~3-8s, typically music-only), BUMPER (~8-15s, voiced+ducked),
  and BUMP-OUT (~15-30s, voiced+ducked); each type's length + voiced flag drive the production
  stages (a sting skips the TTS/duck stage).

**AC-IL-003 (REQ-IL-003 — per-show sonic signature + cohesion) [HARD]**
- VERIFY each show/segment has a distinct instrumentation/tempo signature + a short motif, while a
  station-wide loudness + tonal floor (REQ-IP-005/006) keeps all idents cohesive; no two shows
  converge to the same imaging sound.
- VERIFY the per-show palette is config/AI-driven; the distinct-signature-atop-cohesive-floor
  property is verifiable across shows.

**AC-IL-004 (REQ-IL-004 — catalogued library with rotation variants) [HARD]**
- VERIFY the imaging library (mirroring the talk-clips dir) holds multiple variants per show/segment
  where beds permit, and serving rotates among ready variants to avoid repetition fatigue; a
  single-variant show still airs.

**AC-IL-005 (REQ-IL-005 — refresh cadence) — Medium**
- VERIFY imaging freshness per show/segment is tracked and a stale/over-rotated/thin set is flagged
  for refresh; the refresh thresholds/cadence are tunable; a stale set still airs (degrades to
  repetition, never silence) until the human's next bed batch + re-production refreshes it.

### Group IS — Serving Into Playout

**AC-IS-001 (REQ-IS-001 — serve via imaging seam + jingle/ident discriminator) [HARD]**
- GIVEN an imaging slot is due, WHEN the picker serves, THEN a ready ident is returned through
  OPS-004's imaging serving seam (REQ-OE-007) so `/api/next` serves + commits it like a song, with
  a finer jingle/ident transition discriminator attached.
- VERIFY the discriminator is ADDITIVE transition metadata, not a forked `/api/next` pull contract
  or a competing serving path; no ready ident → fall through to music.

**AC-IS-002 (REQ-IS-002 — musical, no-hard-cut radio.liq transition) [HARD]**
- GIVEN radio.liq plays an ident (signaled by the discriminator), WHEN it transitions, THEN a
  musical crossfade/segue is applied — NOT a hard cut — so the ident feels part of the flow.
- VERIFY the primary `%mp3(bitrate=320)` music mount is unchanged; the transition coordinates with
  CORE-001 + the in-flight playout-transition fix (referenced, not re-owned).

**AC-IS-003 (REQ-IS-003 — director schedules at show/segment boundaries) [HARD]**
- GIVEN the program director plans, WHEN an imaging slot fires, THEN it fires at a show/segment
  boundary (open/close, segment transition, or a director cadence position) with the correct ident
  type + the matching show's variant.
- VERIFY WHEN imaging fires is the OPS-004/ORCH-005 director's decision (REQ-OA-005, referenced);
  IMAGING-010 supplies ready, show-matched idents, it does not re-own scheduling.

**AC-IS-004 (REQ-IS-004 — single clean single-track served ident) [HARD]**
- VERIFY each served ident is a single clean single-track request (no multi-track/chained item),
  inheriting OPS-004 REQ-OE-009 to avoid the post-jingle stall (savonet/liquidsoap #1074).

### Group IX — Experimental Autonomous Bed Generation (OPT-IN, OFF BY DEFAULT)

**AC-IX-001 (REQ-IX-001 — experimental safety envelope) [HARD]**
- VERIFY the experimental path is OFF BY DEFAULT (disabled unless an explicit config opt-in is
  set) and KILL-SWITCHABLE (one flag disables it).
- VERIFY when enabled it runs ONLY on a secondary/throwaway Suno account and NEVER uses the Premier
  account; the optional-premium human-seeded Suno path (Group IB) is the only path that touches
  Premier.
- VERIFY the SPEC/docs label the path as knowingly ToS-violating + ban-risk, and record that
  enabling it requires the actual user's own explicit risk-accepted opt-in (a coordinator relay is
  not consent).

**AC-IX-002 (REQ-IX-002 — first-party headed-browser mechanism)**
- GIVEN the experimental path enabled, WHEN it drives Suno, THEN it uses a HEADED (not headless)
  Chromium via Playwright with a PERSISTENT logged-in profile (saved storage state) reused across
  runs so login/captcha rarely triggers.
- VERIFY it is first-party UI automation, NOT a third-party API wrapper (which stays forbidden,
  AC-IB-001).

**AC-IX-003 (REQ-IX-003 — vision + DOM navigation)**
- GIVEN the experimental path enabled, WHEN it navigates, THEN it uses our own visual recognition
  (claude-vision) + the DOM/accessibility snapshot to find the prompt box, set instrumental/short
  params (instrumental ON / vocals OFF), generate, and download (stems preferred).
- VERIFY the downloaded file lands in the ingest drop dir and is thereafter indistinguishable from
  a human-downloaded bed (re-enters REQ-IB-002 + Group IP unchanged).

**AC-IX-004 (REQ-IX-004 — captcha stance: first-party primary, paid solver rare fallback)**
- GIVEN a captcha challenges the experimental path, WHEN resolving, THEN our own tooling +
  semi-automatic human-solve is primary, and a third-party paid solver (NopeCHA-style) is used ONLY
  as a rare optional fallback (off unless separately enabled).
- VERIFY the honesty note that vision cannot reliably solve hCaptcha/Turnstile (rare human/paid
  fallback expected) is recorded; semi-automatic is acceptable for the infrequent batch.

**AC-IX-005 (REQ-IX-005 — place in the four-way hierarchy + unchanged handoff) [HARD]**
- VERIFY the experimental path sits in its place in the four-way hierarchy (owned by REQ-IG-007):
  local self-hosted = primary/default; human-seeded Suno = optional premium (Premier); headed-browser
  automation = experimental opt-in fallback (secondary account); third-party API wrappers = forbidden.
- GIVEN a bed produced by the experimental path, WHEN it lands in the drop dir, THEN it re-enters
  the existing Group IB ingest (license-ledger recorded, marked secondary-account origin) + the
  Group IP pipeline with NO behavioral difference; the experimental path does NOT bypass ingest
  validation, the ledger, or any production/serving rail.

### Group IG — Local Self-Hosted Music Generation (PRIMARY, DEFAULT-ON)

**AC-IG-001 (REQ-IG-001 — local ACE-Step 1.5 as the primary broadcast-clean engine) [HARD]**
- GIVEN the local-gen path, WHEN the brain requests a bed, THEN it POSTs a JSON request
  (`caption`=mood prompt, `instrumental=true`, `duration`, `inference_steps`/`guidance`/`seed`) to a
  local self-hosted `music-gen.server` (`kortexa-ai`, :4009) running ACE-Step 1.5, and receives a
  usable raw instrumental clip.
- VERIFY ACE-Step is the spine: v1 weights Apache-2.0 / v1.5 weights MIT, wrapper MIT, outputs owned
  outright, no revenue gate — recorded as unconditionally broadcast-clean; the model only emits a raw
  clip that the Group IP pipeline finishes.

**AC-IG-002 (REQ-IG-002 — Stable Audio Open Small companion, revenue-gated, tripwire) [HARD]**
- GIVEN a short clip (≤11s sting/loop) is wanted, WHEN the companion is enabled, THEN Stable Audio
  Open Small (0.5B) MAY render it; ACE-Step alone remains sufficient if the companion is off.
- VERIFY the companion's Stability AI Community License revenue gate (free + owned-outputs only under
  USD $1M annual revenue) is recorded in the ledger with a REVENUE-GATE TRIPWIRE that hard-cuts
  Stable-Audio generation above the threshold and falls back to ACE-Step-only; the companion is never
  a dependency.

**AC-IG-003 (REQ-IG-003 — NonCommercial-weights engines disqualified on air) [HARD]**
- VERIFY no code path uses MusicGen, AudioGen, or any NonCommercial-weights engine (e.g. CC-BY-NC-4.0)
  to generate a bed that airs; a clean CODE license does not make a clean WEIGHTS license.
- VERIFY this matches OPS-004 REQ-OE-010's self-generated-or-CC0-only on-air gate (no NC-weights bed
  passes the gate).

**AC-IG-004 (REQ-IG-004 — GPU Docker sidecar; weights on `/mnt/f`) [HARD]**
- VERIFY the local engine runs as a GPU Docker sidecar on the shared GPU infra (nvidia-container-
  toolkit + CUDA-torch passthrough) and the brain calls it over local JSON HTTP; the sidecar fits the
  verified 6-8GB Ada tier or falls back to CPU.
- VERIFY model weights live on `/mnt/f` (bind mount + `HF_HOME`), NEVER baked into the container
  layer; the sidecar is first-party owned infra, NOT a third-party API/wrapper and NOT a
  brain-internal service.

**AC-IG-005 (REQ-IG-005 — pre-render + cache batch off playout; OE-010 ledger) [HARD]**
- GIVEN a local-gen batch, WHEN it runs, THEN it runs OFF the playout path (infrequent, weekly/monthly
  — never in the live loop; `/api/next` never waits), renders raw clips into the existing imaging
  ingest dir (re-entering REQ-IB-002 + Group IP unchanged), and records each bed in the OPS-004
  REQ-OE-010 ledger.
- VERIFY the `source=local-acestep` class (`commercial_rights: true`, `exclusive: true`,
  `ai_generated: true`, `license: apache-2.0/mit`) is a SELF-GENERATED class the OE-010 gate accepts
  DIRECTLY (no carve-out); the `source=local-stableaudio` class carries `license:
  stability-ai-community` + the revenue-gate note; the ledger store/gate are not forked or weakened.

**AC-IG-006 (REQ-IG-006 — GPU-contention guard: serialize or CPU-fallback) [HARD]**
- VERIFY music-gen is never co-located unmanaged with the live service: it is SERIALIZED against the
  GPU peers (TTS/Whisper) via a queue/lock so it never runs concurrently with a TTS render, OR the
  music-gen batch runs CPU-only.
- VERIFY CPU fallback is acceptable for this infrequent off-playout batch; the live stream is never
  starved (no OOM/502 co-location failure).

**AC-IG-007 (REQ-IG-007 — four-way generation hierarchy explicit) [HARD]**
- VERIFY the four-way hierarchy holds: (1) LOCAL self-hosted (IG) = PRIMARY / default-ON / fully-
  autonomous / ToS-clean / license-clean and the default bed source; (2) human-seeded Suno (IB) =
  optional premium for hero/special idents; (3) headed-browser Suno automation (IX) = experimental
  opt-in fallback beneath local-gen; (4) third-party API wrappers = forbidden always (REQ-IB-001).
- VERIFY everything downstream of the ingest dir is SOURCE-AGNOSTIC regardless of which path produced
  the bed.

### Group IH — Autonomous Hosted-Break Segment

**AC-IH-001 (REQ-IH-001 — first-class autonomously-conceived hosted break) [HARD]**
- GIVEN a show/segment, WHEN the brain conceives a hosted break, THEN it picks the bed source, the
  script, and the treatment on its own accord (no human) and assembles one finished clip = bed + host
  script + TTS host line.
- VERIFY a hosted break (host VO over a bed) is DISTINCT from a pure instrumental ident (the Group IL
  sting/bumper/bump-out taxonomy); the brain selects + assembles from owned capabilities, it does not
  author the script or synthesize the voice itself.

**AC-IH-002 (REQ-IH-002 — bed source: local primary, premium optional) [HARD]**
- GIVEN a hosted break, WHEN its bed is sourced, THEN it comes via the four-way hierarchy (REQ-IG-007):
  a LOCAL-generated bed (Group IG, primary/default) or — optionally, for a hero/special break — a
  premium human-seeded Suno bed (Group IB).
- VERIFY the bed enters the same ingest + license-ledger path and is source-agnostic to the rest of
  the assembly.

**AC-IH-003 (REQ-IH-003 — host script from PROGRAMMING-007; TTS from VOICE-002; referenced) [HARD]**
- VERIFY the hosted break's host script is obtained from PROGRAMMING-007's owned capability (incl. the
  PV host-voice calibration + the grounded-voice/gate rules) and the host line is rendered through
  VOICE-002's TTS providers.
- VERIFY IMAGING-010 does NOT write host scripts, re-own persona conduct/voice/grounding, or re-own
  TTS synthesis — it REQUESTS a script and RENDERS through the TTS, as the existing imaging/news paths
  do.

**AC-IH-004 (REQ-IH-004 — assembled by the existing Group IP pipeline) [HARD]**
- GIVEN a hosted break, WHEN assembled, THEN it is produced THROUGH the existing Group IP stages —
  TTS-over-bed `sidechaincompress` duck (with the `asplit=2` gotcha), cut/phrase-snap/fades,
  loop/extend, two-pass `loudnorm` master to the shared target, anti-dramatic discipline, catalog —
  not a parallel production path.
- VERIFY the only difference from a voiced ident is the richer host script it carries over the bed.

**AC-IH-005 (REQ-IH-005 — scheduled by the director at boundaries) [HARD]**
- GIVEN the program director plans, WHEN a hosted break fires, THEN it fires at a director-chosen
  show/segment boundary (REQ-IS-003), served through the same imaging seam + discriminator + musical
  no-hard-cut transition as other idents.
- VERIFY WHEN a hosted break fires is the OPS-004/ORCH-005 director's decision (REQ-OA-005, referenced);
  IMAGING-010 supplies ready, show-matched hosted breaks, it does not re-own scheduling.

### Non-Functional

**AC-NFR-I-1 (NFR-I-1 — never blocks the pull)**
- VERIFY a `/api/next` pull never waits on an ingest, render, duck, or master; production is an
  offline/off-hot-path batch on the ready-buffer/serialized-generator discipline; no ready ident →
  fall through to music. Measure: pull latency unaffected during active production.

**AC-NFR-I-2 (NFR-I-2 — bounded, throttled, idempotent)**
- VERIFY ingest + production are bounded/throttled (OPS-004 REQ-OH-006 pattern) so imaging does not
  jointly overload the box; re-ingesting a bed or re-producing an ident does not duplicate
  library/ledger entries.

**AC-NFR-I-3 (NFR-I-3 — loudness consistency)**
- VERIFY a sample of produced idents measures within ~0.3 LU of -16 LUFS / -1.5 dBTP / LRA 11, so
  none jumps in level against music/talk/news.

**AC-NFR-I-4 (NFR-I-4 — resilience)**
- GIVEN a corrupt/unreadable bed or a render/filtergraph/master failure, WHEN it occurs, THEN it is
  logged + skipped without aborting the batch, crashing the worker/daemon, or silencing the stream;
  serving falls through to music.

**AC-NFR-I-5 (NFR-I-5 — honest capability)**
- VERIFY the PRIMARY LOCAL path (Group IG) IS described as fully autonomous (generation +
  post-production both the brain's) — describing it so is honest and required (cross-checks
  AC-IG-001/007, Scenario 8).
- VERIFY no requirement/AC/doc/website-copy claims "fully autonomous generation" via *Suno*: the
  Suno seed (Group IB) is human-seeded (off-loop premium) and the experimental Group IX Suno
  automation is a labeled ToS-violating + ban-risk + opt-in POC.
- VERIFY no third-party music-generation API/wrapper is called on any path (the local
  `music-gen.server` sidecar is first-party owned infra, not a third-party API; cross-checks
  AC-IB-001).

**AC-NFR-I-6 (NFR-I-6 — legality)**
- VERIFY no code path airs a free-tier or murkier-rights bed; only paid-tier-licensed
  (generated-while-subscribed) beds air, each recorded in the ledger under the paid-tier-licensed
  class; beds are treated as non-exclusive, non-indemnified furniture.

**AC-NFR-I-7 (NFR-I-7 — simplicity)**
- VERIFY the local-gen `music-gen.server` sidecar is the ONE sanctioned additive external GPU
  service (the brain POSTs to it like Liquidsoap/TTS); there is NO new brain-internal service, NO
  second serving path, NO new datastore, and the primary `%mp3(bitrate=320)` music mount is
  unchanged.
- VERIFY the implementation otherwise adds minimal new dependencies; deferred items (spec
  Section 10) are not partially built; the experimental Group IX is a gated POC behind an opt-in
  flag, not a built-out production subsystem.

**AC-NFR-I-8 (NFR-I-8 — experimental-path safety envelope) [HARD]**
- VERIFY Group IX never endangers default operation: off by default, kill-switchable,
  secondary-account only (never Premier), no third-party API wrapper, and the default bed sources
  (local-gen primary + the optional Suno premium seed) are fully intact and unaffected whether or
  not IX is enabled.
- VERIFY the residual risks are acknowledged honestly (ToS/ban → secondary account; UI brittleness
  → best-effort POC the station never depends on; captcha → rare human/paid fallback; headless
  detection → headed + persistent profile).
- VERIFY enabling Group IX requires the actual user's own explicit risk-accepted opt-in (a
  coordinator relay is not consent).

**AC-NFR-I-9 (NFR-I-9 — local generation off the playout path; GPU-serialized or CPU-fallback)**
- VERIFY the local-gen sidecar runs as an infrequent pre-render + cache batch OFF the playout path;
  a `/api/next` pull never waits on a generation. Measure: pull latency unaffected during an active
  generation batch.
- VERIFY music-gen is serialized against the GPU peers (TTS/Whisper) or runs CPU-only — never
  co-located unmanaged with the live service; the live stream is never starved (no OOM/502).

**AC-NFR-I-10 (NFR-I-10 — local-gen license cleanliness)**
- VERIFY ACE-Step (Apache/MIT, owned, no revenue gate) is the unconditional broadcast-clean spine,
  sufficient alone at any station revenue.
- VERIFY Stable Audio Open Small is recorded as the conditional revenue-gated companion with a
  tripwire that hard-cuts it above USD $1M revenue, falling back to ACE-Step-only; MusicGen/AudioGen
  (NonCommercial weights) are disqualified on air. The unconditional-spine / conditional-companion /
  disqualified-NC distinction is recorded in the ledger and never blurred.

---

## Section B — Given-When-Then scenarios (load-bearing requirements)

### Scenario 1 — Optional Suno-seed (premium) ingest, no third-party API (REQ-IB-001, REQ-IB-002, NFR-I-5)

```
GIVEN the station is running and a human has generated a batch of paid-tier instrumental beds in
      the Suno UI and downloaded them into the watched ingest drop dir
WHEN  the imaging ingest runs
THEN  each bed is read as a LOCAL file, validated as decodable audio, and recorded in the imaging
      library + the license ledger (paid-tier-licensed class)
AND   no code path calls a Suno API, a third-party Suno wrapper, or any third-party/network
      music-generation API (the first-party local music-gen.server sidecar is owned infra, not a
      third-party API — Scenario 8)
AND   a non-audio/corrupt dropped file is logged + skipped, never aired
AND   re-running ingest does not re-ingest an already-known bed
AND   the music keeps playing throughout (ingest is off the pull path)
```

### Scenario 2 — Voiced bumper production with the `asplit=2` duck (REQ-IP-001/002/003/004/005/006)

```
GIVEN an ingested bed and a jingle-spec row for a show's bumper (target ~12s, voiced, duck -10 dB)
WHEN  the brain produces the bumper autonomously
THEN  the bed is cut/trimmed to ~12s snapped to a musical phrase boundary with afade in/out (honoring
      any [End] tag), looped/extended via aloop/acrossfade if shorter than 12s
AND   the host TTS line (Kokoro/Piper) is rendered, positioned with adelay/apad, and the bed is
      ducked ~10 dB under the voice via sidechaincompress with the VOICE as the sidechain key
AND   the delayed voice is asplit=2-fanned (one branch to the duck trigger, one to the amix bus) so
      ffmpeg does NOT fail "matches no streams"
AND   the mix is two-pass loudnorm-mastered within ~0.3 LU of -16 LUFS / -1.5 dBTP / LRA 11 and
      encoded libmp3lame 192k @ 44.1kHz
AND   the master is gentle (not brick-walled/over-limited) — understated, not news-bed loud
AND   the whole pipeline runs with zero human input after ingest
```

### Scenario 3 — Music-only sting skips the duck stage (REQ-IP-004, REQ-IL-002)

```
GIVEN an ingested bed and a jingle-spec row for a show's sting (target ~5s, music-only / no voice)
WHEN  the brain produces the sting
THEN  the bed is cut to ~5s on a phrase boundary with clean fades (or honoring an [End] hard stop)
AND   the TTS-layer + sidechain-duck stage is SKIPPED entirely (no voice, no amix)
AND   the sting is two-pass loudnorm-mastered to the shared station target
AND   it is cataloged as a music-only sting variant for the show
```

### Scenario 4 — Licensing reconciliation with OPS-004's gate (REQ-IB-003, REQ-IB-004, NFR-I-6)

```
GIVEN a paid-tier Suno bed (generated while subscribed) and a free-tier (Basic) Suno bed both in
      the drop dir
WHEN  the beds are ingested + recorded in the OPS-004 license ledger
THEN  the paid-tier bed gets the paid-tier-licensed class (commercial_rights true, exclusive false,
      indemnified false, attribution_required false, generated_while_subscribed true) and is
      permitted to air by the OE-010 gate (which now recognizes the class)
AND   the free-tier bed is NOT aired (attribution + weaker rights — forbidden)
AND   the OE-010 ledger store + gate are not forked or weakened; the paid-tier-licensed class is an
      added permitted-basis alongside procedural/CC0
AND   the bed is treated as non-exclusive, non-indemnified station furniture the station does not
      rely on owning
```

### Scenario 5 — Per-show imaging served with a musical transition at a boundary (REQ-IL-001/003/004, REQ-IS-001/002/003/004)

```
GIVEN catalogued ident variants for "Show A" (distinct sonic signature) and "Show B", and the
      program director scheduling an imaging slot at the Show A → Show B boundary
WHEN  /api/next is pulled at that boundary
THEN  the picker returns a ready Show-A-or-B-appropriate ident through OPS-004's imaging serving seam
      (REQ-OE-007) with a jingle/ident transition discriminator attached
AND   it is a single clean single-track item (no multi-track stall)
AND   radio.liq applies a musical, no-hard-cut transition so the ident feels part of the flow
AND   serving rotates among the show's ready variants to avoid repetition
AND   if no ident is ready, the picker falls through to music (idents are best-effort)
AND   WHEN the slot fires is the director's decision (OPS-004 REQ-OA-005), not IMAGING-010's
```

### Scenario 6 — Resilience: a bad bed never breaks the station (REQ-IP-001, NFR-I-1, NFR-I-4)

```
GIVEN a batch of dropped beds where one file is truncated/corrupt and one render fails on a
      filtergraph error
WHEN  production runs over the batch
THEN  the corrupt bed and the failed render are logged + skipped
AND   the rest of the batch produces normally
AND   the production worker, the director loop, and the daemon do not crash
AND   the stream is never silenced; pulls during production are unaffected (production is off the
      pull path)
```

### Scenario 7 — Experimental autonomous generation, opt-in + secondary account (REQ-IX-001…005, NFR-I-8)

```
GIVEN the experimental path (Group IX) is OPT-IN and the operator has enabled it on a
      secondary/throwaway Suno account (never the Premier account), with the actual user's explicit
      risk-accepted opt-in recorded
WHEN  the experimental path runs a generation batch
THEN  a HEADED Chromium (Playwright) with a persistent logged-in profile drives the real Suno UI
AND   navigation uses our own visual recognition (claude-vision) + the DOM/accessibility snapshot
      to set instrumental/short params, generate, and download beds (no third-party API wrapper)
AND   if a captcha challenges, our own tooling + a semi-automatic human-solve is tried first; a
      paid solver (NopeCHA-style) is only a rare optional fallback
AND   each downloaded bed lands in the drop dir and re-enters the existing Group IB ingest +
      Group IP pipeline UNCHANGED, recorded in the license ledger marked secondary-account origin
AND   the default human-seeded path and the Premier account are completely untouched
AND   disabling the kill-switch immediately stops the path with no effect on default operation
AND   the path is honestly labeled ToS-violating + ban-risk (a POC, never depended on for continuity)
```

### Scenario 8 — Local-primary autonomous generation → ingest → served ident (REQ-IG-001…007, NFR-I-9/10)

```
GIVEN the station is running and the local-gen sidecar (music-gen.server / ACE-Step 1.5) is up on the
      shared GPU infra, weights bind-mounted from /mnt/f, with the GPU serialized against TTS/Whisper
      (or set to CPU-only)
WHEN  the brain runs its infrequent (weekly/monthly) off-playout pre-render batch
THEN  the brain POSTs JSON requests (caption=tasteful BBC6/NTS mood prompt, instrumental=true,
      duration, inference_steps/guidance/seed) to the local sidecar and receives raw instrumental clips
AND   no Suno API, third-party wrapper, captcha, or human is involved — the path is fully autonomous,
      ToS-clean, and license-clean
AND   each generated bed is recorded in the OPS-004 REQ-OE-010 ledger under source=local-acestep
      (Apache/MIT, owned, exclusive) — a self-generated class the gate accepts directly — or
      source=local-stableaudio (revenue-gated, tripwire-guarded)
AND   no NonCommercial-weights engine (MusicGen/AudioGen) is ever used on air
AND   the raw clips land in the existing imaging ingest dir and are finished by the UNCHANGED Group IP
      pipeline (cut/loop/duck/master/TTS-layer/catalog)
AND   the generation batch never blocks /api/next and never starves the live stream (serialized or
      CPU-fallback); the music keeps playing throughout
AND   local generation is the PRIMARY/default bed source; the Suno paths (premium seed, experimental
      automation) are non-default; third-party wrappers stay forbidden
```

### Scenario 9 — Autonomous hosted break: local bed + 007 script + 002 TTS, director-scheduled (REQ-IH-001…005)

```
GIVEN a show/segment and the program director planning a hosted break at its boundary
WHEN  the brain conceives the hosted break autonomously (no human)
THEN  the brain sources a bed via the four-way hierarchy — a local-generated bed (Group IG, primary) or
      optionally a premium human-seeded Suno bed (Group IB)
AND   it REQUESTS a host script from PROGRAMMING-007 (incl. the PV host-voice calibration + the
      grounded-voice/gate rules) and renders the host line through VOICE-002's TTS — re-owning neither
AND   it assembles the break THROUGH the existing Group IP pipeline (TTS-over-bed sidechain duck with
      the asplit=2 gotcha + cut/edit + two-pass loudnorm master + anti-dramatic discipline + catalog),
      not a parallel pipeline
AND   the finished hosted break (host VO over a bed) is DISTINCT from a pure instrumental ident (the IL
      taxonomy) and is catalogued for serving
AND   it fires at a show/segment boundary the DIRECTOR chooses (OPS-004 REQ-OA-005 / ORCH-005), served
      through the same imaging seam + jingle/ident discriminator + musical no-hard-cut transition
AND   IMAGING-010 owns only the segment-type + the autonomous conception + the assembly; the script,
      voice, production stages, and scheduling are all referenced, not re-owned
```

---

## Section C — Definition of Done

- [ ] All 38 REQ + 10 NFR have a passing acceptance entry (1:1 REQ↔AC, parity preserved).
- [ ] LOCAL self-hosted generation (Group IG — ACE-Step 1.5 spine via the writ-fm `music-gen.server`
      sidecar + Stable Audio Open Small companion) is the PRIMARY, default-ON, fully-autonomous,
      ToS-clean, license-clean generation path (REQ-IG-001…007, NFR-I-5/9/10).
- [ ] The four-way generation hierarchy holds: LOCAL primary / Suno premium-optional (human-seed) /
      headed-browser fallback (experimental) / third-party wrappers FORBIDDEN always (REQ-IG-007,
      REQ-IB-001) — the wrapper prohibition is absolute on ANY path.
- [ ] Local-gen runs as an off-playout pre-render batch, GPU-serialized against TTS/Whisper or
      CPU-fallback (never co-located unmanaged), weights on `/mnt/f`, `instrumental=true`; ACE-Step
      (Apache/MIT) unconditional spine, Stable Audio revenue-gate tripwired, MusicGen disqualified
      (REQ-IG-003/004/005/006, NFR-I-9/10).
- [ ] Beds enter only as validated local files from the watched drop dir (from local-gen primary or
      the optional Suno seed); ingest is source-agnostic (REQ-IB-002).
- [ ] Only license-clean beds air (local-gen self-generated, or Suno paid-tier
      generated-while-subscribed); free-tier + NonCommercial-weights forbidden; each bed recorded in
      the OPS-004 ledger under its class extending REQ-OE-010 (REQ-IB-003/004, REQ-IG-005, NFR-I-6).
- [ ] Production is fully autonomous after ingest (REQ-IP-001): cut/phrase-snap, loop/extend,
      TTS-layer + `asplit=2` sidechain duck, two-pass loudnorm master to -16/-1.5/LRA11, catalog
      (REQ-IP-002…008).
- [ ] Imaging is anti-dramatic (gentle dynamics, no brick-walling) — BBC6/NTS/KEXP register
      (REQ-IP-006).
- [ ] Per-show jingle-spec table + ident taxonomy + per-show sonic signature + rotation variants +
      refresh cadence in place (REQ-IL-001…005).
- [ ] Idents served through OPS-004's imaging seam with a jingle/ident discriminator + a musical
      no-hard-cut radio.liq transition + director-scheduled boundaries + single-clean-track guard
      (REQ-IS-001…004).
- [ ] Autonomous HOSTED-BREAK composer (Group IH) — a local-generated (or premium-seeded) bed + a
      PROGRAMMING-007 host script (incl. PV + grounding) + VOICE-002 TTS, assembled by the EXISTING
      Group IP pipeline, scheduled by the director — fully autonomous, REFERENCING (not re-owning)
      the script/voice, the TTS, the production pipeline, and the scheduling; distinct from a pure
      instrumental ident (REQ-IH-001…005).
- [ ] No new datastore, no new brain-internal service, no second serving path, primary `%mp3(320)`
      music mount unchanged; the local-gen `music-gen.server` sidecar is the one sanctioned additive
      external GPU service (the brain POSTs to it); minimal additions otherwise (NFR-I-7).
- [ ] Pull latency never affected by production; a bad bed never aborts the batch or silences the
      stream (NFR-I-1, NFR-I-4).
- [ ] Experimental Group IX (REQ-IX-001…005) is OPT-IN, OFF BY DEFAULT, kill-switchable,
      secondary-account-only (never Premier), no third-party API wrapper, residual risks
      acknowledged, and requires the actual user's own explicit risk-accepted opt-in before
      enabling (NFR-I-8) — coordinator relay is not consent.
- [ ] The four-way generation hierarchy holds (local-gen primary/default / Suno premium-optional
      human-seed / experimental opt-in browser automation / forbidden third-party wrappers); the
      experimental path stays in its place beneath local-gen; everything after the drop dir is
      source-agnostic (REQ-IG-007, REQ-IX-005).
- [ ] No requirement re-specifies, forks, or weakens any CORE-001/VOICE-002/OPS-004/ORCH-005/
      ANALYSIS-006/PROGRAMMING-007 requirement; OPS-004 Group OE + REQ-OE-010 (ledger/gate) are
      fulfilled/extended + referenced by number; Group IG references the OE-010 ledger + the shared
      GPU infra; Group IH references PROGRAMMING-007 (script/voice/PV/grounding), VOICE-002 (TTS),
      Group IP (production), and the director (scheduling) — re-owning none of them.
