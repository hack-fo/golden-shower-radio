# SPEC-RADIO-OPS-004 — Research

Distilled research backing SPEC-RADIO-OPS-004 (Autonomous Program Director,
Self-Produced Imaging, Self-Learning Radio Craft, and Newscasting). Sourced from a
four-strand research workflow (jingle/imaging production, autonomous radio
operations taxonomy, reference-station format patterns, generative/royalty-free
music beds + licensing) plus the confirmed existing stack and the two predecessor
SPECs (SPEC-RADIO-CORE-001, SPEC-RADIO-VOICE-002).

This file is the WHY/EVIDENCE companion to spec.md. spec.md is the WHAT/WHY
contract; plan.md is the HOW.

---

## 0. SPEC-ID and structure decision

- **SPEC-ID = SPEC-RADIO-OPS-004.** The RADIO series uses a GLOBAL-incrementing
  integer suffix, proven by the existing set: CORE-**001**, VOICE-**002**, and
  CALLIN-**003** (reserved — referenced in VOICE-002's spec/acceptance/plan and in
  `brain/voice.py`). The next free integer is **004**. The originally suggested
  `SPEC-RADIO-OPS-001` was rejected because (a) it would visually collide with
  CORE-001 and (b) it contradicts the established global-increment pattern (VOICE
  is 002, not VOICE-001). Verified by grep: no other `-004` assignment exists.
- **Single SPEC, not the two-SPEC split the research recommended.** The research
  synth recommended splitting into SPEC-RADIO-IMAGING + SPEC-RADIO-OPS because they
  have different change cadences/builders and a single SPEC would be large. The
  user's direct directive is ONE SPEC covering autonomous operations + self-produced
  imaging + self-learning (+ later: news + music-history depth). The user directive
  wins; the split remains a noted option in Open Questions.

---

## 1. Imaging / jingle production pipeline (research strand 1 + synth)

### 1.1 Concrete, buildable 6-stage pipeline (per imaging clip)

All stages are supported by the confirmed stack (Claude text via Agent SDK + local
TTS + ffmpeg; add `sox` + optional Stable Audio 3 Small for beds).

1. **CONCEPT (Claude, text-only).** `radio-brain.py` asks Claude for a
   structured-JSON brief, not prose. Schema:
   `{type, lang("en"|"fo"|...), voice, script, target_seconds,
   production("dry"|"wet"|"showpiece"), bed_id|bed_prompt, sfx[],
   fx{pitch,reverb}, lufs_target}`. The system prompt encodes the imaging taxonomy
   + per-type length rules. For Faroese, Claude embeds teldutala inline tags
   (`\pau=Nms\`) directly in the script string. Reuses the existing minimal-config
   brain LLM call pattern (no API key, MAX subscription).
2. **VOICE (local TTS — owned by VOICE-002, reused here).** Render script → WAV:
   Kokoro/Piper for English (offline, fast); teldutala.fo for Faroese (two-step
   async: POST `/api/v1/tts` → audioId, poll GET `/api/v1/tts/generated/{audioId}`
   → MP3; browser-like UA + Origin/Referer; adult voices `Hanna22k_NT`/`Hanus22k_NT`
   only; concurrency ≤ 3 + backoff). CRITICAL: Faroese is high-latency external —
   pre-render and cache imaging ahead of air; never synthesize in the `/api/next`
   path.
3. **MIX (ffmpeg `filter_complex`, + sox for bed prep).** Dry IDs skip the bed.
   Wet pieces: trim/loop the bed (sox), `afade` in (~0.3s) + out (~1.0s tail),
   optional stinger via `adelay`, then DUCK with `sidechaincompress` wired so the
   **VOICE is the sidechain KEY compressing the MUSIC** (NOT the reverse — the #1
   wiring bug):
   `[0:a]asplit=2[v][key];[1:a][key]sidechaincompress=threshold=0.02:ratio=10:attack=50:release=400:makeup=1[ducked];[v][ducked]amix=inputs=2:duration=first:normalize=0`.
   `amix` attenuates inputs by default → use `normalize=0`/explicit volume and
   verify the voice stays full-level. Light FX (`asetrate`/`atempo` pitch nudge,
   subtle reverb) for wet only.
   **This is OFFLINE clip-baking — DISTINCT from VOICE-002's LIVE-stream ducking**
   (VOICE-002 ducks the live Liquidsoap music source under a live talk segment via
   `request.queue`/`smooth_add`). No overlap, no redefinition.
4. **NORMALIZE (ffmpeg `loudnorm` two-pass, EBU R128).** Pass 1:
   `loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null -` → parse
   `measured_I/TP/LRA/thresh/offset`. Pass 2: feed those back with `linear=true`.
   Target MUST match the song catalog exactly: **-16 LUFS / -1.5 dBTP** for Icecast
   (NOT -23/-24 LUFS FM/TV). Same gate applies to songs, imaging, talk, and news →
   one shared constant.
5. **ENCODE + LIBRARY HANDOFF (ffmpeg).** Encode to the stream codec at the
   catalog's sample-rate/channels (radio.liq currently outputs `%mp3(bitrate=128)`).
   Write to a `CLIPS_DIR` (sibling to `MUSIC_DIR`, mounted into both brain +
   liquidsoap containers) with a metadata sidecar (type, lang, duration, lufs,
   created_at, bed license). Register in the brain's clip pool.
6. **SERVE / INSERT (existing pull architecture, ZERO Liquidsoap change).** The
   brain's Picker (`brain/server.py`) already returns `NextItem(kind=...)`. Add
   `kind="imaging"` (and `kind="news"`) alongside the documented `kind="talk"`.
   When the cadence policy says an imaging/news slot is due, `Picker.pick()` returns
   the clip path; `/api/next` serves + commits it identically; `request.dynamic.list`
   plays whatever path it gets. Keep every served item a single clean single-track
   request (avoids the savonet #1074 post-jingle stall). RAMP/TALK-OVER ("hitting
   the post") is a Liquidsoap-layer voice-tracking mode (VOICE-002 territory), NOT
   a produced clip — out of scope for the produced-imaging pipeline.

### 1.2 Imaging taxonomy + cadence (TUNABLE defaults, not fixed rules)

| Type | Definition | Production | Cadence (default, AI-tunable) |
|------|-----------|-----------|-------------------------------|
| Station ID | Name (+ slogan/show) only; identity anchor | dry, or thin 2-3s bed | ~hourly, clustered near :00 |
| Sweeper | 15-20 words / <20s voiced overlay + bed + light SFX | wet | ~every 2-4 songs |
| Liner | Scripted phrase, little/no production; a FORMAT not a function | dry | interchangeable between songs |
| Stager | Deliberate liner framing what's next, 5-10s | dry/light bed | at segment/show boundaries |
| Promo | Short tune-in pitch for an upcoming show | wet/semi-wet | a few times per daypart |
| Stinger/bumper | Sub-second to few-second transition hit; or 60s sweeper+teaser | procedural by default | as punctuation, sparingly |
| Show open/close | Branded intro/outro, voice + richer bed | showpiece/wet | once per show instance |
| Named-segment ident | Recurring branded-segment anchors (e.g. "Tune of the Week") | wet intro jingle | once per segment occurrence |
| News signature / pips | Short tone/jingle prefixing a bulletin | procedural | before each news read |

**Anti-overproduction is a real failure mode** (Audio Brothers / LFM): too many wet
layers "slows a station down." Default most IDs/liners to DRY; reserve showpiece wet
imaging for occasional use. This is a TUNABLE default the AI can evolve, not a
hardcoded rule (Creative Autonomy).

### 1.3 Music-bed sourcing — layered, legally ranked

1. **Procedural synthesis (zero legal risk, instant, offline, PREFERRED for FX).**
   `sox synth` (sine/square/tri/saw/exp + white/pink/brown noise + start:end
   frequency sweeps, `-n` no input), ffmpeg `sine`/`aevalsrc` (arbitrary +
   exponential-sweep expressions)/`anoisesrc` (colored noise), chained with
   fade/reverb/echo. Output is public-domain by construction — nothing for any PRO
   or rightsholder to claim. ffmpeg already in stack; add sox. Covers the bulk of
   imaging FX.
2. **Local generative beds (low legal risk, CPU-feasible).** Stable Audio 3.0 Small
   / Small SFX (open-weight, ~459M params, CPU-capable, released 2026-05-20).
   TRAINED ON FULLY LICENSED DATA; the Stability AI Community License grants OUTPUT
   OWNERSHIP + free commercial/broadcast use while annual revenue < $1,000,000
   (above → Enterprise License; commercial users must REGISTER). No third-party
   recording embedded → no external performance claim on the station's own beds.
   CAVEAT: real CPU inference is far slower than GPU figures — PRE-RENDER + CACHE, a
   reusable bed pool, never generate in the playout path; gate behind a config flag.
3. **First-party CC0 library (low risk if strictly CC0).** FreePD (CC0 1.0,
   no attribution, commercial OK), Pixabay (CC0/royalty-free). Cache + tag with
   license provenance.

**Do NOT use for broadcast default:** MusicGen/AudioCraft (code MIT but WEIGHTS
CC-BY-NC 4.0 non-commercial + GPU-hungry — offline experiment only); CC BY sources
(Incompetech, much of FMA — require attribution; awkward for unattended air);
aggregated CC0 corpora like SoundSafari (README self-admits per-track CC0 status is
unverified — secondary/takedown-aware only). NEVER cut beds from copyrighted
commercial songs; never use MusicGen melody-conditioning or "in the style of
[artist]" prompts.

### 1.4 Honest licensing reality (two independent layers)

- **Layer A — Copyright / reproduction.** Where "royalty-free"/"CC0"/"no
  attribution" live. CC0 = full public-domain dedication. "Royalty-free" is a
  PAYMENT model, NOT a broadcast clearance.
- **Layer B — Public performance rights (the broadcast layer).** A SEPARATE right
  via PROs (ASCAP/BMI/SESAC + SoundExchange in the US; PRS/PPL in the UK; STIM/IFPI
  in Sweden). For the station's OWN synth/Stable-Audio-3/CC0 imaging there is NO
  third-party rightsholder, so Layer B does not bite — imaging is broadcast-safe.
  BUT this does NOT cover the MAIN MUSIC ROTATION: tracks acquired via slskd/yt-dlp
  are unlicensed copies; publicly streaming them needs Layer-B webcast/PRO licensing
  regardless of how files were obtained. That obligation is OUT OF SCOPE for this
  SPEC but flagged as a risk (CORE-001 already gates acquisition off by default).
- AI-generated audio with no meaningful human authorship is uncopyrightable in the
  US (2025-26 USCO guidance) — fine for imaging (no need for exclusivity), but the
  station cannot claim exclusive ownership of its AI beds.

**Bottom line for imaging:** procedural synthesis + Stable Audio 3 + strictly
first-party CC0 = the legally cleanest, fully-autonomous bed stack. A per-clip
license ledger + a hard "self-generated-or-CC0-only for unattended on-air imaging"
gate is the autonomy guardrail.

---

## 2. Autonomous program-director model (research strand 2)

The autonomous PD is a layered pipeline driven by Liquidsoap PULLING the next item
over HTTP from the Python brain. FIXED rails are safety/engineering; everything
creative is the AI's call.

| Layer | Behavior | FIXED (rail) | AI DECIDES |
|-------|----------|--------------|-----------|
| Format clock | Per-daypart 60-min hour skeletons (data, not code); slots typed song-category / imaging / talk / news / id / stopset / request / special; 5 or 7 variants per daypart (never multiples of 24) to break the daily lattice | slot ORDER, top-of-hour ID, daypart boundaries | which concrete item fills each slot; which clock variant is active; may evolve the skeleton |
| Rotation categories | Power Current / Secondary (up/down) / Power Recurrent / Secondary Recurrent / Gold-Stay; uneven category sizes (e.g. 7 currents) so turnover matches target frequency; promotion/demotion/resting (platooning) | category schema + target play-frequency bands | category membership + life-cycle moves; home-scene/local quota |
| Separation solver | Pick next song so all separation constraints hold: artist (~2h30m for top currents) + title no-repeat (HARD); soft tempo/energy/vocalist-gender/era/sound-code spacing; relax soft rules gracefully (widen window, borrow adjacent category, LOG) when no perfect candidate | hard artist/title windows; empty-legal-set must never stall (continuity wins) | final pick among legal candidates; soft-rule relaxation under pressure |
| Dayparting + energy flow | Switch active clock set + persona register by time-of-day (Morning Drive / Midday / Afternoon Drive / Evening / Overnight); shape within-hour energy arc ("now, now, then"); morning = proven + high talk; overnight = long sweeps + minimal interruption | daypart boundaries + each daypart's mandate | energy ordering + tone; persona register (CHR-hype / curatorial / mix-show) |
| Imaging/ID cadence | Insert IDs/sweepers/liners/promos/segment-idents at clock positions; trigger the imaging production pipeline; reserve the top-of-hour ID | top-of-hour ID + cadence positions | which imaging type airs, copy, bed/SFX/FX, wet vs dry, invent/retire segments |
| Segue / adjacency | Choose next-song adjacency for flow (tempo/key/energy, never vocal-over-vocal); emit transition params (crossfade length, cue-in/out at phrase boundaries) | crossfade mechanics + no-vocal-over-vocal guard (playout layer) | adjacency + transition style; energy-arc planning for mix shows |
| Loudness gate | Normalize EVERY item to one target (-16 LUFS / -1.5 dBTP) at ingest/render and cache | the target + peak ceiling (engineering constant) | nothing (deterministic gate) |
| News scheduler + interrupt | Cadence path: clock news slot → assemble headlines → TTS → prefix signature. Interrupt path: event evaluator decides break-in, queues a priority item that plays at the next SAFE boundary (end of current song, not mid-vocal), resumes the clock cleanly | scheduled cadence + safe-boundary insertion rule | story selection/ordering, whether an event clears the bar, the copy |
| Requests + named segments | Vote-weighted queue + ~10-min surface delay; honor only when separation/clock fit; voice dedication via TTS. Named segments (ASOT-style) = name + ident + selection rule + generated intro | queue mechanics, surface delay, separation still applies | which requests to honor; segment feature picks; invent/retire segments |
| Special / scheduled shows | Appointment shows that OVERRIDE the default clock for a window, each with its own clock + genre pool + persona + imaging set; restore the default clock at window end | the schedule slots + each show's mandate | track selection, sequencing, persona, theme within the show |
| Now-playing + play-log | Emit accurate now-playing to Icecast + website; append every aired item to a play log feeding separation history + acquisition gap detection | output obligation (mechanical) | values + any creative title framing only |

**Never-dead-air is the prime directive and is a deterministic layer BELOW the AI**
(CORE-001 Group C owns it). OPS decisions can never be a single point of silence:
on render failure / empty pool / brain timeout, fall back to a music track or a
cached evergreen ID; Liquidsoap `mksafe` covers the gap; a brief interruption on
restart is acceptable.

---

## 3. Reference-station format patterns (research strand 3)

Three reusable presentation MODES the AI can switch between by daypart/show-block —
emulate the FORMAT/PRESENTATION, never copy actual jingles/idents/slogans/names
(all trademarked):

1. **CHATTY-CHR (Sveriges Radio P3 + BBC Radio 1 daytime).** Tiered
   high-rotation playlist (A/B/C or heavy/medium/light), strong host personality,
   frequent short talk breaks with banter/news/humour, idents, a LOCAL-MUSIC QUOTA
   (P3 ≥ 1/3 Swedish; the AI picks its own home scene — e.g. Faroese/Nordic — as a
   rolling counter). Bright, consistent energy. Morning-show personality daypart.
2. **CURATORIAL-CONNOISSEUR (KEXP + Rodigan).** DJ near-total freedom, rotation as
   GUIDE not mandate, ≥ 1 local track/hour, talk = the knowledgeable BACKSELL (name
   artist+title just played + real context/lineage/why-chosen, not hype). Genre-deep
   blocks (a reggae hour) teach history and treat rare/exclusive cuts as EVENT
   MOMENTS. Signature assets to emulate as FORMAT: Live-session-style "spotlight
   artist" blocks (no live guests → several tracks by one artist + narrated
   context); a daily "song of the day" pick. The backsell is the core talk unit for
   curatorial mode.
3. **CONTINUOUS-MIX (A State of Trance).** Near-continuous beatmatched flow ordered
   into a build-peak-winddown energy arc, minimal per-track chatter, structured by a
   small roster of recurring NAMED segments (host pick / listener vote / most-
   requested / emotional throwback / new-local-artist slot) with track-ID callouts
   at boundaries + guest-mix-style spotlight blocks. Real beatmatching needs
   BPM/key/energy tags (later phase — librosa/aubio/essentia at ingest).

**Cross-cutting emulable primitives:** rotation tiers; local-music quota; recurring
named segments as the show skeleton; the backsell as the core curatorial talk unit;
day-part persona switching; signature catchphrase/signature-tune identity anchors
(invent the station's own).

**Reference reweighting (user directive D).** The persona/format patterns the AI
learns from are weighted toward **KEXP** (curatorial-connoisseur, emphasized) and the
Sveriges Radio P3 sub-formats **P3 Dans** (dance/electronic) and **P3 Mix** (mixed) —
both distinct from generic P3 — alongside A State of Trance and BBC 1Xtra (Rodigan);
BBC Radio 1 daytime is a secondary CHR reference. The plan-time research strands did
NOT cover P3 Dans / P3 Mix specifically, so the runtime self-learning loop
(REQ-OD-003) should study them as named references. (spec.md REQ-OB-002, REQ-OD-002.)

**Radiooooo (app.radiooooo.com) — curation inspiration.** The "musical time machine":
pick a decade × a country and it plays music from that time and place (e.g. "1970s
Brazil"). A CURATION INSPIRATION for time/place-themed shows and deep global/historical
curation — emulated as a format/curation idea ONLY, NOT a data feed. The station sources
its own music via slskd (REQ-OH-002); Radiooooo is not queried. Ties to the
music-history/cultural depth dimension (Groups OC/OD). (spec.md REQ-OB-002.)

**Location + local time (relayed directive).** The station is LOCATED in Tórshavn,
Faroe Islands, timezone `Atlantic/Faroe` (UTC+0 winter / UTC+1 summer, WET/WEST). The
program director must know the current LOCAL time + date and program accordingly:
dayparting anchored to real local Faroe time (DST-correct), weekday/weekend +
season/holiday awareness, and location-aware presentation (local greetings, local-time
references). Pairs naturally with the Faroese news angle (kvf.fo/dimma.fo) and the
Faroese TTS path. (spec.md REQ-OA-009, NFR-O-9.)

**Public play-history surface (relayed directive).** The website (extends CORE-001's
self-served site + now-playing) shows timestamped play history: per-show/episode
tracklists (each track + aired-at) AND a "songs played" timeline for unscheduled music
blocks. Requires the brain to persist a timestamped play-history with show-association
recorded from the start (show/episode id OR 'unscheduled'). (spec.md REQ-OB-006/OB-007.)

**Reference-station IP caveat:** emulate format/presentation only; the AI must
invent its own imaging, slogan, catchphrases, and segment names. All five reference
stations operate under broadcast/streaming music licenses — formats are free to
imitate; their recorded assets and trademarked names are not.

---

## 4. Music history / cultural-societal depth + apolitical stance (user directive A)

Folded into Research-Driven Show Prep (Group C) and the Self-Learning Playbook
(Group D), NOT a new subsystem. The AI must understand and continuously learn
history, music, and music history — genre origins, movements, eras, artist
significance, and the role music plays in society and human life. This depth informs
curation ("why this track matters, its context") and banter (the informed "why this
song now" story — KEXP-style backsells, Rodigan-style reggae lore).

**[HARD] APOLITICAL.** This is NOT a political radio station. Music's
cultural/societal significance is the lens; the station SHALL NOT produce partisan
or political commentary, advocacy, or opinion. (Anti-hallucination still applies:
cultural/historical claims should draw from verified facts, not fabrication.)

---

## 5. Newscasting (user directive B) — now in scope, supersedes CORE-001's exclusion

CORE-001 Section 3.2 deferred news/web-search to SPEC-RADIO-NEWS. The user has now
pulled regular newscasting FORWARD into this SPEC as a core autonomous, learned
capability. (CORE-001's product vision Section 1.1 already named on-air news,
breaking-news from trusted sources, and kvf.fo/dimma.fo as the long-term intent.)

Key research grounding (strand 2, news cadence + the licensing/anti-hallucination
notes):

- **Two news modes.** (1) Scheduled cadence: bulletins at clock positions (classically
  top-of-hour), short tightly-packed headline reads, lead-story-first, often prefixed
  by a news signature/pips. (2) Breaking news: event-triggered interrupt that inserts
  at a SAFE boundary (end of current song, not mid-vocal) and resumes the clock
  cleanly. Regular scheduled newscasting is the CORE requirement; the interrupt is an
  OPTIONAL/advanced behavior the AI MAY choose.
- **Source discovery + aggregation.** The AI maintains and evolves its OWN trusted
  source list and finds efficient aggregation (RSS/Atom feeds, news APIs, structured
  scraping where permitted). Prefer official feeds/APIs over scraping for ToS safety.
- **Faroese angle (the confirmed angle).** Prioritise Faroe Islands news (kvf.fo,
  dimma.fo as known trusted seed sources) + Sweden (SVT / Sveriges Radio-class) +
  major international (Reuters / AP-class). Faroese-language news is spoken in
  FAROESE via teldutala.fo (Hanna/Hanus); Swedish/English/other via Kokoro/Piper —
  language routing per VOICE-002 Group V-D.
- **Factual + apolitical + grounded.** News must be FACTUAL, from TRUSTED sources,
  grounded in fetched source content and attributed — no hallucinated news, no
  partisan/editorial slant. Web fetch/search uses the Claude Agent SDK web tools (the
  richer LLM mode).
- **Learned craft.** Newscasting craft (what makes a good newscast, pacing, sourcing,
  fact-care) is part of the self-learning playbook (Group D).
- **Risks:** source reliability/aggregation maintenance; factual accuracy /
  hallucinated-news avoidance (must ground + attribute); scraping ToS (prefer feeds/
  APIs); keeping it apolitical/factual.

---

## 6. Two-LLM-modes efficiency model + subscription auth (confirmed stack + NFR)

- **Mode A — cheap quick-curation.** Pick next track(s) / next imaging type with a
  minimal system prompt, tools OFF, batched. The hot, frequent path.
- **Mode B — richer show-prep / research / news.** Occasional calls WITH web search
  enabled (Claude Agent SDK web tools) producing a show plan (tracklist + per-segment
  talking points/facts), researched themes, music-history/cultural depth, and news
  aggregation/reads. The infrequent, expensive path.
- **Subscription auth (NFR).** Python brain uses Claude via the MAX SUBSCRIPTION
  through the official `claude-agent-sdk`. `ANTHROPIC_API_KEY` MUST be UNSET — if set
  it bills credits and fails; auth is via the mounted `~/.claude` OAuth credentials
  with auto-refresh. Respect the 5-hour rolling subscription quota; batch calls;
  keep the cheap path tools-off and reserve web-tools-on for Mode B.

---

## 7. Fit with the existing stack (verified)

- **The seam exists.** `brain/server.py` `Picker.pick()` returns
  `NextItem(kind="music"|"talk", container_path, ...)` and the docstring explicitly
  anticipates future kinds served identically with no Liquidsoap change. OPS adds
  `kind="imaging"` and `kind="news"`. `deploy/config/radio.liq` is
  `request.dynamic.list` + `mksafe` and needs ZERO change. `/api/next` must stay
  < 1s and never block on synthesis — all imaging/talk/news audio is PRE-RENDERED by
  the director loop and cached.
- **The director loop is the right home.** `brain/director.py` already runs an async
  tick loop, wraps every tick so it never crashes the loop, and batches LLM calls to
  protect the MAX quota. Imaging/news/show-prep production rides the SAME batched,
  quota-aware, crash-isolated loop, rendering to `CLIPS_DIR` out-of-band.
- **`brain/voice.py`** is the documented TTS seam VOICE-002 fills; OPS imaging + news
  call the SAME TTS layer (no redefinition).
- **Containers.** Add `CLIPS_DIR` mounted into both brain + liquidsoap (sibling to
  `/music`); add `sox` to `Dockerfile.brain` (ffmpeg already present); gate Stable
  Audio 3 behind a config flag.
- **Loudness is one shared constant** (-16 LUFS / -1.5 dBTP) consumed by acquisition
  ingest, the imaging pipeline, VOICE-002 talk, and news.

---

## 8. Top risks (carried into spec.md Section 16)

1. Music-bed licensing for public imaging — mitigated by the layered self-cleared
   stack + license ledger + self-generated-or-CC0-only gate.
2. LLM subscription 5h rolling quota for frequent research/news/show-prep — mitigated
   by two-LLM-modes (cheap path tools-off) + batching + async loop + deterministic
   fallback.
3. TTS expressiveness for engaging hosts/news — mitigated by punchy short scripts +
   pacing controls + light FX; capped by graceful-skip.
4. Loudness consistency across songs/imaging/talk/news — mitigated by the single
   shared gate.
5. Web-research / news reliability + factual accuracy / hallucinated news — mitigated
   by grounding in fetched trusted sources + attribution + apolitical constraint.
6. News-source aggregation maintenance + scraping ToS — mitigated by preferring
   official feeds/APIs, AI-evolved source list.
7. sidechaincompress wiring direction (voice keys music) + `amix` voice-level loss —
   mitigated by an explicit level-check acceptance criterion.
8. Stable Audio 3 CPU latency + commercial-use registration/$1M threshold — mitigated
   by pre-render/cache + procedural fallback + config gate + registration step.
9. BPM/key/energy analysis gap for true beatmatched continuous-mix — budget as a
   later phase; adjacency works without it, but don't claim ASOT-grade flow yet.
10. Public-stream music-rights liability (main rotation) — out of scope here; flagged;
    CORE-001 gates acquisition off; scope the build as private/experimental.
11. Apolitical drift — news/banter must stay factual + non-partisan.
12. Gray-area ToS of automated subscription use — flagged; auth via mounted OAuth.
13. Self-change thrashing — measured/rate-limited evolution (REQ-OD-006) modeled on
    the design-constitution evolution-safety framework (rate limiter + cooldown +
    canary + contradiction detection; human-optional since human is out of loop).
14. Disk-space exhaustion — deployment hit disk limits before; hard disk management
    (cap + evict least-valuable + low-space alert) + play-from-library balance.
15. Metadata-enrichment accuracy/cost — tag correction + audio analysis (BPM/key/
    energy) + external enrichment (MusicBrainz/Discogs/Last.fm); off the playout path.

### Folded-in directives beyond the original four strands (user-relayed, confirm)

- **Music-history / cultural-societal depth + APOLITICAL** (knowledge+curation
  dimension of Groups OC/OD; non-political [HARD] REQ-OF-004).
- **Newscasting in scope** (Group OG; Faroese angle kvf.fo/dimma.fo + Sweden + intl;
  supersedes CORE-001's news exclusion; breaking-news optional).
- **Measured self-change** (REQ-OD-006), **reference reweight KEXP/P3 Dans/P3 Mix**
  (Section 3 above), **no-repeat/LRP rotation** (REQ-OA-003a), **self-reasoning
  autonomy** reaffirmed.
- **Library management & acquisition policy** (Group OH): play-from-library balance,
  slskd-first / yt-dlp-last quality preference, organized folder structure, hard
  disk-space management, Bandcamp purchase-recommendation hook.

### writ-fm reference — VALIDATES the design (relayed; emulate patterns, keep our stack)

writ-fm is a mature working AI radio the user pointed to; analyzing it validated and
motivated v0.4.0 additions (emulate the PATTERNS, not the stack):
- **Pre-stocked ready buffer + generation decoupled from playout + serialized heavy
  generators** → REQ-OE-012 + NFR-O-10 (reliability: pull never blocks on TTS/LLM; RAM
  bounded by a single generation worker).
- **Append-only event ledger (idempotent IDs) + director diary** → REQ-OD-007/008
  (cross-run editorial continuity; events: listener_message, decision,
  listener_reaction, diary_entry, active_threads).
- **Per-loop run mode from an editorial brief** (maintenance/responsive/continuity/
  special/quiet) → REQ-OA-013 (deliberate editorial behavior, not "always generate").
- **Anti-AI-slop discipline + word-target quality gate** → REQ-OF-005/006 (no "stay
  tuned/up next/coming up", no manufactured DJ enthusiasm, no "let's dive in", no
  emoji/fourth-wall, no gratuitous AI-announcement; reject below word-target + regen).
- **No self-imitation** (recent output is a topic/repeat avoid-list, never an in-context
  example) → REQ-OC-006 (prevents model collapse / template fatigue).
- **Deliberate divergences kept:** writ-fm GENERATES music via ACE-Step — we ACQUIRE
  real music via slskd (kept). writ-fm shells the Claude CLI — we use claude-agent-sdk
  on the MAX subscription (structured, same no-billing spirit). Noted, not changed.

### Metadata sources (concretize REQ-OA-011/012; user-provided + writ-fm batch)

Library enrichment sources, in order of preference per field:
- **MusicBrainz API** (`musicbrainz.org/doc/MusicBrainz_API`) + **TheAudioDB API**
  (`theaudiodb.com/free_music_api`) for genre/mood/tags/year (Discogs/Last.fm optional).
- Embedded tags (mutagen/ffprobe).
- Audio analysis (librosa/aubio/essentia-class) for BPM/key/energy.
- **Filename `%ARTIST% - %TITLE%` parsing as a reliable fallback** (downloads usually
  follow that format) when tags/APIs are missing.

### Mixing / transitions (REQ-OA-014 + NFR-O-11; build-HOW being researched)

Context-aware transition style picked by the AI per show/daypart:
- CLUB/DANCE (ASOT / P3 Dans): DJ-style mixing — crossfade + BEATMATCHING (BPM/key from
  REQ-OA-011) + high/low-pass EQ filter blends.
- REGULAR shows: clean transition, at minimum a gentle crossfade/fade-out (no
  beatmatch/EQ).
- [HARD/NFR-O-11] NO sharp cut-offs by default — a gentle fade/crossfade is the baseline.
The beatmatch/EQ build sophistication depends on accurate BPM/key metadata + an in-flight
mixing-implementation research effort, so it may phase in; the no-sharp-cutoff floor is
always required.

---

## 9. Sources

Strand 1 (imaging): live365, chriskubacki, lfmaudio, audiobrothers, willvincentvoice,
ffmpeg sidechaincompress/loudnorm docs, ffmpeg-normalize (slhck), radioworld /
sweetwater / youlean loudness guides, mcfiredrill liquidsoap-dynamic-playlist,
savonet/liquidsoap #1074, liquidsoap cookbook.
Strand 2 (operations): Wikipedia broadcast clock / dayparting / program director /
voice-tracking, live365 clockwheels + imaging, radioiloveit CHR scheduling, powergold
+ gomusic1 rotation, radio.co dead-air + requests, fcc unattended operation, EBU R128.
Strand 3 (references): Wikipedia + official pages for Sveriges Radio P3, BBC Radio 1,
KEXP, David Rodigan / 1Xtra, A State of Trance.
Strand 4 (beds/licensing): stability.ai Stable Audio 3 / Open 1.0, HF model cards,
facebookresearch/audiocraft (MusicGen), FreePD / Pixabay / SoundSafari / FMA /
Incompetech, sox + ffmpeg synth docs, ascap / spacial / prometheusradio licensing,
copyright.gov/ai.
