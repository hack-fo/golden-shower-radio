# Analysis Subsystem

The analysis subsystem is the offline, CPU-only intelligence layer that turns raw audio files into structured feature records consumed by the scheduler, harmonic mixer, and metadata catalog.

Two modules cooperate:

- `brain/analysis.py` — DSP engine: BPM, key, energy, LUFS, cue/boundary points, sonic character
- `brain/metadata.py` — Enrichment + consensus: genre/mood/tags/year from MusicBrainz, TheAudioDB, Last.fm, embedded tags, and audio hints

Both modules are background-only and **never raise** into the worker. A failure produces `None` (analysis) or `{}` (metadata) and the track still plays with safe defaults.

---

## brain/analysis.py — DSP Engine

### What it does

Given a path to an audio file on disk, `analyze_file()` decodes it with librosa at 22050 Hz mono and returns a flat `dict` of measured/derived fields ready for `Library.set_analysis()`. On any failure it returns `None`.

### Key constants

| Constant | Value | Purpose |
|---|---|---|
| `_ANALYSIS_SR` | 22050 Hz | Decode sample rate — 5-min track ≈ 26 MB RAM |
| `_REAL_BOUNDARY_MIN_SILENCE` | 1.0 s | Minimum trailing silence to emit a `cue_out` |
| `_SILENCE_TOP_DB` | 40 dB | Silence floor for `librosa.effects.split` |
| `_BPM_MIN` / `_BPM_MAX` | 60 / 180 | Sane DJ range; octave errors folded by halving/doubling |

### Call flow

```
analyze_file(path)
  └─ _analyze_impl(path)
        ├─ librosa.get_duration()        # header read, no full decode
        ├─ [M2 guard] if duration > max_seconds → return conservative record
        ├─ librosa.load(sr=22050, mono=True)
        ├─ _estimate_bpm()               # onset autocorrelation, octave-clamped
        ├─ _estimate_key()               # Krumhansl-Schmuckler chroma correlation
        ├─ _estimate_energy()            # RMS → dBFS → [0,1]
        ├─ _measure_lufs()               # pyloudnorm BS.1770; RMS fallback
        ├─ _detect_cues()                # librosa.effects.split → cue_in/out/true_end
        ├─ _sonic_character()            # spectral heuristics → coarse buckets
        └─ _transition_hints()           # Camelot neighbours (only when key trusted)
```

### Feature extractors

**`_estimate_bpm()`** Uses `librosa.onset.onset_strength` + `librosa.beat.tempo`. Confidence is the peak-to-DC ratio of the onset autocorrelation — stable across library versions. Octave errors (½×, 2×) are corrected by doubling/halving into [60, 180].

**`_estimate_key()`** Computes `chroma_cqt` mean over the track, then correlates it against the canonical Krumhansl-Kessler major and minor profiles for all 12 pitch classes (24 candidates). Confidence is the normalized gap between the top-1 and top-2 correlation scores: a gap of ≈0.2 → confidence ≈ 1.0; near-ties → low confidence. Low confidence withholds the harmonic-mixing claim entirely (REQ-AE-005).

**`_estimate_energy()`** Mean RMS mapped from dBFS (≈ −60..0) to [0, 1].

**`_measure_lufs()`** Decodes a **second** buffer at the file's native sample rate (BS.1770 K-weighting filters are rate-dependent), measures via `pyloudnorm`. Falls back to an RMS-derived pseudo-LUFS if `pyloudnorm` is absent or the track is silent. The returned `replaygain_gain_db = loudness_target − integrated_lufs`.

**`_detect_cues()`** Uses `librosa.effects.split(top_db=40)` to find audible intervals. Results:

- `cue_in` — offset of the first audible sample (skip dead intro)
- `true_end` — offset of the last audible sample
- `trailing_silence` — `file_duration − true_end`
- `cue_out` — **only emitted when `trailing_silence >= 1.0 s`**. When the track ends cleanly (no real boundary), `cue_out = None` and the crossfade owns the overlap. This replaces the old behaviour that set `cue_out = true_end − 8.0` unconditionally and trimmed every analyzed track ~8 s early.

**`_sonic_character()`** Six coarse string buckets derived from spectral features, no LLM (REQ-AE-006):

| Field | Feature used | Labels |
|---|---|---|
| `timbre` | spectral centroid (Hz) | `bright` / `balanced` / `warm` |
| `acoustic_electronic` | flatness + ZCR | `electronic` / `acoustic` |
| `instrumentation_feel` | spectral bandwidth | `dense` / `sparse` |
| `vocal_instrumental` | ZCR + centroid | `vocal` / `instrumental` (weak heuristic) |
| `production_character` | energy + RMS crest | `polished` / `natural` / `lo-fi` |
| `dynamics` | RMS std/mean | `dynamic` / `compressed` |

All land as `audio-hint`/`candidate` provenance. `sonic_description` (LLM-grounded free text) is deferred and absent from the record.

**`_transition_hints()`** Returns Camelot neighbours (same position, ±1 number, relative major/minor) **only when** `key_confidence >= low_conf_threshold`. Low-confidence key → `harmonic_neighbours: []` (withheld, not wrong).

### Returned dict fields

```python
{
    "bpm": float,                   # 0.0 = unknown
    "bpm_confidence": float,        # [0, 1]
    "musical_key": str,             # e.g. "A minor", "" = unknown
    "camelot": str,                 # e.g. "8A", "" = unknown
    "key_confidence": float,        # [0, 1]
    "energy": float,                # [0, 1]
    "integrated_lufs": float|None,
    "replaygain_gain_db": float|None,
    "cue_in": float,                # seconds
    "cue_out": float|None,          # None = play in full
    "true_end": float,              # seconds
    "trailing_silence": float,      # seconds
    "timbre": str,
    "production_character": str,
    "instrumentation_feel": str,
    "vocal_instrumental": str,
    "acoustic_electronic": str,
    "dynamics": str,
    "transition_hints": {
        "bpm": float|None,
        "camelot": str|None,
        "harmonic_neighbours": list[str],
    },
    "low_confidence_flags": list[str],    # e.g. ["bpm", "musical_key"]
    "analysis_error": str,                # "" on success
    "provenance": {
        "engine": {
            "sources": ["librosa"],
            "consensus_level": "audio-hint",
            "confidence": float,
        }
    },
}
```

The caller (`Library.set_analysis`) stamps `schema_version`, `analyzed_at`, and `content_sig` — the engine does not.

### Long-file guard (M2)

Files longer than `max_seconds` (default 900 s, mirrors `Config.analysis_long_file_seconds`) skip the full decode. The guard reads only the container header, returns a conservative record with `cue_out = None` and `low_confidence_flags = ["long_file", "bpm", "musical_key"]`, and bounds worker RAM on the modest host.

### Configuration knobs

`analyze_file()` accepts keyword arguments that flow from the worker's config:

| Argument | Default | Effect |
|---|---|---|
| `low_conf_threshold` | `0.5` | Key/BPM confidence floor; below this the feature is flagged |
| `loudness_target` | `-16.0` | LUFS target for `replaygain_gain_db` calculation |
| `max_seconds` | `900.0` | Long-file guard duration |

---

## brain/metadata.py — Enrichment + Consensus

### What it does

`enrich(artist, title, embedded, audio_hints, cfg)` queries up to four external/local sources for genre, sub-genre, mood, tags, and year, then runs multi-source consensus to produce a single value per feature with auditable provenance. Returns a flat dict ready for `Library.set_analysis`. Returns `{}` on any failure or when enrichment is disabled (`cfg.enrichment_enabled = False`).

### Sources and precedence

| Source | Id | Base confidence | Notes |
|---|---|---|---|
| MusicBrainz | `musicbrainz` | 0.80 | Authoritative — confirms a value on its own |
| TheAudioDB | `theaudiodb` | 0.50 | Crowd folksonomy; uses free key `123` by default |
| Last.fm | `lastfm` | 0.50 | Optional — only runs when `cfg.lastfm_api_key` is set |
| Embedded tags | `embedded` | 0.40 | ID3/Vorbis values parsed upstream |
| Audio hint | `audio-hint` | 0.25 | Tempo-bucket genre from analysis.py; always present |

### Consensus algorithm

For each scalar feature (genre, sub-genre, mood, year):

1. Collect `(value, source, confidence)` tuples from all allowlisted sources.
2. Group by normalized value (case-insensitive).
3. A group is **confirmed** if any AUTHORITATIVE source (MusicBrainz) is in it, or if `n_distinct_sources >= min_sources` (default 2).
4. Winner selection: confirmed > more sources > higher source precedence > higher summed confidence. The displayed value uses the casing from the highest-precedence contributing source.
5. Confidence = `base_confidence + 0.1 × (n_sources − 1)`, capped at 1.0.

A single non-authoritative source is always `"candidate"`, never `"confirmed"`.

### Tags reconciliation

Tags are list-valued so they bypass scalar consensus. `_reconcile_tags()` unions noise-filtered tags from all sources, sorts by corroboration count (most-agreed first), and records confidence proportional to how many tags are corroborated across sources.

### Noise filter

`_is_noise_tag()` drops non-genre folksonomy strings before they can vote: `"seen live"`, `"favourites"`, decade tokens (`"00s"`, `"1990s"`), bare 4-digit years, and similar. Applied to Last.fm and TheAudioDB tags.

### MusicBrainz rate limiting

A process-wide lock (`_MB_LOCK`) enforces the 1 request/second MusicBrainz policy regardless of how many workers run concurrently. Each call also sets an explicit socket timeout via `socket.setdefaulttimeout(timeout)`.

### Audio-hint fallback genre

`_provider_audio_hints()` always derives a coarse genre from BPM even when the caller passes no explicit genre hint, guaranteeing the catalog has at least a weak genre for every track even when every network source is unreachable:

| BPM range | Bucket |
|---|---|
| < 90 | `downtempo` |
| 90–109 | `midtempo` |
| 110–134 | `uptempo` |
| ≥ 135, energy ≥ 0.5 | `high-energy` |
| ≥ 135, energy < 0.5 | `uptempo` |

### Returned dict fields

```python
{
    "genre": str,
    "sub_genre": str,       # may be absent
    "mood": str,            # may be absent
    "year": int,            # may be absent
    "tags": list[str],      # may be absent
    "provenance": {
        "genre": {
            "sources": list[str],
            "consensus_level": "confirmed" | "candidate",
            "confidence": float,
        },
        # one block per resolved feature
    },
}
```

### Configuration knobs (from `cfg`)

| Attribute | Default | Effect |
|---|---|---|
| `enrichment_enabled` | `True` | Set `False` to disable entirely and return `{}` |
| `enrichment_http_timeout_seconds` | `10` | HTTP timeout for TheAudioDB and Last.fm calls |
| `enrichment_min_consensus_sources` | `2` | Sources required for `"confirmed"` status |
| `lastfm_api_key` | `""` | Leave empty to skip Last.fm silently |
| `theaudiodb_api_key` | `"123"` | TheAudioDB API key (free tier = `"123"`) |
| `musicbrainz_user_agent` | `"GoldenShowerRadio/1.0 ..."` | UA string sent to MusicBrainz |

---

## Gotchas

**`cue_out = None` is intentional.** The scheduler treats `None` as "play in full". Only tracks with ≥ 1 s of detected trailing silence receive a non-None `cue_out`. The previous behaviour that always set `cue_out = true_end − 8.0` has been removed.

**LUFS is measured at native sample rate.** `_measure_lufs()` decodes a separate buffer at the file's original SR because pyloudnorm's K-weighting filters are sample-rate-dependent. The 22050 Hz analysis buffer is not reused for this step.

**Lazy imports everywhere.** Both modules import `librosa`, `numpy`, `pyloudnorm`, `musicbrainzngs`, and `httpx` inside their worker functions. Importing `brain.analysis` or `brain.metadata` at module level is always safe even when those libraries are absent.

**Key confidence gates harmonic mixing.** When `key_confidence < low_conf_threshold`, `musical_key` appears in `low_confidence_flags` and `transition_hints.harmonic_neighbours` is empty. Consumers must check the flag before using the key for mixing decisions.

**MusicBrainz alone confirms by design.** A single MusicBrainz genre value produces `consensus_level = "confirmed"` even with no corroboration. This is the authoritative-source rule (REQ-AM-003), not a bug.

**Last.fm is silently absent without a key.** With no `lastfm_api_key`, the module logs one INFO line (`metadata.lastfm_disabled`) per process and never constructs a client or raises. Check that log line to verify the key is set if you expect Last.fm data.

---

## See also

- `.moai/specs/SPEC-RADIO-ANALYSIS-006/spec.md` — full requirements (REQ-AE-*, REQ-AT-*, REQ-AM-*)
- `.moai/specs/SPEC-RADIO-ANALYSIS-006/IMPL-PLAN-INC1.md` — increment plan and golden rules
- `brain/library.py` — `Library.set_analysis()` (allowlist writer that persists the record)
- `deploy/config/radio.liq` — Liquidsoap reads `cue_in`/`cue_out`/`true_end` via `/api/next`
