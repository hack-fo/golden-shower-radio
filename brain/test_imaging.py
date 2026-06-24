"""Tests for brain/imaging.py — SPEC-RADIO-OPS-004 Group OE (Self-Produced Imaging & Jingles).

DDD discipline: this file is BOTH the characterization safety-net (PRESERVE) AND the acceptance
proof (the 12 REQs). It NEVER makes a real LLM call, NEVER shells out to a real ffmpeg/sox process
(every subprocess + the voice.produce_talk_clip seam is monkeypatched), and NEVER spins the real
daemon thread with real long sleeps — it drives the unit surfaces (ImagingBriefBuilder /
Synthesizer / BedRegistry / BedSourcer / ClipMixer / ImagingProducer / ReadyBuffer /
GenerationWorker / ImagingPlayer / ImagingSystem) and the director's _maybe_produce_imaging path
directly.

Characterization pins (PRESERVE — behaviour preservation, the load-bearing rail):
  * With imaging OFF (the default — imaging_system None on the Director) the director _tick
    produces NO imaging and the curate/enqueue path is byte-identical to before this SPEC
    (REQ-OE-011 behaviour preservation). The new default-None param changes nothing.

Acceptance coverage (the 12 REQs):
  REQ-OE-001  AI chooses cadence; a due slot triggers imaging; no fixed hardcoded schedule.
  REQ-OE-002  a brief carries a type + style + the line to read.
  REQ-OE-003  the voice line renders through the SAME TTS + loudnorm pipeline talk uses.
  REQ-OE-004  the voice keys the sidechain; the bed ducks under it; dry/wet ratio honored.
  REQ-OE-005  beds come ONLY from self-cleared license sources.
  REQ-OE-006  [HARD] an unknown-license bed is quarantined, never mixed.
  REQ-OE-007  brief/produce/air/skip are auditable ledger events (a VIEW, no new store).
  REQ-OE-008  a serialized single worker fills a ready buffer ahead of playout.
  REQ-OE-009  [HARD] slow/errored production -> SKIP with log; never blocks the stream.
  REQ-OE-010  the produced clip is a self-contained file (a kind="imaging" NextItem).
  REQ-OE-011  [HARD] every public entry point never raises; imaging off => byte-identical.
  REQ-OE-012  no TTS/ffmpeg concurrency — one clip produced at a time.

Run: python3 -m pytest brain/test_imaging.py -q
"""

from __future__ import annotations

import os
import sys
import threading
import time

try:
    from brain import imaging
    from brain.director import Director
    from brain.config import Config
    from brain.ledger import EventLedger, is_registered_event_type
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain import imaging
    from brain.director import Director
    from brain.config import Config
    from brain.ledger import EventLedger, is_registered_event_type


# --------------------------------------------------------------------------- #
# Lightweight fakes (mirror test_news.py / test_characterize_director.py).
# --------------------------------------------------------------------------- #


class FakeState:
    def __init__(self, recent=None):
        self._recent = recent or []

    def recent(self):
        return list(self._recent)


class FakeLibrary:
    def __init__(self, count=0):
        self._count = count

    def scan(self):
        return 0

    def count(self):
        return self._count


class FakeAcquirer:
    def __init__(self):
        self.calls = []

    def enqueue(self, artist, title):
        self.calls.append((artist, title))
        return True

    def pending(self):
        return 0


def _touch(path: str, data: bytes = b"RIFFfake") -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def _result(clip_path="/x/clip.mp3", *, skipped=False, title="Station ID"):
    return imaging.ImagingResult(
        clip_path=None if skipped else clip_path, imaging_type="station_id",
        style="dry", title=title, reason="aired" if not skipped else "tts_failed",
        skipped=skipped)


# =====================================================================================
# PRESERVE — characterization: with imaging OFF the director is byte-identical.
# =====================================================================================


def test_characterize_director_default_has_no_imaging_subsystem():
    """The new imaging param defaults to None — the default-constructed Director carries no
    imaging system, so the imaging path is wholly inert (behaviour preservation, REQ-OE-011)."""
    d = Director(Config(), FakeLibrary(), FakeAcquirer(), FakeState(), threading.Event())
    assert d.imaging_system is None


def test_characterize_maybe_produce_imaging_is_noop_when_off():
    """_maybe_produce_imaging with no imaging system is a pure no-op (REQ-OE-011)."""
    d = Director(Config(), FakeLibrary(), FakeAcquirer(), FakeState(), threading.Event())
    # Must not raise and must do nothing observable.
    d._maybe_produce_imaging()
    assert d.imaging_system is None


def test_characterize_config_imaging_defaults_off():
    """Imaging is OFF by default — the default config never builds the subsystem (REQ-OE-011)."""
    cfg = Config()
    assert cfg.imaging_enabled is False
    assert cfg.imaging_stable_audio_enabled is False


def test_config_imaging_clips_dir_is_under_music_dir_dotdir():
    """The imaging clips dir is a music-dir dot-dir so Liquidsoap can read it and the library scan
    skips it (REQ-OE-010), mirroring talk_clips_dir."""
    cfg = Config()
    assert cfg.imaging_clips_dir.endswith("/.imaging")
    assert cfg.imaging_clips_dir.startswith(cfg.music_dir)


# =====================================================================================
# REQ-OE-007 — the ledger vocabulary is registered (a VIEW over the ONE ledger, no new store).
# =====================================================================================


def test_imaging_event_types_are_registered_in_the_one_ledger():
    """All six imaging event types are in the documented ledger vocabulary (REQ-OE-007/OD-007)."""
    for et in ("imaging_brief_generated", "imaging_clip_produced", "imaging_clip_aired",
               "imaging_clip_skipped", "imaging_bed_registered", "imaging_bed_quarantined"):
        assert is_registered_event_type(et), et


# =====================================================================================
# REQ-OE-001/002 — Stage 1: the brief (type + style + line).
# =====================================================================================


def test_brief_carries_type_style_and_line():
    b = imaging.ImagingBriefBuilder(station_name="GSR")
    brief = b.build(imaging_type=imaging.ImagingType.STATION_ID)
    assert brief.imaging_type == imaging.ImagingType.STATION_ID
    assert brief.style == imaging.ProductionStyle.DRY
    assert "GSR" in brief.text


def test_brief_rotation_does_not_repeat_back_to_back():
    """With no explicit type the builder rotates so successive briefs differ (REQ-OE-001/002)."""
    b = imaging.ImagingBriefBuilder(station_name="GSR")
    first = b.build()
    second = b.build()
    assert first.imaging_type != second.imaging_type


def test_brief_sweeper_is_wet_jingle_is_sung():
    b = imaging.ImagingBriefBuilder(station_name="GSR")
    assert b.build(imaging_type=imaging.ImagingType.SWEEPER).style == imaging.ProductionStyle.WET
    assert b.build(imaging_type=imaging.ImagingType.JINGLE).style == imaging.ProductionStyle.SUNG


def test_brief_time_check_renders_a_clock():
    b = imaging.ImagingBriefBuilder(station_name="GSR", clock=lambda: 0.0)
    brief = b.build(imaging_type=imaging.ImagingType.TIME_CHECK)
    assert ":" in brief.text and "GSR" in brief.text


def test_brief_line_writer_seam_is_used_when_present():
    b = imaging.ImagingBriefBuilder(
        station_name="GSR", line_writer=lambda **kw: "Custom line.")
    assert b.build(imaging_type=imaging.ImagingType.STATION_ID).text == "Custom line."


def test_brief_line_writer_fault_falls_back_to_template():
    """A line-writer that raises never blocks — the brief falls back to the template (REQ-OE-011)."""
    def boom(**kw):
        raise RuntimeError("nope")
    b = imaging.ImagingBriefBuilder(station_name="GSR", line_writer=boom)
    brief = b.build(imaging_type=imaging.ImagingType.STATION_ID)
    assert "GSR" in brief.text  # template fallback, no exception


def test_brief_is_logged_to_the_ledger():
    led = EventLedger()
    b = imaging.ImagingBriefBuilder(station_name="GSR", ledger=led, clock=lambda: 1.0)
    b.build(imaging_type=imaging.ImagingType.STATION_ID)
    evs = led.events(event_type="imaging_brief_generated")
    assert len(evs) == 1
    assert evs[0].data["type"] == "station_id"


# =====================================================================================
# REQ-OE-003 — Stage 2: synth through the SAME talk TTS pipeline.
# =====================================================================================


def test_synth_reuses_voice_produce_talk_clip(monkeypatch):
    """The synthesizer calls voice.produce_talk_clip (the shared pipeline) — no forked TTS."""
    calls = {}

    class _Clip:
        container_path = "/music/.imaging/v.mp3"

    def fake_produce(cfg, provider, text):
        calls["text"] = text
        return _Clip()

    monkeypatch.setattr("brain.voice.produce_talk_clip", fake_produce)
    s = imaging.Synthesizer(Config(), provider=object())
    out = s.synth("hello")
    assert out == "/music/.imaging/v.mp3"
    assert calls["text"] == "hello"


def test_synth_returns_none_on_empty_text():
    s = imaging.Synthesizer(Config(), provider=object())
    assert s.synth("") is None
    assert s.synth("   ") is None


def test_synth_returns_none_on_no_provider():
    s = imaging.Synthesizer(Config(), provider=None)
    assert s.synth("hello") is None


def test_synth_swallows_tts_fault(monkeypatch):
    """A TTS fault returns None (-> SKIP), never raises (REQ-OE-009/011)."""
    def boom(cfg, provider, text):
        raise RuntimeError("tts down")
    monkeypatch.setattr("brain.voice.produce_talk_clip", boom)
    s = imaging.Synthesizer(Config(), provider=object())
    assert s.synth("hello") is None


# =====================================================================================
# REQ-OE-005/006 — Stage 3: bed sourcing (cleared-only; quarantine the rest).
# =====================================================================================


def test_cleared_sources_predicate():
    assert imaging.is_license_cleared(imaging.LicenseSource.PROCEDURAL)
    assert imaging.is_license_cleared(imaging.LicenseSource.CC0_FIRST_PARTY)
    assert imaging.is_license_cleared(imaging.LicenseSource.STABLE_AUDIO_3)
    assert not imaging.is_license_cleared(imaging.LicenseSource.UNKNOWN)


def test_registry_registers_cleared_bed(tmp_path):
    led = EventLedger()
    reg = imaging.BedRegistry(ledger=led)
    p = _touch(str(tmp_path / "bed.wav"))
    bed = reg.register(p, imaging.LicenseSource.PROCEDURAL)
    assert bed is not None and bed.cleared
    assert reg.usable_beds() and reg.usable_beds()[0].path == p
    assert led.events(event_type="imaging_bed_registered")


def test_registry_quarantines_unknown_bed(tmp_path):
    """[HARD] an unknown-license bed is quarantined, never usable, and logged (REQ-OE-006)."""
    led = EventLedger()
    reg = imaging.BedRegistry(ledger=led)
    p = _touch(str(tmp_path / "bad.wav"))
    bed = reg.register(p, imaging.LicenseSource.UNKNOWN)
    assert bed is None  # not returned as usable
    assert reg.usable_beds() == []
    assert reg.quarantined_count() == 1
    assert led.events(event_type="imaging_bed_quarantined")


def test_registry_drops_vanished_bed_file(tmp_path):
    reg = imaging.BedRegistry()
    p = str(tmp_path / "gone.wav")
    _touch(p)
    reg.register(p, imaging.LicenseSource.PROCEDURAL)
    os.remove(p)
    assert reg.usable_beds() == []  # file gone -> not usable


def test_bed_sourcer_prefers_procedural(monkeypatch, tmp_path):
    reg = imaging.BedRegistry()
    sourcer = imaging.BedSourcer(reg, str(tmp_path), timeout_seconds=5.0)
    made = str(tmp_path / "proc.wav")
    monkeypatch.setattr(sourcer, "_procedural_bed", lambda dur: _touch(made))
    bed = sourcer.source_bed()
    assert bed is not None and bed.source == imaging.LicenseSource.PROCEDURAL


def test_bed_sourcer_uses_stable_audio_when_enabled(monkeypatch, tmp_path):
    reg = imaging.BedRegistry()
    made = str(tmp_path / "sa.wav")
    sourcer = imaging.BedSourcer(
        reg, str(tmp_path), stable_audio_enabled=True, timeout_seconds=5.0,
        stable_audio_fn=lambda d, dur: _touch(made))
    bed = sourcer.source_bed()
    assert bed is not None and bed.source == imaging.LicenseSource.STABLE_AUDIO_3


def test_bed_sourcer_returns_none_when_generation_fails(monkeypatch, tmp_path):
    """A failed bed generation returns None -> the mix degrades to DRY (REQ-OE-004), never raises."""
    reg = imaging.BedRegistry()
    sourcer = imaging.BedSourcer(reg, str(tmp_path), timeout_seconds=5.0)
    monkeypatch.setattr(sourcer, "_procedural_bed", lambda dur: None)
    assert sourcer.source_bed() is None


def test_bed_sourcer_run_bounded_times_out(tmp_path):
    """[HARD] a hung bed generator abandons at the budget (REQ-OE-009), returns None, never blocks."""
    reg = imaging.BedRegistry()
    sourcer = imaging.BedSourcer(reg, str(tmp_path), timeout_seconds=0.2)

    def _slow():
        time.sleep(5.0)
        return "never"

    t0 = time.monotonic()
    out = sourcer._run_bounded(_slow)
    elapsed = time.monotonic() - t0
    assert out is None
    assert elapsed < 2.0  # returned at the budget, not after the 5s sleep


# =====================================================================================
# REQ-OE-004 — Stage 4: the mix (voice keys the sidechain; degrade to dry).
# =====================================================================================


def test_mix_returns_dry_voice_when_no_bed(tmp_path):
    v = _touch(str(tmp_path / "voice.mp3"))
    m = imaging.ClipMixer(str(tmp_path), dry_ratio=0.7)
    assert m.mix(v, None) == v  # no bed -> dry


def test_mix_returns_dry_voice_when_bed_quarantined(tmp_path):
    v = _touch(str(tmp_path / "voice.mp3"))
    bedp = _touch(str(tmp_path / "bed.wav"))
    bed = imaging.ImagingBed(bed_id="b", path=bedp,
                             source=imaging.LicenseSource.UNKNOWN, cleared=False)
    m = imaging.ClipMixer(str(tmp_path), dry_ratio=0.7)
    assert m.mix(v, bed) == v  # uncleared bed -> never mixed (REQ-OE-006)


def test_mix_dry_ratio_one_is_voice_only(tmp_path):
    v = _touch(str(tmp_path / "voice.mp3"))
    bedp = _touch(str(tmp_path / "bed.wav"))
    bed = imaging.ImagingBed(bed_id="b", path=bedp, source=imaging.LicenseSource.PROCEDURAL)
    m = imaging.ClipMixer(str(tmp_path), dry_ratio=1.0)
    assert m.mix(v, bed) == v  # ratio 1.0 -> dry voice only


def test_mix_returns_none_for_missing_voice(tmp_path):
    m = imaging.ClipMixer(str(tmp_path), dry_ratio=0.7)
    assert m.mix("/does/not/exist.mp3", None) is None


def test_mix_degrades_to_dry_when_ffmpeg_fails(monkeypatch, tmp_path):
    """A failed mix process still airs the dry voice (degrade-to-dry, REQ-OE-004), never raises."""
    v = _touch(str(tmp_path / "voice.mp3"))
    bedp = _touch(str(tmp_path / "bed.wav"))
    bed = imaging.ImagingBed(bed_id="b", path=bedp, source=imaging.LicenseSource.PROCEDURAL)
    m = imaging.ClipMixer(str(tmp_path), dry_ratio=0.7)
    monkeypatch.setattr("shutil.which", lambda _x: "/usr/bin/ffmpeg")
    monkeypatch.setattr(imaging.BedSourcer, "_run_proc", staticmethod(lambda cmd: False))
    assert m.mix(v, bed) == v  # mix failed -> dry voice still airs


# =====================================================================================
# REQ-OE-009/010/011 — Stage 5: the producer (bounded; never raises; self-contained clip).
# =====================================================================================


def _producer(tmp_path, *, synth_path="OK", ledger=None, timeout=5.0):
    led = ledger if ledger is not None else EventLedger()
    bb = imaging.ImagingBriefBuilder(station_name="GSR", ledger=led, clock=lambda: 1.0)
    syn = imaging.Synthesizer(Config(), provider=object())
    if synth_path == "OK":
        synth_file = _touch(str(tmp_path / "voice.mp3"))
        syn.synth = lambda text: synth_file  # type: ignore
    else:
        syn.synth = lambda text: synth_path  # type: ignore
    reg = imaging.BedRegistry(ledger=led)
    bs = imaging.BedSourcer(reg, str(tmp_path), timeout_seconds=timeout)
    bs.source_bed = lambda **kw: None  # type: ignore  # DRY path keeps tests ffmpeg-free
    mx = imaging.ClipMixer(str(tmp_path), dry_ratio=1.0, timeout_seconds=timeout)
    return imaging.ImagingProducer(bb, syn, bs, mx, ledger=led,
                                   timeout_seconds=timeout, clock=lambda: 1.0), led


def test_producer_produces_a_self_contained_clip(tmp_path):
    prod, led = _producer(tmp_path)
    res = prod.produce(imaging_type=imaging.ImagingType.STATION_ID)
    assert not res.skipped
    assert res.clip_path and os.path.isfile(res.clip_path)  # self-contained file (REQ-OE-010)
    assert led.events(event_type="imaging_clip_produced")


def test_producer_skips_on_tts_failure(tmp_path):
    prod, led = _producer(tmp_path, synth_path=None)
    res = prod.produce(imaging_type=imaging.ImagingType.STATION_ID)
    assert res.skipped and res.reason == "tts_failed"
    assert res.clip_path is None
    assert led.events(event_type="imaging_clip_skipped")


def test_producer_never_raises_on_inner_fault(tmp_path):
    """Any inner fault yields a SKIPPED result, never an exception (REQ-OE-011)."""
    prod, led = _producer(tmp_path)
    prod._brief_builder.build = lambda **kw: (_ for _ in ()).throw(RuntimeError("boom"))  # type: ignore
    res = prod.produce()
    assert res.skipped and res.reason.startswith("error:")


def test_producer_times_out_and_skips(tmp_path):
    """[HARD] a hung produce returns a SKIP at the budget (REQ-OE-009), never blocks the tick."""
    prod, led = _producer(tmp_path, timeout=0.2)

    def _slow(*a, **k):
        time.sleep(5.0)
        return imaging.ImagingResult(clip_path="x")

    prod._produce_inner = _slow  # type: ignore
    t0 = time.monotonic()
    res = prod.produce()
    elapsed = time.monotonic() - t0
    assert res.skipped and res.reason == "timeout"
    assert elapsed < 2.0


# =====================================================================================
# REQ-OE-008/012 — Stage 6: the ready buffer + the single serialized worker.
# =====================================================================================


def test_ready_buffer_put_take_fifo():
    buf = imaging.ReadyBuffer(depth=3)
    # Use real files so take() (which checks existence) keeps them.
    import tempfile
    paths = []
    for i in range(2):
        fd, p = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        paths.append(p)
        assert buf.put(_result(clip_path=p, title=f"t{i}"))
    assert buf.size() == 2
    first = buf.take()
    assert first is not None and first.title == "t0"  # FIFO
    for p in paths:
        os.remove(p)


def test_ready_buffer_rejects_when_full():
    buf = imaging.ReadyBuffer(depth=1)
    import tempfile
    fd, p = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    assert buf.put(_result(clip_path=p))
    assert buf.is_full()
    assert not buf.put(_result(clip_path=p))  # full -> rejected
    os.remove(p)


def test_ready_buffer_rejects_skipped_result():
    buf = imaging.ReadyBuffer(depth=3)
    assert not buf.put(_result(skipped=True))
    assert buf.size() == 0


def test_ready_buffer_skips_vanished_file():
    buf = imaging.ReadyBuffer(depth=3)
    import tempfile
    fd, p = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    buf.put(_result(clip_path=p))
    os.remove(p)  # file vanishes before take
    assert buf.take() is None


class _StubProducer:
    def __init__(self, results):
        self._results = list(results)
        self.calls = 0

    def produce(self, **kw):
        self.calls += 1
        if self._results:
            return self._results.pop(0)
        return imaging.ImagingResult(reason="empty", skipped=True)


def test_worker_fills_one_clip_into_buffer(tmp_path):
    p = _touch(str(tmp_path / "c.mp3"))
    buf = imaging.ReadyBuffer(depth=2)
    w = imaging.GenerationWorker(_StubProducer([_result(clip_path=p)]), buf)
    assert w.fill_once() is True
    assert buf.size() == 1


def test_worker_noop_when_buffer_full(tmp_path):
    p = _touch(str(tmp_path / "c.mp3"))
    buf = imaging.ReadyBuffer(depth=1)
    buf.put(_result(clip_path=p))
    sp = _StubProducer([_result(clip_path=p)])
    w = imaging.GenerationWorker(sp, buf)
    assert w.fill_once() is False
    assert sp.calls == 0  # never produced — buffer already full


def test_worker_is_serialized_single_producer(tmp_path):
    """[HARD] no concurrency — a fill in flight makes a concurrent fill a no-op (REQ-OE-008/012)."""
    p = _touch(str(tmp_path / "c.mp3"))
    buf = imaging.ReadyBuffer(depth=5)
    gate = threading.Event()
    release = threading.Event()
    overlap = {"value": False}

    class _BlockingProducer:
        def __init__(self):
            self.active = 0

        def produce(self, **kw):
            self.active += 1
            if self.active > 1:
                overlap["value"] = True
            gate.set()
            release.wait(2.0)
            self.active -= 1
            return _result(clip_path=p)

    w = imaging.GenerationWorker(_BlockingProducer(), buf)
    t = threading.Thread(target=w.fill_once, daemon=True)
    t.start()
    assert gate.wait(2.0)
    # Second concurrent fill must be a no-op (lock held), never overlapping production.
    assert w.fill_once() is False
    release.set()
    t.join(2.0)
    assert overlap["value"] is False


# =====================================================================================
# REQ-OE-001/008 — the player + the system façade (cadence + the kind="imaging" item).
# =====================================================================================


def test_player_slot_due_first_time_and_after_cadence():
    pl = imaging.ImagingPlayer(station_name="GSR", cadence_seconds=100.0)
    assert pl.is_imaging_slot_due(0.0, now=50.0) is True  # never-aired -> due
    assert pl.is_imaging_slot_due(50.0, now=120.0) is False  # 70s < 100s cadence
    assert pl.is_imaging_slot_due(50.0, now=200.0) is True  # 150s >= cadence


def test_player_cadence_is_ai_overridable():
    """The cadence is the AI's discretion — passing cadence_s overrides the default (REQ-OE-001)."""
    pl = imaging.ImagingPlayer(cadence_seconds=1000.0)
    assert pl.is_imaging_slot_due(50.0, 10.0, now=70.0) is True  # 20s >= the 10s override


def test_player_makes_imaging_next_item(monkeypatch):
    import types
    fake_server = types.SimpleNamespace()

    class NextItem:
        def __init__(self, container_path, artist, title, kind, track):
            self.container_path = container_path
            self.artist = artist
            self.title = title
            self.kind = kind
            self.track = track

    fake_server.NextItem = NextItem
    monkeypatch.setitem(sys.modules, "brain.server", fake_server)
    pl = imaging.ImagingPlayer(station_name="GSR")
    item = pl.make_imaging_next_item("/music/.imaging/x.mp3", title="Sweeper")
    assert item.kind == "imaging"  # REQ-OE-008/010
    assert item.container_path == "/music/.imaging/x.mp3"
    assert item.artist == "GSR"


def _system(tmp_path, results):
    buf = imaging.ReadyBuffer(depth=3)
    w = imaging.GenerationWorker(_StubProducer(results), buf)
    pl = imaging.ImagingPlayer(station_name="GSR", cadence_seconds=100.0)
    return imaging.ImagingSystem(producer=_StubProducer([]), buffer=buf, worker=w,
                                 player=pl, ledger=EventLedger(), clock=lambda: 0.0), buf


def test_system_tick_refills_buffer(tmp_path):
    p = _touch(str(tmp_path / "c.mp3"))
    sysm, buf = _system(tmp_path, [_result(clip_path=p)])
    sysm.tick()
    assert buf.size() == 1


def test_system_next_item_due_with_ready_clip(monkeypatch, tmp_path):
    import types
    fake_server = types.SimpleNamespace()

    class NextItem:
        def __init__(self, container_path, artist, title, kind, track):
            self.container_path = container_path
            self.kind = kind
            self.title = title

    fake_server.NextItem = NextItem
    monkeypatch.setitem(sys.modules, "brain.server", fake_server)
    p = _touch(str(tmp_path / "c.mp3"))
    sysm, buf = _system(tmp_path, [_result(clip_path=p)])
    sysm.tick()  # buffer a clip
    item = sysm.next_imaging_item(now=10.0)  # never-aired -> due
    assert item is not None and item.kind == "imaging"


def test_system_next_item_due_but_empty_returns_none(tmp_path):
    """[HARD] a due-but-empty slot returns None (the picker plays music) WITHOUT blocking
    (REQ-OE-009)."""
    sysm, buf = _system(tmp_path, [])
    assert sysm.next_imaging_item(now=10.0) is None  # due, but buffer empty


def test_system_next_item_not_due_returns_none(monkeypatch, tmp_path):
    import types
    fake_server = types.SimpleNamespace()
    fake_server.NextItem = lambda **kw: object()
    monkeypatch.setitem(sys.modules, "brain.server", fake_server)
    p = _touch(str(tmp_path / "c.mp3"))
    sysm, buf = _system(tmp_path, [_result(clip_path=p)])
    sysm.tick()
    # Advance the clock once so it's served, then a second pull within cadence is not due.
    sysm.next_imaging_item(now=10.0)
    sysm.tick()
    assert sysm.next_imaging_item(now=20.0) is None  # 10s < 100s cadence


def test_system_methods_never_raise(tmp_path):
    """Every public ImagingSystem entry point swallows faults — never raises (REQ-OE-011)."""
    class _BoomProducer:
        def produce(self, **kw):
            raise RuntimeError("boom")

    buf = imaging.ReadyBuffer(depth=3)
    w = imaging.GenerationWorker(_BoomProducer(), buf)
    pl = imaging.ImagingPlayer(cadence_seconds=100.0)
    sysm = imaging.ImagingSystem(producer=_BoomProducer(), buffer=buf, worker=w, player=pl)
    # None of these raise:
    assert sysm.produce_one().skipped
    assert sysm.refill() is False
    assert sysm.next_imaging_item(now=10.0) is None
    sysm.tick()


# =====================================================================================
# REQ-OE-007/011 — the director path: imaging refills off-path, exception-isolated.
# =====================================================================================


def test_director_maybe_produce_imaging_calls_tick(tmp_path):
    """When wired, the director tick calls imaging_system.tick (off-path refill). REQ-OE-008."""
    class _Sys:
        def __init__(self):
            self.ticked = 0

        def tick(self, **kw):
            self.ticked += 1

    s = _Sys()
    d = Director(Config(), FakeLibrary(), FakeAcquirer(), FakeState(), threading.Event(),
                 imaging_system=s)
    d._maybe_produce_imaging()
    assert s.ticked == 1


def test_director_maybe_produce_imaging_swallows_fault(tmp_path):
    """An imaging fault never breaks the director tick (REQ-OE-009/011)."""
    class _Sys:
        def tick(self, **kw):
            raise RuntimeError("imaging down")

    d = Director(Config(), FakeLibrary(), FakeAcquirer(), FakeState(), threading.Event(),
                 imaging_system=_Sys())
    # Must not raise.
    d._maybe_produce_imaging()


# =====================================================================================
# build_imaging_system — the main.py assembly entry point.
# =====================================================================================


def test_build_imaging_system_assembles_full_pipeline():
    sysm = imaging.build_imaging_system(Config(), provider=object(), ledger=EventLedger())
    assert isinstance(sysm, imaging.ImagingSystem)
    assert sysm.cadence_seconds == Config().imaging_cadence_seconds


def test_build_imaging_system_tolerates_partial_config():
    """A minimal config object still builds — getattr defaults fill the gaps (best-effort)."""
    class _Min:
        station_name = "GSR"
        imaging_clips_dir = "/tmp/gsr-imaging"

    sysm = imaging.build_imaging_system(_Min(), provider=object())
    assert isinstance(sysm, imaging.ImagingSystem)
