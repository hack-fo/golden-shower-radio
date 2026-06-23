"""Offline unit tests for the cue-out early-trim bug (songs cut ~8s short).

Run: python3 -m pytest brain/test_cue_trim.py -v
 or: python3 brain/test_cue_trim.py   (no pytest needed -- a tiny runner is built in)

NO network, NO torch/librosa/numpy required. The DSP libraries are LAZY-imported
inside ``analysis._analyze_impl`` / ``analysis._detect_cues``; we drive the cue
detector DIRECTLY with a tiny fake ``np``/``librosa`` pair that returns scripted
``librosa.effects.split`` intervals, so the test exercises the real boundary logic
with zero heavy deps.

Bug under test (root cause): ``_detect_cues`` historically returned
``cue_out = true_end - 8.0`` for EVERY analyzed track -- even one whose audio runs
clean to its natural end (no real trailing-silence / fade boundary). The server then
ALWAYS emitted ``liq_cue_out`` and Liquidsoap ended the song ~8s early ("cut short").

The fix: only produce a ``cue_out`` when a REAL boundary is detected (genuine
trailing silence / a fade tail the analyzer actually found). With no real boundary,
``cue_out`` is ``None`` so the track plays to its natural end (the crossfade owns the
overlap). ``_annotate_uri`` must then OMIT ``liq_cue_out`` cleanly (well-formed
annotate string), and ``liq_cue_in`` at 0.0 stays harmless.
"""

from __future__ import annotations

import sys

# Allow `python3 brain/test_cue_trim.py` from the repo root.
try:
    from brain import analysis as A
    from brain import server as S
    from brain.library import Track
except Exception:  # noqa: BLE001 - direct-run fallback
    import os

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain import analysis as A
    from brain import server as S
    from brain.library import Track


# ---------------------------------------------------------------------------
# Tiny fakes for the lazy-imported np / librosa, scoped to _detect_cues only.
# _detect_cues uses: np (nothing real here), librosa.effects.split(y, top_db=...).
# We script split() to return whatever intervals the scenario needs.
# ---------------------------------------------------------------------------
class _FakeNp:
    pass


def _fake_librosa(intervals):
    """A librosa stand-in whose effects.split returns the scripted intervals."""

    class _Effects:
        @staticmethod
        def split(y, top_db=None):  # noqa: ARG004 - signature compat only
            return intervals

    class _Librosa:
        effects = _Effects()

    return _Librosa()


# A nominal sample rate; intervals are expressed in samples = seconds * SR.
SR = 22050


def _samples(seconds: float) -> int:
    return int(round(seconds * SR))


# ---------------------------------------------------------------------------
# _detect_cues: a track whose audio runs CLEAN to its natural end.
#   total duration = 200.0s, last audible sample == end of audio -> NO real
#   trailing-silence boundary. Correct behavior: cue_out is None (play full).
# ---------------------------------------------------------------------------
def test_no_boundary_track_emits_no_cue_out():
    total = 200.0
    # One audible interval spanning the whole track: [0, total] in samples.
    intervals = [(0, _samples(total))]
    np = _FakeNp()
    librosa = _fake_librosa(intervals)
    # y length must reflect total so the "len(y)/sr" fallback matches duration.
    y = [0.0] * _samples(total)

    cue_in, cue_out, true_end, trailing_silence = A._detect_cues(np, librosa, y, SR, total)

    assert cue_in == 0.0, cue_in
    assert abs(true_end - total) < 0.05, true_end
    assert trailing_silence < 0.05, trailing_silence
    # THE FIX: no real boundary -> cue_out must be None so the song plays in full.
    # (Pre-fix this was true_end - 8.0 ~= 192.0, which trimmed every track ~8s.)
    assert cue_out is None, (
        f"no-boundary track must not be trimmed: cue_out={cue_out!r} "
        f"(true_end={true_end})"
    )


# ---------------------------------------------------------------------------
# _detect_cues: a track WITH a genuine trailing-silence / fade tail.
#   audio stops at 150.0s but the file runs to 200.0s -> 50s of dead air the
#   analyzer actually detected. Correct behavior: cue_out == true_end (150.0s)
#   so playout stops at the last audible audio, not in the silence.
# ---------------------------------------------------------------------------
def test_real_trailing_silence_emits_cue_out_at_true_end():
    total = 200.0
    audible_end = 150.0
    intervals = [(0, _samples(audible_end))]
    np = _FakeNp()
    librosa = _fake_librosa(intervals)
    y = [0.0] * _samples(total)

    cue_in, cue_out, true_end, trailing_silence = A._detect_cues(np, librosa, y, SR, total)

    assert cue_in == 0.0, cue_in
    assert abs(true_end - audible_end) < 0.05, true_end
    assert abs(trailing_silence - (total - audible_end)) < 0.05, trailing_silence
    # A real boundary WAS found -> emit a cue_out, and it must land at the last
    # audible audio (true_end), never the blanket true_end - 8.0.
    assert cue_out is not None, "real trailing silence must produce a cue_out"
    assert abs(cue_out - true_end) < 0.05, (
        f"cue_out must sit at the real boundary (true_end={true_end}), got {cue_out}"
    )


# ---------------------------------------------------------------------------
# _detect_cues: a real cue-IN boundary (dead intro air) is still honored, and a
# clean ending still yields NO cue_out. cue_in trims the silent intro; cue_out None.
# ---------------------------------------------------------------------------
def test_intro_silence_sets_cue_in_but_clean_end_keeps_cue_out_none():
    total = 180.0
    intro = 5.0  # 5s of dead air before audio starts; audio runs to the end.
    intervals = [(_samples(intro), _samples(total))]
    np = _FakeNp()
    librosa = _fake_librosa(intervals)
    y = [0.0] * _samples(total)

    cue_in, cue_out, true_end, trailing_silence = A._detect_cues(np, librosa, y, SR, total)

    assert abs(cue_in - intro) < 0.05, cue_in
    assert abs(true_end - total) < 0.05, true_end
    assert cue_out is None, f"clean ending must keep cue_out None, got {cue_out}"


# ---------------------------------------------------------------------------
# _analysis_extra + _annotate_uri: a None cue_out must be OMITTED cleanly from the
# annotate string (no malformed "liq_cue_out=None"/empty token).
# ---------------------------------------------------------------------------
def test_annotate_omits_cue_out_when_none():
    t = Track(
        path="/music/song.mp3",
        artist="A",
        title="T",
        schema_version=1,
        cue_in=0.0,
        cue_out=None,   # no real boundary -> play full
        bpm=120.0,
        camelot="8A",
        energy=0.5,
    )
    extra = S._analysis_extra(t)
    assert extra is not None
    assert extra["liq_cue_out"] is None, extra

    uri = S._annotate_uri("A", "T", "music", "/music/song.mp3", extra)
    # Well-formed: starts with annotate:, ends at the real path, and carries NO
    # liq_cue_out token at all (the None field is dropped, not stringified).
    assert uri.startswith("annotate:"), uri
    assert uri.endswith(":/music/song.mp3"), uri
    assert "liq_cue_out" not in uri, f"None cue_out must be omitted, got: {uri}"
    # liq_cue_in at 0.0 is harmless and present (cue at start == no trim).
    assert "liq_cue_in=0.0" in uri, uri
    assert "bpm=120.0" in uri and 'camelot="8A"' in uri, uri


# ---------------------------------------------------------------------------
# _annotate_uri: a present (real-boundary) cue_out IS emitted, unquoted numeric.
# ---------------------------------------------------------------------------
def test_annotate_emits_cue_out_when_present():
    t = Track(
        path="/music/song.mp3",
        artist="A",
        title="T",
        schema_version=1,
        cue_in=0.0,
        cue_out=150.0,  # real trailing-silence boundary
    )
    extra = S._analysis_extra(t)
    uri = S._annotate_uri("A", "T", "music", "/music/song.mp3", extra)
    assert "liq_cue_out=150.0" in uri, uri
    assert uri.endswith(":/music/song.mp3"), uri


# ---------------------------------------------------------------------------
# tiny built-in runner (so the test works with or without pytest)
# ---------------------------------------------------------------------------
def _run_all() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_run_all())
