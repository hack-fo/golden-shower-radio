---
id: SPEC-RADIO-ANALYSIS-006
version: 0.5.0
status: draft
created: 2026-06-22
updated: 2026-06-23
author: charlie
priority: High
issue_number: null
---

# SPEC-RADIO-ANALYSIS-006 — Track Intelligence (Audio-Analysis Substrate)

## HISTORY

- 2026-06-22 (v0.1.0): Initial draft. The audio-analysis SUBSTRATE for the
  golden-shower-radio autonomous AI radio station — the offline, CPU-only analysis
  engine + track-intelligence DATA MODEL + cue/boundary detection that PRODUCE the
  features the rest of the suite consumes. This SPEC is the first-class home of the
  ENGINE that fills SPEC-RADIO-OPS-004's REQ-OA-011 (rich enrichment: BPM/key/energy/
  genre/mood/year) and REQ-OA-012 (queryable catalog), and supplies the cue points,
  beat grid, harmonic (Camelot) notation, and per-item transition metadata that
  REQ-OA-014 (context-aware transition/mixing) and REQ-OA-006 (segue/adjacency) feed to
  the playout layer. It answers two long-standing user questions directly: (Q3) "how
  does the station know WHEN and HOW a song ends, so it can transition intelligently?"
  — by analyzing cue-out / outro / true-end / trailing-silence offline and emitting them
  to Liquidsoap via `annotate:` overrides on top of the decoder's already-known exact
  duration; and (Q4) "how does it determine key, BPM/tempo, and genre?" — by a local
  CPU analysis pass on ingest plus a bounded backfill of the existing library. SPEC-ID =
  ANALYSIS-006 (the RADIO series uses a GLOBAL-INCREMENTING suffix — CORE-001,
  VOICE-002, CALLIN-003 reserved, OPS-004, ORCH-005 authored in parallel — so the next
  free number is 006, NOT 001; ANALYSIS is the substrate, numbered after the SPECs it
  serves). Built on the BRAIN-ONLY seam: it extends the existing Python `brain/`
  package (`library.py` `Track` model + JSON index + `scan()` + `pick_next()`, and the
  `acquire.py` import path) WITHOUT forking the library store and WITHOUT any Liquidsoap
  code change — the only playout-facing contract is the per-request `annotate:` metadata
  the shipped `crossfade(...)` + `request.dynamic.list(prefetch=2)` already read. A
  CRITICAL consumer requirement, relayed from the user 2026-06-22: the data model MUST
  support per-persona/per-show DISTINCT TASTE PROFILES — each host has its own unique,
  hand-curated genres/style/taste, and the catalog must let curation SEPARATE personas
  by genre/feature so no two hosts converge on the same rotation (the
  anti-"algorithmic-curation homogenization" goal). ANALYSIS-006 PROVIDES the feature
  DIMENSIONS that make distinct taste profiles queryable and separable; the curation
  POLICY itself lives in CORE-001/OPS-004 and is REFERENCED, not restated. Recommended
  toolchain (research.md): **Essentia (AGPLv3) as the primary CPU extractor** — the only
  single CPU library delivering BPM + beat grid + key + danceability/energy + integrated
  LUFS (ReplayGain) in one pass — with **librosa (ISC) as the permissive fallback /
  cue-point + silence-trim engine**, aubio (GPLv3) as an optional fast-tempo cross-check,
  and keyfinder-cli (GPLv3) noted as an alternate key engine. Total: 26 REQ + 7 NFR = 33,
  1:1 REQ↔AC.
- 2026-06-22 (v0.2.0): Added REQ-AP-007 (Library Watch / Auto-Ingest) [HARD] to Group AP
  (relayed during authoring — confirm with user, R-A-10). It makes the brain pick up music
  the user MANUALLY drops into the music dir (not just slskd downloads) and keep the catalog
  current "without hammering the disk." Critical technical constraint encoded: do NOT rely on
  inotify alone — the music dir is a Windows-hosted bind mount under WSL2 + Docker where
  inotify events do not reliably cross the host→container boundary, so a periodic METADATA-ONLY
  (`os.scandir`+`stat`: path/size/mtime, no content reads) scan diffed against a persisted
  manifest is the authoritative mechanism; only new/changed files get the expensive
  tag/analysis/enrich/sort treatment; content-hash only to detect moves/renames. It is the
  TRIGGER that feeds the on-ingest hook (REQ-AP-001). Net: +1 REQ (AP-007). Total: 27 REQ +
  7 NFR = 34, 1:1 REQ↔AC preserved.
- 2026-06-22 (v0.3.0): Augmented the metadata-source set with the Last.fm API (relayed —
  confirm with user, R-A-11), folded into EXISTING requirements (no new REQ). REQ-AM-001/002
  now name Last.fm folksonomy top tags (`artist.getInfo` / `track.getTopTags` /
  `artist.getTopTags`) as an additional genre/mood source alongside MusicBrainz/TheAudioDB;
  REQ-AM-003 reconciliation now ranks Last.fm with TheAudioDB as crowd folksonomy (below
  authoritative MusicBrainz) and adds a tunable noisy-crowd-tag filter (drop "seen live",
  "favourites", etc.) + cross-source corroboration boosting confidence. Last.fm SIMILAR-ARTIST
  discovery (`artist.getSimilar` / `tag.getTopArtists`) — per-persona taste expansion +
  targeted acquisition — is explicitly a CORE-001/OPS-004 curation/acquisition concern,
  referenced at REQ-AD-003's discovery-boundary note, NOT owned by the analysis engine.
  Gnoosic (no real API) is recorded as discovery-UX inspiration only (research.md Section 9),
  not a data source. research.md Section 9 + Sources added. Net: +0 REQ. Total: 27 REQ + 7
  NFR = 34, 1:1 REQ↔AC preserved.
- 2026-06-22 (v0.4.0): Deeper-understanding additions so the brain genuinely understands
  "what a track is and how it sounds" — for diversity + good curation across distinct
  personas (relayed — confirm with user, R-A-12). +2 REQ: REQ-AE-006 (SONIC-CHARACTER
  "how it sounds" understanding [HARD] — mood/timbre/production-character/instrumentation/
  vocal-vs-instrumental/acoustic-vs-electronic/dynamics via spectral+MFCC+energy features
  +/- a compact audio embedding +/- a GROUNDED LLM sonic description that describes only what
  the features support, not free hallucination; same CPU/offline/cached AE rails) and
  REQ-AT-007 (MUSIC-THEORY-informed analysis [HARD] — apply Claude's music theory on top of
  the VERIFIED features for harmonic/modal/structural reasoning + sane transitions, grounded:
  no theory claim the features don't support; feeds AT transitions + AD curation). Sharpened
  REQ-AM-003 from "reconciliation" into a multi-source CONSENSUS requirement [HARD]
  (verified-source allowlist + consensus threshold + confidence; single-source/low-consensus
  flagged + down-weighted, never stated as certain) — coordinating with KNOWLEDGE-008 (it owns
  ARTIST-FACT consensus; ANALYSIS owns AUDIO/GENRE/FEATURE consensus). Extended AD-001 (new
  sonic-character + consensus/provenance fields) + AD-003 (anti-convergence consumer note:
  the deeper understanding powers PROGRAMMING-007 REQ-PR-004's firewall — personas
  distinguished on sonic character + lineage, not just genre tag — referenced, not restated).
  +2 risks (R-A-12 sonic/LLM-grounding, R-A-13 consensus thresholds). Net: +2 REQ (AE-006,
  AT-007). Total: 29 REQ + 7 NFR = 36, 1:1 REQ↔AC preserved.
- 2026-06-23 (v0.4.1): Two additive extensions, no behavior change to existing detectors.
  (1) PROVENANCE FIELDS on the Track record (this SPEC owns it, REQ-AD-001): +REQ-AD-006
  [HARD] adds `acquired_at` (acquisition timestamp, DISTINCT from the file's `added_at`/mtime),
  `requested_by` (enum: director-curated | user-requested | ingest-scan | seed-reference), and
  `grab_reason` (the director's stated reason, stored VERBATIM as an UNVERIFIED claim — never
  promoted to a verified fact alongside consensus-backed features). [HARD] Written ONLY through
  the existing allowlist writer (REQ-AD-001); the frozen identity/dedup fields
  (path/artist/title/`Track.key`) are NEVER touched by provenance updaters; persisted at
  DECISION TIME as a pure stored breakdown (not recomputed later). The POPULATING LOGIC (who
  decides + what reason text) is owned by SPEC-RADIO-PROGRAMMING-007 Group PL (taste
  self-learning) — referenced, not re-owned; ANALYSIS-006 owns only the fields + the write
  discipline. (2) ADDITIVE SPECTRAL-FLUX BOUNDARY FEATURE in Group AT: +REQ-AT-008 [HARD]
  computes a spectral-flux / spectrogram-derived onset & offset as an ADDITIONAL per-track
  feature ALONGSIDE the existing energy-envelope cue-in/cue-out/true-end (REQ-AT-001/002/003)
  — [HARD] it does NOT replace the energy-envelope detector, which stays the playout-critical
  path. The spectral-flux signal CORROBORATES/enriches the cue points and feeds the AI's
  transition reasoning (REQ-AT-007) as another GROUNDED input (the grounded-features-feed-the-LLM
  principle); kept bounded/off-playout under the AE rails. Net: +2 REQ (AD-006, AT-008). Total:
  31 REQ + 7 NFR = 38, 1:1 REQ↔AC preserved.
- 2026-06-23 (v0.4.2): Cross-spec audit fix pass (no behavior change, no REQ count change).
  (1) [D1 canonical] REQ-AD-006 keeps `grab_reason` as the canonical Track field; the
  [Boundary] note now cites PROGRAMMING-007 REQ-PL-008 as the owner of the POPULATING LOGIC
  that writes `grab_reason`/`requested_by` through this SPEC's allowlist writer, and adds a
  [HARD] no-double-storage note reconciling `requested_by` (the acquisition ACTOR CLASS, owned
  + stored only here) vs PROGRAMMING-007 REQ-PL-001 `source`/`acquired_for` (channel/target,
  not a duplicate of the actor). (2) [D2] Scoped the [HARD] CPU-only/offline/no-network rail
  OFF the OPTIONAL LLM path in REQ-AE-006, REQ-AT-007, and AC-AE-006: the rail applies to the
  audio-FEATURE extraction (core DSP, NFR-A-1) only; the optional LLM sonic-description /
  music-theory application uses the brain's EXISTING LLM access, OFF the playout path, cached +
  idempotent (mirroring the OA-011 metadata-API exemption from the no-network rail) — removing
  the literally-unsatisfiable "LLM call runs with no network" [HARD] AC. (3) [EARS] Reclassified
  REQ-AM-004 from Ubiquitous to Event-driven (its text is already event-worded: "When a track
  has garbled/filename-parsed tags…"); header + Traceability Index now agree. Net: +0 REQ.
  Total unchanged: 31 REQ + 7 NFR = 38, 1:1 REQ↔AC preserved.
- 2026-06-23 (v0.5.0): One additive extension, no behavior change to existing detectors or to
  the grounded-only discipline (which is in fact tightened). EXTENDED the sonic-character
  understanding (REQ-AE-006) with PRODUCTION OBSERVATIONS: +REQ-AE-007 [HARD] lets the brain
  derive a track-level production observation that LINKS a SOURCED production fact (gear /
  recording location / production technique — read from SPEC-RADIO-KNOWLEDGE-008's researched
  editorial facts, with that fact's provenance + consensus state UNCHANGED) to an AUDIBLE RESULT
  read from the extracted features (REQ-AE-006 sonic-character profile + spectral/MFCC/energy/
  dynamics), so a host can ground "the dry drum tone" in BOTH the analysis feature AND the
  sourced gear fact — NEVER one alone. [HARD] THE TWO-LEG RULE is load-bearing: an observation is
  valid only when BOTH legs are present and agree in direction — a sourced gear fact with no
  corroborating audible feature is just a KNOWLEDGE-008 fact (not a production observation), and an
  audible feature reading with no sourced production fact is just a sonic-character descriptor (not
  a production observation). Grounding is [HARD]: the audible-result claim MUST be supported by the
  features (cannot assert an audible result the features contradict), and the production-fact leg
  carries KNOWLEDGE-008's consensus state so a single-source/unconfirmed production fact yields a
  HEDGED observation, not a confident one; ANALYSIS-006 does NOT re-run consensus on the production
  fact (KNOWLEDGE-008 owns that, REQ-KS-006) and does NOT invent it. The REVEAL/PRESENTATION
  mechanic (solo-the-stem / isolate-the-track CONTENT cue) is owned by SPEC-RADIO-LONGFORM-025
  Group LN (forward-ref) — ANALYSIS-006 supplies only the GROUNDED SONIC SUBSTRATE (feature reading
  + sourced-fact reference + the grounded link), referenced not restated. Added a bridging clause to
  REQ-AE-006, a glossary term, a Group AE scope line, a KNOWLEDGE-008 consumed-concept + LONGFORM-025
  downstream forward-ref to Section 2, a REFERENCES entry to Section 1.4, and risk R-A-14. Net: +1
  REQ (AE-007). Total: 32 REQ + 7 NFR = 39, 1:1 REQ↔AC preserved.

---

## 1. Overview & Background

### 1.1 Why this SPEC — "intelligent transitions and curation need to KNOW the music"

The station can already play continuously (CORE-001), talk (VOICE-002), and program
itself (OPS-004). A gentle volume-aware crossfade just shipped in `radio.liq`
(`crossfade(duration=4.0, fade_in=3.0, fade_out=3.0, smart=true, source)` +
`request.dynamic.list(prefetch=2)`). But the brain is curating and transitioning music
it does NOT actually understand: it knows artist/title/album (from mutagen) and a
play-count, and nothing about the SOUND. It cannot start a crossfade at the right
musical moment, cannot avoid fading into ten seconds of trailing silence, cannot
beat-align a club blend, cannot build a BPM/key-matched DJ set, cannot tell a soul
record from a techno record, and cannot give two hosts genuinely distinct rotations.

This SPEC adds the missing perception layer: a **track-intelligence substrate** that
analyzes each track once, offline, on the CPU, caches the result forever, and exposes
it as a queryable catalog the rest of the system curates and transitions from.

It is deliberately the FOUNDATION the OPS-004 enrichment/mixing requirements were
written against. OPS-004 REQ-OA-011 already NAMES the feature set and the external
metadata sources (MusicBrainz / TheAudioDB / embedded tags / `%ARTIST% - %TITLE%`
filename fallback); REQ-OA-014 already states the mixing POLICY (club beatmatch+EQ vs
regular crossfade); REQ-OA-006 already states the adjacency decision. ANALYSIS-006 does
NOT restate any of those — it builds the ENGINE that fills OA-011, the cue/beat-grid/
camelot inputs OA-014 and OA-006 consume, and the data model OA-012 queries.

### 1.2 Q3 — "How does it know WHEN and HOW a song ends?"

This is answered in full in research.md Section 2 and encoded in Group AT. In short:

- Liquidsoap's decoder ALREADY knows each track's exact **duration** (from the
  request/decoder), so the literal end-of-track is precisely known — that has never been
  the gap.
- What INTELLIGENT transitions need is the analyzed **cue-out** (where the outro begins),
  the **true end + trailing-silence** offset (so a crossfade does not fade into silence),
  and the **tempo + beat grid** (so a club blend can beat-align). These are what
  ANALYSIS-006 produces offline.
- The brain emits per-item transition metadata to playout via Liquidsoap `annotate:`
  overrides — the native `liq_cue_in`, `liq_cue_out`, `liq_cross_duration` (and
  `liq_fade_in`/`liq_fade_out`) plus CUSTOM fields (`bpm`, `camelot`, `mix_mode`,
  `energy`) read in the transition function from the source metadata dict — consumed by
  the shipped `crossfade(...)` today and by future club blends. No Liquidsoap code change
  is required; `annotate:` is a request-protocol feature.
- [Folded from prior mixing research] TRUE beatmatching needs an OFFLINE beat-grid +
  rubberband/ffmpeg time-stretch render — live Liquidsoap cannot phase-lock beats.
  Harmonic (Camelot) compatibility + a ±6% BPM gate is the robust qualifier for ATTEMPTING
  a DJ blend; an EQ bass-swap (`filter.iir.eq.high` sweep) is a mid-tier club transition.
  ANALYSIS-006 owns PRODUCING the beat-grid / camelot / bpm / gate inputs; the
  sample-accurate phase-lock render itself remains the deferred playout-layer tuning phase
  (OPS-004 R-O-9 / REQ-OA-014 phasing) and is NOT claimed here.

### 1.3 Q4 — "How does it determine key, BPM/tempo, and genre?"

- **BPM / tempo / beat grid / downbeats**: from the audio, via Essentia `RhythmExtractor2013`
  (primary; returns BPM + beat positions + confidence) with librosa `beat_track` as the
  permissive fallback. BPM detection is robust; octave errors (½× / 2×) are the known
  failure mode and are mitigated by a confidence threshold + a sane BPM range clamp.
- **Musical key (+ Camelot)**: from the audio, via Essentia `KeyExtractor` (profile
  `edma`/`temperley`) with a librosa chroma + Krumhansl-Schmuckler template fallback;
  mapped to Camelot notation for harmonic mixing. Key detection is inherently error-prone
  (research.md Section 3): ~70-85% "correct" under MIREX-weighted scoring, with
  perfect-fifth / relative-minor confusions the common errors. A per-track confidence is
  recorded and low-confidence keys are flagged so harmonic mixing can refuse uncertain
  matches rather than blend into a clash.
- **Genre / mood / tags**: derived primarily from EXTERNAL metadata (MusicBrainz +
  TheAudioDB per OA-011) + embedded tags, supplemented by audio-feature-derived hints
  (energy/danceability/tempo bucket) and OPTIONAL LLM classification (tools-off curation
  mode), reconciled across sources by an explicit confidence/precedence rule. Garbled
  tags (e.g. "Sly & the Familt Stone") are corrected by OPS-004 REQ-OA-010 (referenced,
  not re-owned); ANALYSIS-006 supplies the analysis-derived hints and the reconciliation
  engine.

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] ANALYSIS-006 owns the ENGINE and the DATA MODEL. It MUST NOT restate or fork any
CORE-001 or OPS-004 requirement.

OWNS:
- The offline CPU audio-analysis extractor and its toolchain (Group AE).
- Cue-in / cue-out / outro / true-end / trailing-silence / beat-grid / downbeat detection
  and the `annotate:` emission contract (Group AT) — the Q3 mechanics.
- Genre/mood/tag DERIVATION + the multi-source reconciliation algorithm (Group AM) — the
  Q4 genre mechanics.
- The track-intelligence DATA MODEL extending `Track` + the queryable catalog feature
  DIMENSIONS, including the per-persona distinct-taste-profile enabler (Group AD).
- The analysis PIPELINE: ingest hook, bounded backfill, throttle, graceful degradation,
  serialized worker, observability (Group AP).

REFERENCES (consumes / feeds; does not restate):
- **OPS-004 REQ-OA-011** — WHAT to enrich + the external source list. ANALYSIS-006 is the
  engine that fills it.
- **OPS-004 REQ-OA-012** — the queryable catalog the PD curates from. ANALYSIS-006 supplies
  the feature dimensions that make it queryable.
- **OPS-004 REQ-OA-014 / NFR-O-11** — the mixing POLICY + no-sharp-cutoff floor.
  ANALYSIS-006 produces the bpm/camelot/cue/beat-grid the policy consumes and emits the
  `annotate:` fields; it does NOT restate the policy or the floor.
- **OPS-004 REQ-OA-006** — the adjacency decision. ANALYSIS-006 provides the cue points +
  key/bpm those transition params are computed from.
- **OPS-004 REQ-OA-010** — tag correction/normalization ACTION. Referenced; ANALYSIS-006
  does not re-own tag-fixing.
- **OPS-004 REQ-OH-006** — acquisition accounting + bounded download queue. The backfill
  throttle (Group AP) ties to it (analysis is downstream of acquisition); referenced.
- **OPS-004 REQ-OE-012 / NFR-O-10** — serialized generators + ready buffer. The serialized
  analysis worker mirrors that RAM-bound pattern; referenced.
- **OPS-004 NFR-O-3 / CORE-001** — the -16 LUFS / -1.5 dBTP loudness constant + ingest.
  ANALYSIS-006 PRODUCES the integrated-LUFS / ReplayGain MEASUREMENT that feeds
  normalization; the normalization ACTION and the constant live in OPS/CORE; referenced.
- **CORE-001 library** — `brain/library.py` `Track` model, JSON index, `scan()`,
  `pick_next()`, the `acquire.py` import path. ANALYSIS-006 EXTENDS this store in place;
  it does not fork it.
- **KNOWLEDGE-008 REQ-KS-002 / REQ-KS-003 / REQ-KS-006** — the researched EDITORIAL FACT
  store (entity model + provenance/as-of + multi-source consensus). The PRODUCTION FACT (gear /
  recording location / production technique) that REQ-AE-007's production observation links to
  is a KNOWLEDGE-008 fact attached to a release/song/artist entity, sourced and consensus-graded
  THERE. ANALYSIS-006 READS that fact (with its provenance + consensus state intact) for the
  production observation; it does NOT re-own the fact, re-source it, or re-run consensus on it
  (KNOWLEDGE-008 owns REQ-KS-006; ANALYSIS-006 owns AM-003 audio/genre/feature consensus —
  neither re-owns the other).
- **LONGFORM-025 Group LN** (forward reference — not yet authored) — the REVEAL / PRESENTATION
  mechanic (solo-the-stem / isolate-the-track CONTENT cue that surfaces a production observation
  to the listener). ANALYSIS-006 supplies ONLY the grounded sonic substrate (REQ-AE-007's
  production observation: the feature reading + the sourced-fact reference + the grounded link);
  LONGFORM-025 Group LN owns HOW and WHEN a host reveals it. Referenced, not restated.

### 1.5 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 Section 1.3 and OPS-004 Section 1.3 in intent. It is mostly an
ENGINEERING substrate (analysis is deterministic DSP, not a creative act), but where it
touches creative decisions it follows the same rule: it GRANTS the AI accurate perception
+ a queryable catalog + safety rails, and MUST NOT prescribe fixed creative content,
genre mixes, taste profiles, scoring formulas, or curation rules. The taste profiles
themselves are the AI's (and the user's hand-curation per persona); ANALYSIS-006 only
guarantees the data model can REPRESENT and QUERY them distinctly. The human stays out of
the run loop; analysis is fully autonomous and continuous.

### 1.6 Fixed engineering/safety rails (the only hard constraints)

- **CPU-only, offline, no GPU.** All analysis runs locally on the CPU in the brain
  container (which is already gaining CPU torch for Kokoro). No GPU, no per-track network
  call required for the core DSP (external metadata APIs are the OA-011 enrichment path,
  not the DSP path).
- **Idempotent + cached, never re-analyze.** A file is analyzed once; the result is
  persisted and keyed so a re-scan, restart, or retry never recomputes it.
- **Never blocks the <1s pull.** Analysis is strictly background; `/api/next` is served
  from already-analyzed (or default) metadata and never waits on a render.
- **Graceful degradation.** A track with no analysis yet still plays, with the safe
  default crossfade (NFR-O-11) and conservative cue defaults — analysis lag is never a
  defect.
- **Accuracy is best-effort, not a contract.** BPM and especially key detection are
  imperfect; a confidence is recorded and low-confidence features are flagged so consumers
  (harmonic mixing) can refuse rather than clash. ANALYSIS-006 does not promise correct
  key for every track.

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001 and SPEC-RADIO-OPS-004 and is consumed by
SPEC-RADIO-ORCH-005 (authored in parallel). It references their subsystems by CONCEPT
(and, where a cited requirement is a deliberately stable invariant, by number).

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any CORE-001, OPS-004, VOICE-002,
or ORCH-005 requirement. Where it needs a predecessor behavior it consumes it. Where an
ANALYSIS decision could conflict with continuous operation, the inherited
continuous-operation behavior WINS.

Consumed CORE-001 concepts:
- **Library store** (`brain/library.py`): the `Track` dataclass, the persisted JSON index
  under `DB_DIR`, `scan()` (mutagen tag read + `%ARTIST% - %TITLE%` filename fallback +
  dedup via `normalize_key`), and `pick_next()` (least-recently-played picker).
  ANALYSIS-006 EXTENDS `Track` with feature fields and adds the analysis pass on the scan/
  import path. [HARD] It keeps the same store (no fork).
- **Acquisition import path** (`brain/acquire.py`, `slskd.py`, `ytdlp.py`): new files land
  in the downloads/library dir and are scanned; ANALYSIS-006 hooks the analysis pass to
  that ingest event (REQ-A-007 metadata extraction).
- **Pull-based playout** (`brain/server.py` `/api/next` → `Picker`/`NextItem` →
  Liquidsoap `request.dynamic.list`): ANALYSIS-006 adds per-item `annotate:` metadata to
  the served request; it does NOT change the pull contract or add a `kind`.
- **Continuous operation / never-dead-air** (CORE Group C): analysis sits ABOVE it and
  must never stall or silence the stream.

Consumed OPS-004 concepts (by number, deliberately):
- **REQ-OA-011** (enrichment feature set + external source list), **REQ-OA-012**
  (queryable catalog), **REQ-OA-014 / NFR-O-11** (mixing policy + no-sharp-cutoff floor),
  **REQ-OA-006** (adjacency), **REQ-OA-010** (tag correction), **REQ-OH-006** (acquisition
  accounting / bounded queue), **REQ-OE-012 / NFR-O-10** (serialized generators / ready
  buffer pattern), **NFR-O-3** (loudness constant), **NFR-O-6** (observability surface).

Consumed VOICE-002 concept:
- Loudness target reuse for any analysis-derived gain (ReplayGain measurement feeds the
  shared -16 LUFS / -1.5 dBTP normalization owned by OPS/CORE).

Consumed KNOWLEDGE-008 concept (for the production observation, REQ-AE-007):
- **REQ-KS-002 / REQ-KS-003 / REQ-KS-006** — the researched editorial-fact store: the
  PRODUCTION FACT (gear / recording location / production technique) the production observation
  links to is a KNOWLEDGE-008 fact attached to a release/song/artist entity, carrying its
  source + as-of date (REQ-KS-003) and its consensus state (REQ-KS-006). ANALYSIS-006 reads it
  for REQ-AE-007 and propagates that consensus state into the observation's grounding (a
  single-source production fact yields a hedged observation); it does NOT fork the knowledge
  store or re-run fact consensus. [HARD] The knowledge store is consumed, never re-owned.

### Downstream SPECs that depend on ANALYSIS-006 (forward references)

- **SPEC-RADIO-ORCH-005** (director loop / world-model / event reaction, authored in
  parallel) CONSUMES track-intelligence as a PERCEPTION input — the world model reads the
  catalog's feature dimensions (genre/key/bpm/energy/era) to reason about what is playing
  and what to schedule. ANALYSIS-006 owns producing those features; ORCH-005 owns
  reasoning over them. Neither redefines the other.
- **SPEC-RADIO-LONGFORM-025 Group LN** (not yet authored) CONSUMES the REQ-AE-007 production
  observation as the GROUNDED SONIC SUBSTRATE for its reveal/presentation mechanic
  (solo-the-stem / isolate-the-track CONTENT cue). ANALYSIS-006 owns producing the grounded
  observation (feature reading + sourced-fact reference + the two-leg grounded link);
  LONGFORM-025 owns the content presentation of it. Neither redefines the other.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Track intelligence** | The set of analyzed, persisted per-track features: BPM/tempo, beat grid + downbeats, musical key + Camelot, energy/danceability, integrated LUFS / ReplayGain, cue points (cue-in / cue-out / outro), true-end + trailing-silence, and derived genre/mood/tags. |
| **Analysis engine** | The offline, CPU-only extractor that computes track intelligence from an audio file. Primary: Essentia; fallback/supplement: librosa. |
| **Feature record** | The persisted analysis result for one track (a versioned block attached to the `Track`), keyed so it is never recomputed. |
| **BPM / tempo** | Beats per minute. The global tempo estimate plus a confidence; the beat grid is the per-beat time positions. |
| **Beat grid / downbeat** | The sequence of beat onset times across the track (and, where detectable, the first beat of each bar — the downbeat). The offline input a club beat-align render needs. |
| **Musical key** | The estimated tonal key (e.g. "A minor"), distinct from the existing `Track.key` field which is the dedup SLUG (artist-title), NOT a musical key — see REQ-AD-005. |
| **Camelot** | The harmonic-mixing notation (1A-12B): the musical key mapped to a number+letter so DJs (and the AI) can pick harmonically compatible blends (same code, ±1 number same letter, or switch letter same number). |
| **Energy / danceability** | Audio-derived descriptors of intensity and rhythmic regularity, used for energy arcs and to seed mood/genre hints. |
| **Integrated LUFS / ReplayGain** | The EBU R128 integrated loudness measurement (and the equivalent ReplayGain track-gain). ANALYSIS-006 MEASURES it; the normalization to the shared -16 LUFS / -1.5 dBTP target is owned by OPS/CORE (NFR-O-3). |
| **Cue-in** | The point where the track's musical content effectively starts — end of a long intro / first downbeat of energy — so the mix can skip dead intro air. |
| **Cue-out / mix-out point** | The point where the outro begins — where a following track can start being mixed in. |
| **True end + trailing silence** | The offset of the last audible audio and the length of any trailing silence, so a crossfade does not fade into silence. |
| **mix_mode** | A per-item transition hint emitted to playout: e.g. `crossfade` (regular) vs `blend` (club beat-align candidate). The AI picks the mode (OA-014); ANALYSIS-006 supplies the data and emits the field. |
| **annotate: override** | Liquidsoap's request-protocol mechanism for attaching per-request metadata (`annotate:key="v",...:uri`). The brain-only seam to playout — native `liq_*` fields plus custom fields read in the transition function. |
| **Backfill** | The bounded, throttled, resumable pass that analyzes the EXISTING library (tracks ingested before analysis existed), as distinct from the on-ingest analysis of new downloads. |
| **Taste profile** | A persona/show-scoped set of feature constraints (include/exclude genres + bpm/key/energy/era bounds) used by curation (CORE-001/OPS-004) to select a DISTINCT candidate pool. ANALYSIS-006 provides the queryable dimensions; the profiles themselves are the AI's/user's. |
| **Confidence** | A per-feature reliability score (especially for key and BPM) recorded with the feature so consumers can refuse low-confidence values rather than act on a wrong one. |
| **Spectral flux** | A frame-to-frame measure of how fast the spectrum is changing. A spectral-flux / spectrogram-derived onset & offset is an ADDITIONAL boundary estimate (REQ-AT-008) computed differently from the energy-envelope cue points, used to CORROBORATE them and enrich transition reasoning — never to replace the playout-critical energy-envelope detector. |
| **Acquisition provenance** | The stored record of WHY/HOW a track entered the library (REQ-AD-006): `acquired_at` (the acquisition-decision timestamp, distinct from file mtime/`added_at`), `requested_by` (director-curated / user-requested / ingest-scan / seed-reference), and `grab_reason` (the director's stated reason, stored verbatim as an UNVERIFIED claim — never a verified fact). |
| **Production observation** | A track-level observation (REQ-AE-007) that LINKS a SOURCED production fact (gear / recording location / production technique — read from KNOWLEDGE-008's editorial-fact store with its provenance + consensus state) to an AUDIBLE RESULT read from the extracted features (the REQ-AE-006 sonic-character profile + spectral/MFCC/energy/dynamics), so a claim like "the dry drum tone" is grounded in BOTH the analysis feature AND the source. [Two-leg rule] Valid only when BOTH legs are present and agree: a sourced fact alone is just a KNOWLEDGE-008 fact; an audible feature alone is just a sonic descriptor. ANALYSIS-006 supplies the substrate; the reveal/presentation cue (solo-the-stem / isolate-the-track) is LONGFORM-025 Group LN's. |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group AE — Audio Analysis Engine.** The offline CPU extractor; the feature set; the
  SONIC-CHARACTER "how it sounds" understanding (mood/timbre/production/instrumentation/
  vocal/acoustic/dynamics +/- a content embedding +/- a grounded LLM sonic description); the
  PRODUCTION OBSERVATION that links a sourced production fact (gear/location/technique from
  KNOWLEDGE-008) to an audible feature result under the two-leg grounding rule (the substrate
  the LONGFORM-025 reveal mechanic consumes, referenced); the idempotent persisted cache
  (never re-analyze); the CPU-only/offline/no-GPU rail; the bounded backfill of the existing
  library; per-feature confidence + low-confidence flagging.
- **Group AT — Transition Intelligence (the Q3 answer).** Cue-in, cue-out/outro, true-end
  + trailing-silence, beat grid + downbeats for club beat-align; an ADDITIVE spectral-flux /
  spectrogram-derived onset & offset that corroborates the energy-envelope cue points (without
  replacing them); music-theory-informed harmonic/modal/structural reasoning on the verified
  features; the per-item `annotate:` emission contract to playout; the safe-default behavior for
  unanalyzed tracks.
- **Group AM — Metadata, Genre & Mood Derivation (the Q4 genre answer).** Genre derivation
  from external metadata (OA-011 sources) + embedded tags + audio-feature hints + optional
  LLM classification; mood + descriptive tags; multi-source CONSENSUS reconciliation
  (verified-source allowlist + threshold + confidence; single-source flagged).
- **Group AD — Track-Intelligence Data Model & Queryable Catalog.** Extend the `Track`
  model with feature fields (no store fork); a queryable catalog over the feature
  dimensions; the per-persona/per-show DISTINCT TASTE PROFILE enabler; DJ-set / harmonic /
  energy-arc queryability; schema versioning + the `Track.key` naming-collision guard; the
  acquisition-provenance fields (acquired_at / requested_by / grab_reason) written through the
  allowlist writer without touching the frozen identity fields.
- **Group AP — Analysis Pipeline, Throttling & Graceful Degradation.** On-ingest analysis
  hook; bounded resumable backfill queue throttled with acquisition (OH-006); strictly
  non-blocking to `/api/next`; graceful degradation when analysis lags; a serialized
  analysis worker bounding RAM (OE-012 pattern); observability through the health/status
  surface (NFR-O-6); and a library watch / auto-ingest trigger — a periodic metadata-only
  (stat) scan that picks up manually-dropped files as well as downloads without hammering
  the disk (the WSL2/Docker inotify-unreliable case).
- Plus **NFRs** (Section 13) and **Risks** (Section 14).

### 4.2 Out of scope (explicitly deferred)

- **Sample-accurate beat-aligned continuous-mix RENDER** — the rubberband/ffmpeg
  time-stretch phase-lock that makes a club blend seamless. ANALYSIS-006 produces the
  beat grid / downbeats / camelot / BPM gate INPUTS; the render itself is the deferred
  playout-layer tuning phase (OPS-004 R-O-9 / REQ-OA-014 phasing).
- **The mixing POLICY** (when to beatmatch vs crossfade, EQ-blend mechanics) — owned by
  OPS-004 REQ-OA-014; ANALYSIS-006 only emits the data + `annotate:` fields it reads.
- **The curation POLICY / taste-profile authoring** — owned by CORE-001/OPS-004;
  ANALYSIS-006 only guarantees the data model can represent + query distinct profiles.
- **Tag correction / normalization ACTION** — owned by OPS-004 REQ-OA-010; ANALYSIS-006
  supplies analysis-derived hints and references it.
- **The loudness NORMALIZATION action + the shared constant** — owned by OPS/CORE
  (NFR-O-3); ANALYSIS-006 only MEASURES integrated LUFS / ReplayGain.
- **External metadata API CLIENTS** (MusicBrainz / TheAudioDB / Discogs / Last.fm HTTP
  integration) — the source list and the obligation are OPS-004 REQ-OA-011; ANALYSIS-006
  consumes whatever those clients return and reconciles it. (The reconciliation ALGORITHM
  is in scope; the HTTP clients are not re-owned here.)
- **GPU / deep-learning training** — no model training; if Essentia's pretrained
  CPU TensorFlow genre/mood models are used they are inference-only and config-gated.
- **Real-time / live-stream analysis** — all analysis is offline batch on files at rest;
  no live-signal analysis.
- **A Liquidsoap code change** — the only playout contract is the per-request `annotate:`
  metadata the shipped `crossfade` + `request.dynamic.list` already read.
- **Lyrics / vocal-presence / structural-segmentation beyond cue points** — vocal-detection
  for the no-vocal-over-vocal guard stays a playout-layer / OPS concern; ANALYSIS-006
  provides cue points, not a full song-structure segmentation product.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain = the existing Python `brain/` package.** ANALYSIS-006 extends it
  (`library.py`, `acquire.py`, `config.py`, `server.py`, `director.py`); it adds an
  analysis module, not a new service.
- [HARD] **CPU-only, offline, no GPU.** The core DSP runs on the CPU in the brain
  container. numpy/scipy are acceptable (torch already arriving for Kokoro); no GPU.
- [HARD] **Idempotent + cached.** Analyze a file once, key the result, never recompute on
  re-scan/restart/retry. Caching survives restarts via the persisted index.
- [HARD] **Never blocks the <1s `/api/next` pull.** Analysis is background only; the pull
  serves already-analyzed or default metadata.
- [HARD] **Graceful degradation.** An unanalyzed track still plays with the safe default
  crossfade (NFR-O-11) and conservative cue defaults.
- [HARD] **No store fork.** Extend `brain/library.py`'s `Track` + JSON index in place.
- [HARD] **No Liquidsoap change.** Only per-request `annotate:` metadata is added.
- [HARD] **Loudness measurement only.** Produce integrated LUFS / ReplayGain; the
  normalization action + the -16 LUFS / -1.5 dBTP constant remain OPS/CORE (NFR-O-3).
- [HARD] **License awareness.** Essentia is AGPLv3; librosa is ISC; aubio/keyfinder-cli are
  GPLv3. The brain is a private server-side process and listeners receive only audio (not
  the software), so AGPL's network clause does not force source disclosure to listeners —
  but if the brain's source is ever distributed, AGPL obligations attach. Flagged (R-A-1).

---

## 6. Requirement Group AE — Audio Analysis Engine

Priority: High.

### REQ-AE-001 — Offline CPU audio-analysis extraction (Event-driven) [HARD]

When a track is ingested (a new file appears on the scan/import path) or selected for
backfill, the system shall analyze the audio file LOCALLY on the CPU — with no GPU and no
network call required for the core DSP — and extract a feature record containing at least:
BPM/tempo (+ confidence), beat grid + downbeats where detectable, musical key (+ Camelot)
(+ confidence), energy and danceability, integrated LUFS / ReplayGain track-gain, and the
cue/boundary points of Group AT. The extractor is the recommended toolchain (Essentia
primary, librosa fallback — research.md); the exact algorithm choice is an implementation
detail behind a stable feature record.

**Acceptance criteria:** see acceptance.md AC-AE-001.

### REQ-AE-002 — Idempotent persisted cache, never re-analyze (Ubiquitous) [HARD]

The system shall persist each track's feature record keyed to the file (path + a content
signal such as size/mtime or a hash) so that a re-scan, daemon restart, or retry NEVER
recomputes an existing valid record; analysis runs at most once per file unless the file
changes or a schema-version bump forces re-analysis. The cache is part of the persisted
library index (no separate store).

**Acceptance criteria:** see acceptance.md AC-AE-002.

### REQ-AE-003 — CPU-only / offline / no-GPU rail (Ubiquitous) [HARD]

The system shall perform all audio analysis on the CPU using offline batch processing on
files at rest; it shall NOT require a GPU and shall NOT depend on a remote analysis
service for the core DSP. Any optional pretrained classifier (e.g. Essentia CPU
TensorFlow genre/mood models) is inference-only, CPU-only, and config-gated.

**Acceptance criteria:** see acceptance.md AC-AE-003.

### REQ-AE-004 — Bounded backfill of the existing library (Event-driven + self-scheduled)

When the daemon starts or on a self-scheduled cadence, the system shall run a BACKFILL
pass that analyzes already-ingested tracks lacking a current feature record, processing
them through a bounded, resumable queue (Group AP) so the existing library gains track
intelligence over time without a flood; backfill is distinct from on-ingest analysis of
new downloads and shares the same engine + cache.

**Acceptance criteria:** see acceptance.md AC-AE-004.

### REQ-AE-005 — Per-feature confidence + low-confidence flagging (Ubiquitous) [HARD]

The system shall record a confidence for the error-prone features — at least musical key
and BPM — and shall FLAG low-confidence values so consumers (harmonic mixing REQ-OA-014,
adjacency REQ-OA-006) can refuse to act on an uncertain key/BPM rather than blend into a
clash. Accuracy is best-effort; a wrong-but-flagged value is acceptable, a wrong-and-
trusted value is the defect this requirement prevents.

**Acceptance criteria:** see acceptance.md AC-AE-005.

### REQ-AE-006 — Sonic-character "how it sounds" understanding (Event-driven) [HARD]

When analyzing a track, the system shall derive — beyond BPM/key/genre — a deeper
SONIC-CHARACTER profile describing what the track IS and HOW IT SOUNDS, so the brain
genuinely understands its music rather than reasoning over labels alone. The profile shall
capture at least: mood/affect, timbre/texture, production character (e.g. lo-fi vs
polished, sparse vs dense, warm vs bright), instrumentation feel, vocal-vs-instrumental,
acoustic-vs-electronic, and dynamics (loud/quiet, compressed/dynamic). It is derived from
audio-content analysis — spectral descriptors, MFCC/timbre features, energy/dynamics, and
the Essentia high-level descriptors (REQ-AE-001) — AND/OR a compact audio EMBEDDING for
content similarity, AND/OR an LLM-generated short "sonic description" that is GROUNDED
strictly in the extracted features + reconciled metadata.

[HARD grounding] Any LLM sonic description shall describe ONLY what the extracted features
and reconciled metadata support — it MUST NOT free-hallucinate sonic claims the features do
not back (e.g. it may not call a track "acoustic" when the features read electronic). The
features are the evidence; the description is a grounded summary of them, not invention.
This is the "pre-listen and understand" capability.

[HARD rail scoping] The [HARD] CPU-only / offline / no-network rail (NFR-A-1, REQ-AE-003)
applies to the audio-FEATURE extraction — the core DSP (spectral/MFCC/energy/dynamics +
Essentia high-level descriptors + the optional content embedding), which is computed
CPU-only and offline on files at rest. The OPTIONAL LLM-generated sonic description is NOT
on the no-network DSP path: it uses the brain's EXISTING LLM access (the same provider the
brain already calls), exactly mirroring the OPS-004 OA-011 external-metadata-API exemption
from the no-network rail — it is OFF the playout/`/api/next` path, its result is CACHED and
IDEMPOTENT with the feature record (REQ-AE-002), and a track that has not had (or skips) the
LLM description still has its complete CPU-derived feature/sonic-character record. The LLM
description is therefore optional enrichment over the offline features, never a precondition
of analysis and never a network dependency of the core DSP.

This feeds the data model (REQ-AD-001) + the per-persona separability (REQ-AD-003),
distinguishing personas on SONIC CHARACTER, not only the genre tag (PROGRAMMING-007
REQ-PR-004 anti-convergence firewall consumes this — referenced, not restated).

[Production-observation extension] Beyond describing how a track sounds in the abstract, the
sonic-character understanding extends to PRODUCTION OBSERVATIONS that link a SOURCED production
fact (gear / recording location / production technique) to an audible result in these same
features — specified in REQ-AE-007. That extension reads the production fact from KNOWLEDGE-008
and grounds the audible-result claim in BOTH the feature and the source under a two-leg rule; it
does not change this requirement's CPU-feature extraction or its existing acceptance.

**Acceptance criteria:** see acceptance.md AC-AE-006.

### REQ-AE-007 — Production observation: grounded link of a sourced production fact to an audible feature result (Event-driven) [HARD]

When analyzing a track for which SPEC-RADIO-KNOWLEDGE-008 has a SOURCED PRODUCTION FACT — gear,
recording location, or production technique (e.g. "close-mic'd, damped drum kit", "recorded to
tape at Studio X", "no reverb on the drums", "tracked live in one room") — the system MAY derive a
PRODUCTION OBSERVATION that LINKS that sourced fact to an AUDIBLE RESULT read from the extracted
features: the REQ-AE-006 sonic-character profile plus the spectral / MFCC / energy / dynamics
features (REQ-AE-001) and, where relevant, the cue/boundary signals (Group AT). The observation's
purpose is to let a host ground an audible claim — e.g. "the dry drum tone" — in BOTH the analysis
feature (low reverb / short decay / tight dynamics reading) AND the sourced gear/technique fact,
never in one alone. This is the deeper "understand WHY it sounds that way" capability built on top
of the "understand HOW it sounds" capability of REQ-AE-006.

[HARD two-leg rule] A production observation is VALID only when BOTH legs are present and agree in
direction:
- **Leg 1 — the sourced production fact**, supplied by KNOWLEDGE-008 (REQ-KS-002 entity +
  REQ-KS-003 provenance/as-of + REQ-KS-006 consensus state). ANALYSIS-006 READS this fact; it does
  NOT invent it, re-source it, or re-run consensus on it.
- **Leg 2 — the supporting FEATURE evidence** from the ANALYSIS feature record (REQ-AE-006
  sonic-character profile + the Group AE/AT features) that is consistent with that production fact.

[HARD] NEITHER LEG ALONE is an airable production observation. A sourced gear/location/technique
fact with NO corroborating audible feature is just a KNOWLEDGE-008 fact (not a production
observation); an audible feature reading with NO sourced production fact is just a sonic-character
descriptor (REQ-AE-006, not a production observation). The host grounds the production claim in the
PAIR.

[HARD grounding] The link assertion (the audible-result description) MUST be supported by the
feature evidence — it MUST NOT claim an audible result the features contradict (it may not say "you
can hear the long plate-reverb tail" when the features read dry / no-reverb). And the
production-fact leg carries KNOWLEDGE-008's provenance + consensus state UNCHANGED: a single-source
or unconfirmed production fact (not consensus-passed per REQ-KS-006) yields a HEDGED observation
(grounded per KNOWLEDGE-008's qualified-claim discipline — "reportedly recorded with…"), NOT a
confident one. This mirrors the AE-006 / AT-007 grounded-features-feed-the-LLM principle: the
feature is the audible evidence, the sourced fact is the attributed cause, and the observation is a
grounded summary of the pair — not invention on either side.

[HARD rail scoping] The CPU-only / offline / no-network rail (NFR-A-1, REQ-AE-003) applies to the
FEATURE leg — the spectral/MFCC/energy/dynamics + sonic-character extraction is the CPU-only,
offline DSP output. The LINK reasoning that pairs a sourced fact with the feature reading uses the
brain's EXISTING LLM access (the same provider the brain already calls), OFF the playout/`/api/next`
path, CACHED + IDEMPOTENT with the feature record (REQ-AE-002) — mirroring the AE-006 / AT-007 /
OA-011 exemption. A track that has no production fact, or skips the link step, still has its
complete CPU-derived feature/sonic-character record; the production observation is optional
enrichment, never a precondition of analysis or playout.

[Storage] The production observation is persisted as part of / alongside the sonic-character
profile on the feature record (REQ-AD-001), carrying its own confidence (the strength of
feature↔fact agreement) and a REFERENCE to the KNOWLEDGE-008 fact (entity/fact reference +
that fact's provenance + consensus state) — NOT a re-owned copy that re-runs consensus.

[Boundary] The REVEAL / PRESENTATION mechanic — the solo-the-stem / isolate-the-track CONTENT cue
that surfaces a production observation to the listener — is owned by SPEC-RADIO-LONGFORM-025 Group
LN (forward reference, not yet authored). ANALYSIS-006 supplies ONLY the GROUNDED SONIC SUBSTRATE
(this observation: feature reading + sourced-fact reference + the grounded link); LONGFORM-025 owns
HOW and WHEN a host reveals it. Referenced, not restated. The production FACT itself is
KNOWLEDGE-008's (REQ-KS-002/003/006); referenced, not re-owned.

**Acceptance criteria:** see acceptance.md AC-AE-007.

---

## 7. Requirement Group AT — Transition Intelligence (Q3)

Priority: High.

### REQ-AT-001 — Cue-in detection (Event-driven)

When analyzing a track, the system shall detect a cue-in point — the end of a long intro /
the first downbeat of musical energy — so the playout layer can skip dead intro air on
mix-in; where no meaningful intro is detected, the cue-in defaults to the track start.

**Acceptance criteria:** see acceptance.md AC-AT-001.

### REQ-AT-002 — Cue-out / outro / mix-out detection (Event-driven)

When analyzing a track, the system shall detect a cue-out / mix-out point — where the
outro begins, computed from the energy envelope and the true-end (REQ-AT-003) — so the
playout layer can begin mixing in the next track at the right musical moment; where no
distinct outro is detected, the cue-out defaults to a conservative offset before the true
end.

**Acceptance criteria:** see acceptance.md AC-AT-002.

### REQ-AT-003 — True-end + trailing-silence detection (Event-driven) [HARD]

When analyzing a track, the system shall detect the TRUE END (offset of the last audible
audio) and the length of any TRAILING SILENCE, so a crossfade never fades into silence and
the cue-out is computed against real audio, not file length. This is the precise answer to
"how does it know HOW a song ends" — the decoder knows the file duration; this requirement
adds where the AUDIO actually ends.

**Acceptance criteria:** see acceptance.md AC-AT-003.

### REQ-AT-004 — Beat grid + downbeats for offline club beat-align (Event-driven)

When analyzing a track the AI may club-mix, the system shall produce a beat grid (per-beat
time positions) and, where detectable, downbeats, as the OFFLINE input a future
beat-aligned club blend needs; live Liquidsoap cannot phase-lock beats, so this offline
beat-grid is the prerequisite the deferred mix-render phase (OPS-004 R-O-9) consumes. This
requirement produces the grid; it does NOT perform the time-stretch render.

**Acceptance criteria:** see acceptance.md AC-AT-004.

### REQ-AT-005 — Per-item transition metadata emitted to playout via annotate (Event-driven) [HARD wiring]

When the brain serves a track on the playout pull, the system shall attach per-item
transition metadata to the request as Liquidsoap `annotate:` overrides — the native
`liq_cue_in`, `liq_cue_out`, `liq_cross_duration` (and `liq_fade_in` / `liq_fade_out`
where used) computed from the analyzed cue/boundary points, PLUS custom fields (`bpm`,
`camelot`, `mix_mode`, `energy`) read in the transition function from the source metadata
dict — so the shipped `crossfade(...)` consumes the per-pair cross duration today and a
future club blend reads bpm/camelot/mix_mode. [HARD] No Liquidsoap code change is required;
`annotate:` is a request-protocol feature. This is the brain-only seam to playout.

**Acceptance criteria:** see acceptance.md AC-AT-005.

### REQ-AT-006 — Safe default for unanalyzed tracks; never block the transition (Unwanted) [HARD]

If a track has no feature record yet (analysis pending or failed), then the system shall
still serve it and shall emit conservative default transition metadata (default safe
crossfade per NFR-O-11; cue-in = start; cue-out = a safe offset before duration; no
club blend) so the stream continues with a clean transition; analysis lag or failure
SHALL NOT block, stall, or degrade below the no-sharp-cutoff floor (OPS-004 NFR-O-11),
and SHALL NOT silence the stream (inherited continuous operation wins).

**Acceptance criteria:** see acceptance.md AC-AT-006.

### REQ-AT-007 — Music-theory-informed analysis on the verified features (Event-driven) [HARD]

When reasoning about transitions and curation, the system shall APPLY MUSIC THEORY on top
of the extracted, verified features — using key/mode, tempo, and structure (cue points,
beat grid, energy envelope) for harmonic, modal, and structural reasoning: harmonic/Camelot
compatibility and modal relationships between adjacent tracks, mood implied by mode
(major/minor) + tempo + energy, energy-arc shaping across a set, and sane transition points
(mix at the outro, not mid-phrase). The brain (Claude) has music-theory knowledge; this
requirement requires that knowledge be APPLIED to the verified feature record, NOT used to
assert theory the track's features do not support.

[HARD grounding] Every theory-derived claim shall be grounded in the extracted features:
the analysis MUST NOT claim a key/mode/structure relationship the features (and their
confidence, REQ-AE-005) do not back — a low-confidence key yields a hedged/withheld
harmonic claim, not a confident one. This produces theory-informed transition + adjacency
hints that FEED Group AT (REQ-AT-004/005 beat-grid + annotate emission) and curation
(REQ-AD-004 harmonic/energy-arc queries); it does NOT restate the mixing policy (OPS-004
REQ-OA-014) or the adjacency decision (REQ-OA-006), which consume these hints.

[HARD rail scoping] The [HARD] CPU-only / offline / no-network rail (NFR-A-1, REQ-AE-003)
applies to the FEATURES this requirement reasons over — the key/tempo/cue/beat-grid/energy
record is the CPU-only, offline DSP output. The APPLICATION of music theory itself is an LLM
reasoning step that uses the brain's EXISTING LLM access (the same provider the brain already
calls), mirroring the OPS-004 OA-011 metadata-API exemption from the no-network rail: it runs
OFF the playout/`/api/next` path, and its theory-informed hints are CACHED + IDEMPOTENT with
the feature record (REQ-AE-002). The grounded-features-feed-the-LLM principle stands — the
offline features are the evidence, the LLM only reasons over them — so the theory step is
optional enrichment over the offline record, never a network dependency of the core DSP and
never a precondition of playout (an un-reasoned track still transitions on its CPU-derived
cue points or the safe defaults, REQ-AT-006).

**Acceptance criteria:** see acceptance.md AC-AT-007.

### REQ-AT-008 — Additive spectral-flux boundary feature alongside the energy envelope (Event-driven) [HARD]

When analyzing a track, the system shall compute an ADDITIONAL boundary signal from a
spectral-flux / spectrogram-derived onset & offset analysis — onset (a flux-based estimate of
where musical content begins) and offset (a flux-based estimate of where it ends / the outro
onset) — and persist it ALONGSIDE the existing energy-envelope cue-in / cue-out / true-end /
trailing-silence (REQ-AT-001 / REQ-AT-002 / REQ-AT-003). The spectral-flux signal is a SECOND,
complementary estimate of the same boundaries from a different measurement (frame-to-frame
spectral change rather than RMS energy), recorded as its own fields with a confidence
(REQ-AE-005 pattern).

[HARD] This feature is STRICTLY ADDITIVE. It SHALL NOT replace, displace, or alter the
energy-envelope detector of REQ-AT-001/002/003 — that detector remains the PLAYOUT-CRITICAL
path that computes the cue points actually emitted to playout via `annotate:` (REQ-AT-005). The
spectral-flux boundary is a corroborating / enriching input only: it CORROBORATES the
energy-envelope cue points (agreement raises cue confidence; disagreement flags a boundary as
uncertain) and feeds the AI's transition reasoning (REQ-AT-007 music-theory-informed analysis)
as another GROUNDED input — consistent with the grounded-features-feed-the-LLM principle (the
features are the evidence; the reasoning summarizes them, it does not invent). The brain MAY use
the corroborated/cross-checked boundary in transition reasoning, but the energy-envelope cue
remains the authoritative emitted value unless a future requirement says otherwise.

[HARD] It is bounded and OFF the playout path under the same AE rails: CPU-only, offline,
cached + idempotent (REQ-AE-002 / REQ-AE-003, NFR-A-1/2), and SHALL NOT block, slow, or be on
the sub-1s `/api/next` pull (REQ-AP-003); a track with no spectral-flux boundary yet still
plays on the energy-envelope cue points (or the safe defaults, REQ-AT-006). This requirement
produces the additional feature; it does NOT change the `annotate:` contract or the mixing
policy (OPS-004 REQ-OA-014).

**Acceptance criteria:** see acceptance.md AC-AT-008.

---

## 8. Requirement Group AM — Metadata, Genre & Mood Derivation (Q4)

Priority: High.

### REQ-AM-001 — Genre derivation from multiple sources (Event-driven) [HARD]

When a track is ingested or re-examined, the system shall derive a genre (and sub-genre
where available) from the OPS-004 REQ-OA-011 source set — external metadata (MusicBrainz /
TheAudioDB) + embedded tags — supplemented by the **Last.fm API** community folksonomy
(`artist.getInfo` / `track.getTopTags` / `artist.getTopTags` top tags — strong for
genre/mood enrichment alongside MusicBrainz/TheAudioDB), audio-feature-derived hints (tempo
bucket, energy, danceability), and OPTIONAL LLM classification (the OPS-004 cheap tools-off
curation mode), so the catalog carries a usable genre for every track. The authoritative
source list is OPS-004 REQ-OA-011 (referenced, not re-enumerated); this requirement owns
DERIVING a genre from whatever those sources (now augmented by Last.fm tags) return plus
the audio hints. Last.fm tags are crowd-sourced and noisy and are reconciled, never trusted
blindly, via REQ-AM-003.

**Acceptance criteria:** see acceptance.md AC-AM-001.

### REQ-AM-002 — Mood + descriptive tags (Event-driven)

When a track is ingested or re-examined, the system shall derive mood and descriptive tags
from the same source set — including the Last.fm folksonomy top tags (`track.getTopTags` /
`artist.getTopTags`), a strong crowd source for mood/descriptor tags — plus audio-feature
hints (energy/danceability/tempo/key mode), so the catalog supports mood/energy arcs and
tag-based curation; mood/tags are best-effort, crowd tags are reconciled (REQ-AM-003), and
each carries a confidence (REQ-AE-005 pattern).

**Acceptance criteria:** see acceptance.md AC-AM-002.

### REQ-AM-003 — Multi-source CONSENSUS reconciliation with verified-source allowlist, threshold & confidence (Event-driven) [HARD]

When more than one source supplies a value for the same feature (genre/mood/year/tags), the
system shall reach CONSENSUS before treating that value as fact: a genre/mood/feature claim
shall be CORROBORATED across MULTIPLE LEGITIMATE sources drawn from a configured
VERIFIED-SOURCE ALLOWLIST (e.g. MusicBrainz, TheAudioDB, Last.fm, embedded tags, the
audio-feature analysis itself) and shall meet a configured CONSENSUS THRESHOLD (e.g. agreed
by >= N allowlisted sources, or by one authoritative source) before it is recorded as a
confident catalog value.

The system shall:
- reconcile candidate values by an explicit precedence rule — authoritative external
  metadata (MusicBrainz) over crowd folksonomy (TheAudioDB / Last.fm top tags) over embedded
  tags over audio-feature hints over LLM guess — and by cross-source agreement;
- record per value WHICH sources agreed, the resulting CONSENSUS LEVEL, and a CONFIDENCE, so
  the catalog has ONE value per feature with auditable provenance;
- FLAG / DOWN-WEIGHT single-source or low-consensus values — they are NEVER stated as
  certain (a single-source genre is "candidate", not "confirmed");
- filter/down-weight noisy crowd tags (Last.fm non-genre tags "seen live", "favourites",
  "00s") so they cannot reach consensus on their own;
- raise confidence when more allowlisted sources corroborate.

The allowlist, the consensus threshold, the precedence order, and the crowd-tag filter are
TUNABLE config; the HARD requirement is that fact-level certainty requires multi-source
consensus, single-source claims are flagged, and provenance + consensus level are recorded
— not silent first-wins.

[Coordination] This requirement owns consensus for AUDIO / GENRE / FEATURE claims.
Consensus for researched ARTIST FACTS (biography, history, scene, lineage) is owned by
SPEC-RADIO-KNOWLEDGE-008 (its provenance + verified-facts requirements) — referenced, not
restated. Where both touch an artist, ANALYSIS-006 supplies the audio/genre/feature
consensus and KNOWLEDGE-008 supplies the fact consensus; neither re-owns the other.

**Acceptance criteria:** see acceptance.md AC-AM-003.

### REQ-AM-004 — Garbled-tag correction is referenced, not re-owned (Event-driven)

When a track has garbled/filename-parsed tags (e.g. "Sly & the Familt Stone"), the system
shall route correction through OPS-004 REQ-OA-010 (tag correction/normalization) and shall
consume the corrected artist/title for analysis keying and genre/metadata lookup;
ANALYSIS-006 supplies analysis-derived hints to that correction but does NOT re-own the
tag-fixing action. This requirement exists only to make the boundary explicit and prevent
duplication.

**Acceptance criteria:** see acceptance.md AC-AM-004.

---

## 9. Requirement Group AD — Track-Intelligence Data Model & Queryable Catalog

Priority: High.

### REQ-AD-001 — Extend the Track model with feature fields, no store fork (Ubiquitous) [HARD]

The system shall extend the existing `brain/library.py` `Track` dataclass (and its
persisted JSON index) with the track-intelligence feature fields — bpm, bpm_confidence,
musical_key, camelot, key_confidence, energy, danceability, integrated_lufs,
replaygain_gain_db, cue_in, cue_out, true_end, trailing_silence, beat_grid (or a reference
to it), genre, sub_genre, mood, tags, year, the SONIC-CHARACTER profile (REQ-AE-006:
timbre/texture, production character, instrumentation feel, vocal_instrumental,
acoustic_electronic, dynamics, an optional sonic_description + an optional content
embedding-or-ref), per-value consensus level + provenance (REQ-AM-003), the
acquisition-provenance fields (REQ-AD-006: acquired_at / requested_by / grab_reason), and an
analysis schema_version + analyzed_at — keeping the SAME store and persistence mechanism (no
fork, no separate database). Fields default to empty/None so a pre-analysis `Track` remains
valid. All field mutations go through the controlled allowlist writer; the frozen
identity/dedup fields (path/artist/title/`Track.key`) are never mutated by feature or
provenance updaters (REQ-AD-005 / REQ-AD-006).

**Acceptance criteria:** see acceptance.md AC-AD-001.

### REQ-AD-002 — Queryable catalog over the feature dimensions (Ubiquitous) [HARD]

The system shall provide a way to QUERY the library by the feature dimensions — filter and
rank tracks by genre/sub-genre, musical key / Camelot compatibility, BPM range, energy/
danceability range, mood, era/year, and tags — so curation (OPS-004 REQ-OA-012) can build
genre nights, mood/energy arcs, and BPM/key-matched DJ sets. This is the engine behind the
OA-012 catalog; OA-012 owns the catalog obligation, this requirement provides the queryable
feature dimensions.

**Acceptance criteria:** see acceptance.md AC-AD-002.

### REQ-AD-003 — Data model enables per-persona/per-show DISTINCT taste profiles (Ubiquitous) [HARD]

The system's feature dimensions and queries shall be granular and separable enough that
distinct per-persona/per-show TASTE PROFILES — each an include/exclude genre set plus
bpm/key/energy/era constraints — select MATERIALLY DISTINCT candidate pools, so no two
hosts are forced to converge on the same rotation (the anti-"algorithmic-curation
homogenization" goal, user 2026-06-22). [HARD] ANALYSIS-006 PROVIDES the dimensions
(genre, sub_genre, musical_key/camelot, bpm, energy/danceability, era/year, tags, and the
SONIC-CHARACTER profile of REQ-AE-006 — timbre, production character, mood, instrumentation
feel) and the scoped query that makes profiles separable; the taste profiles themselves and
the curation POLICY live in CORE-001/OPS-004 (referenced, not owned). The requirement is
satisfied when two deliberately distinct profiles yield low-overlap candidate sets from the
same catalog.

[Anti-convergence consumer] The deeper sonic-character + theory understanding (REQ-AE-006,
REQ-AT-007) lets curation distinguish personas on SONIC CHARACTER and lineage, not only the
genre tag — powering SPEC-RADIO-PROGRAMMING-007's anti-convergence firewall (REQ-PR-004,
which is proven against these ANALYSIS-006 taste dimensions) and genuinely-good, diverse
curation. PROGRAMMING-007 owns the firewall POLICY; ANALYSIS-006 owns supplying the
dimensions it is proven against — referenced, not restated.

[Discovery boundary] Last.fm SIMILAR-ARTIST discovery (`artist.getSimilar` /
`tag.getTopArtists`) — expanding a persona's taste with neighbouring artists and driving
TARGETED per-persona acquisition — is a CURATION/ACQUISITION concern that lives in
CORE-001/OPS-004 (it feeds the acquisition wishlist + the taste profile), NOT in the
ANALYSIS engine. ANALYSIS-006 only guarantees that once such discovered artists are
acquired and analyzed, their feature dimensions (above) make the expanded taste profile
queryable and still separable from other personas. The discovery mechanic itself is
referenced here, not owned (see research.md Section 9).

**Acceptance criteria:** see acceptance.md AC-AD-003.

### REQ-AD-004 — DJ-set / harmonic / energy-arc queryability (Event-driven)

When curation builds a sequenced set, the system shall support adjacency-oriented queries —
"next track within ±N BPM and Camelot-compatible with the current track", "tracks forming a
rising energy arc", "key-compatible neighbors" — so the BPM/key-matched DJ-set adjacency
(OPS-004 REQ-OA-006 / REQ-OA-014) can be computed from the catalog. This provides the query
primitives; the adjacency DECISION and mixing policy are OPS-004's.

**Acceptance criteria:** see acceptance.md AC-AD-004.

### REQ-AD-005 — Schema versioning + Track.key naming-collision guard (Ubiquitous) [HARD]

The system shall version the analysis feature schema (an analysis schema_version on each
record) so a schema change can trigger targeted re-analysis (REQ-AE-002), and shall name
the new MUSICAL key field DISTINCTLY (e.g. `musical_key` + `camelot`) so it does NOT collide
with or overwrite the existing `Track.key` field, which is the DEDUP SLUG (artist-title),
not a musical key. [HARD] The dedup `Track.key` semantics MUST be preserved unchanged.

**Acceptance criteria:** see acceptance.md AC-AD-005.

### REQ-AD-006 — Acquisition-provenance fields on the Track record (Ubiquitous) [HARD]

The system shall extend the `Track` record (REQ-AD-001, the record this SPEC owns) with three
ACQUISITION-PROVENANCE fields that record WHY and HOW a track entered the library, distinct from
its analyzed audio features:
- `acquired_at` — the ACQUISITION timestamp: when the track was acquired/decided-on. [HARD] This
  is DISTINCT from the file's `added_at` / filesystem mtime (when the bytes landed on disk):
  acquired_at is the decision/acquisition moment, not the file-write moment, and the two MUST NOT
  be conflated.
- `requested_by` — an enum recording who/what caused the acquisition:
  `director-curated` (the AI director chose it) | `user-requested` (a human asked for it) |
  `ingest-scan` (discovered by the library-watch stat scan, REQ-AP-007, no explicit request) |
  `seed-reference` (came in as part of the seed/reference library, not a fresh acquisition).
- `grab_reason` — the director's STATED REASON for the grab, stored VERBATIM. [HARD] This is an
  UNVERIFIED CLAIM: it is the AI's own words at decision time, NOT a consensus-backed,
  provenance-recorded fact like a genre (REQ-AM-003). It SHALL NEVER be promoted to or treated as
  a verified feature; it carries no consensus level and is never presented as established fact —
  it is provenance/audit narrative only.

[HARD] Write discipline: these provenance fields are written ONLY through the existing allowlist
writer of REQ-AD-001 (the same controlled mutation path the feature fields use). [HARD] The
FROZEN identity/dedup fields — `path`, `artist`, `title`, and the dedup-slug `Track.key`
(REQ-AD-005) — are NEVER touched by any provenance updater; a provenance write may set only the
three fields above (plus, idempotently, leave everything else untouched).

[HARD] Persisted at DECISION TIME as a pure STORED breakdown: the provenance is recorded once
when the acquisition decision is made and is NOT recomputed/derived later from other state. It is
a stored historical record, not a live-derived view.

[Boundary] ANALYSIS-006 owns the FIELDS and the allowlist write-discipline only. The
POPULATING LOGIC — which actor sets `requested_by`, and the text of `grab_reason` (the
director's taste reasoning) — is owned by SPEC-RADIO-PROGRAMMING-007 Group PL (taste
self-learning), specifically REQ-PL-008, and the acquisition path (CORE-001 / OPS-004);
referenced, not re-owned here. PROGRAMMING-007 REQ-PL-008 WRITES `grab_reason` (and sets
`requested_by`) through this SPEC's allowlist writer; ANALYSIS-006 guarantees the record can
carry these fields safely (through the allowlist writer, never touching frozen fields) and
that `grab_reason` is stored verbatim as an unverified claim.

[Boundary — no double-storage of the acquisition actor] `requested_by` here is the ACTOR
CLASS that caused the acquisition (the enum director-curated | user-requested | ingest-scan |
seed-reference), and it is owned/stored ONLY in this field. It is DISTINCT from
PROGRAMMING-007 REQ-PL-001's `source` / `acquired_for` (the channel/target the populating
logic reasons about — e.g. which persona or show slot the grab serves): those are
PROGRAMMING-007's populating-logic concepts, not duplicate copies of the acquisition actor.
[HARD] The acquisition actor is stored in exactly one place — this `requested_by` field —
and is NOT re-stored under REQ-PL-001's source/acquired_for; PROGRAMMING-007 sets
`requested_by` via the allowlist writer rather than mirroring it into a second field.

**Acceptance criteria:** see acceptance.md AC-AD-006.

---

## 10. Requirement Group AP — Analysis Pipeline, Throttling & Graceful Degradation

Priority: High.

### REQ-AP-001 — On-ingest analysis hook (Event-driven)

When a new track is registered on the scan/import path (CORE-001 REQ-A-007 ingest, driven
by `acquire.py` / `slskd.py` / `ytdlp.py`), the system shall enqueue it for analysis so new
downloads gain track intelligence shortly after import, without analysis being part of the
synchronous import critical path.

**Acceptance criteria:** see acceptance.md AC-AP-001.

### REQ-AP-002 — Bounded, resumable, throttled analysis queue (State-driven) [HARD]

While analyzing, the system shall process tracks through a BOUNDED, RESUMABLE queue: it
shall not enqueue an unbounded flood, it shall persist enough state to resume after a
restart without losing or duplicating work (idempotent per REQ-AE-002), and it shall
THROTTLE analysis throughput in concert with acquisition load and system resources — tying
to OPS-004 REQ-OH-006's acquisition accounting / bounded-queue throttle (analysis is
downstream of acquisition). Queue bound + throttle thresholds are TUNABLE config.

**Acceptance criteria:** see acceptance.md AC-AP-002.

### REQ-AP-003 — Analysis never blocks the playout pull (Unwanted) [HARD]

If analysis is in progress, queued, slow, or errored, then the `/api/next` pull SHALL NOT
wait on it: the pull serves a track with its already-analyzed feature record, or with the
safe defaults (REQ-AT-006) if none exists, and never blocks on analysis. [HARD] Analysis is
strictly decoupled from the sub-1s pull path.

**Acceptance criteria:** see acceptance.md AC-AP-003.

### REQ-AP-004 — Graceful degradation under analysis lag (State-driven) [HARD]

While the analysis queue is backed up (e.g. a large backfill or an acquisition burst), the
system shall degrade gracefully: tracks still play with safe-default transitions
(REQ-AT-006), curation queries return the best available data (analyzed where present,
unanalyzed treated as feature-unknown rather than excluded), and the station never stalls
or silences. Analysis lag is an expected operating state, not a failure.

**Acceptance criteria:** see acceptance.md AC-AP-004.

### REQ-AP-005 — Serialized analysis worker to bound RAM (State-driven) [HARD]

While running, the system shall SERIALIZE heavy analysis — it shall not run multiple
full-track analyses concurrently — using a single analysis worker / queue to bound RAM and
CPU contention on the modest cloud box, mirroring OPS-004 REQ-OE-012 / NFR-O-10's
serialized-generator pattern. The worker concurrency (default 1) is TUNABLE config.

**Acceptance criteria:** see acceptance.md AC-AP-005.

### REQ-AP-006 — Observability of the analysis pipeline (Ubiquitous) — Priority Medium

The system shall emit structured logs and surface health/status — analyzed count, backfill
queue depth, throughput, failures, low-confidence rate, schema version — through the
CORE-001 health/status surface (OPS-004 NFR-O-6), sufficient to diagnose an analysis
backlog or accuracy problem after the fact.

**Acceptance criteria:** see acceptance.md AC-AP-006.

### REQ-AP-007 — Library watch / auto-ingest via periodic stat-only scan (State-driven) [HARD]

While running, the system shall keep the library and queryable catalog continuously up to
date with the music directory regardless of how a file got there — slskd/yt-dlp downloads
AND files the user MANUALLY drops in — by detecting new, changed, and removed audio files
and feeding new/changed ones into the analysis pipeline (the on-ingest hook, REQ-AP-001).

[HARD] Detection mechanism: the system SHALL NOT rely on filesystem-event watching
(inotify) ALONE. The music directory is a Windows-hosted bind mount under WSL2 + Docker,
where inotify events do NOT reliably propagate from the host into the Linux container, so a
pure event-watcher silently MISSES manually-dropped files (research.md Section 8). The
system shall instead run a PERIODIC METADATA-ONLY SCAN on a configured interval that walks
the directory with `os.scandir` + `stat` collecting ONLY (path, size, mtime) — performing
NO file-content reads during the scan — and diffs that against a persisted manifest/catalog
keyed by path + size + mtime. This stat-only walk is light even for thousands of files, so
the catalog stays current "without hammering the disk." (An inotify watcher MAY be added as
an OPTIONAL latency-reducing supplement, but the interval stat-scan is the authoritative,
required mechanism; correctness MUST NOT depend on inotify firing.)

Only NEW or CHANGED files (absent from the manifest, or whose size/mtime differs) receive
the expensive treatment — read embedded ID3/Vorbis tags (mutagen/ffprobe) → run BPM/key/
energy/genre analysis (Groups AE/AT/AM) → enrich (OPS-004 REQ-OA-011 sources + filename
fallback) → sort into the clean managed folder structure (OPS-004 REQ-OH-003) → add to the
catalog. REMOVED files (in the manifest, absent on disk) are pruned. The pass is idempotent
and cached: an unchanged file is NEVER re-analyzed (REQ-AE-002). A content-HASH is computed
only WHEN NEEDED to detect a move/rename (same content at a new path — reattach the existing
feature record instead of re-analyzing), NOT on every scan. The scan throttles / backs off
when idle and coordinates with OPS-004 acquisition-accounting (REQ-OH-006) so a download
burst and the scan do not jointly overload the box. The scan interval, the idle back-off,
and whether the optional inotify supplement is enabled are TUNABLE config.

[Relationship] This requirement is the TRIGGER that feeds the on-ingest hook (REQ-AP-001);
AP-001 enqueues whatever this scan (or an acquisition import) discovers. The bounded/
resumable queue (REQ-AP-002), serialized worker (REQ-AP-005), and graceful degradation
(REQ-AP-004, REQ-AT-006 — an undiscovered-or-unanalyzed file still plays with the safe
default crossfade) all apply unchanged.

**Acceptance criteria:** see acceptance.md AC-AP-007.

---

## 11. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following:

- **Sample-accurate beat-aligned continuous-mix RENDER** (rubberband/ffmpeg time-stretch
  phase-lock) — ANALYSIS-006 produces the beat grid / downbeats / camelot / BPM-gate
  inputs; the render is the deferred playout-layer phase (OPS-004 R-O-9 / REQ-OA-014).
- **The mixing POLICY and EQ-blend mechanics** — owned by OPS-004 REQ-OA-014; only the
  data + `annotate:` emission is here.
- **The curation POLICY and taste-profile authoring** — owned by CORE-001/OPS-004; only
  the queryable, separable data model is here.
- **Tag correction / normalization ACTION** — owned by OPS-004 REQ-OA-010 (referenced).
- **The loudness normalization ACTION + the shared LUFS constant** — owned by OPS/CORE
  (NFR-O-3); only the integrated-LUFS / ReplayGain MEASUREMENT is here.
- **External metadata API HTTP clients** (MusicBrainz / TheAudioDB / Discogs / Last.fm) —
  the source obligation is OPS-004 REQ-OA-011; ANALYSIS-006 consumes their output and
  reconciles it, it does not re-own the clients.
- **Similar-artist DISCOVERY + targeted acquisition** (Last.fm `artist.getSimilar` /
  `tag.getTopArtists`; the Gnoosic-style "3 seed artists → neighbours" mechanic) — a
  CORE-001/OPS-004 curation/acquisition concern that expands per-persona taste and drives a
  wishlist; ANALYSIS-006 only keeps discovered-then-acquired tracks queryable/separable
  (REQ-AD-003). Gnoosic has no API and is inspiration only, never integrated.
- **GPU acceleration or any model TRAINING** — CPU-only inference; pretrained models are
  inference-only and config-gated.
- **Real-time / live-signal analysis** — offline batch on files at rest only.
- **A Liquidsoap code change or a new `kind`** — only per-request `annotate:` metadata.
- **Full song-structure segmentation / lyrics / vocal-presence product** — cue points only;
  the no-vocal-over-vocal guard stays a playout/OPS concern.
- **A new datastore** — extend `brain/library.py`'s existing JSON index in place.

---

## 12. Toolchain note (recommendation, not a hard rail)

The recommended primary engine is **Essentia (AGPLv3)** — the only single CPU library that
delivers BPM + beat grid + key + danceability/energy + integrated LUFS in one pass, with
optional CPU pretrained genre/mood models — with **librosa (ISC)** as the permissive
fallback and the cue-point / silence-trim / onset engine, **aubio (GPLv3)** as an optional
fast-tempo cross-check, and **keyfinder-cli (GPLv3)** noted as an alternate key engine. The
full comparison (capability, license, CPU cost, accuracy realities) is in research.md. The
SPEC fixes the FEATURE RECORD + the rails (CPU-only, idempotent, non-blocking, graceful);
the specific library is an implementation choice behind that stable record, and OPS-004
REQ-OA-011 already phrases it as "librosa / aubio / essentia-class tools."

---

## 13. Non-Functional Requirements

### NFR-A-1 — CPU-only / offline analysis (Ubiquitous) — Priority High
All audio analysis shall run on the CPU, offline, on files at rest, with no GPU and no
remote analysis service for the core DSP (REQ-AE-003). See acceptance.md AC-NFR-A-1.

### NFR-A-2 — Idempotent, cached, never re-analyze (Ubiquitous) — Priority High
A file shall be analyzed at most once (keyed by path + content signal), the result
persisted in the library index, and never recomputed on re-scan/restart/retry unless the
file changes or the schema version bumps (REQ-AE-002). See acceptance.md AC-NFR-A-2.

### NFR-A-3 — Non-blocking to the playout pull (Ubiquitous) — Priority High
Analysis shall be fully decoupled from the `/api/next` pull; a pull shall never wait on an
analysis render and shall always be served within the inherited sub-1s budget (REQ-AP-003).
See acceptance.md AC-NFR-A-3.

### NFR-A-4 — Resilience / never-crash, never-silence (Ubiquitous) — Priority High
A failed analysis (corrupt file, decoder error, library exception) shall log and be skipped
without crashing the analysis worker, the director loop, or the daemon, and without
silencing the stream; the track plays with safe defaults (REQ-AT-006, REQ-AP-004). See
acceptance.md AC-NFR-A-4.

### NFR-A-5 — Best-effort accuracy with confidence (Ubiquitous) — Priority High
BPM and especially musical-key accuracy are best-effort; the system shall record a
confidence and flag low-confidence values (REQ-AE-005) so consumers can refuse rather than
act on a wrong value. No requirement asserts correct key/BPM for every track. See
acceptance.md AC-NFR-A-5.

### NFR-A-6 — Simplicity / no over-engineering / no GPU (Ubiquitous) — Priority Medium
This SPEC shall implement the smallest analysis substrate that delivers the feature record,
cue points, queryable catalog, and per-persona separability on the confirmed CPU stack;
deferred items (Section 11) MUST NOT be partially built; no GPU, no new datastore, no
microservice. See acceptance.md AC-NFR-A-6.

### NFR-A-7 — Observability (Ubiquitous) — Priority Medium
The system shall emit structured logs + health/status for analyzed count, queue depth,
throughput, failures, low-confidence rate, and schema version, through the CORE-001
health/status surface (OPS-004 NFR-O-6, REQ-AP-006). See acceptance.md AC-NFR-A-7.

---

## 14. Open Questions / Risks

- **R-A-1 — Essentia AGPLv3 license (Medium).** Essentia is AGPLv3; the brain is a private
  server-side process and listeners receive only audio (not the software), so AGPL's
  network-distribution clause does not force source disclosure to listeners. Residual: if
  the brain's source is ever distributed/published, AGPL obligations attach to the whole
  combined work. Mitigation: keep the analysis engine behind a thin internal interface so
  swapping to librosa-only (ISC) is cheap, and flag the license posture in the build. The
  feature record is engine-agnostic by design (Section 12).
- **R-A-2 — Key-detection accuracy (Medium).** Automatic musical-key detection is
  inherently error-prone (~70-85% "correct" under MIREX-weighted scoring; perfect-fifth /
  relative-minor confusions common — research.md Section 3). Mitigated by per-key confidence
  + low-confidence flagging (REQ-AE-005) so harmonic mixing refuses uncertain keys, and by
  profile choice (edma/temperley). A wrong-but-flagged key is acceptable.
- **R-A-3 — BPM octave errors (Low/Medium).** Tempo estimation commonly halves/doubles the
  true BPM. Mitigated by a confidence threshold + a sane BPM-range clamp + an optional
  aubio cross-check; the ±6% BPM gate for club blends (OA-014) tolerates this when both
  tracks agree.
- **R-A-4 — Cue/outro detection reliability across genres (Medium).** Energy-envelope-based
  outro detection works well for most pop/dance but can misfire on ambient/long-fade/
  classical material. Mitigated by conservative defaults (REQ-AT-006), trailing-silence
  detection (REQ-AT-003), and the safe-crossfade floor (NFR-O-11) so a bad cue degrades to
  a clean fade, never a sharp cut or silence.
- **R-A-5 — CPU analysis latency on a modest box (Medium).** Full-track analysis can take
  seconds per track; a large backfill could lag. Mitigated by the bounded/throttled/
  resumable queue (REQ-AP-002), serialized worker (REQ-AP-005), graceful degradation
  (REQ-AP-004), and the never-block rail (REQ-AP-003). Backfill throughput is a tuning
  concern, not a correctness one.
- **R-A-6 — Essentia wheel availability on the brain's Python (Low/Medium).** `pip install
  essentia` ships Linux CPU wheels, but a very new Python (3.13) may lag wheels. Mitigated
  by the engine-agnostic feature record + librosa (pure-Python) fallback, and by pinning the
  analysis install in `Dockerfile.brain` (the same place Kokoro/torch are installed off the
  default index).
- **R-A-7 — Multi-source metadata reconciliation drift (Low/Medium).** External sources
  disagree on genre/year; a wrong reconciliation degrades genre nights. Mitigated by explicit
  precedence + recorded provenance + confidence (REQ-AM-003) and graceful partial-data
  handling (REQ-AP-004). External-API rate limits are an OPS-004 REQ-OA-011 concern.
- **R-A-8 — Per-persona separability depends on genre granularity (Low/Medium).** If the
  derived genre is too coarse, distinct taste profiles could still overlap. Mitigated by
  sub-genre + mood + tags + audio-feature dimensions (energy/bpm/key/era) giving curation
  enough axes to separate profiles even when top-level genre is coarse (REQ-AD-003); the
  separability is verified by a low-overlap acceptance test, not assumed.
- **R-A-9 — Schema evolution + re-analysis cost (Low).** Bumping the feature schema forces
  re-analysis of the whole library. Mitigated by versioning per record (REQ-AD-005) so only
  stale records re-run, and by the bounded backfill (REQ-AP-002) absorbing the re-run.
- **R-A-10 — WSL2/Docker inotify unreliability for manual file drops (Medium, relayed).**
  REQ-AP-007: the music dir is a Windows-hosted bind mount under WSL2 + Docker; inotify
  events do not reliably propagate host→container, so a pure event-watcher silently misses
  manually-dropped files. Mitigated by making the periodic METADATA-ONLY (`os.scandir`+`stat`)
  manifest-diff scan the AUTHORITATIVE mechanism (correctness never depends on inotify),
  light enough to run frequently without hammering the disk, with inotify only an optional
  latency supplement. Relayed during authoring; confirm with the user. Build concerns: the
  scan interval + idle back-off tuning, and computing a content-hash ONLY to detect
  moves/renames (not every scan) so a renamed file reattaches its feature record instead of
  re-analyzing.
- **R-A-11 — Last.fm crowd-tag noise + API-key/rate limits (Low/Medium, relayed).**
  REQ-AM-001/002/003: Last.fm folksonomy tags are a strong but NOISY genre/mood source
  (non-genre tags like "seen live", "favourites", "00s" appear among the top tags). Mitigated
  by the multi-source reconciliation (REQ-AM-003): authoritative metadata outranks crowd
  folksonomy, a tunable filter drops non-genre tags, tag weight informs confidence, and
  cross-source corroboration boosts it. Needs a free API key (config-gated like the other
  OA-011 sources); responses cached with the feature record (idempotent, REQ-AE-002) and run
  off the playout path to respect rate limits. The Last.fm HTTP client itself is an OA-011
  external-source-client concern, not re-owned here. Relayed during authoring; confirm with
  the user. (Similar-artist discovery is a CORE-001/OPS-004 curation concern — see REQ-AD-003
  discovery-boundary note + research.md Section 9.)
- **R-A-12 — Sonic-character accuracy + LLM-grounding discipline (Medium, relayed).**
  REQ-AE-006: audio-content sonic descriptors (timbre/production/instrumentation/dynamics)
  are best-effort, and an LLM sonic description risks hallucinating sonic claims the features
  do not support. Mitigated by [HARD] grounding (the description summarizes ONLY the extracted
  features + reconciled metadata, never invents), by carrying these as best-effort
  confidence-bearing fields (REQ-AE-005 pattern), and by an optional embedding for
  content-similarity that does not depend on the LLM. Relayed during authoring; confirm with
  the user.
- **R-A-13 — Consensus threshold + verified-source allowlist tuning (Low/Medium, relayed).**
  REQ-AM-003: too strict a consensus threshold leaves many tracks "candidate-only" (thin
  confident genre coverage); too loose lets a single noisy source assert a wrong genre as
  fact. Mitigated by TUNABLE allowlist + threshold + crowd-tag filter, single-source flagging
  (never stated as certain), and graceful use of candidate values where confident ones are
  absent (REQ-AP-004). Coordinates with KNOWLEDGE-008's fact-consensus (artist facts) to
  avoid duplicate/contradictory consensus logic. Relayed during authoring; confirm with the
  user.
- **R-A-14 — Production-observation depends on a sourced fact AND a confident feature reading
  (Medium).** REQ-AE-007: a production observation needs BOTH legs, so coverage is naturally
  thin — most tracks will lack a researched gear/location/technique fact, and where a fact
  exists the feature reading may be ambiguous or contradict it. This is by design, not a defect:
  the two-leg rule means a missing or weak leg simply means no production observation (the track
  still has its full sonic-character record). Risks: (a) the LLM link step over-asserting an
  audible result the features do not back — mitigated by the [HARD] grounding rule (the claim
  must be feature-supported) and the agreement confidence; (b) propagating an unconfirmed
  KNOWLEDGE-008 production fact as certain — mitigated by carrying KNOWLEDGE-008's consensus
  state through unchanged (single-source → hedged), never re-running consensus here (REQ-KS-006
  owns it). The reveal/presentation of the observation is LONGFORM-025 Group LN's, not built
  here. Relayed via assignment; confirm with the user.

---

## 15. Out-of-Scope / Future SPEC Roadmap

- **Beat-aligned continuous-mix RENDER phase** (OPS-004 R-O-9) — consumes this SPEC's beat
  grid / downbeats / camelot / BPM gate to perform a rubberband/ffmpeg time-stretch
  phase-lock blend. Built when the club-mixing sophistication is taken up.
- **Deeper structural segmentation** (verse/chorus/drop detection) — a richer perception
  product beyond cue points, if a future show format needs it.
- **Vocal-presence / no-vocal-over-vocal analysis input** — currently a playout/OPS guard;
  could become an analysis-derived signal in a later phase.
- **External metadata API clients** — the MusicBrainz/TheAudioDB/Discogs/Last.fm HTTP
  integration that OPS-004 REQ-OA-011 owns; ANALYSIS-006 consumes their output.

---

## 16. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md;
detailed Given-When-Then scenarios for the load-bearing requirements are in acceptance.md
Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-AE-001 | Audio Analysis Engine | High | Event | AC-AE-001 |
| REQ-AE-002 | Audio Analysis Engine | High | Ubiquitous | AC-AE-002 |
| REQ-AE-003 | Audio Analysis Engine | High | Ubiquitous | AC-AE-003 |
| REQ-AE-004 | Audio Analysis Engine | High | Event/Self-scheduled | AC-AE-004 |
| REQ-AE-005 | Audio Analysis Engine | High | Ubiquitous | AC-AE-005 |
| REQ-AE-006 | Audio Analysis Engine | High | Event | AC-AE-006 |
| REQ-AE-007 | Audio Analysis Engine | High | Event | AC-AE-007 |
| REQ-AT-001 | Transition Intelligence | High | Event | AC-AT-001 |
| REQ-AT-002 | Transition Intelligence | High | Event | AC-AT-002 |
| REQ-AT-003 | Transition Intelligence | High | Event | AC-AT-003 |
| REQ-AT-004 | Transition Intelligence | Medium | Event | AC-AT-004 |
| REQ-AT-005 | Transition Intelligence | High | Event | AC-AT-005 |
| REQ-AT-006 | Transition Intelligence | High | Unwanted | AC-AT-006 |
| REQ-AT-007 | Transition Intelligence | High | Event | AC-AT-007 |
| REQ-AT-008 | Transition Intelligence | High | Event | AC-AT-008 |
| REQ-AM-001 | Metadata, Genre & Mood | High | Event | AC-AM-001 |
| REQ-AM-002 | Metadata, Genre & Mood | Medium | Event | AC-AM-002 |
| REQ-AM-003 | Metadata, Genre & Mood | High | Event | AC-AM-003 |
| REQ-AM-004 | Metadata, Genre & Mood | Medium | Event | AC-AM-004 |
| REQ-AD-001 | Data Model & Catalog | High | Ubiquitous | AC-AD-001 |
| REQ-AD-002 | Data Model & Catalog | High | Ubiquitous | AC-AD-002 |
| REQ-AD-003 | Data Model & Catalog | High | Ubiquitous | AC-AD-003 |
| REQ-AD-004 | Data Model & Catalog | Medium | Event | AC-AD-004 |
| REQ-AD-005 | Data Model & Catalog | High | Ubiquitous | AC-AD-005 |
| REQ-AD-006 | Data Model & Catalog | High | Ubiquitous | AC-AD-006 |
| REQ-AP-001 | Analysis Pipeline | High | Event | AC-AP-001 |
| REQ-AP-002 | Analysis Pipeline | High | State | AC-AP-002 |
| REQ-AP-003 | Analysis Pipeline | High | Unwanted | AC-AP-003 |
| REQ-AP-004 | Analysis Pipeline | High | State | AC-AP-004 |
| REQ-AP-005 | Analysis Pipeline | High | State | AC-AP-005 |
| REQ-AP-006 | Analysis Pipeline | Medium | Ubiquitous | AC-AP-006 |
| REQ-AP-007 | Analysis Pipeline | High | State | AC-AP-007 |
| NFR-A-1 | Non-Functional | High | Ubiquitous | AC-NFR-A-1 |
| NFR-A-2 | Non-Functional | High | Ubiquitous | AC-NFR-A-2 |
| NFR-A-3 | Non-Functional | High | Ubiquitous | AC-NFR-A-3 |
| NFR-A-4 | Non-Functional | High | Ubiquitous | AC-NFR-A-4 |
| NFR-A-5 | Non-Functional | High | Ubiquitous | AC-NFR-A-5 |
| NFR-A-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-A-6 |
| NFR-A-7 | Non-Functional | Medium | Ubiquitous | AC-NFR-A-7 |
