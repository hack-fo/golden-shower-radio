"""Tests for brain/news.py — SPEC-RADIO-OPS-004 Group OG (News & Newscasting).

DDD discipline: this file is BOTH the characterization safety-net (PRESERVE) AND the
acceptance proof (the 9 ACs). It NEVER makes a real LLM call, NEVER makes a real HTTP/network
call (the per-source fetch is always an injected fake), and NEVER spins the real daemon thread
with real sleeps — it drives the unit surfaces (NewsSourceList / NewsAggregator /
NewscastBuilder / NewscastProducer / NewsPlayer / BreakingNewsBuffer) and the director's
_maybe_produce_news path directly.

Characterization pins (PRESERVE — behaviour preservation, the load-bearing rail):
  * With newscasting OFF (the default — news_producer/news_player None on the Director) the
    director _tick produces NO newscast and the curate/enqueue path is byte-identical to before
    this SPEC (REQ-OG-009 behaviour preservation). The new default-None params change nothing.

Acceptance coverage (the 9 ACs):
  AC-OG-001  AI chooses cadence; a due slot triggers a newscast; no fixed hardcoded schedule.
  AC-OG-002  the trusted-source list persists + evolves (add/remove/evaluate, each logged), a
             VIEW over the ONE ledger, no human input.
  AC-OG-003  aggregation prefers feeds/APIs, dedups, runs off-path + never blocks.
  AC-OG-004  the newscast reflects what trusted sources report (attribution carries the source).
  AC-OG-005  [HARD] only grounded + attributed + apolitical items air; ungroundable -> dropped.
  AC-OG-006  Faroese angle prioritized first; faroese-majority routes to the teldutala.fo voice.
  AC-OG-007  a due slot yields a kind="news" NextItem through the shared pipeline; no liq change.
  AC-OG-008  (optional) breaking news releases ONLY at a safe boundary; never silences.
  AC-OG-009  [HARD] slow/errored/unavailable news -> SKIP with log; never blocks the stream.

Run: python3 -m pytest brain/test_news.py -q
"""

from __future__ import annotations

import os
import sys
import threading
import time

try:
    from brain import news
    from brain.director import Director
    from brain.config import Config
    from brain.ledger import EventLedger, is_registered_event_type
except Exception:  # noqa: BLE001 - direct-run fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from brain import news
    from brain.director import Director
    from brain.config import Config
    from brain.ledger import EventLedger, is_registered_event_type


# --------------------------------------------------------------------------- #
# Lightweight fakes (mirror test_characterize_director.py).
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


def _item(headline, source_id="src", *, summary="body", language="en",
          priority=news.PRIORITY_INTERNATIONAL, grounded=True, published_at=0.0):
    return news.NewsItem(
        item_id=news.news_key(headline, source_id), source_id=source_id,
        headline=headline, summary=summary, url="http://x", language=language,
        published_at=published_at, fetched_at=0.0, priority=priority, grounded=grounded,
    )


# =====================================================================================
# PRESERVE — characterization: with newscasting OFF the director is byte-identical.
# =====================================================================================


def test_characterize_director_default_has_no_news_subsystem():
    """The new news params default to None — the default-constructed Director carries no
    producer/player/source-list, so the news path is wholly inert (behaviour preservation)."""
    d = Director(Config(), FakeLibrary(), FakeAcquirer(), FakeState(), threading.Event())
    assert d.news_producer is None
    assert d.news_source_list is None
    assert d.news_player is None


def test_characterize_maybe_produce_news_is_noop_when_off():
    """_maybe_produce_news returns immediately (no produce, no clock advance) when the
    producer/player are None — the default station path is byte-identical (REQ-OG-009)."""
    d = Director(Config(), FakeLibrary(), FakeAcquirer(), FakeState(), threading.Event())
    before = d._last_news_at
    d._maybe_produce_news()  # must not raise, must not produce
    assert d._last_news_at == before


def test_characterize_tick_with_news_off_does_not_touch_news(monkeypatch):
    """A full _tick with news off enqueues the curated batch and NEVER builds a newscast — the
    curate/enqueue accounting is identical to before this SPEC."""
    monkeypatch.setattr(
        "brain.director.llm.curate_batch",
        lambda **kw: [{"artist": "A", "title": "B"}],
    )
    acq = FakeAcquirer()
    d = Director(Config(), FakeLibrary(), acq, FakeState(), threading.Event())
    d._tick()
    assert acq.calls == [("A", "B")]
    assert d._last_news_at == 0.0  # the news clock never advanced


# =====================================================================================
# AC-OG-002 — the evolving trusted-source list (a VIEW over the ledger, each change logged).
# =====================================================================================


def test_news_event_types_registered_in_ledger_vocabulary():
    """The news event family is REGISTERED in the ONE ledger vocabulary (no new store)."""
    for ev in ("news_source_added", "news_source_removed", "news_source_evaluated",
               "news_aired", "news_skipped"):
        assert is_registered_event_type(ev), ev


def test_source_list_add_and_list_active_in_memory():
    sl = news.NewsSourceList(ledger=None, clock=lambda: 100.0)
    sl.add_source(news.NewsSource("kvf", "KVF", "http://kvf.fo",
                                  priority=news.PRIORITY_FAROESE, language="fo"))
    active = sl.list_active()
    assert [s.source_id for s in active] == ["kvf"]
    assert active[0].language == "fo"


def test_source_list_persists_through_ledger_view():
    """The list is a VIEW over the ledger: an add is a logged event, and a fresh
    NewsSourceList over the SAME ledger reconstructs the source (cross-instance durability)."""
    led = EventLedger()
    sl = news.NewsSourceList(ledger=led, clock=lambda: 1.0)
    sl.add_source(news.NewsSource("ap", "AP", "http://ap", language="en"))
    assert led.events(event_type="news_source_added")  # the add was logged
    # A brand-new view over the same ledger sees the source — it is a projection, not state.
    sl2 = news.NewsSourceList(ledger=led)
    assert [s.source_id for s in sl2.list_active()] == ["ap"]


def test_source_list_remove_deactivates_via_logged_event():
    led = EventLedger()
    sl = news.NewsSourceList(ledger=led, clock=lambda: 1.0)
    sl.add_source(news.NewsSource("ap", "AP", "http://ap"), at=1.0)
    sl.remove_source("ap", reason="stale", at=2.0)
    assert led.events(event_type="news_source_removed")
    assert sl.list_active() == []           # removed -> inactive
    assert len(sl.list_all()) == 1          # but history is retained (append-only)


def test_source_list_readd_reactivates():
    """Append-only: a re-add AFTER a remove re-activates the source (last event wins)."""
    led = EventLedger()
    sl = news.NewsSourceList(ledger=led, clock=lambda: 1.0)
    sl.add_source(news.NewsSource("ap", "AP", "http://ap"), at=1.0)
    sl.remove_source("ap", at=2.0)
    sl.add_source(news.NewsSource("ap", "AP", "http://ap"), at=3.0)
    assert [s.source_id for s in sl.list_active()] == ["ap"]


def test_source_list_evaluate_logs_without_changing_active_state():
    led = EventLedger()
    sl = news.NewsSourceList(ledger=led, clock=lambda: 1.0)
    sl.add_source(news.NewsSource("ap", "AP", "http://ap"), at=1.0)
    sl.evaluate_source("ap", quality=0.9, note="reliable", at=2.0)
    assert led.events(event_type="news_source_evaluated")
    assert [s.source_id for s in sl.list_active()] == ["ap"]  # still active


def test_source_list_seed_is_idempotent():
    sl = news.NewsSourceList(ledger=None, clock=lambda: 1.0)
    n1 = sl.seed()
    assert n1 > 0
    n2 = sl.seed()                          # already populated
    assert n2 == 0
    assert len(sl.list_all()) == n1


# =====================================================================================
# AC-OG-003 — aggregation: feeds first, dedups, off-path + never-blocks.
# =====================================================================================


def test_aggregator_uses_injected_fetch_and_dedups():
    """fetch_all merges per-source items and DEDUPS by item_id (same story once)."""
    def fake_fetch(source, timeout):
        if source.source_id == "a":
            return [_item("Big Story", "a"), _item("Local Story", "a")]
        return [_item("Big Story", "b")]  # same headline -> dedup

    agg = news.NewsAggregator(fetch_fn=fake_fetch, timeout_seconds=5.0)
    srcs = [news.NewsSource("a", "A", "x"), news.NewsSource("b", "B", "y")]
    items = agg.fetch_all(srcs)
    headlines = sorted(i.headline for i in items)
    assert headlines == ["Big Story", "Local Story"]  # 3 fetched, 2 after dedup


def test_aggregator_skips_inactive_sources():
    def fake_fetch(source, timeout):
        return [_item("S", source.source_id)]

    agg = news.NewsAggregator(fetch_fn=fake_fetch)
    srcs = [news.NewsSource("a", "A", "x", active=True),
            news.NewsSource("b", "B", "y", active=False)]
    items = agg.fetch_all(srcs)
    assert {i.source_id for i in items} == {"a"}


def test_aggregator_one_bad_source_does_not_abort():
    """A per-source fault is isolated — one raising source never aborts the aggregation."""
    def fake_fetch(source, timeout):
        if source.source_id == "bad":
            raise RuntimeError("boom")
        return [_item("Good", source.source_id)]

    agg = news.NewsAggregator(fetch_fn=fake_fetch, timeout_seconds=5.0)
    srcs = [news.NewsSource("bad", "Bad", "x"), news.NewsSource("ok", "Ok", "y")]
    items = agg.fetch_all(srcs)
    assert [i.source_id for i in items] == ["ok"]


def test_aggregator_fetch_source_times_out_to_empty():
    """A slow source NEVER holds the caller past the budget — it yields [] (REQ-OG-009)."""
    def slow_fetch(source, timeout):
        time.sleep(0.5)
        return [_item("Late", source.source_id)]

    agg = news.NewsAggregator(fetch_fn=slow_fetch, timeout_seconds=0.05)
    started = time.monotonic()
    items = agg.fetch_source(news.NewsSource("s", "S", "x"))
    elapsed = time.monotonic() - started
    assert items == []
    assert elapsed < 0.45  # returned at the budget, not after the slow fetch finished


# =====================================================================================
# AC-OG-006 — Faroese angle prioritized first; routing to the teldutala.fo voice.
# =====================================================================================


def test_aggregator_sorts_faroese_first():
    def fake_fetch(source, timeout):
        # Distinct headlines per source so dedup keeps all three (dedup folds same headlines).
        return [_item(f"Story {source.source_id}", source.source_id,
                      priority=source.priority)]

    agg = news.NewsAggregator(fetch_fn=fake_fetch)
    srcs = [
        news.NewsSource("intl", "Intl", "x", priority=news.PRIORITY_INTERNATIONAL),
        news.NewsSource("fo", "FO", "y", priority=news.PRIORITY_FAROESE),
        news.NewsSource("nordic", "N", "z", priority=news.PRIORITY_NORDIC),
    ]
    items = agg.fetch_all(srcs)
    assert [i.priority for i in items] == [
        news.PRIORITY_FAROESE, news.PRIORITY_NORDIC, news.PRIORITY_INTERNATIONAL,
    ]


def test_producer_routes_faroese_majority_to_faroese_voice():
    """A faroese-majority newscast routes the voice to the teldutala.fo Faroese voice."""
    captured = {}

    def synth(text, language, voice_id):
        captured.update(language=language, voice_id=voice_id)
        return "/clip.mp3"

    def fake_fetch(source, timeout):
        return [_item("F1", "fo", language="fo", priority=news.PRIORITY_FAROESE),
                _item("F2", "fo", language="fo", priority=news.PRIORITY_FAROESE)]

    agg = news.NewsAggregator(fetch_fn=fake_fetch)
    prod = news.NewscastProducer(
        aggregator=agg, builder=news.NewscastBuilder(), synth=synth,
        faroese_voice_female="Hanna22k_NT", timeout_seconds=5.0)
    result = prod.produce([news.NewsSource("fo", "FO", "x", language="fo",
                                           priority=news.PRIORITY_FAROESE)])
    assert not result.skipped
    assert captured["language"] == "fo"
    assert captured["voice_id"] == "Hanna22k_NT"


def test_producer_routes_english_majority_to_english_voice():
    captured = {}

    def synth(text, language, voice_id):
        captured.update(language=language)
        return "/clip.mp3"

    def fake_fetch(source, timeout):
        return [_item("E1", "ap", language="en")]

    prod = news.NewscastProducer(
        aggregator=news.NewsAggregator(fetch_fn=fake_fetch),
        builder=news.NewscastBuilder(), synth=synth, timeout_seconds=5.0)
    result = prod.produce([news.NewsSource("ap", "AP", "x", language="en")])
    assert not result.skipped
    assert captured["language"] == "en"


# =====================================================================================
# AC-OG-004 / AC-OG-005 — grounded + attributed + apolitical; ungroundable dropped.
# =====================================================================================


def test_builder_attributes_each_item_to_its_source():
    b = news.NewscastBuilder(name_resolver=lambda sid: {"ap": "Associated Press"}.get(sid, sid))
    script = b.build_script([_item("Markets rise", "ap", summary="Stocks up")])
    assert "According to Associated Press" in script
    assert "Markets rise" in script


def test_builder_drops_ungrounded_items():
    """[HARD] an ungroundable item is DROPPED, never aired (REQ-OG-005)."""
    b = news.NewscastBuilder()
    script = b.build_script([
        _item("Grounded fact", "ap", grounded=True),
        _item("Rumour", "ap", grounded=False),
    ])
    assert "Grounded fact" in script
    assert "Rumour" not in script


def test_builder_returns_none_when_no_grounded_items():
    """Zero grounded items -> None so the producer SKIPS (never airs an empty newscast)."""
    b = news.NewscastBuilder()
    assert b.build_script([_item("X", "ap", grounded=False)]) is None
    assert b.build_script([]) is None


def test_builder_rejects_political_script():
    """[HARD] a partisan script is rejected (None) — the read stays apolitical (REQ-OG-005)."""
    b = news.NewscastBuilder()
    political = [_item("Citizens told to vote for the leftist agenda candidate", "ap")]
    assert b.build_script(political) is None


def test_builder_is_apolitical_predicate():
    assert news.NewscastBuilder.is_apolitical("Weather is mild today.")
    assert not news.NewscastBuilder.is_apolitical("This is left-wing propaganda.")


def test_builder_respects_max_items():
    b = news.NewscastBuilder()
    items = [_item(f"Story {n}", "ap") for n in range(10)]
    script = b.build_script(items, max_items=3)
    assert script.count("According to") == 3


# =====================================================================================
# AC-OG-009 — slow/errored/unavailable news -> SKIP with log; never blocks.
# =====================================================================================


def test_producer_skips_on_no_items():
    prod = news.NewscastProducer(
        aggregator=news.NewsAggregator(fetch_fn=lambda s, t: []),
        builder=news.NewscastBuilder(),
        synth=lambda *a: "/x.mp3", timeout_seconds=5.0)
    result = prod.produce([news.NewsSource("a", "A", "x")])
    assert result.skipped
    assert result.clip_path is None
    assert result.reason == "no_items"


def test_producer_skips_on_ungroundable():
    def fake_fetch(source, timeout):
        return [_item("Rumour", "ap", grounded=False)]

    prod = news.NewscastProducer(
        aggregator=news.NewsAggregator(fetch_fn=fake_fetch),
        builder=news.NewscastBuilder(), synth=lambda *a: "/x.mp3", timeout_seconds=5.0)
    result = prod.produce([news.NewsSource("ap", "AP", "x")])
    assert result.skipped
    assert result.reason == "ungroundable_or_political"


def test_producer_skips_on_tts_failure():
    def fake_fetch(source, timeout):
        return [_item("Real news", "ap")]

    prod = news.NewscastProducer(
        aggregator=news.NewsAggregator(fetch_fn=fake_fetch),
        builder=news.NewscastBuilder(), synth=lambda *a: None,  # TTS failed
        timeout_seconds=5.0)
    result = prod.produce([news.NewsSource("ap", "AP", "x")])
    assert result.skipped
    assert result.reason == "tts_failed"


def test_producer_never_raises_on_internal_error():
    """An exception anywhere inside produce SKIPS the slot, never propagates (never blocks)."""
    class Boom:
        def fetch_all(self, sources, timeout=None):
            raise RuntimeError("kaboom")

    prod = news.NewscastProducer(
        aggregator=Boom(), builder=news.NewscastBuilder(),
        synth=lambda *a: "/x.mp3", timeout_seconds=5.0)
    result = prod.produce([news.NewsSource("a", "A", "x")])
    assert result.skipped
    assert result.reason.startswith("error:")


def test_producer_times_out_without_blocking():
    """A produce that overruns the budget returns a SKIPPED result at the deadline (never blocks)."""
    class Slow:
        def fetch_all(self, sources, timeout=None):
            time.sleep(0.5)
            return [_item("Late", "ap")]

    prod = news.NewscastProducer(
        aggregator=Slow(), builder=news.NewscastBuilder(),
        synth=lambda *a: "/x.mp3", timeout_seconds=0.05)
    started = time.monotonic()
    result = prod.produce([news.NewsSource("a", "A", "x")])
    elapsed = time.monotonic() - started
    assert result.skipped
    assert result.reason == "timeout"
    assert elapsed < 0.45


def test_producer_logs_aired_and_skipped_to_ledger():
    """produce writes a news_aired / news_skipped audit onto the ONE ledger (best-effort)."""
    led = EventLedger()

    def fake_fetch(source, timeout):
        return [_item("Real news", "ap")]

    prod = news.NewscastProducer(
        aggregator=news.NewsAggregator(fetch_fn=fake_fetch),
        builder=news.NewscastBuilder(), synth=lambda *a: "/clip.mp3",
        ledger=led, timeout_seconds=5.0)
    prod.produce([news.NewsSource("ap", "AP", "x")])
    assert led.events(event_type="news_aired")

    prod_skip = news.NewscastProducer(
        aggregator=news.NewsAggregator(fetch_fn=lambda s, t: []),
        builder=news.NewscastBuilder(), synth=lambda *a: "/clip.mp3",
        ledger=led, timeout_seconds=5.0)
    prod_skip.produce([news.NewsSource("ap", "AP", "x")])
    assert led.events(event_type="news_skipped")


# =====================================================================================
# AC-OG-001 / AC-OG-007 — the news slot: AI-chosen cadence + the kind="news" NextItem.
# =====================================================================================


def test_player_slot_due_respects_chosen_cadence():
    """is_news_slot_due answers 'has the AI-chosen cadence elapsed?' — NOT a fixed schedule."""
    p = news.NewsPlayer(cadence_seconds=1800.0)
    # Never aired yet -> due immediately (the station opens in its rhythm).
    assert p.is_news_slot_due(0.0, now=10_000.0)
    # Aired recently -> not due.
    assert not p.is_news_slot_due(10_000.0, now=10_500.0)
    # Cadence elapsed -> due.
    assert p.is_news_slot_due(10_000.0, now=12_000.0)


def test_player_cadence_is_overridable_per_call():
    """The cadence is the AI's discretion — overridable per call, not hardcoded."""
    p = news.NewsPlayer(cadence_seconds=1800.0)
    # A 60s override makes a slot 90s old due even though the default 1800s would not be.
    assert p.is_news_slot_due(10_000.0, 60.0, now=10_090.0)
    assert not p.is_news_slot_due(10_000.0, 1800.0, now=10_090.0)


def test_player_make_news_next_item_is_kind_news():
    """A produced clip becomes a kind="news" NextItem served through the EXISTING pull path
    (REQ-OG-007) — no Liquidsoap change, the picker serves it like any pulled file."""
    p = news.NewsPlayer(station_name="GSR")
    item = p.make_news_next_item("/news/clip.mp3", title="Top of the hour")
    assert item.kind == "news"
    assert item.container_path == "/news/clip.mp3"
    assert item.title == "Top of the hour"


# =====================================================================================
# AC-OG-008 (optional) — breaking news only at a safe boundary; never silences.
# =====================================================================================


def test_breaking_buffer_holds_until_safe_boundary():
    buf = news.BreakingNewsBuffer()
    buf.push(_item("BREAKING", "ap"))
    assert buf.pending() == 1
    # Mid-song (not ended) -> nothing released (never cuts mid-vocal).
    assert buf.pop_if_safe(currently_playing_ended=False) is None
    assert buf.pending() == 1
    # At the song boundary -> released.
    item = buf.pop_if_safe(currently_playing_ended=True)
    assert item is not None and item.headline == "BREAKING"
    assert buf.pending() == 0


def test_breaking_buffer_empty_pop_is_none():
    buf = news.BreakingNewsBuffer()
    assert buf.pop_if_safe(currently_playing_ended=True) is None  # never silences


# =====================================================================================
# AC-OG-001 / AC-OG-007 wired through the director (end-to-end, news ON).
# =====================================================================================


class _FakeProducer:
    def __init__(self, result):
        self._result = result
        self.calls = 0

    def produce(self, sources, *, timeout=None):
        self.calls += 1
        return self._result


def test_director_produces_news_when_slot_due(monkeypatch):
    """With news wired, a due slot drives one produce + builds the kind="news" NextItem, and the
    cadence clock advances so it does not hot-loop."""
    monkeypatch.setattr("brain.director.llm.curate_batch", lambda **kw: [])
    result = news.NewscastResult(clip_path="/clip.mp3", language="en", item_count=2,
                                 reason="aired", skipped=False)
    producer = _FakeProducer(result)
    sl = news.NewsSourceList(ledger=None, clock=lambda: 1.0)
    sl.add_source(news.NewsSource("ap", "AP", "x"))
    player = news.NewsPlayer(cadence_seconds=1800.0)
    d = Director(Config(), FakeLibrary(), FakeAcquirer(), FakeState(), threading.Event(),
                 news_producer=producer, news_source_list=sl, news_player=player)
    assert d._last_news_at == 0.0
    d._tick()
    assert producer.calls == 1            # a due slot produced exactly one newscast
    assert d._last_news_at > 0.0          # cadence clock advanced (no hot-loop)


def test_director_skips_news_when_not_due(monkeypatch):
    monkeypatch.setattr("brain.director.llm.curate_batch", lambda **kw: [])
    producer = _FakeProducer(news.NewscastResult(skipped=True, reason="no_items"))
    player = news.NewsPlayer(cadence_seconds=1800.0)
    d = Director(Config(), FakeLibrary(), FakeAcquirer(), FakeState(), threading.Event(),
                 news_producer=producer, news_source_list=None, news_player=player)
    d._last_news_at = time.time()  # just aired -> not due
    d._tick()
    assert producer.calls == 0


def test_director_news_error_never_breaks_tick(monkeypatch):
    """A producer that raises is swallowed — the tick survives (never blocks the stream)."""
    monkeypatch.setattr("brain.director.llm.curate_batch", lambda **kw: [])

    class Boom:
        def produce(self, sources, *, timeout=None):
            raise RuntimeError("explode")

    player = news.NewsPlayer(cadence_seconds=1800.0)
    d = Director(Config(), FakeLibrary(), FakeAcquirer(), FakeState(), threading.Event(),
                 news_producer=Boom(), news_source_list=None, news_player=player)
    d._tick()  # must not raise
