"""ANALYSIS-006 — the offline, CPU-only audio-analysis ENGINE (Group AE / AT).

This module is the DSP heart of the track-intelligence substrate: given a path to
an audio file at rest, it extracts a feature record (BPM + confidence, musical key
+ Camelot + confidence, energy, integrated LUFS, cue/boundary points, and a
feature-grounded sonic-character profile) and returns it as a plain ``dict`` that
``Library.set_analysis`` (the M5 allowlist writer) persists onto the ``Track``.

Hard rails (SPEC Section 1.6 + IMPL-PLAN-INC1 golden rules):
  - CPU-only / offline: librosa + pyloudnorm + numpy, no GPU, no network. The DSP
    libraries are LAZY-IMPORTED inside ``analyze_file`` so importing this module is
    cheap and never fails even in an env where librosa is not installed (the build
    image installs it; the dev box does not).
  - NEVER raises. ``analyze_file`` is background-only and returns ``None`` on any
    failure (corrupt file, decoder error, missing library) so the worker logs+skips
    and the file still plays with safe defaults — analysis lag/failure is never a
    defect (REQ-AT-006, NFR-A-4). It is the CALLER (the U4 analyzer) that marks the
    failed record schema-current to avoid a retry-loop; the engine just returns None.
  - Idempotent + best-effort accuracy: the engine is pure (same file → same record);
    key/BPM carry a confidence and feed ``low_confidence_flags`` so consumers refuse
    rather than blend into a clash (REQ-AE-005).

Swappable-interface note (R-A-1): the public surface is the single function
``analyze_file`` returning an engine-agnostic dict. Essentia (AGPLv3) was deferred
(librosa covers the needed features, no cp312 wheel); swapping the engine means
rewriting ONLY the body of ``analyze_file`` behind this stable contract.

The long-file guard (M2): a file longer than ``max_seconds`` (default mirrors
``Config.analysis_long_file_seconds`` == 900s) is NOT fully decoded — it returns a
conservative cue default + a low-confidence flag, bounding worker memory on the
modest box.
"""

from __future__ import annotations

import logging
import math
import os
from typing import Any, Dict, List, Optional

log = logging.getLogger("brain.analysis")

# Engine identity for provenance / observability. Bump-independent of the library
# SCHEMA_VERSION (which gates re-analysis); this just records WHICH engine produced
# a record so a future Essentia swap is auditable.
ENGINE = "librosa"

# Decode sample rate for the DSP pass. 22050 is librosa's default and is plenty for
# tempo/chroma/timbre while keeping the in-RAM buffer (and CPU cost) bounded on the
# modest cloud box — a 5-minute mono track at 22050 is ~6.6M float32 == ~26 MB.
_ANALYSIS_SR = 22050

# Real-boundary floor (seconds). A cue_out is emitted ONLY when the detected
# non-audible trailing tail (dead air or a fade-out below the silence floor) is at
# least this long — i.e. there is a GENUINE boundary to stop at. Below this, the
# track is treated as running clean to its natural end and NO cue_out is produced,
# so the song plays IN FULL (the crossfade owns the overlap). This replaces the old
# blanket ``true_end - 8.0`` default that trimmed every analyzed track ~8s early
# (REQ-AT-002/006: trim only at real boundaries, never play-in-full tracks short).
_REAL_BOUNDARY_MIN_SILENCE = 1.0
# Silence floor for trailing-silence / cue detection (dB below peak). 40 dB is a
# robust "audible content" threshold across genres; a long fade still trims.
_SILENCE_TOP_DB = 40.0
# Sane BPM clamp range — octave errors (½× / 2×) are the known failure mode
# (R-A-3); values far outside this fold back via the doubling/halving heuristic.
_BPM_MIN = 60.0
_BPM_MAX = 180.0

# Krumhansl-Schmuckler major/minor key profiles (correlation templates). The chroma
# is correlated against all 24 rotations; the argmax names the key. These are the
# canonical Krumhansl & Kessler (1982) probe-tone profiles.
_KS_MAJOR = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88)
_KS_MINOR = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)

# Pitch-class index 0..11 == C, C#, D, ... B (librosa chroma bin order).
_PITCH_CLASSES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")

# Camelot wheel: musical key -> code. Major == "B" side, minor == "A" side.
# (The harmonic-mixing notation consumers read in adjacency / annotate.)
_CAMELOT = {
    # Major keys (B side)
    "B major": "1B", "F# major": "2B", "Gb major": "2B", "Db major": "3B", "C# major": "3B",
    "Ab major": "4B", "G# major": "4B", "Eb major": "5B", "D# major": "5B", "Bb major": "6B",
    "A# major": "6B", "F major": "7B", "C major": "8B", "G major": "9B", "D major": "10B",
    "A major": "11B", "E major": "12B",
    # Minor keys (A side)
    "Ab minor": "1A", "G# minor": "1A", "Eb minor": "2A", "D# minor": "2A", "Bb minor": "3A",
    "A# minor": "3A", "F minor": "4A", "C minor": "5A", "G minor": "6A", "D minor": "7A",
    "A minor": "8A", "E minor": "9A", "B minor": "10A", "F# minor": "11A", "Gb minor": "11A",
    "C# minor": "12A", "Db minor": "12A",
}


def analyze_file(
    path: str,
    *,
    low_conf_threshold: float = 0.5,
    loudness_target: float = -16.0,
    max_seconds: float = 900.0,
) -> Optional[Dict[str, Any]]:
    """Analyze one audio file on the CPU and return its feature record, or None.

    Returns a plain ``dict`` of analysis fields ready for ``Library.set_analysis``
    (the keys are a subset of the analysis-writable Track fields). NEVER raises:
    any failure — unreadable file, decoder error, librosa/pyloudnorm not installed,
    or unexpected DSP exception — is caught and logged, and ``None`` is returned so
    the caller skips the track and it still plays with safe defaults (REQ-AT-006).

    Args:
        path: absolute path to an audio file at rest.
        low_conf_threshold: key-confidence floor below which "musical_key" is added
            to ``low_confidence_flags`` so harmonic mixing refuses it (REQ-AE-005).
        loudness_target: the configured integrated-LUFS target (e.g. -16.0, the
            existing talk/song target — NOT a hardcoded -18). ``replaygain_gain_db``
            is computed as ``loudness_target - integrated_lufs`` (the gain that would
            normalize the track to target); the MEASUREMENT itself is absolute LUFS.
        max_seconds: long-file guard (M2). A file longer than this is NOT fully
            decoded — a conservative cue default + a low-confidence flag is returned
            and the heavy DSP is skipped to bound worker memory.

    The returned dict always carries ``schema_version`` is NOT set here — the caller
    stamps schema/analyzed_at/content_sig so the cache key reflects the file as the
    worker saw it. The engine returns only the measured/derived fields.
    """
    try:
        return _analyze_impl(
            path,
            low_conf_threshold=low_conf_threshold,
            loudness_target=loudness_target,
            max_seconds=max_seconds,
        )
    except Exception as exc:  # noqa: BLE001 - the engine NEVER raises into the worker
        log.warning("analysis.failed path=%s error=%s", path, exc)
        return None


def _analyze_impl(
    path: str,
    *,
    low_conf_threshold: float,
    loudness_target: float,
    max_seconds: float,
) -> Optional[Dict[str, Any]]:
    """The decode+DSP body. Wrapped by ``analyze_file`` which absorbs every error."""
    if not path or not os.path.isfile(path):
        log.warning("analysis.missing path=%s", path)
        return None

    # Lazy import: keeps module import cheap + lets this file py_compile / import in an
    # env without the audio stack. numpy is a transitive dep of librosa; import it too.
    import numpy as np
    import librosa

    flags: List[str] = []

    # --- duration via header (no full decode) ---------------------------------
    # get_duration reads the container header where possible; fall back to None.
    duration: Optional[float] = None
    try:
        duration = float(librosa.get_duration(path=path))
    except Exception:  # noqa: BLE001 - header read is best-effort
        duration = None

    # --- M2 long-file guard ----------------------------------------------------
    # Over the budget: skip the heavy decode entirely. Conservative cue defaults
    # against the (header) duration, a low-confidence flag, no BPM/key/sonic work.
    if duration is not None and duration > max_seconds:
        log.info("analysis.long_file path=%s duration=%.0f max=%.0f", path, duration, max_seconds)
        true_end = duration
        # No heavy decode happened, so no real boundary was detected. Do NOT trim —
        # cue_out None lets the long file play to its natural end (no ~8s cut-short).
        return {
            "cue_in": 0.0,
            "cue_out": None,
            "true_end": true_end,
            "trailing_silence": 0.0,
            "low_confidence_flags": ["long_file", "bpm", "musical_key"],
            "analysis_error": "",
            "provenance": {"engine": {"sources": [ENGINE], "consensus_level": "audio-hint", "confidence": 0.0}},
        }

    # --- decode (mono, fixed SR) ----------------------------------------------
    # Bounded by max_seconds even when the header duration was unknown.
    y, sr = librosa.load(path, sr=_ANALYSIS_SR, mono=True, duration=max_seconds)
    if y is None or len(y) == 0:
        log.warning("analysis.empty_decode path=%s", path)
        return None
    n = len(y)
    decoded_seconds = n / float(sr)
    if duration is None:
        duration = decoded_seconds

    record: Dict[str, Any] = {}

    # --- tempo / BPM (+ confidence) -------------------------------------------
    bpm, bpm_conf = _estimate_bpm(np, librosa, y, sr)
    record["bpm"] = bpm
    record["bpm_confidence"] = bpm_conf
    if bpm_conf < low_conf_threshold or bpm <= 0.0:
        flags.append("bpm")

    # --- musical key + Camelot (Krumhansl-Schmuckler chroma argmax) ------------
    musical_key, camelot, key_conf = _estimate_key(np, librosa, y, sr)
    record["musical_key"] = musical_key
    record["camelot"] = camelot
    record["key_confidence"] = key_conf
    key_trusted = bool(musical_key) and key_conf >= low_conf_threshold
    if not key_trusted:
        flags.append("musical_key")

    # --- energy ----------------------------------------------------------------
    record["energy"] = _estimate_energy(np, librosa, y)

    # --- integrated LUFS (pyloudnorm; RMS fallback) ----------------------------
    lufs = _measure_lufs(np, librosa, path)
    record["integrated_lufs"] = lufs
    if lufs is not None and math.isfinite(lufs):
        # The gain that would bring the track TO the configured target. Negative
        # for a track louder than target. This is a MEASUREMENT-derived hint; the
        # normalization ACTION + the constant live in OPS/CORE (NFR-O-3).
        record["replaygain_gain_db"] = round(loudness_target - lufs, 2)
    else:
        record["replaygain_gain_db"] = None

    # --- cue / boundary points (computed vs TRUE END, not file duration) -------
    cue_in, cue_out, true_end, trailing_silence = _detect_cues(np, librosa, y, sr, duration)
    record["cue_in"] = cue_in
    record["cue_out"] = cue_out
    record["true_end"] = true_end
    record["trailing_silence"] = trailing_silence

    # --- sonic-character (feature-grounded; NO LLM, REQ-AE-006) ----------------
    record.update(_sonic_character(np, librosa, y, sr, record["energy"]))

    # --- music-theory transition hints (grounded; camelot neighbours ONLY when
    #     the key is trusted, REQ-AT-007 grounding) ------------------------------
    record["transition_hints"] = _transition_hints(camelot, key_trusted, bpm)

    record["low_confidence_flags"] = flags
    record["analysis_error"] = ""
    # Provenance for the audio-derived block: the engine is one source, recorded as
    # an "audio-hint" (never "confirmed" on its own — consensus is U3's job).
    record["provenance"] = {
        "engine": {"sources": [ENGINE], "consensus_level": "audio-hint", "confidence": round(bpm_conf, 3)},
    }
    return record


# --------------------------------------------------------------------------------
# Feature extractors (each takes the already-imported numpy/librosa to avoid
# re-importing per-call; each is defensive and returns a safe default on trouble).
# --------------------------------------------------------------------------------

def _estimate_bpm(np, librosa, y, sr) -> tuple:
    """Global tempo + a confidence in [0,1]. Octave-clamped to a sane DJ range.

    Confidence is the normalized strength of the dominant tempo in the onset
    autocorrelation (tempogram) — a stable, library-version-independent proxy.
    """
    try:
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempo = librosa.beat.tempo(onset_envelope=onset_env, sr=sr)
        bpm = float(np.atleast_1d(tempo)[0])
    except Exception:  # noqa: BLE001
        try:
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            bpm = float(np.atleast_1d(tempo)[0])
            onset_env = None
        except Exception:  # noqa: BLE001
            return 0.0, 0.0

    if not math.isfinite(bpm) or bpm <= 0.0:
        return 0.0, 0.0

    # Fold octave errors into the sane range (½× / 2×) — R-A-3.
    while bpm < _BPM_MIN:
        bpm *= 2.0
    while bpm > _BPM_MAX:
        bpm /= 2.0
    bpm = round(bpm, 1)

    conf = 0.0
    try:
        if onset_env is None:
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        ac = librosa.autocorrelate(onset_env, max_size=len(onset_env))
        if len(ac) > 1:
            ac0 = float(ac[0])
            peak = float(np.max(ac[1:]))
            if ac0 > 0.0:
                conf = max(0.0, min(1.0, peak / ac0))
    except Exception:  # noqa: BLE001
        conf = 0.0
    return bpm, round(conf, 3)


def _estimate_key(np, librosa, y, sr) -> tuple:
    """Krumhansl-Schmuckler key estimate: chroma mean correlated against 24 profiles.

    Returns (musical_key e.g. "A minor", camelot e.g. "8A", confidence in [0,1]).
    Confidence is the gap between the best and second-best correlation, normalized
    — a small gap means an ambiguous (perfect-fifth / relative-minor) call, which is
    exactly the low-confidence case harmonic mixing must refuse (R-A-2).
    """
    try:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)  # 12-vector, pitch-class energy
    except Exception:  # noqa: BLE001
        return "", "", 0.0

    if chroma_mean is None or len(chroma_mean) != 12 or float(np.sum(chroma_mean)) <= 0.0:
        return "", "", 0.0

    maj = np.asarray(_KS_MAJOR, dtype=float)
    minr = np.asarray(_KS_MINOR, dtype=float)
    cm = np.asarray(chroma_mean, dtype=float)

    def _corr(a, b) -> float:
        a = a - a.mean()
        b = b - b.mean()
        denom = float(np.sqrt(np.sum(a * a) * np.sum(b * b)))
        if denom <= 0.0:
            return 0.0
        return float(np.sum(a * b) / denom)

    scores = []  # (corr, key_name)
    for i in range(12):
        scores.append((_corr(cm, np.roll(maj, i)), f"{_PITCH_CLASSES[i]} major"))
        scores.append((_corr(cm, np.roll(minr, i)), f"{_PITCH_CLASSES[i]} minor"))
    scores.sort(key=lambda s: s[0], reverse=True)

    best_corr, best_key = scores[0]
    second_corr = scores[1][0] if len(scores) > 1 else 0.0
    # Confidence = separation between top-1 and top-2, scaled. A correlation gap of
    # ~0.2 is a clear winner -> conf ~1.0; near-ties -> low conf.
    conf = max(0.0, min(1.0, (best_corr - second_corr) / 0.2)) if best_corr > 0.0 else 0.0
    camelot = _CAMELOT.get(best_key, "")
    return best_key, camelot, round(conf, 3)


def _estimate_energy(np, librosa, y) -> float:
    """Perceptual-ish energy in [0,1] from RMS (mapped from dBFS).

    RMS in dBFS spans roughly -60 (very quiet) .. 0 (full scale); we map that band
    to [0,1] so the energy dimension is comparable across tracks for arc shaping.
    """
    try:
        rms = librosa.feature.rms(y=y)
        rms_mean = float(np.mean(rms))
    except Exception:  # noqa: BLE001
        return 0.0
    if rms_mean <= 0.0:
        return 0.0
    db = 20.0 * math.log10(rms_mean)  # <= 0
    energy = (db + 60.0) / 60.0       # -60 dB -> 0.0, 0 dB -> 1.0
    return round(max(0.0, min(1.0, energy)), 3)


def _measure_lufs(np, librosa, path: str) -> Optional[float]:
    """Integrated LUFS via pyloudnorm at the file's NATIVE sample rate; RMS fallback.

    pyloudnorm's BS.1770 meter wants the real sample rate (its K-weighting filters
    are rate-dependent), so we decode a fresh native-rate buffer here rather than
    reuse the 22050 analysis buffer. On any failure (lib missing, silent track ->
    -inf/NaN, decode error) we fall back to an RMS-derived pseudo-LUFS so the field
    is never silently wrong-typed. Returns None only if nothing could be measured.
    """
    # Try pyloudnorm first (lazy import).
    try:
        import pyloudnorm as pyln

        yn, srn = librosa.load(path, sr=None, mono=True)
        if yn is not None and len(yn) > 0:
            meter = pyln.Meter(int(srn))
            lufs = float(meter.integrated_loudness(np.asarray(yn, dtype=float)))
            if math.isfinite(lufs):
                return round(lufs, 2)
    except Exception:  # noqa: BLE001 - pyloudnorm missing / silent / decode issue
        pass

    # RMS fallback: a rough pseudo-LUFS so the measurement is still present. This is
    # NOT BS.1770-accurate; it is a graceful-degradation estimate (NFR-A-4).
    try:
        yn, srn = librosa.load(path, sr=None, mono=True)
        rms = float(np.sqrt(np.mean(np.square(np.asarray(yn, dtype=float)))))
        if rms > 0.0:
            # ~ -0.691 + 20log10(rms) approximates a mono K-weighted level enough
            # to be directionally useful; flagged as fallback by its imprecision.
            return round(-0.691 + 20.0 * math.log10(rms), 2)
    except Exception:  # noqa: BLE001
        pass
    return None


def _detect_cues(np, librosa, y, sr, duration: Optional[float]) -> tuple:
    """Cue-in / cue-out / true-end / trailing-silence — all vs the TRUE END.

    - true_end: offset of the last audible audio (REQ-AT-003). This is the anchor;
      when a cue_out is emitted it is placed AT true_end (never before it), so a
      crossfade never fades into trailing silence and never trims live audio.
    - trailing_silence: file/decoded length minus true_end.
    - cue_in: first audible sample (skip dead intro air); defaults to 0.0.
    - cue_out: ONLY emitted when a REAL trailing boundary is detected — i.e. there
      is genuine non-audible tail (dead air or a fade-out the analyzer found below
      the silence floor) of at least ``_REAL_BOUNDARY_MIN_SILENCE`` seconds. In that
      case cue_out == true_end so playout stops at the last audible audio. When the
      track runs CLEAN to its natural end (no real boundary), cue_out is ``None`` so
      the song plays IN FULL and the crossfade owns the overlap (FIX: the previous
      blanket ``true_end - 8.0`` default trimmed EVERY analyzed track ~8s early).
    """
    total = duration if (duration is not None and duration > 0.0) else (len(y) / float(sr))
    try:
        intervals = librosa.effects.split(y, top_db=_SILENCE_TOP_DB)
    except Exception:  # noqa: BLE001
        intervals = None

    if intervals is None or len(intervals) == 0:
        # No audible content detected (or split failed): we have NO real boundary to
        # trust, so do NOT trim — cue_out None lets the file play to its natural end.
        true_end = round(total, 3)
        return 0.0, None, true_end, 0.0

    first_sample = int(intervals[0][0])
    last_sample = int(intervals[-1][1])
    cue_in = round(max(0.0, first_sample / float(sr)), 3)
    true_end = round(min(total, last_sample / float(sr)), 3)
    trailing_silence = round(max(0.0, total - true_end), 3)

    # A cue_out is produced ONLY when a real trailing boundary exists (meaningful
    # non-audible tail). Below the floor the track ends cleanly → no trim (None).
    if trailing_silence >= _REAL_BOUNDARY_MIN_SILENCE:
        cue_out = round(max(cue_in, true_end), 3)
    else:
        cue_out = None
    return cue_in, cue_out, true_end, trailing_silence


def _sonic_character(np, librosa, y, sr, energy: float) -> Dict[str, str]:
    """Feature-grounded sonic-character buckets (REQ-AE-006) — NO LLM.

    Every field is a coarse bucket derived strictly from spectral + MFCC + energy
    features; the grounded-LLM ``sonic_description`` stays EMPTY this increment
    (DEFERRED). These land as "audio-hint"/"candidate" provenance downstream, never
    "confirmed" — they describe what the features support, not invention.
    """
    out = {
        "timbre": "",
        "production_character": "",
        "instrumentation_feel": "",
        "vocal_instrumental": "",
        "acoustic_electronic": "",
        "dynamics": "",
    }
    try:
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
        flatness = float(np.mean(librosa.feature.spectral_flatness(y=y)))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y)))
        rms = librosa.feature.rms(y=y)
        rms_arr = np.asarray(rms, dtype=float).flatten()
        rms_mean = float(np.mean(rms_arr)) if rms_arr.size else 0.0
        rms_std = float(np.std(rms_arr)) if rms_arr.size else 0.0
        bandwidth = float(np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr)))
    except Exception:  # noqa: BLE001 - sonic character is best-effort, never fatal
        return out

    # timbre: spectral brightness via centroid (Hz). Coarse low/mid/high band.
    if centroid > 0.0:
        out["timbre"] = "bright" if centroid >= 3000.0 else ("warm" if centroid <= 1500.0 else "balanced")

    # acoustic vs electronic: flatness (noisiness) + ZCR are higher for synthetic/
    # percussive electronic content; lower/tonal for acoustic. Heuristic bucket.
    if flatness > 0.0:
        out["acoustic_electronic"] = "electronic" if (flatness >= 0.02 or zcr >= 0.10) else "acoustic"

    # instrumentation_feel: spectral bandwidth proxies density (wide == dense mix).
    if bandwidth > 0.0:
        out["instrumentation_feel"] = "dense" if bandwidth >= 2200.0 else "sparse"

    # vocal_instrumental: ZCR + centroid hint at vocal/fricative energy; this is a
    # weak heuristic (full vocal detection is OUT OF SCOPE) so it stays coarse and
    # is consumed only as an "audio-hint" candidate.
    if zcr > 0.0:
        out["vocal_instrumental"] = "vocal" if (0.05 <= zcr <= 0.15 and centroid >= 1800.0) else "instrumental"

    # production_character: energy + dynamic range (rms variation). Loud + steady ==
    # polished/compressed; quiet/variable == lo-fi/raw. Coarse two-axis label.
    if rms_mean > 0.0:
        crest = (rms_std / rms_mean) if rms_mean > 0.0 else 0.0
        if energy >= 0.6 and crest <= 0.5:
            out["production_character"] = "polished"
        elif energy <= 0.35:
            out["production_character"] = "lo-fi"
        else:
            out["production_character"] = "natural"

    # dynamics: relative RMS variation. High variation == dynamic; low == compressed.
    if rms_mean > 0.0:
        crest = rms_std / rms_mean
        out["dynamics"] = "dynamic" if crest >= 0.6 else "compressed"

    return out


def _transition_hints(camelot: str, key_trusted: bool, bpm: float) -> Dict[str, Any]:
    """Grounded music-theory hints for transitions (REQ-AT-007).

    Returns harmonically-compatible Camelot neighbours ONLY when the key is trusted
    (key_confidence >= threshold). A low-confidence key yields NO harmonic claim
    (hedged/withheld, not a confident-but-wrong blend) — the [HARD] grounding rule:
    no theory claim the features (and their confidence) do not back. ``bpm`` is
    echoed so a consumer can apply its own ±tolerance gate; this owns NO policy.
    """
    hints: Dict[str, Any] = {"bpm": bpm if bpm > 0.0 else None}
    if key_trusted and camelot:
        hints["camelot"] = camelot
        hints["harmonic_neighbours"] = sorted(_camelot_neighbours(camelot))
    else:
        hints["camelot"] = camelot if camelot else None
        hints["harmonic_neighbours"] = []  # withheld: key not trusted enough
    return hints


def _camelot_neighbours(camelot: str) -> set:
    """Harmonically-compatible Camelot codes (same code, ±1 number same letter, or
    relative major/minor). Mirrors ``Library._camelot_neighbors`` semantics so the
    engine's hint and the catalog's adjacency agree. Empty set for an unparseable code.
    """
    import re

    m = re.fullmatch(r"(\d{1,2})([AB])", camelot.strip().upper())
    if not m:
        return set()
    num = int(m.group(1))
    letter = m.group(2)
    if not 1 <= num <= 12:
        return set()
    up = num % 12 + 1
    down = (num - 2) % 12 + 1
    other = "B" if letter == "A" else "A"
    return {f"{num}{letter}", f"{up}{letter}", f"{down}{letter}", f"{num}{other}"}
