---
id: SPEC-RADIO-ANALYSIS-006
version: 0.5.0
updated: 2026-06-23
---

# SPEC-RADIO-ANALYSIS-006 — Acceptance Criteria

1:1 REQ ↔ AC mapping: every requirement and NFR in spec.md has exactly one acceptance
entry here (Section A). Detailed Given-When-Then scenarios for the load-bearing
requirements are in Section B. The Definition of Done is in Section C.

All acceptance criteria assume the inherited CORE-001 + OPS-004 behavior holds: analysis
never blocks or silences the stream; no human is in the run loop; the library store is
extended in place (no fork); the only playout contract is per-request `annotate:` metadata
(no Liquidsoap code change).

---

## Section A — Acceptance criteria (1:1 with requirements)

### Group AE — Audio Analysis Engine

**AC-AE-001 (REQ-AE-001).**
- On ingest or backfill selection, a track is analyzed on the CPU (no GPU, no network for
  the core DSP) and a feature record is produced containing BPM (+confidence), beat grid +
  downbeats where detectable, musical key (+Camelot, +confidence), energy, danceability,
  integrated LUFS / ReplayGain, and the Group AT cue/boundary points.
- The feature record is engine-agnostic (same fields regardless of Essentia vs librosa
  path) and attached to the track.
- A file that cannot be decoded logs and is skipped without producing a partial record that
  looks valid.

**AC-AE-002 (REQ-AE-002) [HARD].**
- [HARD] A feature record is keyed by file path + a content signal (size/mtime or hash); a
  re-scan, daemon restart, or retry of an already-analyzed unchanged file produces NO
  recomputation (verified: analysis is invoked at most once per file).
- A changed file (different content signal) or a schema-version bump re-analyzes; an
  unchanged file with a current schema does not.
- The cache lives in the persisted library index (no separate store).

**AC-AE-003 (REQ-AE-003) [HARD].**
- [HARD] All analysis runs on the CPU; no code path requires a GPU and none calls a remote
  analysis service for the core DSP.
- Any optional pretrained classifier is inference-only, CPU-only, and disabled unless
  explicitly config-enabled.

**AC-AE-004 (REQ-AE-004).**
- On daemon start / self-scheduled cadence, tracks lacking a current feature record are
  enqueued for backfill through the bounded queue (Group AP) and analyzed over time.
- Backfill shares the engine + cache with on-ingest analysis (no second code path) and does
  not flood the system.
- Backfill is resumable: restarting mid-backfill continues without re-analyzing completed
  tracks or losing pending ones.

**AC-AE-005 (REQ-AE-005) [HARD].**
- [HARD] Each record carries a confidence for at least musical key and BPM; values below a
  configured threshold are flagged.
- A consumer (harmonic-mixing / adjacency query) can see the flag and refuse to act on a
  low-confidence key/BPM (verified: a flagged-low key is not used as a harmonic-match basis).
- A wrong-but-flagged value is acceptable; a wrong-and-unflagged value is the defect this
  prevents.

**AC-AE-006 (REQ-AE-006) [HARD].**
- [HARD] Each analyzed track gains a sonic-character profile capturing at least mood,
  timbre/texture, production character, instrumentation feel, vocal-vs-instrumental,
  acoustic-vs-electronic, and dynamics, derived from audio-content features (spectral/MFCC/
  energy + Essentia high-level descriptors) and/or a content embedding and/or a grounded LLM
  sonic description.
- [HARD] Any LLM sonic description is GROUNDED in the extracted features + reconciled
  metadata — verified: a description does not assert a sonic claim the features contradict
  (e.g. it does not label an electronic-feature track "acoustic"); fed a feature set, the
  description only restates what those features support.
- [HARD] Rail scoping: the CPU-only / offline / no-network rail (AC-NFR-A-1, AC-AE-003)
  applies to the audio-FEATURE extraction (the core DSP + optional content embedding), which
  is computed CPU-only/offline on files at rest. The OPTIONAL LLM sonic description is NOT on
  the no-network DSP path: it uses the brain's EXISTING LLM access (mirroring the OPS-004
  OA-011 metadata-API exemption from the no-network rail), runs OFF the `/api/next` path, and
  its result is CACHED + idempotent with the feature record (AC-AE-002) — verified: a track
  WITHOUT the LLM description still has a complete CPU-derived feature/sonic-character record,
  and the no-network DSP path does not make an LLM/network call. The LLM description is
  optional enrichment, never a precondition of analysis.
- The profile feeds the data model (AC-AD-001) and per-persona separability (AC-AD-003).

**AC-AE-007 (REQ-AE-007) [HARD].**
- [HARD] When a track has a SOURCED production fact in KNOWLEDGE-008 (gear / recording location /
  production technique) AND the extracted features support it, analysis derives a PRODUCTION
  OBSERVATION that LINKS the sourced fact to an audible result from the feature record (e.g. the
  sourced "close-mic'd, damped kit" technique linked to the analysis's low-reverb / short-decay /
  tight-dynamics reading → the audible "dry drum tone") — grounded in BOTH legs.
- [HARD] Two-leg rule: the observation is recorded ONLY when BOTH legs are present and agree — a
  sourced production fact with NO corroborating audible feature yields NO production observation
  (it remains a KNOWLEDGE-008 fact), and an audible feature reading with NO sourced production fact
  yields NO production observation (it remains a sonic-character descriptor, AC-AE-006). Verified:
  feeding only one leg produces no production observation.
- [HARD] Grounding: the audible-result claim does NOT assert a result the features contradict
  (verified: it does not claim an audible reverb tail when the features read dry); and the
  production-fact leg carries KNOWLEDGE-008's consensus state unchanged — a single-source /
  unconfirmed production fact yields a HEDGED observation ("reportedly recorded with…"), not a
  confident one (verified: ANALYSIS-006 does not re-run consensus on the fact; REQ-KS-006 owns it).
- [HARD] Rail scoping: the feature leg is CPU-only / offline (AC-NFR-A-1, AC-AE-003); the link
  reasoning uses the brain's EXISTING LLM access OFF the `/api/next` path, cached + idempotent with
  the feature record (AC-AE-002) — verified: a track with no production fact (or that skips the link
  step) still has its complete CPU-derived feature/sonic-character record, and the production
  observation is never a precondition of analysis or playout.
- The production observation is stored alongside the sonic-character profile (AC-AD-001) with its
  own confidence and a REFERENCE to the KNOWLEDGE-008 fact (provenance + consensus state), not a
  re-owned copy.
- The reveal / presentation cue (solo-the-stem / isolate-the-track) is SPEC-RADIO-LONGFORM-025 Group
  LN's (forward-ref); ANALYSIS-006 supplies only the grounded substrate (verified: no
  reveal/presentation logic here).

### Group AT — Transition Intelligence (Q3)

**AC-AT-001 (REQ-AT-001).**
- Analysis produces a cue-in offset; for a track with a long quiet intro the cue-in is
  after the intro (skips dead air); for a track that starts immediately the cue-in defaults
  to the track start.

**AC-AT-002 (REQ-AT-002).**
- Analysis produces a cue-out / mix-out offset before the true end (REQ-AT-003), at the
  outro onset where detectable; where no distinct outro is detected the cue-out defaults to
  a conservative offset before the true end.

**AC-AT-003 (REQ-AT-003) [HARD].**
- [HARD] Analysis produces the true-end offset (last audible audio) and the trailing-silence
  length; a track with N seconds of trailing silence yields a true-end ≈ duration − N and a
  trailing_silence ≈ N (verified within tolerance on a track with known padding).
- The cue-out (REQ-AT-002) is computed against the true end, not the file length, so a
  crossfade never fades into silence.

**AC-AT-004 (REQ-AT-004).**
- For a 4/4 rhythmic track, analysis produces a beat grid (per-beat times) and, where
  detectable, downbeats; the grid spacing is consistent with the detected BPM.
- This requirement does NOT perform a time-stretch render; it only produces the grid the
  deferred mix-render phase (OPS-004 R-O-9) consumes.

**AC-AT-005 (REQ-AT-005) [HARD wiring].**
- [HARD] On the playout pull, the served request carries `annotate:` overrides:
  `liq_cue_in` / `liq_cue_out` / `liq_cross_duration` (and `liq_fade_in` / `liq_fade_out`
  where used) from the analyzed cue/boundary points, plus custom fields `bpm`, `camelot`,
  `mix_mode`, `energy`.
- The shipped `crossfade(...)` reads `liq_cross_duration` to vary the per-pair fade; the
  custom fields are readable in a transition function from the source metadata dict.
- [HARD] No Liquidsoap code change is required (verified: only the request string the brain
  emits changes).

**AC-AT-006 (REQ-AT-006) [HARD].**
- [HARD] A track with no feature record still plays, with conservative default transition
  metadata (safe crossfade per NFR-O-11; cue-in = start; cue-out = safe offset before
  duration; no club blend).
- [HARD] Analysis lag or failure never blocks/stalls the transition, never drops below the
  no-sharp-cutoff floor (OPS-004 NFR-O-11), and never silences the stream (verified by
  serving an unanalyzed track and confirming a clean default crossfade).

**AC-AT-007 (REQ-AT-007) [HARD].**
- [HARD] Music theory is APPLIED on the verified features: harmonic/Camelot + modal
  relationships, mood-from-mode+tempo+energy, energy-arc shaping, and sane transition points
  (mix at the outro, not mid-phrase) are produced from the feature record.
- [HARD] Every theory claim is grounded in the features: a low-confidence key (AC-AE-005)
  yields a hedged/withheld harmonic claim, not a confident one (verified: theory does not
  assert a relationship the features do not support).
- The theory-informed hints feed AT (AC-AT-004/005) + curation (AC-AD-004); they do not
  restate the OPS-004 mixing policy or adjacency decision.

**AC-AT-008 (REQ-AT-008) [HARD].**
- [HARD] Analysis produces an ADDITIONAL spectral-flux / spectrogram-derived onset & offset
  (a flux-based boundary estimate) persisted ALONGSIDE the energy-envelope cue-in / cue-out /
  true-end (AC-AT-001/002/003), as its own fields with a confidence.
- [HARD] The energy-envelope detector is NOT replaced: the cue points actually emitted to
  playout via `annotate:` (AC-AT-005) still come from the energy-envelope path (verified: the
  emitted `liq_cue_in`/`liq_cue_out` are the energy-envelope values; the spectral-flux fields
  are additive metadata, not the emitted values).
- The spectral-flux boundary CORROBORATES the energy-envelope cue points — agreement raises cue
  confidence, disagreement flags the boundary uncertain — and is available as a GROUNDED input
  to the music-theory transition reasoning (AC-AT-007).
- [HARD] It runs under the AE rails (CPU-only/offline/cached/idempotent, AC-AE-002/003) and is
  OFF the playout path: it never blocks or slows `/api/next` (AC-AP-003); a track with no
  spectral-flux boundary yet still plays on the energy-envelope cue points or the safe defaults
  (AC-AT-006).

### Group AM — Metadata, Genre & Mood Derivation (Q4)

**AC-AM-001 (REQ-AM-001) [HARD].**
- [HARD] Each track is given a genre (and sub-genre where available) derived from the
  OA-011 source set (external metadata + embedded tags) augmented by Last.fm folksonomy top
  tags (`artist.getInfo` / `track.getTopTags` / `artist.getTopTags`) plus audio-feature
  hints and optional LLM classification.
- The source list is OA-011's (not re-enumerated here); a track with no external/embedded
  genre still receives a best-effort audio-hint-derived genre rather than none.
- Last.fm tags are crowd-sourced and reconciled via AC-AM-003, never trusted blindly.

**AC-AM-002 (REQ-AM-002).**
- Each track is given mood + descriptive tags from the same sources — including Last.fm
  top tags (`track.getTopTags` / `artist.getTopTags`) — plus audio-feature hints, each
  best-effort with a confidence; missing mood/tags degrade gracefully (empty, not an error).

**AC-AM-003 (REQ-AM-003) [HARD].**
- [HARD] A genre/mood/feature value is treated as CONFIRMED only when corroborated across
  multiple sources from the verified-source allowlist meeting the configured consensus
  threshold (>= N allowlisted sources, or one authoritative source); the record stores which
  sources agreed, the consensus level, and a confidence (verified: a value below threshold is
  stored as "candidate", not "confirmed").
- [HARD] Single-source or low-consensus values are FLAGGED / down-weighted and NEVER stated
  as certain (verified: a single-source genre is not presented as confirmed).
- [HARD] When sources disagree, precedence resolves the winner (MusicBrainz > TheAudioDB /
  Last.fm crowd folksonomy > embedded > audio-hint > LLM) and the resolution is deterministic
  with recorded provenance; noisy crowd tags ("seen live", "favourites", "00s") are
  filtered/down-weighted and cannot reach consensus alone (verified: a junk Last.fm tag does
  not become the genre); more corroborating allowlisted sources raise confidence.
- The allowlist, threshold, precedence order, and crowd-tag filter are TUNABLE config.
- [HARD] Consensus here covers AUDIO/GENRE/FEATURE claims only; researched ARTIST-FACT
  consensus is SPEC-RADIO-KNOWLEDGE-008's (verified: no artist-fact consensus logic is
  duplicated here).

**AC-AM-004 (REQ-AM-004).**
- A track with a garbled tag (e.g. "Sly & the Familt Stone") is corrected via OPS-004
  REQ-OA-010 and the corrected artist/title is used for analysis keying + metadata lookup;
  ANALYSIS-006 does not re-implement tag correction (verified: no duplicate tag-fix logic).

### Group AD — Data Model & Queryable Catalog

**AC-AD-001 (REQ-AD-001) [HARD].**
- [HARD] The `Track` dataclass + JSON index gain the feature fields (bpm, bpm_confidence,
  musical_key, camelot, key_confidence, energy, danceability, integrated_lufs,
  replaygain_gain_db, cue_in, cue_out, true_end, trailing_silence, beat_grid-or-ref, genre,
  sub_genre, mood, tags, year, the sonic-character profile of AC-AE-006 — timbre/production/
  instrumentation/vocal_instrumental/acoustic_electronic/dynamics + optional
  sonic_description + optional embedding-or-ref, per-value consensus level + provenance from
  AC-AM-003, schema_version, analyzed_at) using the SAME store (no fork).
- A pre-analysis `Track` (fields empty/None) loads and plays without error (backward
  compatible with existing persisted records).

**AC-AD-002 (REQ-AD-002) [HARD].**
- [HARD] The library can be queried/filtered/ranked by genre/sub-genre, key/Camelot, BPM
  range, energy/danceability range, mood, era/year, and tags.
- The query is the engine behind OPS-004 REQ-OA-012's catalog (verified: a "genre = soul,
  era 1965-1979" query returns only matching analyzed tracks).

**AC-AD-003 (REQ-AD-003) [HARD].**
- [HARD] Given two deliberately distinct taste profiles (e.g. P1 = {genre in [soul, funk],
  era 1965-1979}; P2 = {genre in [techno, house], bpm 120-130, Camelot-harmonic}), querying
  the same catalog with each yields MATERIALLY DISTINCT (low-overlap) candidate pools —
  proving the feature dimensions (now including the sonic-character profile, AC-AE-006)
  support per-persona separation so no two hosts converge on the same rotation.
- [HARD] ANALYSIS-006 provides the dimensions + the scoped query; it does NOT author the
  taste profiles or the curation policy (those are CORE-001/OPS-004) — verified: no curation
  policy is hardcoded here.
- The sonic-character + theory dimensions let personas be distinguished on SOUND + lineage,
  not just genre tag, powering PROGRAMMING-007 REQ-PR-004's anti-convergence firewall (which
  is proven against these dimensions); PROGRAMMING-007 owns the firewall policy, ANALYSIS-006
  owns the dimensions (verified: no firewall policy here).
- Last.fm similar-artist DISCOVERY (`artist.getSimilar` / `tag.getTopArtists`) that expands
  a persona's taste and drives targeted acquisition is a CORE-001/OPS-004 concern, NOT in
  the analysis engine (verified: no discovery/acquisition logic here); once discovered
  artists are acquired and analyzed, their dimensions keep the expanded profile queryable
  and separable.

**AC-AD-004 (REQ-AD-004).**
- Adjacency queries work: "next track within ±N BPM and Camelot-compatible with the current
  track", "rising energy arc", "key-compatible neighbors" return correct candidates from the
  catalog.
- This provides query primitives; the adjacency DECISION + mixing policy remain OPS-004's.

**AC-AD-005 (REQ-AD-005) [HARD].**
- [HARD] Each feature record carries an analysis schema_version; bumping it triggers
  targeted re-analysis (AC-AE-002) of stale records only.
- [HARD] The new musical-key field is named distinctly (`musical_key` + `camelot`) and the
  existing `Track.key` (dedup slug) is preserved unchanged (verified: dedup still works;
  musical key is a separate field, never overwriting `Track.key`).

**AC-AD-006 (REQ-AD-006) [HARD].**
- [HARD] The `Track` record gains three acquisition-provenance fields: `acquired_at` (the
  acquisition-decision timestamp), `requested_by` (enum: director-curated | user-requested |
  ingest-scan | seed-reference), and `grab_reason` (free text).
- [HARD] `acquired_at` is DISTINCT from the file's `added_at` / filesystem mtime — verified: a
  track whose bytes were written at time T1 but whose acquisition decision was made at T0 stores
  acquired_at = T0, not T1; the two are never conflated.
- [HARD] `grab_reason` is stored VERBATIM as an UNVERIFIED claim: it carries no consensus level,
  is never promoted to a verified feature, and is never presented as established fact alongside
  consensus-backed features like genre (AC-AM-003) — verified: nothing treats grab_reason as a
  fact or runs consensus on it.
- [HARD] Provenance is written ONLY through the existing allowlist writer (AC-AD-001); a
  provenance update sets only the three fields above and NEVER touches the frozen identity/dedup
  fields `path` / `artist` / `title` / `Track.key` (verified: after a provenance write, the dedup
  slug and identity fields are byte-identical to before).
- [HARD] Provenance is persisted at DECISION TIME as a pure stored breakdown — recorded once when
  the acquisition decision is made, not recomputed/derived later (verified: the stored values do
  not change on re-scan/re-analysis).
- ANALYSIS-006 owns only the fields + write discipline; the populating logic (which actor sets
  `requested_by`, the `grab_reason` text) is PROGRAMMING-007 Group PL / the acquisition path,
  referenced not re-owned (verified: no taste/reason-authoring logic here).

### Group AP — Analysis Pipeline, Throttling & Graceful Degradation

**AC-AP-001 (REQ-AP-001).**
- A newly registered track (via `acquire.py`/`slskd.py`/`ytdlp.py` → scan/import) is
  enqueued for analysis shortly after import; analysis is NOT on the synchronous import
  critical path (import completes without waiting for analysis).

**AC-AP-002 (REQ-AP-002) [HARD].**
- [HARD] The analysis queue is bounded (no unbounded flood), resumable across restarts
  (idempotent per AC-AE-002, no lost/duplicated work), and throttled in concert with
  acquisition load (ties to OPS-004 REQ-OH-006).
- Queue bound + throttle thresholds are TUNABLE config (verified: setting a small bound
  caps in-flight analysis).

**AC-AP-003 (REQ-AP-003) [HARD].**
- [HARD] With analysis in progress/queued/slow/errored, `/api/next` still returns within the
  inherited sub-1s budget, serving the analyzed record or the safe defaults (AC-AT-006) —
  never waiting on analysis (verified by forcing a slow/stuck analysis and confirming the
  pull is unaffected).

**AC-AP-004 (REQ-AP-004) [HARD].**
- [HARD] Under a backed-up queue (large backfill / acquisition burst), tracks still play
  with safe-default transitions, curation queries return best-available data (unanalyzed =
  feature-unknown, not excluded), and the station never stalls or silences.
- Analysis lag is treated as an expected operating state, not a failure.

**AC-AP-005 (REQ-AP-005) [HARD].**
- [HARD] Heavy analysis is serialized — no two full-track analyses run concurrently — via a
  single worker/queue (default concurrency 1, TUNABLE), bounding RAM/CPU contention
  (verified: concurrent enqueue does not spawn parallel analyses).

**AC-AP-006 (REQ-AP-006).**
- Structured logs + health/status surface analyzed count, backfill queue depth, throughput,
  failures, low-confidence rate, and schema version, through the CORE-001 health/status
  surface (OPS-004 NFR-O-6).

**AC-AP-007 (REQ-AP-007) [HARD].**
- [HARD] A file the user MANUALLY drops into the music dir (no slskd/yt-dlp involvement) is
  detected and enqueued for ingest within one scan interval — verified WITHOUT relying on any
  inotify event firing (the case that fails on the WSL2/Docker bind mount).
- [HARD] Detection is a periodic metadata-only scan: it uses `os.scandir` + `stat`
  (path/size/mtime) only and reads NO file content during the scan; the scan is diffed
  against a persisted manifest keyed by path + size + mtime (verified: scanning N files does
  N stats, not N content reads).
- Only new (absent from manifest) or changed (size/mtime differs) files get the expensive
  treatment (tag read → analysis → enrich → sort into the managed folder structure per
  OPS-004 REQ-OH-003 → catalog add); an unchanged file is NOT re-analyzed (AC-AE-002).
- Removed files (in manifest, absent on disk) are pruned from the catalog.
- A content-hash is computed only when needed to detect a move/rename (same content, new
  path → reattach the existing feature record), NOT on every scan.
- The scan throttles / backs off when idle and coordinates with OPS-004 acquisition
  accounting (REQ-OH-006); scan interval + idle back-off + optional-inotify-supplement are
  TUNABLE config.
- A file discovered but not yet analyzed still plays with the safe default crossfade
  (AC-AT-006); the catalog being briefly behind never stalls or silences the stream.

### Non-Functional

**AC-NFR-A-1 (NFR-A-1).** All analysis runs CPU-only, offline, on files at rest; no GPU,
no remote DSP service (verified by inspecting the analysis path).

**AC-NFR-A-2 (NFR-A-2).** A file is analyzed at most once (keyed by path + content signal),
cached in the index, never recomputed on re-scan/restart/retry absent a content/schema
change (AC-AE-002).

**AC-NFR-A-3 (NFR-A-3).** `/api/next` never waits on analysis and stays within the
sub-1s budget (AC-AP-003).

**AC-NFR-A-4 (NFR-A-4).** A corrupt-file / decoder-error / exception logs and is skipped
without crashing the worker, the director loop, or the daemon, and without silencing the
stream (AC-AT-006, AC-AP-004).

**AC-NFR-A-5 (NFR-A-5).** Key/BPM are best-effort with recorded confidence + low-confidence
flagging (AC-AE-005); no requirement asserts correct key/BPM for every track.

**AC-NFR-A-6 (NFR-A-6).** The implementation is the smallest substrate delivering the
feature record + cue points + queryable catalog + per-persona separability on the CPU stack;
no deferred item (Section 11) is partially built; no GPU, no new datastore, no microservice.

**AC-NFR-A-7 (NFR-A-7).** Logs + health/status expose analyzed count, queue depth,
throughput, failures, low-confidence rate, and schema version (AC-AP-006).

---

## Section B — Given-When-Then scenarios (load-bearing requirements)

### B1 — REQ-AE-001 / REQ-AE-002 (analyze once, cache, never recompute)

```
Given a freshly imported FLAC with no feature record
When the analysis worker processes it
Then a feature record is produced with bpm, musical_key, camelot, energy, danceability,
     integrated_lufs, cue_in, cue_out, true_end, trailing_silence, and a beat grid
And the record is persisted in the library index keyed by path + content signal
And the record carries schema_version and analyzed_at

Given that same FLAC, unchanged, after a daemon restart and re-scan
When the scan re-encounters the file
Then NO re-analysis occurs (the cached record is reused)

Given the file's content signal changes (re-downloaded at higher bitrate)
When the scan encounters it
Then it is re-analyzed and the record is replaced
```

### B2 — REQ-AT-003 / REQ-AT-002 (true-end, trailing silence, cue-out against real audio)

```
Given a track that is 200.0s long with 6.0s of trailing digital silence
When analysis runs
Then true_end ≈ 194.0s (within tolerance) and trailing_silence ≈ 6.0s
And cue_out is computed at the outro onset, no later than true_end (never at 200.0s)
So a crossfade beginning at cue_out fades over real audio, not into the 6s of silence
```

### B3 — REQ-AT-005 / REQ-AT-006 (annotate emission; safe default when unanalyzed)

```
Given an analyzed track with cue_in=2.5, cue_out=190.0, bpm=124, camelot="8A", energy=0.7
When the brain serves it on the playout pull
Then the request string includes annotate: liq_cue_in="2.5", liq_cue_out="190.0",
     liq_cross_duration=<computed>, bpm="124", camelot="8A", mix_mode="<ai-chosen>",
     energy="0.7"
And no Liquidsoap source code is changed (only the request the brain emits)

Given an UNANALYZED track (no feature record) is selected for the pull
When the brain serves it
Then it emits conservative defaults (safe crossfade per NFR-O-11; liq_cue_in="0";
     liq_cue_out=<safe offset before duration>; no club blend)
And the transition is a clean fade, never a sharp cut, never silence
```

### B4 — REQ-AM-003 (multi-source CONSENSUS with allowlist, threshold + provenance)

```
Given MusicBrainz reports genre "soul", TheAudioDB reports "funk/soul",
      Last.fm top tags are ["soul", "funk", "seen live", "favourites"],
      and the embedded tag says "R&B" for the same track
When consensus reconciliation runs (allowlist = MB/TheAudioDB/Last.fm/embedded/audio;
     precedence MusicBrainz > TheAudioDB/Last.fm > embedded > audio-hint; threshold >= 2)
Then the noisy Last.fm tags "seen live"/"favourites" are filtered out
And "soul" is corroborated by MusicBrainz + Last.fm (>= 2 allowlisted) → CONFIRMED, confidence raised
And the resolved genre = "soul", winning source "musicbrainz", consensus level + provenance recorded

Given a different track where ONLY a single Last.fm tag "vaporwave" exists (no other source)
When consensus runs
Then "vaporwave" is stored as a CANDIDATE, flagged low-consensus, and NOT presented as certain
```

### B5 — REQ-AD-003 (per-persona distinct taste profiles — the critical consumer req)

```
Given a catalog of analyzed tracks spanning many genres/eras/tempos
And taste profile P1 = {genre in [soul, funk], era 1965-1979}
And taste profile P2 = {genre in [techno, house], bpm 120-130, Camelot-harmonic}
When curation queries the catalog with P1 and with P2 separately
Then P1's candidate pool and P2's candidate pool are materially DISTINCT (low overlap)
So two hosts using these profiles do not converge on the same rotation
And ANALYSIS-006 supplied only the queryable dimensions — the profiles + curation policy
    came from CORE-001/OPS-004
```

### B6 — REQ-AP-003 / REQ-AP-005 (non-blocking pull; serialized worker)

```
Given the analysis worker is mid-way through a slow full-track analysis
When five new tracks are imported and /api/next is pulled repeatedly
Then each /api/next returns within the sub-1s budget (never waits on the analysis)
And the five new tracks are enqueued, not analyzed in parallel
And only one analysis runs at a time (serialized, default concurrency 1)
```

### B7 — REQ-AD-005 (Track.key naming-collision guard)

```
Given the existing Track dataclass where `key` is the dedup slug "sly and the family stone - thank you"
When the feature fields are added
Then the musical key is stored in a NEW field `musical_key` (e.g. "A minor") with `camelot` (e.g. "8A")
And the existing `Track.key` dedup slug is preserved unchanged (dedup still works)
And no code path writes a musical key into `Track.key`
```

### B8 — REQ-AP-007 (library watch / auto-ingest; manual drop; stat-only scan)

```
Given the music dir is a Windows-hosted bind mount under WSL2 + Docker (inotify unreliable)
And the user copies a new FLAC directly into the music dir from Windows
And NO inotify event fires inside the container
When the next periodic metadata-only scan runs
Then the scan walks the dir with os.scandir+stat (path/size/mtime), reading NO file content
And it diffs against the persisted manifest, finds the FLAC absent, and enqueues it for ingest
And the FLAC is then tag-read, analyzed, enriched, sorted into the managed folder, and cataloged
And the catalog is up to date within one scan interval, without a content read per file

Given a file already in the manifest, unchanged (same size/mtime), on the next scan
Then it is skipped (no re-stat-triggered re-analysis; AC-AE-002 holds)

Given a file present in the manifest but now deleted on disk
Then it is pruned from the catalog on the next scan

Given a file that was moved/renamed (same content, new path)
Then a content-hash (computed only for this move-detection case) matches the existing record
And the feature record is reattached to the new path rather than re-analyzed
```

### B9 — REQ-AE-006 / REQ-AT-007 (sonic-character grounding + theory on verified features)

```
Given a track whose extracted features read: high spectral flatness/noise, four-on-the-floor
      beat grid, BPM 128, synthetic timbre, no detected vocals, key A minor (high confidence)
When the sonic-character profile + theory analysis run
Then the profile reports electronic / instrumental / driving / dense — grounded in the features
And the LLM sonic description does NOT call it "acoustic" or "vocal-led" (features contradict that)
And theory reasoning reports key A minor → Camelot 8A and offers harmonic neighbours (8A/7A/9A/8B)
And the harmonic claim is confident BECAUSE the key confidence is high

Given a second track with LOW key confidence
When theory analysis runs
Then the harmonic claim is hedged/withheld (not asserted as a confident match basis)
```

### B10 — REQ-AT-008 (additive spectral-flux boundary corroborates, never replaces)

```
Given a track analyzed with energy-envelope cue_in=2.5 and cue_out=190.0
When the spectral-flux / spectrogram boundary analysis also runs
Then additional fields flux_onset and flux_offset are stored alongside the energy-envelope cues
And the spectral-flux fields carry a confidence
And the cue points EMITTED to playout via annotate: (liq_cue_in/liq_cue_out, AC-AT-005) remain
    the ENERGY-ENVELOPE values (2.5 / 190.0) — the spectral-flux fields are additive metadata

Given flux_onset agrees closely with the energy-envelope cue_in
Then the cue-in is marked higher-confidence (corroborated)

Given flux_offset disagrees materially with the energy-envelope cue_out
Then the boundary is flagged uncertain and surfaced to the theory reasoning (AC-AT-007) as a
    grounded cross-check — but playout still uses the energy-envelope cue_out

Given a track with no spectral-flux boundary computed yet
When it is served on the pull
Then it plays on the energy-envelope cue points (or safe defaults, AC-AT-006); the flux analysis
    never blocked or slowed /api/next (AC-AP-003)
```

### B11 — REQ-AD-006 (acquisition provenance; verbatim unverified grab_reason; frozen fields untouched)

```
Given the director decides at 2026-06-23T10:00Z to acquire a track because "fills the late-night
      ambient gap on Persona X's Tuesday set"
And the file's bytes are written to disk at 2026-06-23T10:07Z (mtime/added_at)
When the provenance is recorded through the allowlist writer at decision time
Then acquired_at = 2026-06-23T10:00Z (NOT the 10:07Z file mtime — the two are not conflated)
And requested_by = "director-curated"
And grab_reason = "fills the late-night ambient gap on Persona X's Tuesday set" stored VERBATIM
And grab_reason carries no consensus level and is never treated as a verified fact

Given the same track already has artist/title/Track.key (dedup slug) set
When the provenance write runs
Then path / artist / title / Track.key are byte-identical before and after (frozen, untouched)
And only acquired_at / requested_by / grab_reason were written

Given the track is re-scanned and re-analyzed later
Then acquired_at / requested_by / grab_reason do NOT change (recorded once at decision time,
    a pure stored breakdown, not recomputed)

Given a file discovered by the library-watch stat scan (REQ-AP-007) with no explicit request
Then requested_by = "ingest-scan"
```

### B12 — REQ-AE-007 (production observation: two-leg grounded link; reveal deferred to LONGFORM-025)

```
Given KNOWLEDGE-008 holds a SOURCED, consensus-passed production fact for the track:
      "drums close-mic'd on a damped kit in a dry room" (provenance + as-of recorded)
And the extracted features read: low reverberance / short decay tail, tight transient dynamics,
      drum-band timbre present
When the production-observation step runs (link reasoning over the verified feature record)
Then a PRODUCTION OBSERVATION is recorded linking the sourced "dry close-mic" fact to the
     audible "dry drum tone" feature reading — grounded in BOTH legs
And it is stored alongside the sonic-character profile with its own agreement-confidence and a
    REFERENCE to the KNOWLEDGE-008 fact (provenance + consensus state), not a re-owned copy
And the audible-result claim does not assert anything the features contradict (no "reverb tail")

Given the SAME sourced fact but features that read LONG reverb tail / wet ambience (contradicting)
When the step runs
Then NO production observation is recorded (the two legs do not agree)
And the track keeps its full sonic-character record regardless (AC-AE-006)

Given a sourced production fact exists but NO supporting audible feature (one leg only)
Then NO production observation is recorded (a bare KNOWLEDGE-008 fact is not an observation)

Given an audible "dry" feature reading but NO sourced production fact (one leg only)
Then NO production observation is recorded (a bare sonic descriptor is not an observation)

Given the production fact is SINGLE-SOURCE / not consensus-passed in KNOWLEDGE-008 (REQ-KS-006)
When an observation is derived
Then it is HEDGED ("reportedly recorded with…"), not stated as confident
And ANALYSIS-006 does NOT re-run consensus on the fact (KNOWLEDGE-008 owns REQ-KS-006)

Given a track with no production fact at all
When it is served on the playout pull
Then it plays normally on its CPU-derived features / safe defaults; the production observation
    was never a precondition of analysis or playout, and the link step made no /api/next call

Note: the REVEAL of a production observation to the listener (solo-the-stem / isolate-the-track)
is SPEC-RADIO-LONGFORM-025 Group LN's content mechanic — ANALYSIS-006 supplies only this grounded
substrate, never the presentation.
```

---

## Section C — Definition of Done

- All 32 REQ + 7 NFR have a passing acceptance check (Section A), with Section B scenarios
  green for the load-bearing requirements.
- The analysis engine runs CPU-only/offline, is idempotent + cached (never re-analyzes),
  and never blocks the sub-1s `/api/next` pull (NFR-A-1/2/3).
- The `Track` model + JSON index are extended IN PLACE (no fork); a pre-analysis `Track`
  remains valid; the dedup `Track.key` is preserved and the musical key is a distinct field
  (REQ-AD-001/005).
- Cue-in / cue-out / true-end / trailing-silence / beat-grid are produced, and per-item
  transition metadata is emitted via `annotate:` with NO Liquidsoap code change
  (REQ-AT-001..006); music-theory reasoning is applied on the verified features, grounded —
  no theory claim the features don't support (REQ-AT-007); an ADDITIVE spectral-flux /
  spectrogram-derived onset & offset corroborates the energy-envelope cue points and feeds the
  theory reasoning as a grounded cross-check WITHOUT replacing the playout-critical
  energy-envelope detector or the emitted cues (REQ-AT-008).
- A sonic-character "how it sounds" profile (mood/timbre/production/instrumentation/vocal/
  acoustic/dynamics +/- embedding +/- grounded LLM description) is produced under the AE
  rails, the LLM description grounded strictly in the extracted features (REQ-AE-006).
- A PRODUCTION OBSERVATION links a SOURCED production fact (gear/location/technique from
  KNOWLEDGE-008, with its provenance + consensus state) to an audible feature result under the
  TWO-LEG rule — valid only when both legs are present and agree, neither leg alone airable;
  the audible-result claim never contradicts the features, a single-source production fact yields
  a hedged observation, and ANALYSIS-006 never re-runs the fact's consensus (KNOWLEDGE-008 owns
  REQ-KS-006); the observation rides the AE rails (cached/idempotent, link step off the playout
  path) and the reveal/presentation mechanic is referenced to LONGFORM-025 Group LN, not built
  here (REQ-AE-007).
- Genre/mood/tags reach multi-source CONSENSUS (verified-source allowlist + threshold +
  confidence); single-source/low-consensus values are flagged, never stated as certain;
  artist-fact consensus is deferred to KNOWLEDGE-008; tag correction is referenced to OPS-004
  REQ-OA-010, not duplicated (REQ-AM-001..004).
- The catalog is queryable by every feature dimension, and two distinct taste profiles
  yield low-overlap candidate pools (REQ-AD-002/003/004).
- The `Track` record carries the acquisition-provenance fields acquired_at (distinct from file
  mtime/added_at), requested_by (director-curated | user-requested | ingest-scan | seed-reference),
  and grab_reason (stored verbatim as an unverified claim, never a verified fact); they are
  written only through the allowlist writer, never touch the frozen identity/dedup fields, and are
  persisted once at decision time; the populating logic is referenced to PROGRAMMING-007 Group PL,
  not re-owned (REQ-AD-006).
- The pipeline is bounded/resumable/throttled, serialized, and degrades gracefully under
  lag without stalling or silencing the stream (REQ-AP-001..006, NFR-A-4).
- Library watch / auto-ingest keeps the catalog current for manually-dropped files AND
  downloads via a periodic metadata-only (`os.scandir`+`stat`) manifest-diff scan that does
  NOT depend on inotify (the WSL2/Docker bind-mount case), reads no content during the scan,
  analyzes only new/changed files, prunes removed files, and hashes only to detect moves
  (REQ-AP-007).
- Key/BPM carry confidence + low-confidence flags; consumers can refuse uncertain values
  (REQ-AE-005, NFR-A-5).
- Observability surfaces analyzed count, queue depth, throughput, failures, low-confidence
  rate, schema version (REQ-AP-006, NFR-A-7).
- No deferred item (Section 11) is partially built; no GPU, no new datastore, no
  microservice (NFR-A-6).
- No CORE-001 / OPS-004 / VOICE-002 requirement is re-specified, forked, or weakened.
