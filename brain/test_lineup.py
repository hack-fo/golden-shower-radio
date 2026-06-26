"""SPEC-RADIO-LINEUP-050 tests — M1 ShowRegistry + M2 cross-persona firewall.

Brownfield TDD (RED -> GREEN -> REFACTOR). Mirrors the LIKE-015 / STATS-013 test
convention (see brain/test_analytics.py): a per-test fresh connection to a tmp
events.db via sqlite_store.reset_registry_for_tests(). Not committed by this agent;
git is handled at the orchestrator level.

Run with:
    python3 -m pytest brain/test_lineup.py -q

AC map (1:1 with .moai/specs/SPEC-RADIO-LINEUP-050/acceptance.md):
  M1 store     -> AC-SH-001, AC-NFR-LU-6
  M2 firewall  -> AC-SQ-001, AC-SQ-002 (B3), AC-SQ-003 (B9), AC-NFR-LU-4 (B8)
"""

from __future__ import annotations

import sqlite3

import pytest

from brain import sqlite_store
from brain.shows import angle_similarity
from brain.lineup import (
    Concept,
    CrossPersonaFirewall,
    FirewallResult,
    ShowRegistry,
    fingerprint_text,
    make_fingerprint,
    LINEUP_ACTIVE,
    LINEUP_HIATUS,
    LINEUP_RETIRED,
    LINEUP_DISCONTINUED,
    SHOW_REGISTRY_COLUMNS,
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def _reset_registry():
    """Each test gets fresh connections to its tmp dbs (no cached handle)."""
    sqlite_store.reset_registry_for_tests()
    yield
    sqlite_store.reset_registry_for_tests()


@pytest.fixture
def events_db(tmp_path):
    return str(tmp_path / "events.db")


@pytest.fixture
def registry(events_db):
    return ShowRegistry(events_db)


class _Cfg:
    """Minimal config stub exposing the two reused SHOWS-020 knobs."""

    def __init__(self, threshold=0.6, max_regen=3):
        self.shows_novelty_threshold = threshold
        self.shows_max_regenerate = max_regen


def _register(registry, show_id, *, persona_id="p", day=0, hour=20,
              status=LINEUP_ACTIVE, pinned=False, fingerprint="", name="Show",
              created_at=None, paused_at=None):
    registry.register(
        show_id=show_id, name=name, persona_id=persona_id, slot_day_of_week=day,
        slot_hour=hour, format_type="mixtape", lineup_status=status, pinned=pinned,
        fingerprint=fingerprint or make_fingerprint(name, "", ""),
        created_at=created_at, paused_at=paused_at,
    )


def _has_table(db_path, table):
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        )
        return cur.fetchone() is not None
    finally:
        conn.close()


# ========================================================================== #
# M1 — ShowRegistry table + CRUD (REQ-SH-001, NFR-LU-1/6) — AC-SH-001, AC-NFR-LU-6
# ========================================================================== #


def test_table_created_with_full_column_set(registry, events_db):
    """AC-SH-001: show_registry exists in events.db with every required column."""
    assert _has_table(events_db, "show_registry")
    conn = sqlite3.connect(events_db)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(show_registry)")}
    finally:
        conn.close()
    expected = {
        "show_id", "name", "persona_id", "slot_day_of_week", "slot_hour",
        "format_type", "lineup_status", "pinned", "created_at", "last_aired_at",
        "paused_at", "lineup_fingerprint",
    }
    assert expected <= cols
    assert set(SHOW_REGISTRY_COLUMNS) == expected


def test_table_not_named_shows(registry, events_db):
    """AC-SH-001: the table is `show_registry`, NOT `shows` (reserved for STATS-013)."""
    assert _has_table(events_db, "show_registry")
    assert not _has_table(events_db, "shows")


def test_idempotent_create_on_populated_events_db_no_data_loss(events_db):
    """AC-SH-001 (D9 migration): an already-populated events.db is untouched.

    A pre-existing play_events row (STATS-013) survives; show_registry is added
    CREATE-IF-NOT-EXISTS beside it; re-initializing is a no-op.
    """
    from brain.analytics import PlayEventsStore

    play = PlayEventsStore(events_db)
    eid = play.open_event("Artist", "Title", "music", 1000.0, "artist|title")
    play.close_event(eid, 120.0)
    assert play.count() == 1

    # LINEUP initializes against the same, populated events.db.
    reg = ShowRegistry(events_db)
    _register(reg, "s1", name="Kvoldljod")
    assert reg.get("s1") is not None

    # The STATS-013 ledger row is untouched.
    assert play.count() == 1
    assert play.all_closed()[0]["seconds_aired"] == pytest.approx(120.0)

    # Re-initialize: idempotent, no data loss.
    reg2 = ShowRegistry(events_db)
    assert reg2.get("s1") is not None
    assert play.count() == 1


def test_row_survives_simulated_reopen(events_db):
    """AC-SH-001: a written row is durable across a process restart (reopen)."""
    reg = ShowRegistry(events_db)
    _register(reg, "s1", persona_id="vesturljod", day=1, hour=21,
              status=LINEUP_ACTIVE, name="Kvoldljod")
    # Simulate restart: drop cached connections, reopen.
    sqlite_store.reset_registry_for_tests()
    reg2 = ShowRegistry(events_db)
    row = reg2.get("s1")
    assert row is not None
    assert row["persona_id"] == "vesturljod"
    assert row["slot_day_of_week"] == 1
    assert row["slot_hour"] == 21
    assert row["lineup_status"] == LINEUP_ACTIVE


def test_brain_db_and_knowledge_db_untouched(tmp_path):
    """AC-SH-001: initializing LINEUP touches ONLY events.db.

    A pre-existing brain.db (with its own table + marker row) is not modified, and
    show_registry is never created in brain.db or knowledge.db.
    """
    brain_db = str(tmp_path / "brain.db")
    knowledge_db = str(tmp_path / "knowledge.db")
    events_db = str(tmp_path / "events.db")

    # Seed brain.db with a frozen-looking marker table.
    conn = sqlite3.connect(brain_db)
    conn.execute("CREATE TABLE tracks (k TEXT)")
    conn.execute("INSERT INTO tracks VALUES ('frozen')")
    conn.commit()
    conn.close()
    # knowledge.db exists but empty.
    sqlite3.connect(knowledge_db).close()

    sqlite_store.reset_registry_for_tests()
    ShowRegistry(events_db)  # only events.db

    assert _has_table(events_db, "show_registry")
    assert not _has_table(brain_db, "show_registry")
    assert not _has_table(knowledge_db, "show_registry")
    # brain.db marker intact.
    conn = sqlite3.connect(brain_db)
    assert conn.execute("SELECT k FROM tracks").fetchone()[0] == "frozen"
    conn.close()


def test_single_file_no_cross_file_atomic_write(registry, events_db):
    """AC-SH-001 / NFR-LU-6: the store holds ONE handle, to events.db only.

    There is no second db handle on the store, so a registry write cannot span two
    files atomically — the row is canonical; any ledger journal is a separate write.
    """
    import os

    assert os.path.abspath(registry.handle.path) == os.path.abspath(events_db)
    # The store exposes exactly one connection handle.
    handles = [v for v in vars(registry).values()
               if isinstance(v, sqlite_store.DbHandle)]
    assert len(handles) == 1


def test_rows_are_never_deleted_by_any_path(registry):
    """AC-NFR-LU-6: a non-active/retired row is provably never deleted.

    Exercise every mutating method; the row remains. The store exposes NO delete API.
    """
    _register(registry, "ret1", status=LINEUP_RETIRED, name="Midnight Static")
    assert registry.get("ret1") is not None

    # All mutating paths preserve the row.
    registry.set_status("ret1", LINEUP_DISCONTINUED)
    registry.set_last_aired("ret1", 12345.0)
    registry.register(  # re-register same id (upsert, not delete+lose)
        show_id="ret1", name="Midnight Static", persona_id="p",
        slot_day_of_week=0, slot_hour=20, format_type="mixtape",
        lineup_status=LINEUP_RETIRED, pinned=False,
        fingerprint=make_fingerprint("Midnight Static", "", ""),
    )
    assert registry.get("ret1") is not None
    assert registry.count() == 1

    # No delete/drop/remove method is exposed.
    for attr in ("delete", "remove", "drop", "purge", "vacuum"):
        assert not hasattr(registry, attr)


def test_register_then_status_transition_preserves_row(registry):
    """NFR-LU-6: paused_at is recorded and the row persists through hiatus."""
    _register(registry, "s1", status=LINEUP_ACTIVE)
    registry.set_status("s1", LINEUP_HIATUS, paused_at=999.0)
    row = registry.get("s1")
    assert row["lineup_status"] == LINEUP_HIATUS
    assert row["paused_at"] == pytest.approx(999.0)


# ========================================================================== #
# M2 — Cross-persona firewall (REQ-SQ-001/002/003, NFR-LU-2/4)
# ========================================================================== #


def test_fingerprint_roundtrip():
    """make_fingerprint stores JSON; fingerprint_text extracts the comparable text."""
    fp = make_fingerprint("Midnight Static", "after-hours drift", "tape hiss deep cuts")
    text = fingerprint_text(fp)
    assert "midnight" in text.lower()
    assert "drift" in text.lower()
    assert "deep" in text.lower()


def test_fingerprint_text_tolerates_non_json():
    """A legacy/raw fingerprint string is used as-is (never crashes)."""
    assert fingerprint_text("plain text angle") == "plain text angle"
    assert fingerprint_text("") == ""
    assert fingerprint_text(None) == ""


def test_scan_is_cross_persona_excludes_active_and_pinned(registry):
    """AC-SQ-001: the scan covers EVERY non-active, non-pinned row across personas."""
    # Persona A: a retired show (in scope).
    _register(registry, "A_ret", persona_id="A", status=LINEUP_RETIRED,
              fingerprint=make_fingerprint("Midnight Static",
                                           "lo-fi after-hours drift",
                                           "tape hiss deep cuts"))
    # Persona B: an ACTIVE show (out of scope — active excluded).
    _register(registry, "B_act", persona_id="B", status=LINEUP_ACTIVE,
              fingerprint=make_fingerprint("Morning Brass", "bright jazz", "upbeat"))
    # Persona C: a pinned hiatus flagship (out of scope — pinned exempt).
    _register(registry, "C_pin", persona_id="C", status=LINEUP_HIATUS, pinned=True,
              fingerprint=make_fingerprint("Solstice Hour", "ceremony", "anthemic"))

    fw = CrossPersonaFirewall(registry, _Cfg())
    rows = registry.non_active_rows(exclude_pinned=True)
    ids = {r["show_id"] for r in rows}
    assert ids == {"A_ret"}  # cross-persona but only non-active, non-pinned

    # A near-duplicate of A's retired show is caught even though it is persona B's.
    concept_text = "midnight drift after-hours lo-fi drift tape hiss deep cuts"
    score, matched = fw.score_concept(concept_text)
    assert matched == "A_ret"
    assert score >= 0.6


def test_score_equals_angle_similarity_no_second_metric(registry):
    """AC-SQ-001: the score IS angle_similarity over name+theme+music_angle vs fp text."""
    fp = make_fingerprint("Midnight Static", "lo-fi after-hours drift",
                          "tape hiss deep cuts")
    _register(registry, "A_ret", persona_id="A", status=LINEUP_RETIRED, fingerprint=fp)
    fw = CrossPersonaFirewall(registry, _Cfg())
    concept_text = "midnight drift after-hours lo-fi drift tape hiss deep cuts"
    score, _ = fw.score_concept(concept_text)
    assert score == pytest.approx(angle_similarity(concept_text, fingerprint_text(fp)))


def test_near_duplicate_from_another_host_rejected_then_regenerated(registry):
    """AC-SQ-002 / B3: a >=0.6 near-dup is rejected and regenerated to a clean concept."""
    _register(registry, "A_ret", persona_id="A", status=LINEUP_RETIRED,
              fingerprint=make_fingerprint(
                  "Midnight Static", "lo-fi after-hours drift", "tape hiss deep cuts"))
    fw = CrossPersonaFirewall(registry, _Cfg())

    calls = {"n": 0}
    near_dup = Concept("Midnight Drift", "after-hours lo-fi drift", "tape hiss deep cuts")
    clean = Concept("Harbour Brass", "bright morning jazz", "upbeat horns sunrise")

    def generate():
        calls["n"] += 1
        return near_dup if calls["n"] == 1 else clean

    result = fw.admit(generate)
    assert result.status == "admitted"
    assert result.concept is clean
    assert result.score < 0.6
    assert calls["n"] == 2  # first rejected, regenerated once


def test_b3_score_is_over_threshold(registry):
    """B3 concrete: the named near-duplicate scores >= the 0.6 threshold (rejected)."""
    fp = make_fingerprint("Midnight Static", "lo-fi after-hours drift",
                          "tape hiss deep cuts")
    score = angle_similarity(
        "midnight drift after-hours lo-fi drift tape hiss deep cuts",
        fingerprint_text(fp),
    )
    assert score >= 0.6  # spec illustrative 0.72; the real metric is >= threshold


def test_distinct_concept_below_threshold_passes_first_try(registry):
    """AC-SQ-002: a concept scoring strictly < 0.6 against every row passes."""
    _register(registry, "A_ret", persona_id="A", status=LINEUP_RETIRED,
              fingerprint=make_fingerprint(
                  "Midnight Static", "lo-fi after-hours drift", "tape hiss deep cuts"))
    fw = CrossPersonaFirewall(registry, _Cfg())
    clean = Concept("Harbour Brass", "bright morning jazz", "upbeat horns sunrise")

    result = fw.admit(lambda: clean)
    assert result.status == "admitted"
    assert result.concept is clean
    assert result.attempts == 1


def test_exhausted_bound_escalates_never_binds(registry):
    """AC-SQ-002 / B3: after max_regen+1 over-threshold tries, escalate (no bind)."""
    _register(registry, "A_ret", persona_id="A", status=LINEUP_RETIRED,
              fingerprint=make_fingerprint(
                  "Midnight Static", "lo-fi after-hours drift", "tape hiss deep cuts"))
    fw = CrossPersonaFirewall(registry, _Cfg(max_regen=3))

    calls = {"n": 0}
    near_dup = Concept("Midnight Drift", "after-hours lo-fi drift", "tape hiss deep cuts")

    def generate():
        calls["n"] += 1
        return near_dup

    result = fw.admit(generate)
    assert result.status == "escalated"
    assert result.concept is None  # never binds a near-duplicate
    assert calls["n"] == 4  # 1 initial + 3 regenerations (bounded, no infinite loop)
    assert result.matched_show_id == "A_ret"


def test_empty_registry_admits_any_concept(registry):
    """AC-SQ-002: with no non-active rows, the first concept passes (corpus empty)."""
    fw = CrossPersonaFirewall(registry, _Cfg())
    c = Concept("Anything", "any theme", "any angle")
    result = fw.admit(lambda: c)
    assert result.status == "admitted"
    assert result.score == 0.0


def test_propose_failure_does_not_crash_slot_unscheduled(registry):
    """AC-NFR-LU-4 / B8: a propose_show fault -> no crash, slot stays unscheduled."""
    _register(registry, "A_ret", persona_id="A", status=LINEUP_RETIRED,
              fingerprint=make_fingerprint("X", "y", "z"))
    fw = CrossPersonaFirewall(registry, _Cfg())

    def boom():
        raise RuntimeError("LLM timeout")

    result = fw.admit(boom)
    assert result.status == "failed"  # slot unscheduled, no exception propagated
    assert result.concept is None


def test_propose_returning_none_does_not_crash(registry):
    """AC-NFR-LU-4: propose_show returning None (no persona id) degrades, no crash."""
    fw = CrossPersonaFirewall(registry, _Cfg())
    result = fw.admit(lambda: None)
    assert result.status == "failed"
    assert result.concept is None


# --- SQ-003 long-hiatus reactivation re-vet entry point (B9) ---------------- #


def test_long_hiatus_revet_rejects_meanwhile_registered_collision(registry):
    """AC-SQ-003 / B9: a long hiatus re-vets against shows registered meanwhile.

    "Pier Sessions" paused at T0; "Wharf Hours" was registered AFTER T0 with an
    overlapping theme. On reactivation (hiatus_age > long-hiatus bound) the firewall
    finds the collision and escalates (no generate provided) — never silent reactivate.
    """
    pier_fp = make_fingerprint("Pier Sessions", "harbour evening tape drift",
                               "slow deep cuts coastal")
    _register(registry, "pier", persona_id="A", status=LINEUP_HIATUS,
              fingerprint=pier_fp, created_at=100.0, paused_at=200.0)
    # Registered meanwhile (created_at after pier's paused_at) with overlapping theme.
    _register(registry, "wharf", persona_id="B", status=LINEUP_ACTIVE,
              fingerprint=make_fingerprint("Wharf Hours", "harbour evening tape drift",
                                           "slow deep cuts coastal"),
              created_at=300.0)

    fw = CrossPersonaFirewall(registry, _Cfg())
    result = fw.revet_reactivation("pier", hiatus_age=90.0, long_hiatus_bound=30.0)
    assert result.status == "escalated"
    assert result.matched_show_id == "wharf"
    assert result.score >= 0.6


def test_long_hiatus_revet_with_generate_regenerates(registry):
    """AC-SQ-003: an over-threshold reactivation with a generator regenerates a clean concept."""
    _register(registry, "pier", persona_id="A", status=LINEUP_HIATUS,
              fingerprint=make_fingerprint("Pier Sessions", "harbour evening tape drift",
                                           "slow deep cuts coastal"),
              created_at=100.0, paused_at=200.0)
    _register(registry, "wharf", persona_id="B", status=LINEUP_ACTIVE,
              fingerprint=make_fingerprint("Wharf Hours", "harbour evening tape drift",
                                           "slow deep cuts coastal"),
              created_at=300.0)
    fw = CrossPersonaFirewall(registry, _Cfg())
    clean = Concept("Pier Sessions", "bright noon brass parade", "loud horns festival")
    result = fw.revet_reactivation("pier", hiatus_age=90.0, long_hiatus_bound=30.0,
                                   generate=lambda: clean)
    assert result.status == "admitted"
    assert result.concept is clean


def test_short_hiatus_reactivates_without_revet(registry):
    """AC-SQ-003 / B9: a hiatus WITHIN the bound reactivates without a re-vet scan."""
    _register(registry, "pier", persona_id="A", status=LINEUP_HIATUS,
              fingerprint=make_fingerprint("Pier Sessions", "harbour evening tape drift",
                                           "slow deep cuts coastal"),
              created_at=100.0, paused_at=200.0)
    _register(registry, "wharf", persona_id="B", status=LINEUP_ACTIVE,
              fingerprint=make_fingerprint("Wharf Hours", "harbour evening tape drift",
                                           "slow deep cuts coastal"),
              created_at=300.0)
    fw = CrossPersonaFirewall(registry, _Cfg())
    result = fw.revet_reactivation("pier", hiatus_age=10.0, long_hiatus_bound=30.0)
    assert result.status == "reactivate"  # short hiatus: no scan, no collision check


def test_pinned_show_is_exempt_from_revet(registry):
    """AC-SQ-003: a pinned (flagship) show reactivates exempt from the firewall."""
    _register(registry, "solstice", persona_id="A", status=LINEUP_HIATUS, pinned=True,
              fingerprint=make_fingerprint("Solstice Hour", "ceremony", "anthemic"),
              created_at=100.0, paused_at=200.0)
    _register(registry, "twin", persona_id="B", status=LINEUP_ACTIVE,
              fingerprint=make_fingerprint("Solstice Hour", "ceremony", "anthemic"),
              created_at=300.0)
    fw = CrossPersonaFirewall(registry, _Cfg())
    result = fw.revet_reactivation("solstice", hiatus_age=90.0, long_hiatus_bound=30.0)
    assert result.status == "reactivate"  # pinned exempt even on a long hiatus


def test_revet_clear_when_no_meanwhile_collision(registry):
    """AC-SQ-003: a long hiatus with no meanwhile-registered collision reactivates clean."""
    _register(registry, "pier", persona_id="A", status=LINEUP_HIATUS,
              fingerprint=make_fingerprint("Pier Sessions", "harbour evening tape drift",
                                           "slow deep cuts coastal"),
              created_at=100.0, paused_at=200.0)
    _register(registry, "brass", persona_id="B", status=LINEUP_ACTIVE,
              fingerprint=make_fingerprint("Morning Brass", "bright noon parade",
                                           "loud horns festival"),
              created_at=300.0)
    fw = CrossPersonaFirewall(registry, _Cfg())
    result = fw.revet_reactivation("pier", hiatus_age=90.0, long_hiatus_bound=30.0)
    assert result.status == "reactivate"
    assert result.score < 0.6


def test_fingerprint_text_tolerates_json_array():
    """A JSON value that is not an object (e.g. an array) degrades to its raw string."""
    assert fingerprint_text("[1, 2, 3]") == "[1, 2, 3]"


def test_fingerprint_text_rebuilds_from_fields_when_text_missing():
    """A fingerprint object lacking a flat ``text`` key rebuilds from name/theme/angle."""
    import json as _json

    fp = _json.dumps({"name": "Pier", "theme": "harbour", "music_angle": "drift"})
    assert fingerprint_text(fp) == "Pier harbour drift"


def test_is_novel_public_predicate(registry):
    """AC-SQ-002: is_novel is True below threshold, False at/above it."""
    _register(registry, "A_ret", persona_id="A", status=LINEUP_RETIRED,
              fingerprint=make_fingerprint(
                  "Midnight Static", "lo-fi after-hours drift", "tape hiss deep cuts"))
    fw = CrossPersonaFirewall(registry, _Cfg())
    assert fw.is_novel("bright morning brass upbeat horns sunrise parade") is True
    assert fw.is_novel(
        "midnight drift after-hours lo-fi drift tape hiss deep cuts") is False


def test_all_rows_returns_every_status(registry):
    """all_rows surfaces the full permanent history regardless of status (NFR-LU-6)."""
    _register(registry, "a", status=LINEUP_ACTIVE)
    _register(registry, "h", status=LINEUP_HIATUS)
    _register(registry, "r", status=LINEUP_RETIRED)
    ids = {r["show_id"] for r in registry.all_rows()}
    assert ids == {"a", "h", "r"}


def test_explicit_threshold_and_max_regen_override_cfg(registry):
    """The firewall accepts explicit threshold/max_regen overriding the cfg knobs."""
    fw = CrossPersonaFirewall(registry, _Cfg(threshold=0.6, max_regen=3),
                              threshold=0.9, max_regen=1)
    assert fw.threshold == pytest.approx(0.9)
    assert fw.max_regen == 1


def test_revet_unknown_show_id_fails_safely(registry):
    """A re-vet against an unknown show id degrades to a failed verdict, no crash."""
    fw = CrossPersonaFirewall(registry, _Cfg())
    result = fw.revet_reactivation("nope", hiatus_age=90.0, long_hiatus_bound=30.0)
    assert result.status == "failed"


def test_firewall_result_is_dataclass_shape():
    """A FirewallResult carries status/concept/score/matched/attempts for the caller."""
    r = FirewallResult(status="admitted", concept=Concept("n", "t", "a"),
                       score=0.1, matched_show_id=None, attempts=1)
    assert r.status == "admitted"
    assert r.concept.text == "n t a"
