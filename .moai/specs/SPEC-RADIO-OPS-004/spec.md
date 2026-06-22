---
id: SPEC-RADIO-OPS-004
version: 0.4.0
status: draft
created: 2026-06-22
updated: 2026-06-22
author: charlie
priority: High
issue_number: null
---

# SPEC-RADIO-OPS-004 — Autonomous Program Director, Self-Produced Imaging, Self-Learning Radio Craft & Newscasting

## HISTORY

- 2026-06-22 (v0.1.0): Initial draft. Third SPEC in the golden-shower-radio RADIO
  series, building ON TOP OF SPEC-RADIO-CORE-001 (music engine, LLM program-director
  loop, self-staffing personas, pull-based playout, self-controlled website) and
  SPEC-RADIO-VOICE-002 (TTS: Kokoro/Piper English, teldutala.fo Faroese, live music
  ducking, language routing). This SPEC makes the station ALIVE: it grants the AI an
  autonomous program director that plans + schedules its own 24h programming
  (Group OA); themed shows + hosts with character (Group OB); research-driven show
  prep with two LLM modes — cheap tools-off curation + richer web-search-on show-prep
  (Group OC); a self-learning radio-craft + music-history/cultural-context playbook
  that refines 24/7 with no human input (Group OD); self-produced station imaging /
  jingles via a 6-stage concept→TTS→ffmpeg-bed-duck→loudnorm→clip→pull pipeline
  (Group OE); liveliness + apolitical quality constraints (Group OF); and autonomous
  factual newscasting with self-discovered/aggregated trusted sources and a Faroese
  angle (Group OG). Inherits CORE-001's Creative Autonomy Principle, human-out-of-loop
  Operating Model, "smart and human, not a corporate business" ethos, zero
  monetization, and continuous-operation identity — every requirement grants the AI
  AUTHORITY + TOOLS + SAFETY RAILS and never prescribes fixed creative content/scripts/
  rules. SPEC-ID = OPS-004 (RADIO series uses a global-incrementing suffix; CALLIN-003
  is reserved; OPS-001 was rejected to avoid visual collision with CORE-001). Folds in
  directives relayed during authoring (to be user-confirmed): (A) music-history /
  cultural-societal depth as a knowledge+curation DIMENSION of Groups OC+OD, with a
  [HARD] APOLITICAL constraint (REQ-OF-004); (B) autonomous NEWSCASTING pulled forward
  from the deferred SPEC-RADIO-NEWS into Group OG, with the Faroese-news angle
  (kvf.fo/dimma.fo) — supersedes CORE-001 Section 3.2's news exclusion for regular
  scheduled newscasting (breaking-news interrupt remains OPTIONAL/advanced); (C)
  MEASURED, rate-limited, stability-preserving self-change (REQ-OD-006) modeled on the
  design-constitution evolution-safety framework; (D) reference-station emphasis on
  KEXP + P3 Dans + P3 Mix (REQ-OB-002/OD-002); (E) explicit no-repeat /
  least-recently-played rotation (REQ-OA-003a); (F) rich library metadata enrichment
  — tag correction + genre/mood/BPM/key/energy/year + a queryable catalog
  (REQ-OA-010/011/012, which also closes the former BPM/key analysis gap); (G)
  self-reasoning autonomy reaffirmed (Section 1.3); (H) Group OH — Library Management
  & Acquisition Policy: play-from-library balance (REQ-OH-001), slskd-first/yt-dlp-last
  quality preference (REQ-OH-002), organized library folder structure (REQ-OH-003),
  hard disk-space management / never run out (REQ-OH-004), and a Bandcamp
  purchase-recommendation hook (REQ-OH-005). Total: 57 REQ + 8 NFR = 65, 1:1 REQ↔AC.
- 2026-06-22 (v0.2.0): plan-auditor APPROVE-WITH-MINOR-FIXES (0 Critical, 2 Major, 5
  Minor) applied, plus a relayed time/date/location requirement and the Radiooooo
  reference. D1 (Major): documented the deliberate OA-009 numbering gap — and then
  FILLED it with the new REQ-OA-009 (time/date/location); no requirement was ever cut.
  D2 (Major): split REQ-OA-003's empty-set relaxation into its own Unwanted REQ
  (REQ-OA-003b); labeled REQ-OA-002 and REQ-OA-011 as documented compound requirements.
  D3 (Minor): reframed AC-OA-002's "5 or 7 variants, never a multiple of 24" into a
  tested anti-lattice PROPERTY (variant count not a divisor/multiple of 24) as default
  guidance, keeping the count AI-authored/tunable. D4 (Minor): added [HARD] to
  REQ-OA-011/OA-012 (rich-library-metadata directive). D5 (Minor): glossary-defined
  "daypart mandate" as the STRUCTURAL rail only (existence/boundary), explicitly NOT a
  fixed energy/creative prescription; REQ/AC-OA-005 reworded to match. D6 (Minor): made
  REQ-OA-003a the SOLE hard no-repeat/artist-rail statement and reduced REQ-OA-003 to
  the soft separation layer. D7 (Minor): reframed REQ-OG-003 to the feeds/APIs-first
  test, dropping the vague "efficiently." Added Radiooooo (app.radiooooo.com) as a
  curation INSPIRATION (time/place-themed shows; NOT a data feed) in REQ-OB-002 +
  research.md. NEW (relayed, confirm with user — R-O-20): REQ-OA-009 local
  time/date/location awareness (Tórshavn, `Atlantic/Faroe`, DST-correct dayparting,
  weekday/weekend/season context, local time references) + NFR-O-9 timezone/clock
  correctness. ALSO NEW (relayed, confirm with user — R-O-21): REQ-OB-006 persisted
  timestamped play-history with show association (recorded from the start; 'unscheduled'
  when no show active) + REQ-OB-007 website renders per-show/episode tracklists + an
  unscheduled "songs played" timeline (both extend CORE-001's now-playing/play-log +
  self-served website). Net: +4 REQ (OA-003b, OA-009, OB-006, OB-007) and +1 NFR
  (NFR-O-9). Total: 61 REQ + 9 NFR = 70, 1:1 REQ↔AC preserved.
- 2026-06-22 (v0.3.0): Two more website/listener-interaction requirements (relayed,
  confirm with user — R-O-22). REQ-OB-008: AI-authored SHOW DESCRIPTIONS/blurbs
  displayed on the website's show lineup/schedule, updating as the AI plans/evolves the
  schedule (extends CORE-001 self-served website + schedule surface). REQ-OB-009:
  listener CONTACT/FEEDBACK channel (website form → brain POST endpoint) ingested as a
  listener signal feeding the EXISTING CORE-001 listener-signals contract (REQ-D-008)
  that OPS-004 already consumes; the AI reads + acts on feedback as it wishes (full
  autonomy), with the [HARD consistency] guard that feedback is human-curatorial input
  the AI WEIGHS, never an engagement/appeal/popularity-optimization target (aligned with
  the smart-and-human / anti-appeal ethos, REQ-OF-004 / NFR-O-7), and untrusted-input
  validation per CORE-001. Net: +2 REQ (OB-008, OB-009). Total: 63 REQ + 9 NFR = 72,
  1:1 REQ↔AC preserved.
- 2026-06-22 (v0.4.0): writ-fm-validated reliability/editorial additions + concrete
  metadata sources + mixing/rotation/acquisition refinements (relayed, confirm with
  user — R-O-23/24/25). writ-fm batch: REQ-OE-012 pre-stocked ready buffer +
  serialized generators (+ NFR-O-10 no under-run from generation latency); REQ-OD-007
  append-only event ledger (idempotent IDs) + REQ-OD-008 director diary for cross-run
  continuity; REQ-OA-013 editorial run-mode selection per loop
  (maintenance/responsive/continuity/special/quiet); REQ-OF-005 anti-AI-slop talk
  discipline + REQ-OF-006 script quality gate with regeneration; REQ-OC-006
  no-self-imitation (recent output is an avoid-list, never an in-context example).
  Metadata sources concretized in REQ-OA-011 (MusicBrainz API + TheAudioDB API +
  embedded tags + audio analysis + `%ARTIST% - %TITLE%` filename-parse fallback).
  Mixing/rotation/acquisition batch: REQ-OA-014 context-aware transition/mixing
  (DJ-mix+beatmatch+EQ for club/dance via BPM/key metadata; clean crossfade for regular)
  + NFR-O-11 no-sharp-cutoffs baseline; REQ-OA-003c artist-frequency limit (strengthens
  the OA-003a rotation rail); REQ-OH-006 acquisition accounting + bounded download queue
  (track library size + pending count, throttle by size/disk/queue depth — ties to
  OH-001/OH-004). Noted-not-changed: writ-fm GENERATES music (ACE-Step) — we ACQUIRE
  via slskd (kept); writ-fm shells the Claude CLI — we use claude-agent-sdk on the
  subscription (structured, same no-billing spirit). Net: +10 REQ (OA-003c, OA-013,
  OA-014, OC-006, OD-007, OD-008, OE-012, OF-005, OF-006, OH-006) and +2 NFR (NFR-O-10,
  NFR-O-11). Total: 73 REQ + 11 NFR = 84, 1:1 REQ↔AC preserved.

---

## 1. Overview & Background

### 1.1 Why this SPEC — "the station must be ALIVE, not a dead auto-DJ"

SPEC-RADIO-CORE-001 delivers continuous music playout, a 24/7 scheduler with
shows/personas, a self-controlled website, and an LLM program-director loop (no
voice). SPEC-RADIO-VOICE-002 adds the on-air spoken-host voice layer (Kokoro/Piper
English, teldutala.fo Faroese, live music ducking). Together they can make hosts
talk over music — but they do NOT, on their own, give the station CHARACTER: a
self-planned 24h programme, themed shows, informed commentary, recurring bits, a
point of view, station imaging, or news.

This SPEC adds that character. Its prime directive (REQ-OF-001):

> The station must be ALIVE, engaging, funny, thoughtful, interesting — hosts with
> personalities, themed shows, talk, commentary, recurring bits, a point of view. It
> is explicitly NOT a dead/quiet auto-DJ shuffling a liked-songs list.

A critical nuance the requirements encode: pure music-only stretches ARE fine when
the AI schedules them — the AI plans the talk↔music balance itself (REQ-OF-003). The
failure mode this SPEC prevents is a station with NO character / NO programming at
all, NOT the presence of music blocks.

### 1.2 The six confirmed user directives this SPEC implements

This SPEC is the first-class home for six confirmed user directives. Each is
reflected as one or more requirements:

1. **Liveliness Principle [HARD]** — alive, not a dead auto-DJ; music blocks are
   fine when the AI schedules them (Group OF, esp. REQ-OF-001/003).
2. **Autonomous Program Director** — the AI plans + schedules its own 24h
   programming (Group OA).
3. **Research-Driven Show Prep [HARD]** — invent themes, web-research into tracklist
   + banter/facts; two LLM modes (Group OC).
4. **Self-Learning Radio Craft [HARD]** — a persistent, self-improving playbook the
   station builds and refines 24/7 (Group OD).
5. **Self-Produced Imaging / Jingles [HARD]** — the AI creates its own station
   imaging (Group OE).
6. **Full Autonomy** — complete creative + operational control; human out of the run
   loop (the cross-cutting Creative Autonomy Principle, Section 1.3).

Plus directives relayed during authoring (folded in, to be user-confirmed — see
Section 16 R-O-11/R-O-12/R-O-16 and the return-summary caveat):

- **(A) Music-history / cultural-societal awareness + APOLITICAL** — a knowledge +
  curation DIMENSION of Groups OC and OD, with a [HARD] non-political constraint
  (REQ-OF-004).
- **(B) Autonomous newscasting** — a new Group OG; supersedes CORE-001's news
  exclusion for regular scheduled news; Faroese angle.
- **(C) Measured self-change** — playbook/format/persona evolution is gradual,
  rate-limited, and stability-preserving (REQ-OD-006), modeled on the
  evolution-safety framework in the design constitution.
- **(D) Reference-station emphasis** — KEXP, P3 Dans, and P3 Mix are weighted heavily
  in the persona/format patterns the AI learns from (REQ-OB-002, REQ-OD-002).
- **(E) No-repeat / least-recently-played rotation [HARD]** — explicit variety rule
  (REQ-OA-003a) under the separation solver.
- **(F) Rich library metadata enrichment** — correct tags + genre/mood/BPM/key/
  energy/year + a queryable catalog so the AI knows its catalog and can build genre
  nights and BPM/key-matched DJ-sets (REQ-OA-010/011/012).
- **(G) Self-reasoning autonomy reaffirmed** — fully self-directed; no human in the
  run loop (Section 1.3).

### 1.3 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits SPEC-RADIO-CORE-001 Section 1.3 verbatim in intent and does NOT
redefine it. Every requirement here:

- [HARD] GRANTS the AI authority + supplies tools/inputs/context + defines safety
  rails. It MUST NOT prescribe fixed creative content, scripts, playlists, weights,
  scoring formulas, copy, mandated genre mixes, or a fixed creative method. Mirror
  the CORE-001 REQ-D phrasing: "the system SHALL delegate X to the LLM" + "the LLM
  MAY decide Y."
- Treats all cadence defaults (ID/hour, sweeper every 2-4 songs), the imaging
  taxonomy length rules, rotation category schema, separation windows, daypart
  mandates, and news cadence as TUNABLE config the AI may override/evolve on its own
  planning cadence (mirroring CORE-001 REQ-D-006). The only FIXED rails are
  safety/engineering (Section 1.4).
- Keeps the human OUT of the run loop. No manual approval steps, operator actions, or
  human-in-the-loop gates in normal operation (CORE-001 Operating Model). The human
  is a tool/infrastructure provider only.
- [HARD] **Self-reasoning autonomy.** The AI reasons through its own decisions and
  makes its own choices — there is NO human present to make them. Every requirement
  assumes fully self-directed decision-making; no requirement implies waiting for,
  prompting, or deferring to human input in the run loop. Even the self-imposed
  stability rails (REQ-OD-006) are the AI's own discipline, not a human gate.
- Keeps the "smart and human, not a corporate business" ethos: no monetization, no
  ad-reads, no engagement/appeal/popularity optimization. Appeal-maximization is an
  explicit ANTI-GOAL (CORE-001 Operating Ethos).

### 1.4 Fixed engineering/safety rails (the only hard constraints on autonomy)

These are the ONLY things this SPEC fixes; everything creative is the AI's call:

- **Never a single point of silence.** Continuous operation (CORE-001 Section 1.2 +
  Group C) is the prime safety rail and lives BELOW the AI. No OPS decision may
  silence the stream: on render failure / empty pool / brain timeout, fall back to a
  music track or a cached evergreen ID; the brain returns empty-200 only as a last
  resort; Liquidsoap `mksafe` covers the gap. A brief interruption on restart is
  acceptable; this SPEC does NOT add zero-gap failover machinery.
- **One shared loudness constant.** Every aired item — song, imaging clip, talk,
  news — is normalized to -16 LUFS / -1.5 dBTP (Icecast target). Songs and imaging
  MUST sit at the same perceived level (REQ-OE-005, NFR-O-3).
- **Hard rotation separation.** Same-track no-repeat window and artist spacing are
  hard rails (REQ-OA-003).
- **Top-of-hour station ID** is a reserved slot (REQ-OE-008).
- **Self-cleared-imaging gate.** Only self-generated (procedural / Stable Audio 3) or
  strictly-CC0 first-party audio is auto-published as on-air imaging (REQ-OE-010).
- **Single clean single-track served items** (avoids the savonet #1074 post-jingle
  stall) (REQ-OE-009).
- **Apolitical + factual + grounded.** News and commentary are factual and
  non-partisan (REQ-OF-004, REQ-OG-005).
- **Subscription auth + quota discipline.** `ANTHROPIC_API_KEY` unset; OAuth via
  mounted `~/.claude`; respect the 5h rolling quota; two LLM modes (NFR-O-1/2).

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001 and SPEC-RADIO-VOICE-002 and is built on
top of them. It references their subsystems by CONCEPT (and, where the cited
requirement is a deliberately stable invariant, by number) rather than re-specifying
them.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any CORE-001 or VOICE-002
requirement. Where it needs a predecessor behavior it consumes it. Where a
predecessor requirement and an OPS requirement could conflict (e.g. stream continuity
vs. airing an imaging/news item), the predecessor's continuous-operation behavior
WINS.

Consumed CORE-001 concepts:
- **Pull-based playout** (Liquidsoap `request.dynamic.list` + Icecast; the brain's
  `Picker.pick()` → `NextItem(kind=...)` seam; `/api/next` < 1s, never blocks on
  synthesis). OPS adds `kind="imaging"` and `kind="news"`. No Liquidsoap change.
- **Continuous operation / never-dead-air failover** (CORE Group C). OPS MUST NOT
  re-engineer it; OPS decisions sit above it.
- **Runtime-extensible, system-owned persona/host model** + **MAX 2 HOSTS PER SHOW**
  (CORE-001 REQ-B-011, a deliberately stable invariant, cited by number on purpose).
- **24h scheduler / shows / segments / talk-slot placeholders** (CORE Group B). OPS
  enriches scheduling; it does not fork the schedule store.
- **Minimal no-repeat / artist-spacing rotation window** (CORE-001 REQ-B-006). OPS's
  separation solver (REQ-OA-003) EXTENDS/SUPERSEDES it — see the precedence note in
  REQ-OA-003.
- **LLM program-director loop** + async/never-block-the-queue fallback + autonomous
  self-initiated cadence (CORE REQ-D-006/007). OPS extends this loop with the two
  LLM modes, show-prep, playbook, imaging, and news.
- **Seed reference dataset** (non-binding), **listener-signals input contract**
  (REQ-D-008, human-curatorial, never an optimization target), **self-controlled
  website**, **config + secrets discipline**, **health/status surface**.

Consumed VOICE-002 concepts:
- **Provider-agnostic TTS interface** (Kokoro/Piper English, ElevenLabs optional,
  teldutala.fo Faroese). OPS imaging + news call the SAME TTS layer; OPS does NOT
  redefine TTS.
- **Language routing** (English ↔ Faroese; English via Kokoro/Piper/ElevenLabs;
  Faroese via teldutala.fo, adult voices `Hanna22k_NT`/`Hanus22k_NT` only).
- **Live-stream music ducking** (VOICE-002 Group V-C). NOTE: OPS imaging ducking
  (REQ-OE-002) is OFFLINE clip-baking — a static bed ducked under voice to bake a
  self-contained clip file — and is DISTINCT from VOICE-002's live-stream ducking.
  Neither redefines the other.
- **Faroese single-host cap** (VOICE-002 REQ-V-D-005) for Faroese-language shows.

### Downstream SPECs that will depend on OPS-004 (forward references, not built here)

These are distinct future subsystems with their own SPECs; OPS-004 owns only the
seams/scheduling they will attach to. Full design notes are in the Section 17 roadmap.

- **SPEC-RADIO-CALLIN-003** (live listener call-in) will attach its scheduled call-in
  windows to OPS-004's scheduling group (Group OA — format clock + special-show
  windows). OPS-004 owns the scheduling slot; CALLIN-003 owns the live-caller behavior
  (phone via Twilio/SIP, messaging via WhatsApp/Messenger/Instagram DMs, Whisper STT,
  short delay + live AI moderation, in-character persona). It attaches to VOICE-002's
  call-in seam (REQ-V-F-001).
- **SPEC-RADIO-SOCIAL** (autonomous Instagram + messaging management) will feed
  listener DMs/comments into CORE-001's listener-signals contract (REQ-D-008), which
  OPS-004 already consumes; the social subsystem itself (read/reply + autonomous
  content creation/posting via the official Instagram Graph API) is out of scope here.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Program director (PD)** | The autonomous LLM role that plans and schedules the 24h programme: clock/format, rotation, dayparting, talk↔music balance, imaging cadence, shows, segues, news. |
| **Format clock / clock wheel** | A per-daypart 60-minute hour-skeleton (data, not code): ordered slots typed song-category / imaging / talk / news / id / stopset / request / special. The AI resolves each slot to a concrete item on each pull. |
| **Daypart** | A time-of-day block (e.g. Morning Drive / Midday / Afternoon Drive / Evening / Overnight) anchored to LOCAL Faroe time (REQ-OA-009), with its own clock set, persona register, and energy curve that the AI authors. |
| **Daypart mandate** | The STRUCTURAL rail of a daypart ONLY: that the daypart exists and where its boundary sits on the local clock (REQ-OA-009). It is NOT a fixed energy/tone/creative prescription — the energy curve, persona register, and content within a daypart are entirely the AI's creative call (REQ-OA-005). "Mandate" = the boundary/existence rail, not a content rule. |
| **Rotation category** | A track's life-cycle class (Power Current / Secondary Current up-or-down / Power Recurrent / Secondary Recurrent / Gold-Stay) governing how heavily it rotates. |
| **Separation rules** | Anti-repetition constraints: hard same-track no-repeat + artist spacing; soft tempo/energy/vocalist-gender/era/sound-code spacing. |
| **Persona register** | A presentation mode the AI switches between by daypart/show: CHR-hype, curatorial-connoisseur, or continuous-mix. |
| **Show-prep / research** | An occasional richer LLM call WITH web search (Claude Agent SDK web tools) that produces a show plan: tracklist + per-segment talking points / facts / context. |
| **Quick-curation** | The frequent, cheap LLM call with a minimal prompt and tools OFF that picks the next track(s) or next imaging type. |
| **Playbook** | The station's own persistent, self-improving knowledge base of radio craft, music history, cultural/societal context, and newscasting craft. Seeded at plan time; refined at runtime 24/7. |
| **Imaging** | The family of short produced audio elements branding the station between songs: station ID, sweeper, liner, stager, promo, stinger/bumper, show open/close, named-segment ident, news signature. |
| **Imaging clip** | A finished, loudness-normalized produced imaging audio file in the clip library, served like a track. |
| **Imaging pipeline** | The 6-stage production path: concept JSON → TTS voice → ffmpeg bed mix + offline ducking + fades + stingers → two-pass loudnorm → encode → clip library → pull insertion. |
| **Music bed** | The background audio under a voiced imaging clip; sourced (in legal-safety order) from procedural synthesis, local generative (Stable Audio 3), or first-party CC0. |
| **License ledger** | A per-clip record of source, license, attribution flag, AI-generated flag, and performance-rights status, gating what may be auto-published as imaging. |
| **Newscast** | A spoken news segment: a short headline read from trusted sources, lead-story-first, optionally prefixed by a news signature, in the appropriate language. |
| **News source list** | The AI-maintained, AI-evolved set of trusted news sources (RSS/Atom feeds, news APIs, permitted scraping) it aggregates from. |
| **Breaking-news interrupt** | An OPTIONAL/advanced behavior: inserting a major story out of cadence at a safe boundary (end of current song), then resuming the clock. |
| **CLIPS_DIR** | The clip-library directory (sibling to the music dir) mounted into both the brain and Liquidsoap containers, holding produced imaging/news clips. |
| **`kind`** | The brain's `NextItem` discriminator; CORE-001 ships `music`/`talk`; OPS adds `imaging` and `news`. |
| **Two LLM modes** | (A) cheap quick-curation, minimal prompt, tools OFF, batched; (B) richer show-prep/research/news, web tools ON, occasional. |
| **Catalog** | The accurate, queryable library record per track: artist/title/album + genre, mood, BPM, key, energy, year, rotation category, and play history; the foundation the program director curates genre nights and DJ-sets from. |
| **Enrichment** | Correcting/normalizing tags and adding genre/mood/BPM/key/energy/year via embedded tags, audio analysis, and external metadata or LLM knowledge. |
| **Measured self-change** | The discipline that identity-affecting evolution (playbook rules acted on, format defaults, personas, segment roster) is gradual, rate-limited, cooldown-gated, and canary-checked so the station's identity stays consistent while still improving. |
| **Library housekeeping** | Organizing/sorting imported files into a clean managed folder structure (e.g. by artist/album or genre) instead of slskd's raw download dirs. |
| **Disk-space management** | Monitoring free disk and never running out — capping library size and/or evicting least-valuable tracks (least-played, lower-quality duplicates) when low. |
| **Bandcamp hook** | A user-facing "buy this" recommendation channel (notification/webhook/log/push, TBD) that recommends the human PURCHASE music the AI cannot obtain via slskd/yt-dlp; never an autonomous purchase. |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group OA — Program Director & 24h Scheduling.** Autonomous schedule planning,
  format clock/wheel, rotation categories, separation solver (incl. artist-frequency
  limits), dayparting, talk↔music balance, imaging cadence direction, editorial run-mode
  selection, context-aware transition/mixing style, never-single-point-of-silence above
  the inherited failover.
- **Group OB — Shows & Host Personas.** Themed shows, hosts with character, show
  construction, persona-register switching, named recurring segments, a persisted
  timestamped play-history rendered on the website (per-show tracklists + unscheduled
  timeline), AI-authored show descriptions on the website schedule, and a listener
  contact/feedback channel feeding the listener-signals contract. Builds on CORE-001
  self-staffing + now-playing/play-log + self-served website + listener-signals contract
  (REQ-D-008), and VOICE-002 personas.
- **Group OC — Research-Driven Show Prep.** Invent themes; two LLM modes; web-research
  into tracklist + banter/facts; musical/cultural/historical depth; anti-hallucination.
- **Group OC — Research-Driven Show Prep.** (above) plus no-self-imitation (recent
  output is an avoid-list, never an in-context example).
- **Group OD — Self-Learning Radio-Craft Playbook.** Persistent knowledge base
  (radio craft + music history + cultural/societal context + newscasting craft) backed
  by an append-only event ledger + director diary; plan-time seeding; runtime
  refinement loop applied to programming.
- **Group OE — Self-Produced Imaging & Jingles.** The 6-stage pipeline, taxonomy,
  cadence, offline ducking, loudness-matching, anti-overproduction, clip library,
  pull insertion, layered bed sourcing + license gate, and a pre-stocked ready buffer
  with serialized generation.
- **Group OF — Liveliness & Quality Constraints.** Alive-not-dead as a checkable
  property; music-blocks-are-fine; talk/music balance is the AI's call;
  anti-shallow-banter; anti-AI-slop discipline + script quality gate; apolitical.
- **Group OG — News & Newscasting.** Autonomous how/when; self-discovered/aggregated
  trusted sources; factual grounded reads; Faroese angle; optional breaking-news
  interrupt; learned newscasting craft.
- **Group OH — Library Management & Acquisition Policy.** Play-from-library balance,
  slskd-first / yt-dlp-last acquisition quality preference, organized library folder
  structure, disk-space management (never run out), acquisition accounting + bounded
  download queue, Bandcamp purchase-recommendation hook. Extends CORE-001's library &
  acquisition group.
- Plus **NFRs** (Section 15) and **Risks** (Section 16).

### 4.2 Out of scope (explicitly deferred)

- **Full live listener call-in** — telephony/VoIP/STT/two-way/caller mixing
  (SPEC-RADIO-CALLIN-003; VOICE-002 owns the seam).
- **Instagram / social** (SPEC-RADIO-SOCIAL).
- **Finance / monetization** (SPEC-RADIO-FINANCE). Zero commercial motive here.
- **Full listener analytics product** — beyond CORE-001's typed listener-signals
  input contract (REQ-D-008) and operational health/logging (SPEC-RADIO-ANALYTICS).
- **Elaborate self-staffing org apparatus** — rich hiring workflow, multi-agent org,
  external agents (SPEC-RADIO-ORG). OPS consumes CORE-001's runtime-extensible model
  as-is.
- **Music-rotation broadcast/PRO licensing** — the main-rotation performance-rights
  obligation is a separate, larger matter; flagged (R-O-10) and left out of scope.
  CORE-001 gates acquisition off by default; this build is private/experimental.
- **Multi-region / horizontally scaled playout** (single cloud server).
- **Languages beyond English + Faroese** for talk/news (Swedish-language reads route
  to English/Faroese voices per VOICE-002; native Swedish TTS is a future extension).
- **TTS engine internals, live-stream ducking mechanics, persona-model internals** —
  owned by VOICE-002 / CORE-001 and consumed, not redefined.
- **Real beatmatched ASOT-grade continuous-mix flow requiring BPM/key/energy
  analysis** — adjacency (REQ-OA-006) is in scope, but true beatmatching depends on a
  later analysis phase (R-O-9); this SPEC does not claim ASOT-grade flow.
- **Ramp / talk-over ("hitting the post")** — Liquidsoap-layer voice-tracking, not a
  produced clip (VOICE-002 territory).

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain = Python `radio-brain.py` using Claude via the MAX SUBSCRIPTION
  through the official `claude-agent-sdk`.** `ANTHROPIC_API_KEY` MUST be UNSET (if
  set, it bills credits and fails); auth is via mounted `~/.claude` OAuth with
  auto-refresh.
- [HARD] **Two LLM modes.** Cheap quick-curation (minimal prompt, tools OFF, batched)
  for the frequent path; richer show-prep/research/news (Claude Agent SDK web tools
  ON) for the occasional path. Respect the 5-hour rolling subscription quota; batch
  calls.
- [HARD] **Pull-based playout, no Liquidsoap change.** Liquidsoap PULLS each next
  item (song OR imaging OR news clip) from the brain's HTTP `/api/next`. OPS adds
  `kind="imaging"`/`kind="news"` to the existing `NextItem` seam. `/api/next` stays
  < 1s and never blocks on synthesis; all produced audio is PRE-RENDERED and cached
  by the async director loop.
- [HARD] **Music acquired via slskd (+ yt-dlp fallback)** — owned by CORE-001,
  config-gated, consumed here for gap-driven acquisition.
- [HARD] **Local TTS reused from VOICE-002** — Kokoro/Piper English, teldutala.fo
  Faroese; language routing per VOICE-002 Group V-D. OPS does not redefine TTS.
- [HARD] **ffmpeg + sox for imaging production.** ffmpeg already in stack; add sox.
  Stable Audio 3 Small (CPU, config-gated) optional for generative beds.
- [HARD] **One shared loudness constant** — -16 LUFS / -1.5 dBTP for every aired
  item (songs, imaging, talk, news).
- [HARD] **Self-cleared imaging only** — auto-published on-air imaging beds are
  self-generated (procedural / Stable Audio 3) or strictly first-party CC0.
- [HARD] **Apolitical + factual.** The station is non-political; news is factual,
  trusted-sourced, grounded, and attributed.
- [HARD] **Continuous operation is the prime rail** — no OPS decision is a single
  point of silence; the inherited failover (CORE Group C) is not re-engineered.
- [HARD] **Inherited ethos** — human out of run loop; no monetization; no
  appeal/engagement optimization; "smart and human, not a corporate business."

---

## 6. Requirement Group OA — Program Director & 24h Scheduling

Priority: High.

### REQ-OA-001 — Autonomous 24h programme planning (Event-driven + self-scheduled)

When the daemon starts OR on the program director's self-scheduled planning cadence
(inherited from CORE-001 REQ-D-006), the system shall let the LLM program director
autonomously plan the station's 24h programme — the arrangement of talk shows, music
blocks, themed hours, and imaging across the day — without any human prompt and
without prescribing the creative arrangement.

**Acceptance criteria:** see acceptance.md AC-OA-001.

### REQ-OA-002 — Format clock / clock-wheel engine (Ubiquitous) [documented compound]

[Documented compound requirement: two tightly-coupled obligations — REPRESENT the
clock structure and RESOLVE a slot from it — kept together because the resolver is
meaningless without the structure and both share one AC. Verified intentionally
compound, not an oversight.]

(a) The system shall represent the hour structure as data-driven per-daypart format
clocks (ordered, typed slots: song-category / imaging / talk / news / id / stopset /
request / special). (b) The system shall resolve the current slot to one concrete item
on each playout pull. The clock variants and slot contents are the AI's to author and
evolve (TUNABLE); the slot ORDER within an active clock, the reserved top-of-hour ID
slot, and daypart boundaries are the FIXED rails.

**Acceptance criteria:** see acceptance.md AC-OA-002.

### REQ-OA-003 — Soft separation-rule scheduler (State-driven) — supersedes CORE-001 REQ-B-006

While selecting the next song (within the hard variety rail of REQ-OA-003a), the
system shall apply SOFT separations — tempo / energy / vocalist-gender / era /
sound-code spacing — as a scoring layer the AI may weigh and relax, choosing the
best-scoring legal candidate. This requirement governs ONLY the soft separation
layer; the hard same-track no-repeat and artist-spacing rails are stated solely by
REQ-OA-003a, and the empty-legal-set fallback is REQ-OA-003b.

[Precedence] This requirement EXTENDS and SUPERSEDES CORE-001 REQ-B-006's minimal
no-repeat/artist-spacing window by adding the soft-separation scoring layer on top of
it. Where both could apply, the OPS separation layer (REQ-OA-003 + REQ-OA-003a) is the
tighter authority; the hard same-track/artist rails are preserved. CORE-001 is NOT
modified.

**Acceptance criteria:** see acceptance.md AC-OA-003.

### REQ-OA-003a — No-repeat / artist-separation / least-recently-played rotation (State-driven) [HARD]

While selecting the next song, the system shall NOT play the same song repeatedly: it
shall honor a configured no-repeat window per track, enforce artist/title separation,
and bias selection toward least-recently-played eligible tracks so the rotation favors
variety. [HARD] Repetition within the no-repeat window is prohibited. This is the SOLE
statement of the hard no-repeat / artist-separation rail (the soft layer is REQ-OA-003;
the empty-set fallback is REQ-OA-003b), and is the explicit OPS-level statement of the
music engine's existing recent-window + least-recently-played picker (CORE-001
REQ-B-006).

**Acceptance criteria:** see acceptance.md AC-OA-003a.

### REQ-OA-003b — Empty-legal-set graceful relaxation (Unwanted) [HARD]

If no candidate satisfies the soft separations (REQ-OA-003) — e.g. a thin category or
request pressure — then the system shall widen the soft window or borrow from an
adjacent category and log the relaxation, rather than stall the queue or violate the
hard no-repeat / artist rails (REQ-OA-003a); continuity wins (REQ-OA-008). The hard
rails are never relaxed; only the soft layer is.

**Acceptance criteria:** see acceptance.md AC-OA-003b.

### REQ-OA-003c — Artist-frequency limit (State-driven) [HARD]

While selecting songs, the system shall enforce ARTIST-FREQUENCY limits beyond the
no-repeat-track rail (REQ-OA-003a): the same artist shall not play too often — a
configured minimum gap between same-artist plays and/or a maximum number of plays per
artist within a rolling window. This strengthens the hard rotation rail so a single
artist cannot dominate the log; the gap/window values are TUNABLE config, and the limit
is a hard rail relaxed only under the empty-legal-set degradation (REQ-OA-003b) with
logging.

**Acceptance criteria:** see acceptance.md AC-OA-003c.

### REQ-OA-004 — Rotation categories & rotation-rate management (Event-driven)

When managing the library for rotation, the system shall let the AI classify tracks
into rotation categories (e.g. Power Current / Secondary / Recurrent / Gold-Stay) and
autonomously promote, demote, and rest titles so each category's turnover matches the
AI's intended play frequency; the category schema and target frequency bands are
TUNABLE config the AI may evolve. No taste/coherence match is enforced (consistent
with CORE-001 REQ-D-002).

**Acceptance criteria:** see acceptance.md AC-OA-004.

### REQ-OA-005 — Dayparting & energy-flow control (State-driven)

While the LOCAL Faroe wall clock (REQ-OA-009) is in a given daypart, the system shall
let the AI switch the active clock set, persona register, and within-hour energy curve
for that daypart. Only the daypart MANDATE — its existence and boundary on the local
clock (a structural rail per the Glossary, NOT a fixed energy/creative prescription) —
is fixed; the energy ordering, tone, and register choice within a daypart are entirely
the AI's call.

**Acceptance criteria:** see acceptance.md AC-OA-005.

### REQ-OA-006 — Segue / adjacency decision (Event-driven)

When choosing the next song's adjacency, the system shall let the AI decide track
adjacency for flow (tempo/energy/key compatibility) and emit transition parameters
(crossfade length, cue points) for the playout layer; the "no vocal-over-vocal" guard
and crossfade mechanics are FIXED rails in the playout layer. True beatmatched
continuous-mix flow depending on BPM/key/energy analysis is a later phase (R-O-9) and
is not claimed here.

**Acceptance criteria:** see acceptance.md AC-OA-006.

### REQ-OA-007 — Imaging & ID cadence direction (Event-driven)

When the active clock reaches an imaging or ID slot, the system shall let the AI
decide which imaging element airs (type, copy, wet/dry, language) and shall trigger
the imaging production pipeline (Group OE) to produce it; the top-of-hour ID slot is
reserved (REQ-OE-008) and cadence positions are TUNABLE defaults the AI may evolve.

**Acceptance criteria:** see acceptance.md AC-OA-007.

### REQ-OA-008 — Scheduling decisions never a single point of silence (Unwanted) [HARD]

If a scheduled item (imaging, news, talk, or a selected song) is unavailable, fails
to render, or the program-director decision is slow/errored, then the system shall
fall back to an available music track or a cached evergreen imaging clip so the
stream continues; no OPS scheduling decision shall be a single point of silence
(continuous operation, inherited from CORE-001 Group C, wins).

**Acceptance criteria:** see acceptance.md AC-OA-008.

### REQ-OA-009 — Local time / date / location awareness (Tórshavn, Faroe Islands) (Ubiquitous) [HARD]

The system shall be aware of the current LOCAL time and date for its location —
Tórshavn, Faroe Islands, timezone Atlantic/Faroe (UTC+0 winter / UTC+1 summer,
WET/WEST) — and the program director shall schedule and program accordingly:
- Dayparting (morning / daytime / drive / evening / overnight) is anchored to REAL
  LOCAL FAROE time, not UTC (DST-correct).
- The AI is aware of the date, day-of-week (so it may differentiate weekday vs weekend
  programming), and season/holidays for theming — how it uses them is the AI's call.
- Location-aware presentation: the station knows it is in Tórshavn (local greetings,
  local relevance), and time/date references in talk and news use local Faroe time.

The location and timezone are configurable (default `Atlantic/Faroe`); all
scheduling/clock decisions (Group OA) and time references (talk, news Faroese angle
Group OG) use this local timezone. The AWARENESS and correct local time are the rail;
WHAT the AI programs from that awareness is its creative call.

[Numbering note] This requirement fills what had been a reserved OA-009 gap; no
requirement was cut at any point — the gap was deliberate and is now occupied. The
traceability index (Section 18) reflects this.

**Acceptance criteria:** see acceptance.md AC-OA-009.

### REQ-OA-010 — Correct & normalize library metadata (Event-driven) — extends CORE-001 Group A

When a track is ingested or re-examined, the system shall correct and normalize its
metadata — fixing bad/garbled/filename-parsed tags (e.g. a typo like "Sly & the
Familt Stone") and reconciling artist/title/album against authoritative metadata —
so the catalog the program director reasons over is trustworthy. This EXTENDS
SPEC-RADIO-CORE-001's library group (metadata extraction + dedup); it does not fork
the library store.

**Acceptance criteria:** see acceptance.md AC-OA-010.

### REQ-OA-011 — Rich track enrichment (genre, mood, BPM, key, energy, year) (Event-driven) [HARD] [documented compound]

[Documented compound requirement: enrichment from three sources (embedded tags / audio
analysis / external metadata) is one coherent obligation with one AC; the three sources
are alternatives feeding the same enriched record, not separable requirements.
Verified intentionally compound. The user directive marks rich library metadata [HARD].]

When a track is ingested or re-examined, the system shall enrich it with genre, mood,
BPM, musical key, energy, and year, sourced from any of (a) embedded tags
(mutagen/ffprobe), (b) audio analysis for BPM/key/energy (librosa / aubio /
essentia-class tools), (c) external metadata APIs — the **MusicBrainz API**
(`musicbrainz.org/doc/MusicBrainz_API`) and **TheAudioDB API**
(`theaudiodb.com/free_music_api`) for genre/mood/tags/year (Discogs / Last.fm
optional) — and/or LLM knowledge, and (d) **filename parsing of the
`%ARTIST% - %TITLE%` convention as a reliable fallback** (downloads usually follow
that format) when tags/APIs are missing, so the AI truly knows its catalog.
Enrichment runs off the playout path and never blocks the stream. (This delivers the
BPM/key/energy data that R-O-9 previously deferred, enabling DJ-set adjacency
REQ-OA-006.)

**Acceptance criteria:** see acceptance.md AC-OA-011.

### REQ-OA-012 — Accurate, queryable, current catalog the PD curates from (Ubiquitous) [HARD]

The system shall maintain an accurate, queryable library catalog (artist, title,
album, genre, mood, BPM, key, energy, year, rotation category, play history) that the
program director uses to build genre nights, mood/energy arcs, and BPM-matched /
key-compatible DJ-sets, and shall keep the catalog current as acquisition adds music
(CORE-001 acquisition feeds it). [HARD] per the rich-library-metadata directive.

**Acceptance criteria:** see acceptance.md AC-OA-012.

### REQ-OA-013 — Editorial run-mode selection each loop (Event-driven)

When the director loop runs a planning cycle, the system shall let the AI select a RUN
MODE for that cycle from an editorial brief — e.g. maintenance (top up buffers / keep
rotation healthy), responsive (act on listener feedback / fresh signals), continuity
(advance running threads / themes), special (run a planned special show/segment), or
quiet (deliberately let music run, minimal talk) — so the station behaves with
deliberate editorial intent rather than "always generate." The mode set is TUNABLE and
the mode choice each loop is the AI's call; no fixed per-loop behavior is mandated.
(Validated against the writ-fm reference, which picks a run mode per loop from an
editorial brief.)

**Acceptance criteria:** see acceptance.md AC-OA-013.

### REQ-OA-014 — Context-aware transition / mixing style (Event-driven)

When sequencing tracks, the system shall let the AI pick a transition/mixing style by
show/daypart context and emit the corresponding transition parameters for the playout
layer:
- For CLUB/DANCE shows (e.g. ASOT-style, P3 Dans): DJ-style mixing — crossfade plus
  BEATMATCHING (tempo/BPM alignment) and high-pass/low-pass EQ filter blends, using the
  BPM/key metadata from REQ-OA-011/OA-012.
- For REGULAR shows: NO beatmatch/EQ-mix — clean transitions with at minimum a gentle
  crossfade / fade-out.
The AI decides the mode by context (TUNABLE); the transition mechanics execute in the
playout layer (Liquidsoap/ffmpeg). The beatmatch/EQ-blend specifics depend on accurate
BPM/key metadata (REQ-OA-011) and the in-flight mixing-implementation research, so the
build sophistication may phase in; the baseline no-sharp-cutoff transition (NFR-O-11) is
always required. Relates to the adjacency decision (REQ-OA-006).

**Acceptance criteria:** see acceptance.md AC-OA-014.

---

## 7. Requirement Group OB — Shows & Host Personas

Priority: High.

### REQ-OB-001 — Autonomous themed shows with character (Event-driven)

When the program director plans the schedule, the system shall let the AI invent and
schedule themed shows with distinct identity and character (e.g. a soul night, a
reggae specialist hour, a curator deep-cuts block, a hype morning show), using the
runtime-extensible, system-owned persona/host model (CORE-001), without a
human-authored show list and without prescribing the show's creative content.

**Acceptance criteria:** see acceptance.md AC-OB-001.

### REQ-OB-002 — Persona register switching (State-driven)

While a show is active, the system shall let the AI adopt a persona register
appropriate to the show/daypart — CHR-hype, curatorial-connoisseur, or
continuous-mix — that shapes talk frequency, tone, and selection style; the register
choice and its expression are the AI's call (no fixed register is mandated per slot).
The reference-station presentation patterns the AI may draw from are weighted toward
KEXP (curatorial-connoisseur, emphasized), Sveriges Radio P3 sub-formats P3 Dans
(dance/electronic) and P3 Mix (mixed), and the continuous-mix / specialist-selector
patterns of A State of Trance and BBC 1Xtra (Rodigan); BBC Radio 1 daytime is a
secondary CHR reference. Radiooooo (app.radiooooo.com), the "musical time machine"
(decade × country), is a CURATION INSPIRATION for time/place-themed shows and deep
global/historical curation (e.g. "1970s Brazil") — emulated as a format/curation idea
ONLY, NOT a data feed (the station sources its own music via slskd, REQ-OH-002). These
are reference patterns the AI learns from and emulates in spirit (REQ-OD-002), never
assets/names/data to copy (REQ-OB-004).

**Acceptance criteria:** see acceptance.md AC-OB-002.

### REQ-OB-003 — Host character respects the inherited host caps (Ubiquitous)

The system shall construct shows and assign hosts within the inherited host caps: at
most 2 hosts per show (CORE-001 REQ-B-011) and at most 1 host per Faroese-language
show (VOICE-002 REQ-V-D-005). This SPEC adds no new host-count authority; it consumes
those caps.

**Acceptance criteria:** see acceptance.md AC-OB-003.

### REQ-OB-004 — Recurring named segments as a show skeleton (Event-driven)

When building a show, the system shall let the AI define, run, evolve, and retire its
OWN recurring named segments (e.g. a host pick of the week, a listener-voted feature,
a most-requested slot, an emotional throwback, a new-local-artist slot), each with an
AI-authored segment ident and an AI-chosen selection rule; the segment roster is the
AI's to grow. The AI MUST invent its own segment names (no reference-station
trademarked names).

**Acceptance criteria:** see acceptance.md AC-OB-004.

### REQ-OB-005 — Special shows override and restore the clock (Event-driven)

When a scheduled special show's window begins, the system shall let the AI run an
override clock / genre pool / persona / imaging set for that window and shall restore
the default clock cleanly at the window's end; the AI owns the show's content and
sequencing, the override-and-restore mechanism is the FIXED rail.

**Acceptance criteria:** see acceptance.md AC-OB-005.

### REQ-OB-006 — Persisted timestamped play-history with show association (Event-driven) — extends CORE-001 now-playing/play-log

When a track airs, the system shall append a persisted play-history entry recording at
least `{track (artist/title), aired_at (local-time timestamp, REQ-OA-009),
show_or_episode_id OR 'unscheduled'}`; the show/episode association shall be recorded
from the start (set to 'unscheduled' when no show is active), so per-show tracklists
populate automatically once shows come online. This EXTENDS SPEC-RADIO-CORE-001's
now-playing / play-log surface; it does not fork the play-history store.

**Acceptance criteria:** see acceptance.md AC-OB-006.

### REQ-OB-007 — Website renders play history: per-show tracklists + unscheduled timeline (Event-driven) — extends CORE-001 self-served website

When the station serves its self-controlled website (CORE-001 Group E), the system
shall render the persisted play-history (REQ-OB-006) as (a) per-show/episode
TRACKLISTS — each scheduled show/episode listing the tracks it played, each with its
aired-at timestamp, grouped by show/episode — and (b) a "SONGS PLAYED" TIMELINE: a
timestamped log of songs played outside regular scheduled show hours (entries marked
'unscheduled'). This EXTENDS the self-served website; it does not fork it.

**Acceptance criteria:** see acceptance.md AC-OB-007.

### REQ-OB-008 — AI-authored show descriptions on the website (Event-driven) — extends CORE-001 self-served website

When the program director plans or evolves a show (Group OA / Group OB), the system
shall let the AI author a description/blurb for that show — what it is about, its
vibe/theme — and the self-controlled website (CORE-001 Group E) shall display the show
lineup/schedule WITH those descriptions. The descriptions are AI-authored (no fixed
copy) and update as the AI plans/evolves the schedule. This EXTENDS the self-served
website + the schedule surface; it does not fork them.

**Acceptance criteria:** see acceptance.md AC-OB-008.

### REQ-OB-009 — Listener contact / feedback channel feeding the listener-signals contract (Event-driven) — feeds CORE-001 REQ-D-008

When a listener submits feedback through the website's contact/feedback channel (a
feedback form POSTing to an endpoint on the brain), the system shall ingest that
feedback as a listener signal feeding the EXISTING typed listener-signals input
contract (CORE-001 REQ-D-008) that OPS-004 already consumes (Groups OD/OF). The AI MAY
read the feedback and act on it as it wishes — incorporating it into curation, show
ideas, or direction — with full autonomy and no human in the loop.

[HARD consistency] Feedback is human-curatorial input the AI WEIGHS, NOT an
engagement/appeal/popularity-optimization target. Consistent with CORE-001's
"smart and human, not a corporate business" ethos and appeal-maximization anti-goal
(REQ-OF-004 / NFR-O-7 and CORE-001 REQ-D-008), no path shall use feedback volume or
sentiment as a score to maximize, and the system shall NOT pander or chase popularity
in response to feedback. Untrusted-input handling (validation/sanitization of the POST
body) follows CORE-001's external-input discipline.

**Acceptance criteria:** see acceptance.md AC-OB-009.

---

## 8. Requirement Group OC — Research-Driven Show Prep

Priority: High.

### REQ-OC-001 — Two LLM modes (cheap curation vs. richer research) (Ubiquitous) [HARD]

The system shall provide two distinct LLM call modes: (A) a cheap quick-curation mode
with a minimal system prompt and tools OFF for frequent next-track / next-imaging
selection, batched; and (B) a richer show-prep / research mode WITH web search
enabled (Claude Agent SDK web tools) for occasional show planning, theme research,
and news. The frequent path MUST use mode A; mode B is reserved for occasional
research to respect the subscription quota.

**Acceptance criteria:** see acceptance.md AC-OC-001.

### REQ-OC-002 — AI invents and researches its own themes (Event-driven)

When the AI decides to build a themed show or segment, the system shall let the AI
invent the theme and research it via mode B, producing a show plan: a tracklist
(classics + deep cuts) plus per-segment talking points, artist/label/song history,
cultural context, anecdotes, and inspiration — so shows are informed, not shallow.
The theme and its treatment are entirely the AI's; no theme list is prescribed.

**Acceptance criteria:** see acceptance.md AC-OC-002.

### REQ-OC-003 — Show plan = tracklist + per-segment talking points (Event-driven)

When show-prep runs for a show, the system shall produce a structured show plan
binding the show's tracklist to per-segment talking points / facts, so the talk layer
(VOICE-002) and the scheduler consume informed, show-specific material rather than
generic patter; the plan's content is AI-authored.

**Acceptance criteria:** see acceptance.md AC-OC-003.

### REQ-OC-004 — Musical / cultural / historical research depth (Ubiquitous)

The system shall let the AI research and incorporate musical, cultural, and
historical depth into show prep — genre origins and movements, eras, artist
significance, song/label history, and the role music plays in society and human life
— so curation and commentary carry genuine "why this matters / why this song now"
context. This depth draws on the playbook's knowledge dimension (REQ-OD-005).

**Acceptance criteria:** see acceptance.md AC-OC-004.

### REQ-OC-005 — Research is grounded, not fabricated (Unwanted) [HARD]

The system shall not assert fabricated facts in show prep or banter; factual claims
about artists, tracks, history, and culture shall be grounded in the AI's verified
knowledge or in fetched mode-B research, and uncertain claims shall be avoided or
hedged rather than invented.

**Acceptance criteria:** see acceptance.md AC-OC-005.

### REQ-OC-006 — No self-imitation: recent output is an avoid-list, not an example (Unwanted) [HARD]

The system shall NOT feed its own recent episodes/segments/scripts to the LLM as
examples or style references to imitate. Recent output shall be used ONLY as a
topic/repeat AVOID-LIST (what was recently said/played, so the AI does not repeat
itself), never as in-context exemplars — preventing the model from imitating and
amplifying its own past output (model collapse / template fatigue). This applies to
show-prep (Group OC), talk-script generation (VOICE-002 scripts driven from here), and
the self-learning loop (Group OD).

**Acceptance criteria:** see acceptance.md AC-OC-006.

---

## 9. Requirement Group OD — Self-Learning Radio-Craft Playbook

Priority: High.

### REQ-OD-001 — Persistent self-built playbook knowledge base (Ubiquitous) [HARD]

The system shall maintain its OWN persistent, queryable knowledge base — the playbook
— capturing what it learns about running a radio station: how hosts work, what makes
a good show / a good DJ, what is interesting and important to tell listeners, pacing,
backselling, segues, and engagement craft. The playbook persists across daemon
restarts and is owned by the system (no human authoring required).

**Acceptance criteria:** see acceptance.md AC-OD-001.

### REQ-OD-002 — Plan-time seeding of the playbook (Event-driven)

When the playbook is first initialized (or re-seeded), the system shall seed it from
the plan-time research distilled in research.md (the autonomous-operations taxonomy
and the reference-station format patterns), giving the station a non-empty starting
body of radio craft it can immediately apply and then refine. The reference-station
patterns to study are weighted toward KEXP (emphasized) and the Sveriges Radio P3
sub-formats P3 Dans and P3 Mix, plus A State of Trance, BBC 1Xtra (Rodigan), and BBC
Radio 1. Where research.md did not cover P3 Dans / P3 Mix specifically, the runtime
self-learning loop (REQ-OD-003) shall study them as named references.

**Acceptance criteria:** see acceptance.md AC-OD-002.

### REQ-OD-003 — Runtime self-refinement loop (Event-driven + self-scheduled) [HARD]

When triggered by a runtime event or on its own self-scheduled cadence, the system
shall let the AI research radio craft (what hosts do, what makes good radio,
engagement, pacing) and distill new/updated entries into the playbook 24/7 with no
human input, so the playbook improves over time.

**Acceptance criteria:** see acceptance.md AC-OD-003.

### REQ-OD-004 — Playbook informs all programming (Ubiquitous)

The system shall make the playbook available as context to the program director, the
show-prep mode, the imaging-copy generation, and the newscast generation, so the
station's accumulated craft actually shapes its programming, imaging, banter, and
news — not just sits in storage.

**Acceptance criteria:** see acceptance.md AC-OD-004.

### REQ-OD-005 — Music-history / cultural-context + newscasting-craft knowledge dimensions (Ubiquitous)

The system's playbook shall include, as first-class knowledge dimensions, (a) music
history and cultural/societal context (genre origins, movements, artist significance,
the role of music in society and human life) and (b) newscasting craft (what makes a
good newscast, pacing, sourcing, fact-care), both continuously learned (REQ-OD-003)
and applied (REQ-OD-004, REQ-OC-004, Group OG).

**Acceptance criteria:** see acceptance.md AC-OD-005.

### REQ-OD-006 — Measured, rate-limited, stability-preserving self-change (State-driven) [HARD]

While refining the playbook or evolving its format/personas/identity, the system
shall change GRADUALLY and infrequently — it shall research and learn freely, but
shall apply identity-affecting changes (playbook rules it acts on, format/clock
defaults, persona definitions, recurring-segment roster) under a bounded change rate
with a cooldown between applied changes, so the station's identity and format feel
consistent over time rather than thrashing or over-tuning.

The mechanism is modeled on the evolution-safety framework in
`.claude/rules/moai/design/constitution.md` Section 5, adapted to a human-out-of-loop
station:
- **Rate limiter:** a bounded maximum number of applied identity-affecting changes per
  period, with a minimum cooldown between applied changes (TUNABLE config).
- **Canary check:** before applying an identity-affecting change, the AI evaluates it
  for regression against recent programming and rejects it if it degrades the station.
- **Contradiction detection:** a new learning that contradicts an existing applied
  rule is reconciled deliberately (old + new recorded), never silently churned.
- **Human-optional:** because the human is out of the run loop, no human approval is
  required; the AI is the decider. (The rails are self-imposed stability, not a
  human gate.)
This requirement bounds the velocity of REQ-OD-003's refinement and REQ-OA/OB
evolution; it does not cap how much the AI may LEARN, only how fast it CHANGES what
it acts on.

**Acceptance criteria:** see acceptance.md AC-OD-006.

### REQ-OD-007 — Append-only event ledger with idempotent IDs (Ubiquitous) [HARD]

The system shall persist the self-learning playbook's memory as an APPEND-ONLY event
ledger — events such as `listener_message`, `decision`, `listener_reaction`,
`diary_entry`, and `active_threads`, each with an idempotent ID so a replay or retry
does not duplicate an event. The ledger is the durable, ordered record the playbook and
director read back for continuity (it does not overwrite history; corrections are new
events). (Validated against the writ-fm reference's append-only ledger design.)

**Acceptance criteria:** see acceptance.md AC-OD-007.

### REQ-OD-008 — Director diary for cross-run editorial continuity (Event-driven)

When the director loop completes a cycle, the system shall let the director write a
DIARY entry (an editorial note on what it did / is thinking / running threads) into the
ledger (REQ-OD-007), so that on the next run — and across restarts — the director picks
up its own editorial through-line rather than starting cold. The diary is the AI's own
continuity memory; its content is the AI's call.

**Acceptance criteria:** see acceptance.md AC-OD-008.

---

## 10. Requirement Group OE — Self-Produced Imaging & Jingles

Priority: High.

### REQ-OE-001 — Imaging concept generation as structured JSON (Event-driven)

When the AI decides to produce an imaging element, the system shall let the AI
generate a structured-JSON brief — `{type, lang, voice, script, target_seconds,
production(dry|wet|showpiece), bed_id|bed_prompt, sfx[], fx, lufs_target}` — encoding
the AI's chosen type, copy, language, and production directives; the imaging taxonomy
and per-type length rules are TUNABLE context, not fixed copy.

**Acceptance criteria:** see acceptance.md AC-OE-001.

### REQ-OE-002 — Offline voice-over-bed mixing (ducking, fades, stingers) (Event-driven) [HARD wiring]

When producing a wet imaging clip, the system shall mix the TTS voice over a music bed
using ffmpeg, ducking the bed under the voice via `sidechaincompress` wired so the
VOICE is the sidechain key compressing the MUSIC (not the reverse), with fades
(`afade`) and optional stingers (`adelay`), keeping the voice at full level after the
mix. Dry pieces skip the bed.

[Distinction] This is OFFLINE clip-baking, DISTINCT from VOICE-002's live-stream
ducking; it bakes a self-contained clip file, it does not duck the live stream.

**Acceptance criteria:** see acceptance.md AC-OE-002.

### REQ-OE-003 — Procedural synthesis for stingers/sweeps/pips (Event-driven)

When the AI needs abstract imaging FX (stingers, whooshes, risers, beeps, sub-drops,
news pips), the system shall synthesize them procedurally via sox/ffmpeg
(`synth`/`aevalsrc`/`anoisesrc` + fades/reverb), producing public-domain-by-
construction audio with zero external assets and zero licensing exposure.

**Acceptance criteria:** see acceptance.md AC-OE-003.

### REQ-OE-004 — Generative + CC0 music-bed sourcing (Event-driven)

When the AI needs a musical bed beyond procedural synthesis, the system shall source
it (in legal-safety order) from local generative (Stable Audio 3 Small, CPU,
config-gated, pre-rendered + cached) or first-party CC0 libraries (FreePD/Pixabay),
selecting the layer per piece; generation/selection prompts and choices are the AI's.

**Acceptance criteria:** see acceptance.md AC-OE-004.

### REQ-OE-005 — Loudness normalization to the shared target (Event-driven) [HARD]

When an imaging clip is produced, the system shall normalize it via two-pass
`loudnorm` to the SAME shared target as the song catalog — -16 LUFS integrated,
-1.5 dBTP true-peak — so imaging never jumps out relative to music, talk, or news.

**Acceptance criteria:** see acceptance.md AC-OE-005.

### REQ-OE-006 — Clip library + metadata + encode (Event-driven)

When a clip is normalized, the system shall encode it to the stream codec at the
catalog's sample-rate/channels and register it in the clip library (CLIPS_DIR) with a
metadata sidecar (type, lang, duration, lufs, created_at, bed license), so the brain
can serve it on the next pull.

**Acceptance criteria:** see acceptance.md AC-OE-006.

### REQ-OE-007 — Pull insertion as `kind="imaging"` (Event-driven)

When the cadence policy says an imaging slot is due, the system shall return the
imaging clip from the brain's `Picker.pick()` as `NextItem(kind="imaging")` so
`/api/next` serves and commits it identically to a song, with no Liquidsoap change.

**Acceptance criteria:** see acceptance.md AC-OE-007.

### REQ-OE-008 — Top-of-hour station ID reserved (Ubiquitous) [HARD rail]

The system shall reserve a station-ID slot at/near the top of every hour and reliably
fill it with a station-ID clip; the AI authors the ID copy/treatment but the
top-of-hour ID slot itself is a FIXED identity rail. The ID MUST NOT claim a real
broadcast frequency the station does not hold.

**Acceptance criteria:** see acceptance.md AC-OE-008.

### REQ-OE-009 — Single clean single-track served items (Unwanted) [HARD]

The system shall not return a malformed or multi-track item from `/api/next`; each
served imaging/news/song item shall be a single clean single-track request (avoiding
the post-jingle next-song stall, savonet/liquidsoap #1074).

**Acceptance criteria:** see acceptance.md AC-OE-009.

### REQ-OE-010 — Self-cleared-imaging license gate + ledger (Unwanted) [HARD]

The system shall not auto-publish any imaging bed that is not self-generated
(procedural / Stable Audio 3) or strictly first-party CC0; the system shall maintain
a per-clip license ledger (source, license, attribution flag, AI-generated flag,
performance-rights status), and any bed of murkier rights is quarantined and not aired
unattended.

**Acceptance criteria:** see acceptance.md AC-OE-010.

### REQ-OE-011 — Anti-overproduction default (State-driven)

While producing imaging, the system shall default most IDs and liners to DRY (voice
only) and reserve wet/showpiece production for occasional use, so the station does not
feel slow/overproduced; this is a TUNABLE default the AI may evolve, not a hardcoded
ceiling.

**Acceptance criteria:** see acceptance.md AC-OE-011.

### REQ-OE-012 — Pre-stocked ready buffer + serialized generation (State-driven) [HARD]

While running, the system shall maintain a READY BUFFER of N-ahead pre-rendered talk
segments and imaging clips so that a Liquidsoap `/api/next` PULL is always served from
the buffer and NEVER blocks on TTS or LLM latency; generation is fully decoupled from
playout and runs in the async director loop. The system shall SERIALIZE heavy
generators — it shall not run multiple TTS/LLM renders concurrently — to bound RAM (a
single generation worker / queue, not parallel renders). The buffer depth N and the
serialization are TUNABLE config. (Validated against the writ-fm reference's
pre-stocked, generation-decoupled, serialized-generator reliability design.)

**Acceptance criteria:** see acceptance.md AC-OE-012.

---

## 11. Requirement Group OF — Liveliness & Quality Constraints

Priority: High.

### REQ-OF-001 — The station is ALIVE, not a dead auto-DJ (Ubiquitous) [HARD]

The system shall present as a LIVE, character-driven station — hosts with
personalities, themed shows, talk/commentary/recurring bits, and a point of view —
and shall NOT operate as a character-less auto-DJ that merely shuffles a track list
with no programming or identity.

**Acceptance criteria:** see acceptance.md AC-OF-001.

### REQ-OF-002 — Anti-shallow banter (Unwanted)

The system shall not produce shallow, generic, or repetitive filler banter; spoken
commentary shall draw on show-prep material (Group OC) and the playbook (Group OD) and
vary in structure to avoid template fatigue across the 24/7 stream.

**Acceptance criteria:** see acceptance.md AC-OF-002.

### REQ-OF-003 — Music-only stretches are valid when the AI schedules them (Ubiquitous)

The system shall treat AI-scheduled music-only stretches as valid programming; the AI
owns the talk↔music balance. No requirement mandates a minimum talk density, and the
absence of talk in an AI-planned music block is not a defect — only the absence of any
character/programming across the station is (REQ-OF-001).

**Acceptance criteria:** see acceptance.md AC-OF-003.

### REQ-OF-004 — Apolitical, non-partisan station (Unwanted) [HARD]

The system shall not produce partisan or political commentary, advocacy, or opinion
in any talk, banter, imaging, or news content; music's cultural/societal significance
is the editorial lens, never partisan political commentary. The station is explicitly
non-political.

**Acceptance criteria:** see acceptance.md AC-OF-004.

### REQ-OF-005 — Anti-AI-slop talk discipline (Unwanted) [HARD]

The system shall not produce AI-slop talk: it shall NOT use radio-filler clichés
("stay tuned", "up next", "coming up"), manufactured morning-DJ enthusiasm,
"let's dive in"-style openers, emoji or fourth-wall narration in spoken copy, and it
shall not gratuitously announce that it is an AI. Host/talk scripts read as genuine,
specific, human-curatorial speech, not generic LLM filler. (Validated against the
writ-fm reference's anti-slop discipline; complements anti-shallow-banter REQ-OF-002.)

**Acceptance criteria:** see acceptance.md AC-OF-005.

### REQ-OF-006 — Script quality gate with regeneration (Event-driven) [HARD]

When a host/talk/imaging script is generated, the system shall apply a quality gate
that rejects a script falling below its word-target minimum (or failing the anti-slop
discipline REQ-OF-005) and regenerates it; a script that cannot pass the gate within a
bounded number of attempts is dropped (graceful-skip, never blocking the stream —
consistent with VOICE-002's skip-talk-keep-music and REQ-OE-012's buffer). Word
targets and the attempt bound are TUNABLE config.

**Acceptance criteria:** see acceptance.md AC-OF-006.

---

## 12. Requirement Group OG — News & Newscasting

Priority: High. (Supersedes CORE-001 Section 3.2's news exclusion for regular
scheduled newscasting; the breaking-news interrupt is OPTIONAL/advanced.)

### REQ-OG-001 — Autonomous news cadence & format (Event-driven) [HARD autonomy]

When the program director plans the schedule, the system shall let the AI decide HOW
and WHEN to do news — cadence, format, which segments, how long — at its own
discretion; no fixed news schedule or format is mandated. Regular scheduled
newscasting is the core capability.

**Acceptance criteria:** see acceptance.md AC-OG-001.

### REQ-OG-002 — Self-discovered, AI-evolved trusted source list (Event-driven + self-scheduled)

When researching news, the system shall let the AI continuously discover, evaluate,
and maintain its OWN list of trusted news sources, evolving it over time with no human
input; the source list is system-owned and persistent.

**Acceptance criteria:** see acceptance.md AC-OG-002.

### REQ-OG-003 — Source aggregation via feeds/APIs first (Ubiquitous)

The system shall aggregate news from its sources by preferring official feeds and APIs
(RSS/Atom, news APIs) over scraping, and shall use structured scraping only where the
source's terms permit; aggregation runs off the playout path and never blocks the
stream. (The feeds/APIs-first preference is the testable definition of efficient
aggregation; no vague "efficiently" obligation is asserted.)

**Acceptance criteria:** see acceptance.md AC-OG-003.

### REQ-OG-004 — Factual news from trusted sources (Ubiquitous)

The system shall deliver factual news drawn from trusted sources; newscast content
shall reflect what those sources report.

**Acceptance criteria:** see acceptance.md AC-OG-004.

### REQ-OG-005 — News grounded + attributed, never fabricated (Unwanted) [HARD]

The system shall not air fabricated or unverified news; every newscast item shall be
grounded in fetched source content and attributed to its source(s); items that cannot
be grounded shall be dropped rather than invented. News shall remain factual and
apolitical (REQ-OF-004).

**Acceptance criteria:** see acceptance.md AC-OG-005.

### REQ-OG-006 — Faroese-angle prioritization + language routing (Event-driven)

When selecting and voicing news, the system shall let the AI prioritize a Faroese
angle — Faroe Islands news (kvf.fo, dimma.fo as known trusted seed sources) plus
Sweden (SVT / Sveriges Radio-class) plus major international (Reuters / AP-class) —
and shall voice Faroese-language news in Faroese via teldutala.fo (Hanna/Hanus) and
other-language news via Kokoro/Piper, routing language per VOICE-002 Group V-D.

**Acceptance criteria:** see acceptance.md AC-OG-006.

### REQ-OG-007 — Newscast production & pull insertion (Event-driven)

When a news slot is due, the system shall produce the newscast through the imaging/TTS
pipeline (optional news-signature pips via procedural synthesis REQ-OE-003 → TTS read
→ loudnorm to the shared target REQ-OE-005 → clip library) and serve it as
`NextItem(kind="news")`, identically to imaging, with no Liquidsoap change.

**Acceptance criteria:** see acceptance.md AC-OG-007.

### REQ-OG-008 — Optional breaking-news interrupt at a safe boundary (Optional feature)

Where the AI judges an event significant enough, the system shall be able to insert a
breaking-news item out of cadence at a SAFE boundary (the end of the current song, not
mid-vocal) and then resume the clock cleanly; this is an OPTIONAL/advanced behavior
the AI MAY choose, never a mandate, and it MUST NOT silence the stream.

**Acceptance criteria:** see acceptance.md AC-OG-008.

### REQ-OG-009 — News never blocks the stream (Unwanted) [HARD]

If news aggregation, research, production, or TTS is slow, errored, or unavailable,
then the system shall skip the news slot (or fall back to music) without blocking,
stalling, or silencing the stream, consistent with the inherited continuous-operation
behavior.

**Acceptance criteria:** see acceptance.md AC-OG-009.

---

## 12a. Requirement Group OH — Library Management & Acquisition Policy

Priority: High. These EXTEND SPEC-RADIO-CORE-001's library & acquisition group
(Group A); they consume its slskd/yt-dlp acquisition pipeline and library store, and
add management/policy on top. They do NOT fork the acquisition pipeline.

### REQ-OH-001 — Play from the amassed library, balanced against acquisition (State-driven)

While selecting music, the system shall increasingly play from its amassed library as
the catalog grows; acquisition GROWS the library and is not the only source. The AI
balances reusing the existing catalog against acquiring new music — that balance is
the AI's call — and the system shall NOT acquire on every selection.

**Acceptance criteria:** see acceptance.md AC-OH-001.

### REQ-OH-002 — Acquisition quality preference: slskd first, yt-dlp last resort (Event-driven) [HARD]

When acquiring a track, the system shall ALWAYS prefer slskd (typically FLAC /
high-bitrate) over yt-dlp; yt-dlp is the LAST resort only, used when slskd cannot
supply the track. The acquisition ranking shall make slskd the primary source and
yt-dlp the fallback of last resort.

**Acceptance criteria:** see acceptance.md AC-OH-002.

### REQ-OH-003 — Organized, managed library folder structure (Event-driven)

When a downloaded file is imported, the system shall sort it into a clean, managed
library folder structure (e.g. by artist/album or genre) rather than leaving files in
slskd's raw download directories; library housekeeping (organizing, sorting, tidying)
is an explicit capability. The organization scheme is the AI's to choose/evolve.

**Acceptance criteria:** see acceptance.md AC-OH-003.

### REQ-OH-004 — Disk-space management: never run out (State-driven) [HARD]

While running, the system shall monitor free disk space and shall NEVER run out: it
shall cap library size and/or evict the least-valuable tracks (least-played,
lower-quality duplicates) when space is low, and shall surface a low-space condition
in health/status. (The deployment has hit disk limits before; this is a hard
operational rail.)

**Acceptance criteria:** see acceptance.md AC-OH-004.

### REQ-OH-005 — Bandcamp purchase-recommendation hook (Event-driven)

When the AI identifies music it judges worth having but cannot obtain via slskd or
yt-dlp/YouTube, and the music is available on Bandcamp, the system shall NOTIFY the
user via a user-facing recommendation channel (a notification / webhook / log / push
— mechanism TBD) recommending the user PURCHASE it. This is a "buy this"
recommendation to the human, not an autonomous purchase.

**Acceptance criteria:** see acceptance.md AC-OH-005.

### REQ-OH-006 — Acquisition accounting + bounded download queue (State-driven) [HARD]

While acquiring music, the system shall TRACK its acquisition stats — current library
size and pending-download/queued count — and shall BOUND the acquisition/download queue
to a configured maximum; it shall NOT amass a massive, uncontrolled queue it has no
oversight of. The director shall THROTTLE new acquisition based on library size, free
disk, and queue depth (ties to REQ-OH-001 play-from-library balance and REQ-OH-004
disk-never-runs-out): when the queue is at its bound or disk is low, new acquisition is
deferred rather than piled on. The queue bound and throttle thresholds are TUNABLE
config; the stats are exposed in health/status (NFR-O-6).

**Acceptance criteria:** see acceptance.md AC-OH-006.

---

## 13. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following:

- **Full live listener call-in** — telephony/VoIP, STT, two-way conversation,
  caller-audio mixing (SPEC-RADIO-CALLIN-003; VOICE-002 owns the seam).
- **Instagram / any social** read/reply (SPEC-RADIO-SOCIAL).
- **Finance / monetization / ad-reads / sponsorship** (SPEC-RADIO-FINANCE). Zero
  commercial motive.
- **Full listener-analytics product** beyond CORE-001's listener-signals contract and
  operational health/logging (SPEC-RADIO-ANALYTICS).
- **Elaborate self-staffing org apparatus** (SPEC-RADIO-ORG) — OPS consumes CORE-001's
  runtime-extensible persona model as-is.
- **Music-rotation broadcast/PRO licensing** — separate, larger obligation; flagged
  (R-O-10); out of scope; build stays private/experimental.
- **Redefining TTS engines, live-stream ducking mechanics, persona-model internals,
  or the playout topology** — consumed from VOICE-002/CORE-001, never redefined.
- **Sample-accurate, fully beatmatched ASOT-grade continuous-mix flow** — adjacency
  (REQ-OA-006) and BPM/key/energy-aware DJ-set ordering are in scope (enabled by the
  enrichment in REQ-OA-011); the playout-layer beat-aligned crossfade refinement that
  makes mixes sample-accurate remains a later tuning phase (R-O-9).
- **Ramp / talk-over ("hitting the post")** — Liquidsoap-layer voice-tracking, not a
  produced clip.
- **MusicGen / CC-BY-NC or attribution-required beds for unattended on-air imaging**
  — blocked by the self-cleared gate (REQ-OE-010).
- **Languages beyond English + Faroese** for talk/news voicing; **partisan/political
  content** of any kind (REQ-OF-004).
- **Zero-gap failover re-engineering** — OPS adds "fall back to music, never silence,"
  not a new availability SLA.
- **Autonomous purchasing / payment** — the Bandcamp hook (REQ-OH-005) only
  RECOMMENDS a purchase to the human; the system does NOT buy, pay, or transact (no
  monetization/finance — SPEC-RADIO-FINANCE).

---

## 14. Two-SPEC split option (noted, not taken)

The research recommended splitting imaging (production pipeline) and operations
(decision engine) into two SPECs because they have different change cadences and
builders. Per the user directive this is ONE SPEC. If implementation reveals the
combined SPEC is unwieldy, Groups OE (imaging) and OA-OD/OF-OG (operations) are
cleanly separable along the `kind="imaging"`/`kind="news"` seam and the decision-vs-
production boundary, and could be re-split into SPEC-RADIO-IMAGING-005 +
SPEC-RADIO-OPS-004 without re-architecture. (Open question, R-O-13.)

---

## 15. Non-Functional Requirements

### NFR-O-1 — Subscription LLM auth (Ubiquitous) — Priority High
The brain shall use Claude via the MAX subscription through `claude-agent-sdk` with
`ANTHROPIC_API_KEY` UNSET (setting it bills credits and fails), authenticating via the
mounted `~/.claude` OAuth credentials with auto-refresh. See acceptance.md AC-NFR-O-1.

### NFR-O-2 — LLM quota discipline & two modes (Ubiquitous) — Priority High
The system shall protect the 5-hour rolling subscription quota by using the cheap
tools-off quick-curation mode for the frequent path, reserving the web-tools-on
research mode for occasional show-prep/news, batching LLM calls, and running the LLM
loop asynchronously off the playout path (inherited from CORE-001 REQ-D-007). See
acceptance.md AC-NFR-O-2.

### NFR-O-3 — Loudness consistency (Ubiquitous) — Priority High
Every aired item — song, imaging, talk, news — shall sit at the single shared target
(-16 LUFS / -1.5 dBTP), sourced from one config constant shared with acquisition
ingest (CORE-001) and the talk layer (VOICE-002). See acceptance.md AC-NFR-O-3.

### NFR-O-4 — Resilience / never-crash the loop (Ubiquitous) — Priority High
The director loop shall isolate every tick so a failed imaging/news/show-prep/playbook
operation logs and is skipped without crashing the loop or the daemon; no OPS failure
silences the stream (REQ-OA-008, REQ-OG-009). See acceptance.md AC-NFR-O-4.

### NFR-O-5 — Continuous operation (Ubiquitous) — Priority High
The system shall operate continuously 24/7 indefinitely (inherited from CORE-001
Section 1.2); a brief interruption on restart is acceptable; no zero-gap failover is
built. See acceptance.md AC-NFR-O-5.

### NFR-O-6 — Observability (Ubiquitous) — Priority Medium
The system shall emit structured logs for program-director decisions, separation
relaxations, imaging production (concept/mix/loudnorm/encode), playbook updates, news
aggregation/grounding/attribution, and fallbacks, sufficient to diagnose an incident
after the fact, surfaced through the CORE-001 health/status surface. See acceptance.md
AC-NFR-O-6.

### NFR-O-7 — Apolitical & factual integrity (Ubiquitous) — Priority High
No code path shall generate partisan/political content (REQ-OF-004) or fabricated
facts/news (REQ-OC-005, REQ-OG-005); generated copy/news is logged so non-compliant
content can be detected after the fact. See acceptance.md AC-NFR-O-7.

### NFR-O-8 — Simplicity (Ubiquitous) — Priority Medium
This SPEC shall implement the smallest design that delivers the autonomous PD,
imaging, self-learning playbook, and newscasting on the confirmed stack; deferred
items (Section 13) MUST NOT be partially built. See acceptance.md AC-NFR-O-8.

### NFR-O-9 — Timezone / local-clock correctness (Ubiquitous) — Priority High
All scheduling, dayparting, clock-slot resolution, and time/date references shall use
the configured local timezone (default `Atlantic/Faroe`, Tórshavn) with correct
DST handling (WET ↔ WEST), not UTC or server-local time (REQ-OA-009). A wrong timezone
or DST error MUST NOT misalign dayparts or surface incorrect on-air time/date. See
acceptance.md AC-NFR-O-9.

### NFR-O-10 — No audio under-run from generation latency (Ubiquitous) — Priority High
Talk/imaging/news generation (TTS + LLM) shall be fully decoupled from the playout
pull path: a `/api/next` PULL is served from the pre-stocked ready buffer (REQ-OE-012)
and shall never wait on a synchronous render, so generation latency never causes an
audio under-run/stall. Heavy generators are serialized to bound RAM (REQ-OE-012). See
acceptance.md AC-NFR-O-10.

### NFR-O-11 — No sharp cut-offs; gentle fade is the baseline transition (Ubiquitous) — Priority High
Tracks shall not hard-cut by default: the baseline transition between any two items is
at minimum a gentle crossfade / fade-out (REQ-OA-014). A sharp cut-off is a defect.
Richer DJ-style beatmatch/EQ mixing applies only to club/dance shows by the AI's
context choice; the no-sharp-cutoff floor applies everywhere. See acceptance.md
AC-NFR-O-11.

---

## 16. Open Questions / Risks

- **R-O-1 — Music-bed licensing for public imaging (Medium).** Mitigated by the
  layered self-cleared stack (procedural → Stable Audio 3 → first-party CC0) + the
  license ledger + self-generated-or-CC0-only gate (REQ-OE-010). Residual: confirming
  Stable Audio 3 registration + the <$1M revenue threshold (R-O-8).
- **R-O-2 — LLM subscription 5h rolling quota (Medium).** Frequent research/news/
  show-prep calls could exhaust the window. Mitigated by two modes (cheap path
  tools-off), batching, async loop + deterministic fallback (NFR-O-2). Open: the
  exact mode-B cadence/budget.
- **R-O-3 — TTS expressiveness for engaging hosts/news (Medium).** Local TTS can sound
  flat for high-energy delivery. Mitigated by punchy short scripts + pacing controls +
  light FX; capped by graceful-skip. Inherited from VOICE-002.
- **R-O-4 — Loudness consistency across content types (Low/Medium).** Imaging/news/
  talk must hit the same LUFS as songs or the station jumps in volume. Mitigated by
  one shared gate (NFR-O-3); verified by AC-OE-005.
- **R-O-5 — Web-research reliability + factual accuracy (Medium).** Mode-B research and
  news can fabricate. Mitigated by grounding in fetched sources + attribution +
  hedging + apolitical constraint (REQ-OC-005, REQ-OG-005, REQ-OF-004).
- **R-O-6 — News-source aggregation maintenance + scraping ToS (Medium).** The
  AI-evolved source list must stay reliable; scraping may breach ToS. Mitigated by
  preferring official feeds/APIs and permitted scraping only (REQ-OG-003).
- **R-O-7 — sidechaincompress wiring + amix voice-level loss (Low, build-time).**
  Voice must key the music; amix attenuates by default. Mitigated by an explicit
  level-check acceptance criterion (AC-OE-002).
- **R-O-8 — Stable Audio 3 CPU latency + commercial registration/$1M threshold
  (Medium).** Real CPU inference is slow; the free grant requires registration + a
  revenue check. Mitigated by pre-render/cache + procedural fallback + config gate
  (REQ-OE-004) + a registration/revenue step.
- **R-O-9 — Beat-aligned mix refinement (Low/Medium, partly deferred).** BPM/key/
  energy enrichment is now an in-scope requirement (REQ-OA-011, via
  librosa/aubio/essentia + external metadata), which enables DJ-set adjacency
  ordering (REQ-OA-006). The remaining gap is only the playout-layer sample-accurate
  beat-aligned crossfade that makes a mix seamless; that refinement is budgeted as a
  later tuning phase, and analysis quality/coverage on a modest box is a tuning
  concern.
- **R-O-10 — Public-stream music-rights liability (High, out of scope).** The main
  rotation (slskd/yt-dlp-acquired tracks) needs SoundExchange/PRO webcast licensing
  for any public stream. Out of scope here; flagged; CORE-001 gates acquisition off;
  scope the build as private/experimental. The separation solver doubles as a
  DMCA performance-complement mechanism if the stream ever goes public.
- **R-O-11 — Music-history/cultural depth + apolitical directive (relayed, confirm).**
  Folded into Groups OC/OD + REQ-OF-004 from a coordinator-relayed directive. It is
  consistent with the user's prior intent but was NOT a direct user message during
  this authoring; confirm with the user.
- **R-O-12 — Newscasting in scope (relayed, confirm; supersedes CORE-001 exclusion).**
  Group OG pulls regular newscasting forward from the deferred SPEC-RADIO-NEWS, via a
  coordinator-relayed directive. It is consistent with CORE-001's stated long-term
  vision (Section 1.1 names on-air news + breaking-news + kvf.fo/dimma.fo) but
  supersedes CORE-001 Section 3.2's news exclusion; confirm with the user, and on
  confirmation update CORE-001's roadmap note to reflect that regular newscasting
  moved into OPS-004 (breaking-news interrupt remains optional/advanced).
- **R-O-13 — One SPEC vs. the recommended two-SPEC split (Low).** Built as one SPEC
  per the user directive; cleanly re-splittable along the imaging/operations boundary
  if it proves unwieldy (Section 14).
- **R-O-14 — Gray-area ToS of automated subscription use (Low/Medium).** Automated use
  of the MAX subscription via OAuth is a gray area; flagged. Auth via mounted
  `~/.claude` per the confirmed stack; `ANTHROPIC_API_KEY` unset (NFR-O-1).
- **R-O-15 — Metadata-enrichment accuracy + cost (Medium).** Tag correction + audio
  analysis (BPM/key/energy) + external enrichment (MusicBrainz/Discogs/Last.fm) can be
  wrong or rate-limited; mismatched enrichment degrades genre nights / DJ-sets.
  Mitigated by running off the playout path (REQ-OA-011/012), multiple sources with
  reconciliation (REQ-OA-010), and graceful degradation (partial metadata still
  usable). External-API rate limits are a tuning concern.
- **R-O-16 — Self-change stability tuning (Low/Medium, relayed).** The
  rate-limit/cooldown/canary values for REQ-OD-006 (measured self-change) are tunable
  and must balance "improve a lot" against "don't thrash." Modeled on the design-
  constitution evolution-safety framework; relayed during authoring, confirm with the
  user.
- **R-O-17 — Disk-space exhaustion (High, operational; relayed).** The deployment has
  hit disk limits before; an unbounded growing library on a single cloud server will
  fill the disk. Mitigated by hard disk-space management (REQ-OH-004: cap + evict
  least-valuable + low-space alert) and play-from-library balance (REQ-OH-001, don't
  always download). Eviction policy (what counts as least-valuable) is a tuning
  concern. Relayed during authoring; confirm with the user.
- **R-O-18 — Bandcamp hook mechanism + reliability (Low, relayed).** The "buy this"
  recommendation channel mechanism is TBD (notification/webhook/log/push), and
  detecting Bandcamp availability for an unobtainable track is best-effort. It is
  recommend-only (no autonomous purchase). Relayed during authoring; confirm with the
  user.
- **R-O-19 — Downstream-SPEC scope notes for CALLIN-003 + SOCIAL (Low, relayed).**
  Section 17 records confirmed-DESIGN notes for two FUTURE SPECs (CALLIN-003 channels/
  STT/moderation/scheduling tie-in; SOCIAL autonomous Instagram management via the
  official Graph API). These are roadmap/dependency notes only — NOT requirement groups
  in OPS-004; the full SPECs are authored at those phases. The SOCIAL note expands
  CORE-001's deferred "Instagram read/reply" into full autonomous social management.
  Both relayed during OPS-004 authoring; confirm with the user when those SPECs are
  taken up.
- **R-O-20 — Location/timezone awareness (Low/Medium, relayed).** REQ-OA-009 + NFR-O-9
  fix the station's location to Tórshavn, Faroe Islands (`Atlantic/Faroe`, DST-correct)
  and anchor all dayparting/clock/time references to local time. Relayed during
  authoring; confirm with the user (location + default timezone). Build concern: DST
  correctness (WET↔WEST) and using a proper tz database, not a hardcoded offset, so the
  twice-yearly transition does not misalign dayparts. The location is configurable.
- **R-O-21 — Public play-history surface (Low, relayed).** REQ-OB-006/OB-007 add a
  persisted timestamped play-history (show-associated from the start) and a website
  rendering (per-show tracklists + unscheduled timeline), extending CORE-001's
  now-playing/play-log + self-served website. Relayed during authoring; confirm with the
  user. Build concern: recording the show association at air time so per-show grouping
  populates automatically once shows come online; keep it on CORE-001's play-log store
  (no fork).
- **R-O-22 — Show descriptions + listener feedback channel (Low/Medium, relayed).**
  REQ-OB-008 adds AI-authored show descriptions on the website; REQ-OB-009 adds a
  listener contact/feedback channel feeding CORE-001's listener-signals contract
  (REQ-D-008). Relayed during authoring; confirm with the user. Build concerns: (a) the
  feedback endpoint accepts untrusted public input — validate/sanitize per CORE-001 and
  consider abuse/spam handling; (b) [HARD] feedback must remain human-curatorial input
  the AI weighs, never an engagement/appeal-optimization target — the alignment with the
  anti-appeal ethos (REQ-OF-004 / NFR-O-7) must hold in implementation, with no
  feedback-volume/sentiment score to maximize and no pandering.
- **R-O-23 — writ-fm-validated reliability/editorial additions (Low, relayed).** The
  writ-fm reference (a mature working AI radio the user pointed to) VALIDATES the design
  and motivated: pre-stocked ready buffer + serialized generators (REQ-OE-012 / NFR-O-10),
  append-only ledger + diary (REQ-OD-007/008), per-loop run modes (REQ-OA-013), anti-slop
  + quality gate (REQ-OF-005/006), no-self-imitation (REQ-OC-006). Relayed; confirm with
  the user. Build concerns: buffer-depth N + serialization tuning vs. RAM; ledger
  idempotency + replay; anti-slop checklist maintenance. Divergences kept deliberately:
  we ACQUIRE music via slskd (writ-fm GENERATES via ACE-Step), and we use
  claude-agent-sdk (writ-fm shells the Claude CLI) — same no-billing spirit, structured.
- **R-O-24 — Context-aware mixing build sophistication (Medium, relayed).** REQ-OA-014 +
  NFR-O-11: DJ-style beatmatch/EQ mixing for club/dance depends on accurate BPM/key
  metadata (REQ-OA-011) and an in-flight mixing-implementation research effort, so the
  beatmatch/EQ sophistication may phase in; the no-sharp-cutoff gentle-crossfade floor
  is always required and is the safe baseline. Relayed; confirm with the user.
- **R-O-25 — Acquisition accounting / bounded queue (Low/Medium, relayed).** REQ-OH-006:
  track library size + pending-download count and bound the queue, throttling by size/
  disk/queue depth (ties to R-O-17 disk + OH-001 balance). Relayed; confirm with the
  user. Build concern: choosing the queue bound + throttle thresholds so the station
  keeps acquiring what it needs without amassing an uncontrolled backlog.

---

## 17. Out-of-Scope / Future SPEC Roadmap

- **SPEC-RADIO-CALLIN-003 — live listener interaction (built after the voice/TTS
  layer; attaches to VOICE-002's call-in seam REQ-V-F-001).** Confirmed design notes
  (coordinator-relayed during OPS-004 authoring — to be user-confirmed when this SPEC
  is taken up):
  - Channels: real PHONE (Twilio / SIP — live voice) + MESSAGING (WhatsApp / Messenger
    / Instagram DMs — text requests/shout-outs the host reads on air).
  - STT: local Whisper for transcribing live callers.
  - SCHEDULED call-in shows/segments: the program director blocks call-in windows in
    the schedule. [Dependency on OPS-004] this ties into OPS-004's scheduling group
    (Group OA, format clock + special-show windows) — the call-in window is a clock
    slot/special show the PD owns; CALLIN-003 supplies the live-caller behavior within
    that window. OPS-004 does NOT implement call-in; it only owns the scheduling that
    a future call-in window would occupy.
  - SHORT broadcast delay + LIVE AI moderation (not full pre-screen).
  - The on-air host persona converses in character (reuses CORE-001 personas +
    VOICE-002 voices).
  - Requires user-provisioned Twilio + Meta dev app/tokens (human = credential
    provider, per the inherited Operating Model).
  - Full telephony/STT/two-way/caller-mixing subsystem is its OWN SPEC; not built here.
- **SPEC-RADIO-NEWS** — IF the user confirms Group OG here, this roadmap entry narrows
  to advanced news only (deeper investigative formats, richer breaking-news), since
  regular newscasting moves into OPS-004.
- **SPEC-RADIO-INGEST** — concrete seed ingestion (mostly delivered in CORE-001
  v0.3.0).
- **SPEC-RADIO-SOCIAL — autonomous Instagram + messaging management (expands CORE-001's
  deferred "Instagram read/reply" into FULL autonomous social management).** Confirmed
  design notes (coordinator-relayed during OPS-004 authoring — to be user-confirmed
  when this SPEC is taken up):
  - The AI manages an Instagram account ITSELF: reads + replies to listener
    DMs/comments AND autonomously CREATES + POSTS content (images / captions / stories)
    as it sees fit (consistent with the station's full creative autonomy + ethos:
    human/curatorial, no engagement/appeal optimization, no monetization).
  - API: official Instagram Graph API (Business/Creator account + Meta app + tokens,
    user-provisioned). [HARD] Never unofficial scraping.
  - Also WhatsApp / Messenger.
  - This is a distinct subsystem with its OWN SPEC; OPS-004 does NOT build social
    management. (Note: listener DMs/comments that surface as requests/shout-outs would
    flow through CORE-001's listener-signals input contract REQ-D-008 and could feed
    OPS-004's request handling, but the social subsystem itself is out of scope here.)
- **SPEC-RADIO-FINANCE** — finance / monetization (possible future feature; not now).
- **SPEC-RADIO-ANALYTICS** — full listener analytics (behind CORE-001's
  listener-signals seam).
- **SPEC-RADIO-ORG** — elaborate self-staffing org.
- **SPEC-RADIO-IMAGING-005 (only if re-split)** — extracted imaging production
  pipeline (Section 14, R-O-13).
- **BPM/key/energy ingest analysis + beatmatched continuous-mix** — later phase
  enabling true ASOT-grade flow (R-O-9).

---

## 18. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in
acceptance.md; detailed Given-When-Then scenarios for the load-bearing requirements
are in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-OA-001 | Program Director & Scheduling | High | Event/Self-scheduled | AC-OA-001 |
| REQ-OA-002 | Program Director & Scheduling | High | Ubiquitous | AC-OA-002 |
| REQ-OA-003 | Program Director & Scheduling | High | State | AC-OA-003 |
| REQ-OA-003a | Program Director & Scheduling | High | State | AC-OA-003a |
| REQ-OA-003b | Program Director & Scheduling | High | Unwanted | AC-OA-003b |
| REQ-OA-003c | Program Director & Scheduling | High | State | AC-OA-003c |
| REQ-OA-004 | Program Director & Scheduling | High | Event | AC-OA-004 |
| REQ-OA-005 | Program Director & Scheduling | High | State | AC-OA-005 |
| REQ-OA-006 | Program Director & Scheduling | Medium | Event | AC-OA-006 |
| REQ-OA-007 | Program Director & Scheduling | High | Event | AC-OA-007 |
| REQ-OA-008 | Program Director & Scheduling | High | Unwanted | AC-OA-008 |
| REQ-OA-009 | Program Director & Scheduling | High | Ubiquitous | AC-OA-009 |
| REQ-OA-010 | Program Director & Scheduling | High | Event | AC-OA-010 |
| REQ-OA-011 | Program Director & Scheduling | High | Event | AC-OA-011 |
| REQ-OA-012 | Program Director & Scheduling | High | Ubiquitous | AC-OA-012 |
| REQ-OA-013 | Program Director & Scheduling | Medium | Event | AC-OA-013 |
| REQ-OA-014 | Program Director & Scheduling | Medium | Event | AC-OA-014 |
| REQ-OB-001 | Shows & Host Personas | High | Event | AC-OB-001 |
| REQ-OB-002 | Shows & Host Personas | High | State | AC-OB-002 |
| REQ-OB-003 | Shows & Host Personas | High | Ubiquitous | AC-OB-003 |
| REQ-OB-004 | Shows & Host Personas | Medium | Event | AC-OB-004 |
| REQ-OB-005 | Shows & Host Personas | Medium | Event | AC-OB-005 |
| REQ-OB-006 | Shows & Host Personas | High | Event | AC-OB-006 |
| REQ-OB-007 | Shows & Host Personas | Medium | Event | AC-OB-007 |
| REQ-OB-008 | Shows & Host Personas | Medium | Event | AC-OB-008 |
| REQ-OB-009 | Shows & Host Personas | High | Event | AC-OB-009 |
| REQ-OC-001 | Research-Driven Show Prep | High | Ubiquitous | AC-OC-001 |
| REQ-OC-002 | Research-Driven Show Prep | High | Event | AC-OC-002 |
| REQ-OC-003 | Research-Driven Show Prep | High | Event | AC-OC-003 |
| REQ-OC-004 | Research-Driven Show Prep | Medium | Ubiquitous | AC-OC-004 |
| REQ-OC-005 | Research-Driven Show Prep | High | Unwanted | AC-OC-005 |
| REQ-OC-006 | Research-Driven Show Prep | High | Unwanted | AC-OC-006 |
| REQ-OD-001 | Self-Learning Playbook | High | Ubiquitous | AC-OD-001 |
| REQ-OD-002 | Self-Learning Playbook | High | Event | AC-OD-002 |
| REQ-OD-003 | Self-Learning Playbook | High | Event/Self-scheduled | AC-OD-003 |
| REQ-OD-004 | Self-Learning Playbook | High | Ubiquitous | AC-OD-004 |
| REQ-OD-005 | Self-Learning Playbook | Medium | Ubiquitous | AC-OD-005 |
| REQ-OD-006 | Self-Learning Playbook | High | State | AC-OD-006 |
| REQ-OD-007 | Self-Learning Playbook | High | Ubiquitous | AC-OD-007 |
| REQ-OD-008 | Self-Learning Playbook | Medium | Event | AC-OD-008 |
| REQ-OE-001 | Self-Produced Imaging | High | Event | AC-OE-001 |
| REQ-OE-002 | Self-Produced Imaging | High | Event | AC-OE-002 |
| REQ-OE-003 | Self-Produced Imaging | High | Event | AC-OE-003 |
| REQ-OE-004 | Self-Produced Imaging | Medium | Event | AC-OE-004 |
| REQ-OE-005 | Self-Produced Imaging | High | Event | AC-OE-005 |
| REQ-OE-006 | Self-Produced Imaging | High | Event | AC-OE-006 |
| REQ-OE-007 | Self-Produced Imaging | High | Event | AC-OE-007 |
| REQ-OE-008 | Self-Produced Imaging | High | Ubiquitous | AC-OE-008 |
| REQ-OE-009 | Self-Produced Imaging | High | Unwanted | AC-OE-009 |
| REQ-OE-010 | Self-Produced Imaging | High | Unwanted | AC-OE-010 |
| REQ-OE-011 | Self-Produced Imaging | Medium | State | AC-OE-011 |
| REQ-OE-012 | Self-Produced Imaging | High | State | AC-OE-012 |
| REQ-OF-001 | Liveliness & Quality | High | Ubiquitous | AC-OF-001 |
| REQ-OF-002 | Liveliness & Quality | Medium | Unwanted | AC-OF-002 |
| REQ-OF-003 | Liveliness & Quality | High | Ubiquitous | AC-OF-003 |
| REQ-OF-004 | Liveliness & Quality | High | Unwanted | AC-OF-004 |
| REQ-OF-005 | Liveliness & Quality | High | Unwanted | AC-OF-005 |
| REQ-OF-006 | Liveliness & Quality | High | Event | AC-OF-006 |
| REQ-OG-001 | News & Newscasting | High | Event | AC-OG-001 |
| REQ-OG-002 | News & Newscasting | High | Event/Self-scheduled | AC-OG-002 |
| REQ-OG-003 | News & Newscasting | High | Ubiquitous | AC-OG-003 |
| REQ-OG-004 | News & Newscasting | High | Ubiquitous | AC-OG-004 |
| REQ-OG-005 | News & Newscasting | High | Unwanted | AC-OG-005 |
| REQ-OG-006 | News & Newscasting | High | Event | AC-OG-006 |
| REQ-OG-007 | News & Newscasting | High | Event | AC-OG-007 |
| REQ-OG-008 | News & Newscasting | Medium | Optional | AC-OG-008 |
| REQ-OG-009 | News & Newscasting | High | Unwanted | AC-OG-009 |
| REQ-OH-001 | Library Management & Acquisition Policy | High | State | AC-OH-001 |
| REQ-OH-002 | Library Management & Acquisition Policy | High | Event | AC-OH-002 |
| REQ-OH-003 | Library Management & Acquisition Policy | High | Event | AC-OH-003 |
| REQ-OH-004 | Library Management & Acquisition Policy | High | State | AC-OH-004 |
| REQ-OH-005 | Library Management & Acquisition Policy | Medium | Event | AC-OH-005 |
| REQ-OH-006 | Library Management & Acquisition Policy | High | State | AC-OH-006 |
| NFR-O-1 | Non-Functional | High | Ubiquitous | AC-NFR-O-1 |
| NFR-O-2 | Non-Functional | High | Ubiquitous | AC-NFR-O-2 |
| NFR-O-3 | Non-Functional | High | Ubiquitous | AC-NFR-O-3 |
| NFR-O-4 | Non-Functional | High | Ubiquitous | AC-NFR-O-4 |
| NFR-O-5 | Non-Functional | High | Ubiquitous | AC-NFR-O-5 |
| NFR-O-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-O-6 |
| NFR-O-7 | Non-Functional | High | Ubiquitous | AC-NFR-O-7 |
| NFR-O-8 | Non-Functional | Medium | Ubiquitous | AC-NFR-O-8 |
| NFR-O-9 | Non-Functional | High | Ubiquitous | AC-NFR-O-9 |
| NFR-O-10 | Non-Functional | High | Ubiquitous | AC-NFR-O-10 |
| NFR-O-11 | Non-Functional | High | Ubiquitous | AC-NFR-O-11 |
