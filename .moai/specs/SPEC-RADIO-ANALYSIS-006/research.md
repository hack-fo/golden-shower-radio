# SPEC-RADIO-ANALYSIS-006 — Research

Research artifact for the Track Intelligence audio-analysis substrate. Covers: the
analysis toolchain comparison (capability / license / CPU cost / accuracy), BPM and
key-detection accuracy realities, cue-point / onset / silence detection, the Liquidsoap
`annotate:` + cue + ReplayGain interface, harmonic (Camelot) mixing + BPM gating, the
explicit Q3 "how does it know when/how a song ends" explainer, and the per-persona
taste-profile data-model note. Sources are cited inline; library availability/versions
were confirmed via Context7 and the projects' own docs.

---

## 1. Toolchain comparison — librosa / aubio / Essentia / keyfinder-cli

The brain is a Python package (`brain/`) already carrying `mutagen`, and gaining CPU
`torch` (for Kokoro TTS) in `Dockerfile.brain` — so `numpy`/`scipy`/`numba` and CPU ML
wheels are acceptable. Constraint set: CPU-only, offline, cached, idempotent, must not
block the sub-1s `/api/next` pull, runs on a modest single cloud box.

| Library | License | Delivers | CPU cost | Notes |
|---------|---------|----------|----------|-------|
| **Essentia** | **AGPLv3** | BPM + beat grid + confidence (`RhythmExtractor2013`, `PercivalBpmEstimator`); key + scale + strength (`KeyExtractor`, profiles edma/krumhansl/temperley); `Danceability`; **integrated LUFS** (`LoudnessEBUR128`); one-shot `MusicExtractor`; optional CPU **pretrained genre/mood TensorFlow models** (`essentia-tensorflow`) | Moderate (C++ core, fast per track) | The ONLY single CPU library that produces the full feature set in one pass. `pip install essentia` ships Linux CPU wheels; `essentia-tensorflow` adds the pretrained models. CPU-only; TF inference optional. AGPLv3 is the catch — see §1.1. |
| **librosa** | **ISC** (permissive) | `beat_track` (tempo + beat frames); `feature.chroma_cqt` / `chroma_stft` (→ key via a template); `feature.rms` (energy / outro envelope); `onset.onset_detect`; `effects.trim` (silence trim → true-end / trailing silence); `load` | Higher (pure Python + numpy/scipy/numba; numba JIT helps) | Permissive license, deps already compatible with the stack. Best for cue-point / silence / onset / energy. No built-in key classifier (add a Krumhansl-Schmuckler template over chroma) and no LUFS/danceability built in. The safe FALLBACK and the cue/silence engine. |
| **aubio** | **GPLv3** | `aubiotempo` (fast BPM), `aubioonset`, `aubiopitch`, beat tracking | Low (C library, real-time-grade) | Fast tempo + onset. No key, no LUFS, no danceability. PyPI wheels can lag new Python releases. Useful as an optional fast-tempo CROSS-CHECK against Essentia to catch octave errors. |
| **keyfinder-cli** / libKeyFinder | **GPLv3** | Musical key only (the engine behind Mixxx) | Low | Single-purpose, Camelot-friendly key detection; a separate native binary dependency. Noted as an ALTERNATE key engine if Essentia's key is weak on the catalog. |

Sources: Essentia algorithms reference and install docs (essentia.upf.edu/algorithms_reference.html,
essentia.upf.edu/installing.html), Essentia repo (github.com/MTG/essentia — "released under
the Affero GPLv3 license"); librosa docs (librosa.org); aubio (aubio.org / github.com/aubio/aubio);
libKeyFinder (github.com/mixxxdj/libkeyfinder). Library IDs/availability confirmed via Context7
(`/librosa/librosa`, `/aubio/aubio`, `/mtg/essentia`).

### 1.1 The Essentia AGPLv3 question (load-bearing — R-A-1)

Essentia is **AGPLv3**. librosa is **ISC** (permissive), aubio and libKeyFinder are
**GPLv3**. AGPL's distinguishing clause: if you DISTRIBUTE the software OR let users
interact with a MODIFIED version over a network, you must offer the corresponding source.

For this station:
- The brain is a PRIVATE, server-side process. Listeners receive only the audio STREAM,
  not the software, and audio output is not a "derivative work" of the analysis library —
  so AGPL's network clause does NOT force source disclosure to listeners.
- The risk is purely: if the brain's SOURCE is ever distributed/published (or run as a
  modified networked service for third parties), AGPL obligations attach to the combined
  work.

Mitigation (designed into the SPEC): keep the analysis engine behind a thin internal
interface and an engine-agnostic FEATURE RECORD (REQ-AE-001) so swapping to a
librosa-only (ISC) path is cheap if the license posture ever becomes a problem. Install
Essentia in `Dockerfile.brain` (the same place Kokoro/torch are installed off the default
index), not via the default `requirements.txt`.

### 1.2 Recommendation

**Primary: Essentia. Fallback / cue + silence engine: librosa.** Essentia is recommended
because it is the only CPU library that produces BPM + beat grid + key + danceability +
integrated LUFS in a single pass — which is precisely the per-track idempotent batch this
SPEC needs, and it matches OPS-004 REQ-OA-011's "librosa / aubio / essentia-class tools"
phrasing. librosa is the permissive fallback and owns cue-point / silence-trim / onset /
energy detection (`effects.trim`, `onset_detect`, `feature.rms`) regardless of engine.
aubio is an optional fast-tempo cross-check; keyfinder-cli is an alternate key engine. The
SPEC fixes the feature record + the rails; the library is an implementation choice behind
that stable record.

---

## 2. Q3 — "How does the station know WHEN and HOW a song ends?"

This is the user's recurring question and the reason Group AT exists.

**The literal end was never the gap.** Liquidsoap's decoder/request already knows each
track's exact DURATION. The end-of-file is precisely known. What was missing is the
MUSICAL information needed to transition INTELLIGENTLY rather than just at the file end:

1. **Cue-out / outro onset** (REQ-AT-002): where the outro begins, so the next track can
   start being mixed in at the right musical moment — not when the file happens to end.
2. **True end + trailing silence** (REQ-AT-003): where the AUDIO actually ends. Many files
   carry seconds of trailing digital silence; a crossfade timed to file duration fades into
   that silence. Detecting the true end (librosa `effects.trim`, or an RMS-threshold scan
   from the tail) lets the cue-out be computed against real audio.
3. **Tempo + beat grid + downbeats** (REQ-AT-004): so a CLUB blend can beat-align. Live
   Liquidsoap CANNOT phase-lock beats; that needs an offline beat grid + a time-stretch
   render. ANALYSIS-006 produces the grid; the render is deferred (OPS-004 R-O-9).

**How it reaches playout — the brain-only seam (REQ-AT-005).** The brain attaches per-item
metadata to the served request using Liquidsoap's `annotate:` request protocol:

```
annotate:liq_cue_in="2.5",liq_cue_out="190.0",liq_cross_duration="4.0",bpm="124",camelot="8A",mix_mode="crossfade",energy="0.7":<uri>
```

- `liq_cue_in` / `liq_cue_out` are Liquidsoap NATIVE metadata fields consumed by `cue_cut`
  to trim the start/end of the played track to the cue region (so dead intro air and
  trailing silence are skipped). Confirmed special fields: `liq_cue_in`, `liq_cue_out`,
  `liq_fade_in`, `liq_fade_out`, `liq_cross_duration`, `liq_amplify`, `replaygain`
  (liquidsoap.info/doc-dev/metadata.html).
- `liq_cross_duration` tells the crossfade how long to fade for THIS pair — so the shipped
  `crossfade(duration=4.0, fade_in=3.0, fade_out=3.0, smart=true, source)` can vary the
  fade per track instead of a fixed 4s.
- CUSTOM (non-`liq_`) fields — `bpm`, `camelot`, `mix_mode`, `energy` — are passed through
  as ordinary metadata and read inside a transition function from the source metadata dict
  (e.g. `m["camelot"]`), exactly as the metadata docs show custom keys being accessed. A
  future club blend reads `bpm`/`camelot`/`mix_mode` to decide whether to beat-align.

No Liquidsoap source code changes: `annotate:` is a request-protocol feature
(liquidsoap.info/doc-dev/protocols.html — `annotate:key="val",...:uri` "Add metadata to a
request"). The brain changes only the request string it emits on `/api/next`.

**Folded-in mixing research (prior effort):**
- TRUE beatmatching needs OFFLINE beat-grid analysis + a rubberband / ffmpeg time-stretch
  render to phase-lock two tracks; live Liquidsoap cannot phase-lock beats. So the offline
  beat grid (REQ-AT-004) is the prerequisite, and the render is the deferred phase.
- HARMONIC (Camelot) compatibility + a **±6% BPM gate** is the robust QUALIFIER for whether
  to even attempt a DJ blend: only blend when keys are Camelot-compatible AND tempos are
  within ±6% (a range tempo-stretch can bridge without artefacts).
- An EQ BASS-SWAP (sweeping `filter.iir.eq.high` / low-shelf between the outgoing and
  incoming track) is a solid MID-TIER club transition that does not require sample-accurate
  beat-lock — a good intermediate step before full beatmatching.

**Interaction with ReplayGain / loudness.** `replaygain` / `liq_amplify` are also `annotate`
metadata. ANALYSIS-006 MEASURES integrated LUFS (Essentia `LoudnessEBUR128`) / ReplayGain
track-gain and can supply it; the actual normalization to the shared −16 LUFS / −1.5 dBTP
target is owned by OPS/CORE (NFR-O-3) and is referenced, not re-owned here.

---

## 3. BPM and key-detection accuracy realities (R-A-2, R-A-3)

These set honest expectations; the SPEC encodes confidence + flagging (REQ-AE-005) rather
than pretending analysis is exact.

**BPM / tempo.** Modern estimators (Essentia `RhythmExtractor2013`, librosa `beat_track`)
are robust for steady 4/4 material. The dominant failure mode is the **octave error**: the
estimate is half or double the true tempo (e.g. 70 vs 140). Mitigations: a confidence score
(RhythmExtractor2013 returns one), a sane BPM-range clamp (e.g. fold into 70-180), and an
optional aubio cross-check. The ±6% club-blend gate (§2) tolerates residual error because
both tracks must AGREE.

**Musical key.** Automatic key detection is INHERENTLY error-prone. Realistic accuracy is
~70-85% "correct" depending on genre and algorithm, and the standard MIREX-style scoring
gives PARTIAL credit for the predictable confusions:
- **Correct** (full credit),
- **Perfect fifth** (e.g. C vs G — dominant/subdominant confusion),
- **Relative major/minor** (e.g. C major vs A minor — share the same notes),
- **Parallel major/minor** (e.g. C major vs C minor).

These confusions arise because the algorithms estimate key from chroma/pitch-class profiles
(Krumhansl-Schmuckler templates, or Essentia's edma/temperley/krumhansl profiles), and
related keys share pitch content. Practical guidance:
- Choose the profile empirically; `edma` and `temperley` often beat the classic Krumhansl
  profile on contemporary/electronic material.
- Record a key STRENGTH/confidence and FLAG low-confidence keys (REQ-AE-005) so harmonic
  mixing refuses an uncertain match rather than blending into a clash. A wrong-but-flagged
  key is acceptable; a wrong-and-trusted key is the harmful case.

(General MIR accuracy framing from the MIREX evaluation tradition and the
Krumhansl-Schmuckler key-finding method; algorithm/profile names confirmed in Essentia's
KeyExtractor docs.)

---

## 4. Cue points, onsets, energy, silence

- **True end + trailing silence** (REQ-AT-003): librosa `effects.trim(y, top_db=...)`
  returns the trimmed signal + the (start, end) sample indices of non-silent audio; the end
  index gives the true end and `duration − true_end` gives the trailing silence. Equivalent:
  scan the RMS envelope (`feature.rms`) from the tail for the last frame above a dB floor.
- **Cue-in** (REQ-AT-001): the first sustained rise in the RMS / onset-strength envelope
  past the intro — the end of a long quiet intro / first downbeat of energy. Default to 0
  when no meaningful intro is present.
- **Cue-out / outro** (REQ-AT-002): the point where the energy envelope begins its sustained
  decline before the true end (the outro onset). Default to a conservative offset before the
  true end when no distinct outro is detected.
- **Beat grid + downbeats** (REQ-AT-004): Essentia `RhythmExtractor2013` (or `BeatTrackerDegara`/
  `BeatTrackerMultiFeature`) returns beat positions; librosa `beat_track` returns beat frames.
  Downbeats (bar firsts) are detectable on strongly metered material; where not, the grid
  alone is still useful.
- **Energy / danceability** (REQ-AM-002 hints): Essentia `Danceability` + RMS energy give the
  intensity / rhythmic-regularity descriptors used for energy arcs and as genre/mood hints.

These work well on pop/dance/rock; ambient, long-fade, live, and classical material is the
hard case (R-A-4), which is why conservative defaults + the safe-crossfade floor (NFR-O-11)
catch a bad cue and degrade to a clean fade rather than a sharp cut or silence.

---

## 5. Harmonic mixing — the Camelot wheel + BPM gate

Camelot notation maps each musical key to a number (1-12) + letter (A = minor inner ring,
B = major outer ring), e.g. 8B = C major, 8A = A minor. Harmonic compatibility rules
(mixedinkey.com/camelot-wheel/):
- **Same code** (8A → 8A): perfect match.
- **Adjacent number, same letter** (8A → 7A or 9A): smooth.
- **Same number, switch letter** (8A → 8B): smooth (relative major/minor).

For the station: ANALYSIS-006 stores `musical_key` + `camelot` per track, and the catalog
exposes a "Camelot-compatible neighbours" query (REQ-AD-004). The DJ-blend qualifier is
Camelot-compatible AND within the ±6% BPM gate (§2). This is why both `musical_key`
confidence AND BPM confidence matter — a low-confidence key should not be used to claim a
harmonic match.

---

## 6. Per-persona distinct taste profiles — data-model note (REQ-AD-003)

The critical consumer requirement (user, 2026-06-22): each host has its OWN unique,
hand-curated genres/style/taste, and the catalog must let curation SEPARATE personas by
genre/feature so no two hosts converge on the same rotation — the
anti-"algorithmic-curation homogenization" goal.

ANALYSIS-006's responsibility is narrow and clear: PROVIDE the feature DIMENSIONS that make
distinct taste profiles QUERYABLE and SEPARABLE. The dimensions:
- `genre` + `sub_genre` (the primary separation axis),
- `mood` + `tags` (secondary descriptive axes),
- `musical_key` / `camelot`, `bpm`, `energy` / `danceability` (sonic axes),
- `era` / `year` (temporal axis).

A taste profile is then an include/exclude genre set plus bounds on the sonic/temporal axes.
The data model satisfies the requirement when two deliberately distinct profiles select
MATERIALLY DISTINCT (low-overlap) candidate pools from the same catalog (verified by the
acceptance test, not assumed). Granularity matters (R-A-8): if `genre` is too coarse,
profiles could still overlap — so `sub_genre` + mood + the sonic axes give curation enough
separation even when the top-level genre is broad.

The taste profiles themselves, the targeted per-persona acquisition, and the curation policy
live in CORE-001 / OPS-004 — ANALYSIS-006 references them and does not author them. This
keeps the brain-only seam clean: ANALYSIS provides dimensions; curation consumes them.

---

## 7. Integration seam in the existing brain (confirmed by reading the code)

- `brain/library.py`: `Track` is a frozen-ish dataclass {path, artist, title, album, key,
  added_at, last_played, play_count} persisted to a JSON index under `DB_DIR`; `scan()`
  reads tags via `mutagen` (+ `%ARTIST% - %TITLE%` filename fallback) and dedups via
  `normalize_key`; `pick_next()` is the least-recently-played picker; `mark_played()`
  updates history. ANALYSIS-006 EXTENDS `Track` with feature fields and adds the analysis
  pass — same store, same persistence (REQ-AD-001), backward compatible.
- **Naming-collision guard (REQ-AD-005):** `Track.key` here is the DEDUP SLUG, NOT a musical
  key. The new musical key MUST be a distinct field (`musical_key` + `camelot`) so it never
  overwrites the dedup `key`.
- `brain/acquire.py` / `slskd.py` / `ytdlp.py`: the import path that lands new files; the
  on-ingest analysis hook (REQ-AP-001) attaches here, off the synchronous critical path.
- `brain/server.py` (`/api/next`) + `brain/director.py` (the async loop): the pull must
  never wait on analysis (REQ-AP-003); the serialized analysis worker (REQ-AP-005) runs in
  the director loop, mirroring OPS-004 REQ-OE-012's serialized-generator pattern. The
  `annotate:` metadata (REQ-AT-005) is added to the request the server emits.
- `requirements.txt` carries `mutagen`, `httpx`, `piper-tts`, `claude-agent-sdk`; the
  analysis engine (Essentia + librosa) is installed in `Dockerfile.brain` alongside the
  CPU torch/Kokoro stack, NOT in the default-index `requirements.txt` (the same pattern the
  file already documents for the Kokoro stack).

---

## 8. Library watch / auto-ingest — why interval-scan-with-manifest, not inotify (REQ-AP-007)

The user wants the brain to pick up music they MANUALLY drop into the music directory (not
only slskd/yt-dlp downloads), identify and analyze it, sort it, and keep the catalog current
— "without constantly hammering the disk."

**The WSL2 + Docker inotify gotcha (the load-bearing reason).** The music directory is a
Windows-hosted path bind-mounted into a Linux container under WSL2 + Docker. Across that
host→guest boundary, Linux `inotify` filesystem events do NOT reliably propagate: a file
written on the Windows side (or even from another WSL distro) frequently fires NO inotify
event inside the container. This is a well-known limitation of the 9P / drvfs / bind-mount
path used for Windows-hosted files under WSL2 + Docker Desktop — inotify works for changes
made INSIDE the Linux filesystem, but not for changes that originate on the Windows host. A
pure event-watcher (e.g. `watchdog`/`inotify`) therefore SILENTLY MISSES manually-dropped
files: no event, no ingest, the file never enters the catalog. This is exactly the failure
the user is asking to avoid.

**The robust mechanism: a periodic metadata-only scan diffed against a manifest.** Instead of
trusting events, walk the directory on an interval with `os.scandir` + `stat`, collecting
ONLY (path, size, mtime) per entry — performing NO file-content reads during the walk —
and diff that snapshot against a persisted manifest/catalog keyed by path + size + mtime:

- A `stat` is a single inode metadata read; it does NOT open or read the file body. A walk
  of even several thousand files is milliseconds-to-low-seconds of metadata I/O — light
  enough to run frequently, which is precisely "stay up to date without hammering the disk."
  (`os.scandir` is the efficient choice because it returns dirent + a cached `stat` in one
  syscall per entry on Linux, avoiding a second `stat` call.)
- The DIFF classifies entries cheaply: NEW (path absent from manifest), CHANGED (path present
  but size or mtime differs), REMOVED (path in manifest, absent on disk), UNCHANGED
  (everything matches → skipped).
- Only NEW and CHANGED files pay the expensive cost: read embedded ID3/Vorbis tags
  (mutagen/ffprobe), run BPM/key/energy/genre analysis (Groups AE/AT/AM), enrich (OA-011
  sources + filename fallback), sort into the managed folder structure (OH-003), add to the
  catalog. UNCHANGED files cost only their `stat` — never a re-analysis (idempotent, AC-AE-002).
- REMOVED files are pruned. This matches and generalizes the existing `brain/library.py`
  `scan()`, which already walks with `os.walk`, dedups, and prunes vanished files — AP-007
  formalizes it as the authoritative watch mechanism, adds the size/mtime manifest so it does
  not re-tag-read unchanged files, and adds the deletion/move handling.

**Content-hash only for move/rename detection, not every scan.** Hashing a file body is
expensive (a full content read) — the opposite of the stat-only goal — so it is used ONLY in
the narrow case of detecting a MOVE/RENAME: when the diff shows a NEW path AND a REMOVED path
with the same size, a hash of just those two candidates confirms they are the same content,
and the existing feature record is reattached to the new path instead of re-analyzing. The
common case (unchanged files) never hashes.

**inotify as an optional supplement, never the source of truth.** An inotify/watchdog watcher
MAY be added to react FASTER to changes made inside the Linux filesystem (e.g. slskd writing
into a container-side download dir). But correctness must never depend on it firing; the
interval stat-scan is the authoritative mechanism that catches everything inotify misses
(especially Windows-host manual drops). Configure the scan interval + idle back-off so the
scan runs often enough to feel responsive but backs off when nothing is changing, and so a
download burst (OH-006 acquisition accounting) and the scan do not jointly overload the box.

**Graceful degradation.** A just-dropped file that the scan has not yet picked up, or has
picked up but not yet analyzed, still plays with the safe default crossfade (AT-006). The
catalog being briefly behind the filesystem is an expected state, never a stall or silence.

---

## 9. Last.fm as a metadata + discovery source; Gnoosic as inspiration (REQ-AM-001/002/003, AD-003)

The user pointed to Last.fm and Gnoosic as discovery aids. These split cleanly along the
ANALYSIS-vs-CURATION boundary: Last.fm's TAGS augment this SPEC's genre/mood enrichment;
Last.fm's SIMILAR-ARTIST graph and Gnoosic's mechanic are curation/acquisition (CORE-001/
OPS-004), referenced here, not owned.

### 9.1 Last.fm as a genre/mood TAG source (in scope — feeds reconciliation)

The Last.fm API (free; requires registering for an API key) exposes a large community
FOLKSONOMY — user-applied tags — that is a strong complement to MusicBrainz and TheAudioDB
for genre/mood enrichment. Relevant methods (confirmed against last.fm/api):
- `artist.getInfo` — artist bio + the artist's top tags + listener/playcount stats.
- `track.getTopTags` — the crowd's tags for a specific track (the most granular genre/mood
  signal).
- `artist.getTopTags` — the crowd's tags for an artist (fallback when a track has few tags).

These feed REQ-AM-001 (genre) and REQ-AM-002 (mood + descriptive tags) as an ADDITIONAL
source alongside MusicBrainz/TheAudioDB/embedded tags/audio hints.

**The catch — crowd tags are noisy (handled by REQ-AM-003).** Last.fm's top tags mix real
genre/mood descriptors ("soul", "funk", "melancholic") with non-genre noise ("seen live",
"favourites", "albums i own", "00s", "british"). So Last.fm tags are NEVER trusted blindly:
they enter the existing multi-source reconciliation (REQ-AM-003) where authoritative metadata
(MusicBrainz) outranks crowd folksonomy (TheAudioDB / Last.fm), a tunable filter/allow-list
drops obvious non-genre tags, tag WEIGHT (Last.fm returns a count/weight per tag) informs
confidence, and a tag corroborated across multiple sources gains confidence. The result is
one reconciled genre/mood per track with recorded provenance — Last.fm contributes breadth
without polluting the catalog.

**Practical notes:** register a free API key (config-gated like the other OPS-004 REQ-OA-011
external sources); cache responses with the feature record so re-analysis does not re-hit the
API (idempotent per REQ-AE-002); respect Last.fm's rate guidance (cache + batch, run off the
playout path). The Last.fm HTTP CLIENT is an OPS-004 REQ-OA-011 external-source-client concern
(same category as the MusicBrainz/TheAudioDB clients); ANALYSIS-006 owns reconciling whatever
it returns, not the client implementation.

### 9.2 Last.fm SIMILAR-ARTIST discovery (out of the analysis engine — curation/acquisition)

`artist.getSimilar` (artists similar to a given artist) and `tag.getTopArtists` (top artists
for a genre tag) are a DISCOVERY graph: they expand a persona's taste with neighbouring
artists and drive TARGETED per-persona acquisition (a "find more like this" wishlist that
feeds slskd/yt-dlp). This is exactly the per-persona taste-EXPANSION the user wants — but it
is a CURATION + ACQUISITION concern (CORE-001 wishlist/acquisition + OPS-004 OH library policy
+ the persona taste profiles), NOT the analysis engine. ANALYSIS-006's only role: once those
discovered artists are acquired and analyzed, their feature dimensions (genre/key/bpm/energy/
era/tags) keep the expanded taste profile queryable and still separable from other personas
(REQ-AD-003). So the discovery mechanic is REFERENCED at AD-003's discovery-boundary note and
left to CORE-001/OPS-004 to own.

### 9.3 Gnoosic — inspiration only, NOT a data source

Gnoosic ("name 3 bands you like → discover neighbours") has no real public API and is not a
data feed. It is recorded only as a DISCOVERY-UX INSPIRATION: a "3 seed artists → discover
neighbours" mechanic the curation layer (CORE-001/OPS-004) could emulate using the Last.fm
similar-artist graph (§9.2) as the actual data backend. ANALYSIS-006 does not integrate
Gnoosic and does not own the mechanic; it is named here so the idea is captured at the right
layer.

---

## 10. Deeper understanding: sonic character, music theory on verified features, consensus (REQ-AE-006, REQ-AT-007, REQ-AM-003)

The user wants the brain to genuinely UNDERSTAND its music — "what it is and how it sounds" —
so it can curate diversely and well across distinct personas, not just shuffle by a genre
label. Three mechanisms, all grounded in the extracted features (never free hallucination):

### 10.1 Sonic-character "how it sounds" understanding (REQ-AE-006)

Beyond BPM/key/genre, a sonic-character profile describes the track's SOUND. The CPU-only
inputs are already in the analysis pass:
- **Spectral descriptors** (centroid = brightness, rolloff, flatness = noisy-vs-tonal,
  contrast, bandwidth) → timbre / texture / brightness.
- **MFCCs** → overall timbre fingerprint + a basis for a compact content EMBEDDING (mean +
  covariance of MFCC frames, or an Essentia/`musicnn`-style CPU embedding) for
  content-similarity neighbours independent of tags.
- **RMS / dynamics / loudness range** → loud-vs-quiet, compressed-vs-dynamic.
- **Essentia high-level descriptors** (danceability, plus the optional CPU TensorFlow
  mood/genre/instrumental models from `essentia-tensorflow`) → mood, vocal-vs-instrumental,
  acoustic-vs-electronic.

Optionally, a short LLM "sonic description" turns these numbers into a human phrase ("warm,
sparse, late-night soul with a dry vocal"). [HARD] It is GROUNDED: the prompt is the
extracted feature vector + reconciled metadata, and the model is instructed to describe ONLY
what those features support — it may not invent "acoustic" when the spectrum/flatness reads
electronic. This is the analysis-side analogue of KNOWLEDGE-008's fact-grounding discipline:
evidence first, description second. All CPU/offline/cached under the AE rails.

### 10.2 Music theory APPLIED to the verified features (REQ-AT-007)

Claude already knows music theory; the requirement is that it be applied ON TOP of the
verified feature record, not used to assert theory the features don't support:
- **Harmonic / Camelot + modal** reasoning between adjacent tracks (relative major/minor,
  perfect-fifth neighbours, modal interchange) — gated by key CONFIDENCE (REQ-AE-005): a
  low-confidence key yields a hedged or withheld harmonic claim.
- **Mood from mode + tempo + energy** (minor + slow + low energy → melancholic; major + fast
  + high energy → upbeat) — a theory-informed mood hint that corroborates §10.1.
- **Energy-arc shaping** across a set and **sane transition points** (mix at the analyzed
  outro / on a downbeat, not mid-phrase) — feeding the AT beat-grid + annotate emission
  (REQ-AT-004/005) and the AD harmonic/energy-arc queries (REQ-AD-004).

This is reasoning over deterministic DSP outputs; it stays grounded because the features
(and their confidences) are the evidence. The mixing POLICY (OPS-004 REQ-OA-014) and the
adjacency DECISION (REQ-OA-006) consume these hints; ANALYSIS-006 does not restate them.

### 10.3 Multi-source consensus, and the boundary with KNOWLEDGE-008 (REQ-AM-003)

A genre/mood/feature claim becomes "confirmed" only when corroborated across multiple
sources from a verified-source ALLOWLIST (MusicBrainz / TheAudioDB / Last.fm / embedded tags
/ the audio analysis itself) meeting a consensus THRESHOLD; single-source or low-consensus
claims are stored as "candidate", flagged, and never stated as certain. This is the same
"don't state as fact until corroborated" discipline KNOWLEDGE-008 applies to researched
ARTIST FACTS — split by domain so the two SPECs do not duplicate or contradict each other:
- **ANALYSIS-006 (REQ-AM-003)** = consensus for AUDIO / GENRE / FEATURE claims (what the
  track sounds like, what genre/mood it is).
- **KNOWLEDGE-008** = consensus for ARTIST FACTS (biography, history, scene, lineage,
  time-sensitive facts) with provenance + as-of dates.
Where both touch an artist, ANALYSIS supplies the audio/genre/feature consensus and
KNOWLEDGE supplies the fact consensus; neither re-owns the other.

### 10.4 Why this powers anti-convergence (PROGRAMMING-007, AD-003)

Genre tags alone make personas converge ("five name tags on one average"). The
sonic-character profile (§10.1) + theory/lineage understanding (§10.2) give curation real
axes — timbre, production era, mood, instrumentation, harmonic neighbourhood — to keep
personas genuinely DISTINCT. PROGRAMMING-007's anti-convergence firewall (REQ-PR-004) is
proven against exactly these ANALYSIS-006 dimensions; this SPEC supplies the dimensions, that
SPEC owns the firewall policy.

---

## Sources

- Essentia algorithms reference — essentia.upf.edu/algorithms_reference.html (RhythmExtractor2013,
  PercivalBpmEstimator, KeyExtractor, Danceability, LoudnessEBUR128, MusicExtractor, TensorflowPredict).
- Essentia install — essentia.upf.edu/installing.html (`pip install essentia`, Linux CPU wheels,
  optional `--with-tensorflow`).
- Essentia repo / license — github.com/MTG/essentia ("released under the Affero GPLv3 license";
  `essentia-tensorflow` for pretrained CPU models).
- librosa — librosa.org (beat_track, feature.chroma_cqt, feature.rms, onset.onset_detect,
  effects.trim, load); ISC license.
- aubio — aubio.org / github.com/aubio/aubio (tempo, onset, pitch); GPLv3.
- libKeyFinder / Mixxx key detection — github.com/mixxxdj/libkeyfinder; GPLv3.
- Liquidsoap metadata + protocols — liquidsoap.info/doc-dev/metadata.html (liq_cue_in,
  liq_cue_out, liq_fade_in, liq_fade_out, liq_cross_duration, liq_amplify, replaygain;
  custom-metadata access in transition functions) and liquidsoap.info/doc-dev/protocols.html
  (`annotate:key="val",...:uri`).
- Camelot wheel / harmonic mixing — mixedinkey.com/camelot-wheel/ (same code / ±1 same letter /
  switch letter same number compatibility rules).
- Last.fm API — last.fm/api (artist.getInfo, track.getTopTags, artist.getTopTags for crowd
  genre/mood tags; artist.getSimilar, tag.getTopArtists for similar-artist discovery; free API
  key required; method names confirmed against the live API index).
- Gnoosic — gnoosic.com (3-seed-artist discovery UX; no public API — inspiration only).
- Key-detection accuracy framing — MIREX key-detection evaluation tradition (correct / perfect
  fifth / relative / parallel weighted scoring) and the Krumhansl-Schmuckler key-finding method.
- Context7 confirmations of library availability/versions: `/librosa/librosa`, `/aubio/aubio`,
  `/mtg/essentia`.
