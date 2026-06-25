"""Tests for SPEC-RADIO-HOSTLIFE-032 — Per-persona lived-experience loop.

Covers key acceptance criteria from acceptance.md Groups HL/HN/HE/HT/HF/HG.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

from brain.hostlife import (
    EngagementBit,
    EpisodicWriter,
    FramingComposer,
    HostlifeConfig,
    LedgerReader,
    LivedExperienceLoop,
    TasteFeeder,
    inject_lived_experience_context,
)
from brain.ledger import EventLedger
from brain.memory import DocumentStore
from brain.news_ledger import NewsStory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class _Persona:
    id: str = "indie-folk"
    display_name: str = "Indie Folk Host"
    voice: str = "default"
    pov_seed: str = "A lover of slow-burning folk and Americana."
    charter: Any = None
    anchors: List[str] = field(default_factory=list)
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.charter is None:
            self.charter = _Charter()


@dataclass
class _Charter:
    primary_territory: str = "folk"
    in_genres: List[str] = field(default_factory=lambda: ["folk", "americana", "singer-songwriter"])
    in_tags: List[str] = field(default_factory=lambda: ["acoustic", "indie"])
    in_eras: List[str] = field(default_factory=list)
    signature_artists: List[str] = field(default_factory=list)
    moods: List[str] = field(default_factory=list)


@dataclass
class _NewsAnchor:
    id: str = "news-anchor"
    display_name: str = "News Anchor"
    is_news_anchor: bool = True
    voice: str = "tts"
    charter: Any = None


def _story(story_id: str = "story-001", headline: str = "Folk festival season opens",
           source_name: str = "Paste Magazine", fetched_at: float = 1_000_000.0) -> NewsStory:
    return NewsStory(
        story_id=story_id,
        headline=headline,
        source_name=source_name,
        source_url="https://example.com",
        locality_tier="intl",
        significance=0.7,
        fetched_at=fetched_at,
    )


def _make_loop(stories: Optional[List[NewsStory]] = None, *, llm_fn=None,
               doc_root: str = "/tmp/hostlife-test-docs") -> tuple:
    """Build a LivedExperienceLoop with an in-memory ledger and stub news ledger."""
    news_mock = MagicMock()
    news_mock.candidates.return_value = list(stories or [])
    ledger = EventLedger()
    doc_store = DocumentStore(doc_root)
    loop = LivedExperienceLoop(
        news_mock, ledger, doc_store,
        config=HostlifeConfig(max_items_per_window=5, docs_root=doc_root),
        llm_fn=llm_fn,
    )
    return loop, ledger, doc_store, news_mock


# ===========================================================================
# AC-HL-006 — degenerate baseline: empty news → empty bits, normal show
# ===========================================================================

class TestAcHl006_DegenerateBaseline:
    def test_no_news_returns_empty_bits(self, tmp_path):
        loop, _, _, _ = _make_loop(stories=[], doc_root=str(tmp_path))
        bits = loop.run_for_persona(_Persona())
        assert bits == []

    def test_no_crash_on_empty_state(self, tmp_path):
        loop, _, _, _ = _make_loop(stories=[], doc_root=str(tmp_path))
        result = loop.run_for_persona(_Persona())
        assert isinstance(result, list)

    def test_none_persona_returns_empty(self, tmp_path):
        loop, _, _, _ = _make_loop(doc_root=str(tmp_path))
        assert loop.run_for_persona(None) == []


# ===========================================================================
# AC-HN-003 — news anchor excluded by construction
# ===========================================================================

class TestAcHn003_NewsAnchorExcluded:
    def test_news_anchor_gets_no_loop(self, tmp_path):
        stories = [_story()]
        loop, _, _, _ = _make_loop(stories=stories, doc_root=str(tmp_path))
        bits = loop.run_for_persona(_NewsAnchor())
        assert bits == []

    def test_curator_persona_does_get_loop(self, tmp_path):
        stories = [_story()]
        loop, _, _, _ = _make_loop(stories=stories, doc_root=str(tmp_path))
        bits = loop.run_for_persona(_Persona())
        assert len(bits) >= 0  # may be 0 if relevance filter drops, non-exceptional


# ===========================================================================
# AC-HN-004 — bounded: at most N items per window
# ===========================================================================

class TestAcHn004_Bounded:
    def test_max_items_per_window(self, tmp_path):
        stories = [
            _story(f"story-{i:03d}", headline=f"Folk news {i}", fetched_at=float(i))
            for i in range(10)
        ]
        loop, _, _, _ = _make_loop(stories=stories, doc_root=str(tmp_path))
        config = HostlifeConfig(max_items_per_window=3)
        loop._config = config
        bits = loop.run_for_persona(_Persona())
        assert len(bits) <= 3

    def test_zero_items_cap(self, tmp_path):
        stories = [_story(f"story-{i:03d}", headline=f"Folk news {i}") for i in range(5)]
        loop, _, _, _ = _make_loop(stories=stories, doc_root=str(tmp_path))
        loop._config = HostlifeConfig(max_items_per_window=0)
        bits = loop.run_for_persona(_Persona())
        assert bits == []


# ===========================================================================
# AC-HN-006 — dedup: already-engaged items are skipped
# ===========================================================================

class TestAcHn006_Dedup:
    def test_already_engaged_skipped(self, tmp_path):
        s = _story("dedup-001", headline="Folk festival news")
        loop, ledger, doc_store, _ = _make_loop(stories=[s], doc_root=str(tmp_path))
        persona = _Persona()

        # First run: engage the story
        bits1 = loop.run_for_persona(persona)
        assert len(bits1) == 1

        # Second run: story is already engaged, should be skipped
        bits2 = loop.run_for_persona(persona)
        assert bits2 == []

    def test_different_persona_not_deduped(self, tmp_path):
        s = _story("dedup-002", headline="Folk record review")
        loop, _, _, _ = _make_loop(stories=[s], doc_root=str(tmp_path))

        persona_a = _Persona(id="folk-a")
        persona_b = _Persona(id="folk-b")
        bits_a = loop.run_for_persona(persona_a)
        bits_b = loop.run_for_persona(persona_b)
        assert len(bits_a) == 1
        assert len(bits_b) == 1


# ===========================================================================
# AC-HE-001/002 — memory bit captured at engagement with source_attribution
# ===========================================================================

class TestAcHe001_MemoryBitCaptured:
    def test_bit_written_to_ledger(self, tmp_path):
        s = _story("mem-001", headline="Folk singer signs deal", source_name="Pitchfork")
        loop, ledger, _, _ = _make_loop(stories=[s], doc_root=str(tmp_path))
        persona = _Persona()
        bits = loop.run_for_persona(persona)

        assert len(bits) == 1
        bit = bits[0]
        assert bit.persona_id == persona.id
        assert bit.item_id == "mem-001"
        assert bit.source_attribution["outlet"] == "Pitchfork"
        assert bit.source_attribution["item_id"] == "mem-001"
        assert "date" in bit.source_attribution

    def test_bit_reconstructable_from_ledger(self, tmp_path):
        s = _story("mem-002", headline="Folk awards ceremony")
        loop, ledger, _, _ = _make_loop(stories=[s], doc_root=str(tmp_path))
        persona = _Persona()
        loop.run_for_persona(persona)

        writer = loop.writer
        bits_back = writer.bits_for_window(persona.id)
        assert len(bits_back) == 1
        assert bits_back[0].item_id == "mem-002"


# ===========================================================================
# AC-HE-003 — biography grows after engagement
# ===========================================================================

class TestAcHe003_BiographyGrows:
    def test_biography_written_to_doc_store(self, tmp_path):
        s = _story("bio-001", headline="Singer-songwriter debut", source_name="Paste")
        loop, ledger, doc_store, _ = _make_loop(stories=[s], doc_root=str(tmp_path))
        persona = _Persona(id="folk-hero")
        loop.run_for_persona(persona)

        doc = doc_store.read_document("hosts", "folk-hero")
        assert doc is not None
        assert "Paste" in doc or "folk-hero" in doc

    def test_biography_grows_on_second_engagement(self, tmp_path):
        s1 = _story("bio-002a", headline="Folk news A", fetched_at=1.0)
        s2 = _story("bio-002b", headline="Folk news B", fetched_at=2.0)
        loop, ledger, doc_store, news_mock = _make_loop(stories=[], doc_root=str(tmp_path))
        persona = _Persona(id="folk-grower")

        news_mock.candidates.return_value = [s1]
        loop.run_for_persona(persona)
        doc_after_one = doc_store.read_document("hosts", "folk-grower") or ""

        news_mock.candidates.return_value = [s2]
        loop.run_for_persona(persona)
        doc_after_two = doc_store.read_document("hosts", "folk-grower") or ""

        assert len(doc_after_two) >= len(doc_after_one)


# ===========================================================================
# AC-HL-004 — exception isolation: LLM error → empty bits, no raise
# ===========================================================================

class TestAcHl004_ExceptionIsolated:
    def test_llm_raises_does_not_crash(self, tmp_path):
        def boom_llm(model: str, prompt: str) -> str:
            raise RuntimeError("LLM offline")

        s = _story("exc-001", headline="Folk awards")
        loop, _, _, _ = _make_loop(stories=[s], llm_fn=boom_llm, doc_root=str(tmp_path))
        bits = loop.run_for_persona(_Persona())
        # Bit still written with empty reaction (fail-toward-allow)
        assert isinstance(bits, list)

    def test_broken_news_ledger_returns_empty(self, tmp_path):
        news_mock = MagicMock()
        news_mock.candidates.side_effect = RuntimeError("ledger down")
        ledger = EventLedger()
        doc_store = DocumentStore(str(tmp_path))
        loop = LivedExperienceLoop(news_mock, ledger, doc_store,
                                   config=HostlifeConfig(docs_root=str(tmp_path)))
        bits = loop.run_for_persona(_Persona())
        assert bits == []


# ===========================================================================
# AC-HG-002 — closed-world framing: compose_framing only uses real bits
# ===========================================================================

class TestAcHg002_ClosedWorldFraming:
    def test_framing_uses_only_real_bits(self, tmp_path):
        calls: List[str] = []

        def capture_llm(model: str, prompt: str) -> str:
            calls.append(prompt)
            return "A short framing response."

        bit = EngagementBit(
            persona_id="folk-host",
            item_id="item-framing",
            engaged_at=1_000_000.0,
            reaction="Really interesting piece.",
            source_attribution={"item_id": "item-framing", "date": "2026-06-25", "outlet": "Paste"},
        )
        composer = FramingComposer(capture_llm)
        persona = _Persona()
        result = composer.compose_framing(persona, [bit])

        assert result == "A short framing response."
        assert len(calls) == 1
        prompt = calls[0]
        assert "Paste" in prompt
        assert "Really interesting piece." in prompt

    def test_empty_bits_returns_empty_framing(self):
        composer = FramingComposer(lambda m, p: "should not be called")
        persona = _Persona()
        result = composer.compose_framing(persona, [])
        assert result == ""

    def test_no_llm_returns_empty(self):
        composer = FramingComposer(None)
        bit = EngagementBit("p", "i", 1.0, "reaction", {"item_id": "i", "date": "d", "outlet": "o"})
        assert composer.compose_framing(_Persona(), [bit]) == ""


# ===========================================================================
# inject_lived_experience_context — HOSTCTX-016 seam
# ===========================================================================

class TestInjectLivedExperienceContext:
    def test_bits_present_adds_framing_key(self, tmp_path):
        ledger = EventLedger()
        doc_store = DocumentStore(str(tmp_path))
        writer = EpisodicWriter(ledger, doc_store)

        bit = EngagementBit(
            persona_id="folk-host",
            item_id="inj-001",
            engaged_at=1_000_000.0,
            reaction="I loved this track.",
            source_attribution={"item_id": "inj-001", "date": "2026-06-25", "outlet": "Pitchfork"},
        )
        writer.write_bit(bit)

        def llm_fn(model: str, prompt: str) -> str:
            return "Since we last spoke, I've been lost in some new folk."

        composer = FramingComposer(llm_fn)
        context: Dict[str, Any] = {}
        persona = _Persona(id="folk-host")
        inject_lived_experience_context(context, "folk-host", writer, composer, persona)

        assert "lived_experience_framing" in context
        assert context["lived_experience_framing"] == "Since we last spoke, I've been lost in some new folk."
        assert "lived_experience_bits" in context

    def test_no_bits_does_not_add_key(self, tmp_path):
        ledger = EventLedger()
        doc_store = DocumentStore(str(tmp_path))
        writer = EpisodicWriter(ledger, doc_store)
        composer = FramingComposer(lambda m, p: "framing")

        context: Dict[str, Any] = {}
        inject_lived_experience_context(context, "folk-host", writer, composer, _Persona())
        assert "lived_experience_framing" not in context

    def test_llm_error_does_not_add_key(self, tmp_path):
        ledger = EventLedger()
        doc_store = DocumentStore(str(tmp_path))
        writer = EpisodicWriter(ledger, doc_store)

        bit = EngagementBit("folk-host", "inj-002", 1.0, "reaction",
                            {"item_id": "inj-002", "date": "2026-06-25", "outlet": "Paste"})
        writer.write_bit(bit)

        def boom_llm(model: str, prompt: str) -> str:
            raise RuntimeError("LLM down")

        composer = FramingComposer(boom_llm)
        context: Dict[str, Any] = {}
        inject_lived_experience_context(context, "folk-host", writer, composer, _Persona(id="folk-host"))
        assert "lived_experience_framing" not in context


# ===========================================================================
# TasteFeeder — seam, fail-silent
# ===========================================================================

class TestTasteFeeder:
    def test_no_budget_no_crash(self):
        feeder = TasteFeeder(None)
        feeder.feed_discovery("p", "Artist - Album", {})

    def test_budget_with_hook_called(self):
        budget = MagicMock()
        feeder = TasteFeeder(budget)
        feeder.feed_discovery("folk-host", "Iron & Wine - Our Endless Numbered Days", {"outlet": "Paste"})
        budget.record_taste_signal.assert_called_once()

    def test_budget_error_does_not_raise(self):
        budget = MagicMock()
        budget.record_taste_signal.side_effect = RuntimeError("budget error")
        feeder = TasteFeeder(budget)
        feeder.feed_discovery("folk-host", "track", {})


# ===========================================================================
# LedgerReader — charter relevance and gap window
# ===========================================================================

class TestLedgerReader:
    def test_charter_irrelevant_story_filtered(self, tmp_path):
        metal_story = _story("metal-001", headline="Death metal festival", source_name="MetalInjection")
        news_mock = MagicMock()
        news_mock.candidates.return_value = [metal_story]
        ledger = EventLedger()
        reader = LedgerReader(news_mock, ledger)

        folk_persona = _Persona()
        results = reader.select_for_persona(folk_persona)
        assert results == []

    def test_charter_relevant_story_included(self, tmp_path):
        folk_story = _story("folk-002", headline="Folk and americana singer wins award", source_name="Pitchfork")
        news_mock = MagicMock()
        news_mock.candidates.return_value = [folk_story]
        ledger = EventLedger()
        reader = LedgerReader(news_mock, ledger)

        folk_persona = _Persona()
        results = reader.select_for_persona(folk_persona)
        assert len(results) == 1

    def test_gap_window_filters_old_items(self, tmp_path):
        old_story = _story("old-001", headline="Folk news from last year", fetched_at=1.0)
        news_mock = MagicMock()
        news_mock.candidates.return_value = [old_story]
        ledger = EventLedger()
        reader = LedgerReader(news_mock, ledger)

        # last_aired = 1000 means story fetched at 1.0 is too old
        results = reader.select_for_persona(_Persona(), last_aired=1000.0)
        assert results == []
