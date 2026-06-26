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
    BindResult,
    Concept,
    CrossPersonaFirewall,
    FirewallResult,
    LineupController,
    ShowRegistry,
    clamp_hiatus_bounds,
    fingerprint_text,
    make_caps_ok,
    make_fingerprint,
    DEFAULT_LONG_HIATUS_SECONDS,
    DEFAULT_MAX_HIATUS_SECONDS,
    LINEUP_ACTIVE,
    LINEUP_CONCEPT,
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


# ========================================================================== #
# M3 + M4 fakes — a caps_ok-honoring spy schedule, a spy lifecycle, a fake roster.
# ========================================================================== #

from types import SimpleNamespace  # noqa: E402

from brain.ledger import EventLedger  # noqa: E402
from brain.schedule import (  # noqa: E402
    HOUSE_LANE,
    NoOrphanBootstrap,
    Schedule,
    ScheduleBlock,
)


class _SpySchedule:
    """A minimal Schedule double that HONORS the caps_ok gate exactly like the real
    assign_persona (schedule.py:907) so the one-per-day/PR-004 wiring is exercised."""

    def __init__(self, *, accept=True):
        self.accept = accept
        self.calls = []
        self.removed = []

    def assign_persona(self, slot_id, persona_id, show_or_episode_id, *,
                       caps_ok=None, editorial_reason=""):
        self.calls.append({
            "slot_id": slot_id, "persona_id": persona_id,
            "show_or_episode_id": show_or_episode_id, "caps_ok": caps_ok,
            "editorial_reason": editorial_reason,
        })
        if caps_ok is not None and not caps_ok(persona_id, slot_id):
            return False
        return self.accept

    def remove_slot(self, slot_id, *, discontinue=False, editorial_reason=""):
        self.removed.append({"slot_id": slot_id, "discontinue": discontinue})
        return True


class _SpyLifecycle:
    """A LifecycleEngine double recording discontinue_show delegation (it NEVER emits
    show_relaunched here — only the REAL engine does, and LINEUP must not duplicate it)."""

    def __init__(self, *, ok=True):
        self.ok = ok
        self.calls = []

    def discontinue_show(self, persona, *, editorial_reason="", library=None):
        self.calls.append({"persona": persona, "editorial_reason": editorial_reason})
        return SimpleNamespace(ok=self.ok)


class _FakeRoster:
    """A Roster double exposing the PR-004 seam (get + validate_candidate)."""

    def __init__(self, *, ok=True, enabled=True, present=True):
        self._ok = ok
        self._enabled = enabled
        self._present = present

    def get(self, persona_id):
        if not self._present:
            return None
        return SimpleNamespace(id=persona_id, enabled=self._enabled)

    def validate_candidate(self, persona, exclude_id=None):
        return SimpleNamespace(ok=self._ok)


class _BoomLedger:
    """A ledger whose append always raises — proves the journal is best-effort."""

    def append(self, *a, **k):
        raise RuntimeError("ledger down")


# ========================================================================== #
# M3 — one-per-day rule + WIRED caps_ok (REQ-SH-002/003) — AC-SH-002, AC-SH-003
# ========================================================================== #


def test_active_show_ids_on_day_one_per_day_query(registry):
    """AC-SH-002: the registry surfaces a persona's active shows on a given day_of_week."""
    _register(registry, "s1", persona_id="P", day=2, status=LINEUP_ACTIVE)
    _register(registry, "s2", persona_id="P", day=3, status=LINEUP_ACTIVE)
    _register(registry, "s3", persona_id="P", day=2, status=LINEUP_CONCEPT)  # not active
    assert registry.active_show_ids_on_day("P", 2) == ["s1"]
    assert registry.active_show_ids_on_day("P", 3) == ["s2"]
    # exclude_show_id lets the bound show ignore its own active row.
    assert registry.active_show_ids_on_day("P", 2, exclude_show_id="s1") == []


def test_caps_ok_blocks_second_same_day_active(registry):
    """AC-SH-002 / B2: a persona already active on day D fails caps_ok for a second day-D show."""
    _register(registry, "s1", persona_id="P", day=2, status=LINEUP_ACTIVE)
    caps_ok = make_caps_ok(registry, slot_day_of_week=2, exclude_show_id="s2")
    assert caps_ok("P", "wed-17") is False  # P already works Wednesday


def test_caps_ok_allows_different_day(registry):
    """AC-SH-002 / B2: the same persona on a DIFFERENT day is allowed."""
    _register(registry, "s1", persona_id="P", day=2, status=LINEUP_ACTIVE)
    caps_ok = make_caps_ok(registry, slot_day_of_week=3, exclude_show_id="s2")
    assert caps_ok("P", "thu-17") is True  # Thursday is free


def test_caps_ok_composes_pr004_roster_firewall(registry):
    """AC-SH-003: caps_ok ALSO enforces PROGRAMMING-007 PR-004 via Roster.validate_candidate."""
    # No same-day active show, so only PR-004 can block.
    ok_roster = _FakeRoster(ok=True)
    blocked_roster = _FakeRoster(ok=False)
    caps_pass = make_caps_ok(registry, slot_day_of_week=0, roster=ok_roster)
    caps_block = make_caps_ok(registry, slot_day_of_week=0, roster=blocked_roster)
    assert caps_pass("P", "mon-20") is True
    assert caps_block("P", "mon-20") is False  # PR-004 firewall rejected


def test_caps_ok_blocks_absent_or_disabled_persona(registry):
    """AC-SH-003: an absent/disabled roster persona fails the PR-004 half (never bound)."""
    absent = make_caps_ok(registry, slot_day_of_week=0, roster=_FakeRoster(present=False))
    disabled = make_caps_ok(registry, slot_day_of_week=0, roster=_FakeRoster(enabled=False))
    assert absent("ghost", "mon-20") is False
    assert disabled("P", "mon-20") is False


def test_caps_ok_degrades_closed_on_fault(registry):
    """NFR-LU-4: a caps_ok fault degrades CLOSED (returns False), never raises."""
    class _BoomRoster:
        def get(self, pid):
            raise RuntimeError("roster down")

    caps_ok = make_caps_ok(registry, slot_day_of_week=0, roster=_BoomRoster())
    assert caps_ok("P", "mon-20") is False


def test_bind_always_supplies_non_none_caps_ok(registry):
    """AC-SH-003 [HARD] / R-LU-3 / D7: NO LINEUP bind path may pass caps_ok=None.

    This is the guard test that FAILS if a bind ever leaves caps_ok unset.
    """
    _register(registry, "s1", persona_id="P", day=1, status=LINEUP_CONCEPT)
    sched = _SpySchedule()
    ctl = LineupController(registry, schedule=sched)
    ctl.bind_show("s1", "tue-21")
    assert sched.calls, "assign_persona was never called"
    for call in sched.calls:
        assert call["caps_ok"] is not None
        assert callable(call["caps_ok"])


def test_bind_show_activates_through_assign_persona(registry):
    """AC-SH-003 / B1: a clean bind goes THROUGH assign_persona and activates the row."""
    _register(registry, "s1", persona_id="vesturljod", day=1, hour=21,
              status=LINEUP_CONCEPT)
    sched = _SpySchedule(accept=True)
    ctl = LineupController(registry, schedule=sched, roster=_FakeRoster(ok=True))
    result = ctl.bind_show("s1", "tue-21", editorial_reason="new slot")
    assert isinstance(result, BindResult)
    assert result.bound is True
    assert registry.get("s1")["lineup_status"] == LINEUP_ACTIVE
    # show_id is the slot's show_or_episode_id.
    assert sched.calls[-1]["show_or_episode_id"] == "s1"
    assert sched.calls[-1]["persona_id"] == "vesturljod"


def test_bind_show_rejected_leaves_row_inactive(registry):
    """AC-SH-002 / B2: caps_ok=False blocks the bind; the row is NOT set active."""
    _register(registry, "s1", persona_id="P", day=2, status=LINEUP_ACTIVE)   # already Wed
    _register(registry, "s2", persona_id="P", day=2, status=LINEUP_CONCEPT)  # second Wed show
    sched = _SpySchedule(accept=True)
    ctl = LineupController(registry, schedule=sched)
    result = ctl.bind_show("s2", "wed-17")
    assert result.bound is False  # one-per-day rejected via the wired caps_ok
    assert registry.get("s2")["lineup_status"] == LINEUP_CONCEPT  # stays inactive


def test_bind_second_show_allowed_on_different_day(registry):
    """AC-SH-002 / B2: the same persona's second show on a DIFFERENT day binds."""
    _register(registry, "s1", persona_id="P", day=2, status=LINEUP_ACTIVE)   # Wed
    _register(registry, "s2", persona_id="P", day=3, status=LINEUP_CONCEPT)  # Thu
    sched = _SpySchedule(accept=True)
    ctl = LineupController(registry, schedule=sched)
    result = ctl.bind_show("s2", "thu-17")
    assert result.bound is True
    assert registry.get("s2")["lineup_status"] == LINEUP_ACTIVE


def test_bind_unknown_show_and_no_schedule(registry):
    """Bind safety: an unknown show id or an unwired schedule never crashes."""
    ctl_no_sched = LineupController(registry)
    _register(registry, "s1", status=LINEUP_CONCEPT)
    assert ctl_no_sched.bind_show("s1", "x").reason == "no schedule wired"
    ctl = LineupController(registry, schedule=_SpySchedule())
    assert ctl.bind_show("nope", "x").reason == "unknown show"


def test_bind_assign_raises_degrades(registry):
    """NFR-LU-4: an assign_persona fault leaves the slot safe, no crash."""
    class _BoomSchedule:
        def assign_persona(self, *a, **k):
            raise RuntimeError("grid down")

    _register(registry, "s1", status=LINEUP_CONCEPT)
    ctl = LineupController(registry, schedule=_BoomSchedule())
    result = ctl.bind_show("s1", "x")
    assert result.bound is False
    assert registry.get("s1")["lineup_status"] == LINEUP_CONCEPT


# ========================================================================== #
# M4 — hiatus state + flagship pin (REQ-SY-001/002/003) — AC-SY-001/002/003
# ========================================================================== #


def _real_grid_with_show(slot_id, *, persona_id, show_id, hour):
    """A real ledger-backed Schedule with a base hour-0 slot + a show slot (no-gap)."""
    led = EventLedger()
    sched = Schedule(led)
    sched.add_slot(ScheduleBlock(slot_id="base", start_hour=0, daypart="night",
                                 show_or_episode_id="unscheduled"), seed=True)
    sched.add_slot(ScheduleBlock(slot_id=slot_id, start_hour=hour, daypart="late",
                                 persona_id=persona_id, show_or_episode_id=show_id), seed=True)
    return sched


def test_active_to_hiatus_preserves_row_and_staffs_slot(registry):
    """AC-SY-001 / B4: active->hiatus preserves the row, sets paused_at, and the slot is
    brought to a STAFFED state that NEVER names the paused show."""
    _register(registry, "show1", persona_id="P", day=4, hour=22, status=LINEUP_ACTIVE)
    sched = _real_grid_with_show("fri-22", persona_id="P", show_id="show1", hour=22)
    ctl = LineupController(registry, schedule=sched)
    result = ctl.to_hiatus("show1", slot_id="fri-22", now=1000.0)
    assert result.ok is True
    row = registry.get("show1")
    assert row["lineup_status"] == LINEUP_HIATUS       # row preserved, not deleted
    assert row["paused_at"] == pytest.approx(1000.0)   # paused_at set
    # The Friday slot no longer NAMES the paused show.
    fri = next(b for b in sched.blocks() if b.slot_id == "fri-22")
    assert fri.show_or_episode_id != "show1"
    assert result.staffed_via == "same_persona"        # default-curation lane (b)


def test_hiatus_binds_vetted_replacement(registry):
    """AC-SY-001 / B4 lane (a): a vetted replacement is bound via the assign_persona path."""
    _register(registry, "show1", persona_id="P", day=4, hour=22, status=LINEUP_ACTIVE)
    sched = _real_grid_with_show("fri-22", persona_id="P", show_id="show1", hour=22)
    ctl = LineupController(registry, schedule=sched)
    result = ctl.to_hiatus("show1", slot_id="fri-22",
                           replacement={"persona_id": "Q", "show_id": "show2"}, now=1000.0)
    assert result.staffed_via == "replacement"
    fri = next(b for b in sched.blocks() if b.slot_id == "fri-22")
    assert fri.show_or_episode_id == "show2"
    assert fri.persona_id == "Q"


def test_hiatus_no_grid_degrades_to_house_lane(registry):
    """NFR-LU-3: with no schedule wired the hiatus slot is the house lane (never silenced)."""
    _register(registry, "show1", persona_id="P", day=4, status=LINEUP_ACTIVE)
    ctl = LineupController(registry)  # no schedule
    result = ctl.to_hiatus("show1", slot_id="fri-22")
    assert result.staffed_via == "house"
    # The no-orphan rail still serves a non-silent block.
    assert NoOrphanBootstrap(None).resolve() is HOUSE_LANE


def test_hiatus_reverts_to_house_lane_when_no_replacement(registry):
    """NFR-LU-3 / B4 lane (c): when (a)+(b) cannot staff, revert to the house lane; the
    real grid still resolves a non-silent block at the slot's hour."""
    _register(registry, "show1", persona_id="P", day=4, hour=22, status=LINEUP_ACTIVE)
    sched = _real_grid_with_show("fri-22", persona_id="P", show_id="show1", hour=22)
    # A rejecting roster makes the same-persona rebind (b) fail PR-004 -> falls to (c) remove.
    ctl = LineupController(registry, schedule=sched, roster=_FakeRoster(ok=False))
    result = ctl.to_hiatus("show1", slot_id="fri-22", now=1000.0)
    assert result.staffed_via == "house"
    assert all(b.slot_id != "fri-22" for b in sched.blocks())  # slot removed (house lane)
    # The stream is never silenced: the base hour-0 block still governs hour 22.
    boot = NoOrphanBootstrap(sched)
    assert boot.resolve(epoch=None) is not None


def test_hiatus_unknown_show_is_safe(registry):
    """to_hiatus on an unknown show degrades without crashing."""
    ctl = LineupController(registry)
    result = ctl.to_hiatus("nope", slot_id="x")
    assert result.ok is False
    assert result.reason == "unknown show"


def test_lineup_emits_no_show_relaunched_and_delegates_discontinue(registry):
    """AC-SY-002 / B5 [HARD]: a hiatus->discontinued exit routes THROUGH
    lifecycle.discontinue_show; LINEUP emits NO show_relaunched of its own."""
    _register(registry, "harbour", persona_id="P", day=4, status=LINEUP_HIATUS,
              paused_at=0.0)
    life = _SpyLifecycle(ok=True)
    ctl = LineupController(registry, lifecycle=life)
    persona = SimpleNamespace(id="P")
    # paused at 0, now well beyond max-hiatus -> auto-discontinue.
    result = ctl.auto_discontinue_if_expired(
        "harbour", persona, now=DEFAULT_MAX_HIATUS_SECONDS + 1000.0)
    assert getattr(result, "ok", False) is True
    assert len(life.calls) == 1                                  # delegated exactly once
    assert life.calls[0]["persona"] is persona
    assert registry.get("harbour")["lineup_status"] == LINEUP_DISCONTINUED


def test_lineup_source_never_emits_show_relaunched():
    """AC-SY-001 [HARD]: LINEUP re-owns no FSM — its source emits no show_relaunched event."""
    import brain.lineup as _lineup

    with open(_lineup.__file__, "r", encoding="utf-8") as fh:
        src = fh.read()
    assert "show_relaunched" not in src
    assert "EV_SHOW_RELAUNCHED" not in src


def test_auto_discontinue_not_expired_is_noop(registry):
    """AC-SY-002: a hiatus WITHIN the max bound is not auto-discontinued."""
    _register(registry, "harbour", persona_id="P", status=LINEUP_HIATUS, paused_at=1000.0)
    life = _SpyLifecycle()
    ctl = LineupController(registry, lifecycle=life)
    result = ctl.auto_discontinue_if_expired("harbour", SimpleNamespace(id="P"), now=2000.0)
    assert result is None
    assert life.calls == []
    assert registry.get("harbour")["lineup_status"] == LINEUP_HIATUS


def test_auto_discontinue_ignores_non_hiatus(registry):
    """AC-SY-002: only a hiatus row is eligible for auto-discontinue."""
    _register(registry, "live", persona_id="P", status=LINEUP_ACTIVE, paused_at=0.0)
    life = _SpyLifecycle()
    ctl = LineupController(registry, lifecycle=life)
    assert ctl.auto_discontinue_if_expired(
        "live", SimpleNamespace(id="P"), now=DEFAULT_MAX_HIATUS_SECONDS + 1.0) is None
    assert life.calls == []


def test_ordered_bounds_clamp_long_le_max():
    """AC-SY-002: a config with long-hiatus > max-hiatus is CLAMPED (long lowered to max)."""
    long_v, max_v = clamp_hiatus_bounds(100.0, 50.0)
    assert max_v == 50.0
    assert long_v == 50.0
    assert long_v <= max_v
    # An already-ordered pair is preserved.
    assert clamp_hiatus_bounds(20.0, 50.0) == (20.0, 50.0)


def test_controller_clamps_bad_config_bounds(registry):
    """AC-SY-002: the controller enforces the ordered-bounds invariant from cfg."""
    cfg = SimpleNamespace(lineup_long_hiatus_seconds=999.0, lineup_max_hiatus_seconds=100.0)
    ctl = LineupController(registry, cfg=cfg)
    assert ctl.long_hiatus_seconds <= ctl.max_hiatus_seconds
    assert ctl.max_hiatus_seconds == 100.0


def test_controller_defaults_when_cfg_absent(registry):
    """The controller falls back to the M4 default bounds when cfg lacks the knobs."""
    ctl = LineupController(registry, cfg=None)
    assert ctl.long_hiatus_seconds == DEFAULT_LONG_HIATUS_SECONDS
    assert ctl.max_hiatus_seconds == DEFAULT_MAX_HIATUS_SECONDS


def test_pinned_flagship_auto_hiatus_rejected(registry):
    """AC-SY-003 / B6: a pinned flagship cannot be AUTO-hiatus'd without an override."""
    _register(registry, "solstice", persona_id="P", status=LINEUP_ACTIVE, pinned=True)
    ctl = LineupController(registry, schedule=_SpySchedule())
    result = ctl.to_hiatus("solstice", slot_id="x")
    assert result.ok is False
    assert "pinned" in result.reason
    assert registry.get("solstice")["lineup_status"] == LINEUP_ACTIVE  # stays active


def test_pinned_flagship_auto_discontinue_rejected(registry):
    """AC-SY-003 / B6: a pinned flagship cannot be AUTO-discontinued without an override."""
    _register(registry, "solstice", persona_id="P", status=LINEUP_HIATUS, pinned=True,
              paused_at=0.0)
    life = _SpyLifecycle()
    ctl = LineupController(registry, lifecycle=life)
    result = ctl.auto_discontinue_if_expired(
        "solstice", SimpleNamespace(id="P"), now=DEFAULT_MAX_HIATUS_SECONDS + 1000.0)
    assert result is None
    assert life.calls == []
    assert registry.get("solstice")["lineup_status"] == LINEUP_HIATUS  # protected


def test_pinned_override_allows_hiatus(registry):
    """AC-SY-003: an EXPLICIT override permits pausing a pinned flagship."""
    _register(registry, "solstice", persona_id="P", day=0, status=LINEUP_ACTIVE, pinned=True)
    ctl = LineupController(registry)
    result = ctl.to_hiatus("solstice", override=True, now=1000.0)
    assert result.ok is True
    assert registry.get("solstice")["lineup_status"] == LINEUP_HIATUS


def test_pinned_exempt_from_remint_firewall(registry):
    """AC-SY-003 / B6: a pinned flagship's fingerprint does NOT block a fresh re-mint."""
    _register(registry, "solstice", persona_id="A", status=LINEUP_HIATUS, pinned=True,
              fingerprint=make_fingerprint("Solstice Hour", "ceremony", "anthemic"))
    fw = CrossPersonaFirewall(registry, _Cfg())
    # An identical fresh concept is admitted because the pinned row is excluded from the scan.
    clone = Concept("Solstice Hour", "ceremony", "anthemic")
    result = fw.admit(lambda: clone)
    assert result.status == "admitted"
    assert result.concept is clone


# ---- M4 reactivation (hiatus->active) via the M2 revet entry point ---------- #


def test_reactivate_short_hiatus_no_revet(registry):
    """AC-SY-001 / SQ-003: a short hiatus reactivates and flips the row back to active."""
    _register(registry, "pier", persona_id="P", day=4, status=LINEUP_HIATUS,
              created_at=100.0, paused_at=200.0)
    ctl = LineupController(registry)
    result = ctl.reactivate("pier", now=205.0)  # 5s hiatus << long bound
    assert result.status == "reactivate"
    assert registry.get("pier")["lineup_status"] == LINEUP_ACTIVE


def test_reactivate_long_hiatus_collision_stays_hiatus(registry):
    """AC-SY-001 / SQ-003 / B9: a long-hiatus collision escalates; the row STAYS hiatus
    (never a silent reactivation into a near-duplicate)."""
    _register(registry, "pier", persona_id="A", status=LINEUP_HIATUS,
              fingerprint=make_fingerprint("Pier Sessions", "harbour evening tape drift",
                                           "slow deep cuts coastal"),
              created_at=100.0, paused_at=200.0)
    _register(registry, "wharf", persona_id="B", status=LINEUP_ACTIVE,
              fingerprint=make_fingerprint("Wharf Hours", "harbour evening tape drift",
                                           "slow deep cuts coastal"),
              created_at=300.0)
    cfg = SimpleNamespace(lineup_long_hiatus_seconds=30.0,
                          lineup_max_hiatus_seconds=90.0,
                          shows_novelty_threshold=0.6, shows_max_regenerate=3)
    ctl = LineupController(registry, cfg=cfg)
    result = ctl.reactivate("pier", now=300.0)  # age 100 > long bound 30
    assert result.status == "escalated"
    assert registry.get("pier")["lineup_status"] == LINEUP_HIATUS  # not silently reactivated


def test_reactivate_unknown_show_fails(registry):
    """reactivate on an unknown show degrades to a failed verdict, no crash."""
    ctl = LineupController(registry)
    assert ctl.reactivate("nope").status == "failed"


# ---- best-effort ledger journal (NFR-LU-6) --------------------------------- #


def test_hiatus_journaled_best_effort(registry):
    """NFR-LU-6: a hiatus transition is journaled on the ledger as a lineup_transition event."""
    _register(registry, "show1", persona_id="P", day=4, status=LINEUP_ACTIVE)
    led = EventLedger()
    ctl = LineupController(registry, ledger=led)
    ctl.to_hiatus("show1", now=1000.0)
    evs = led.events(event_type="lineup_transition")
    assert evs and evs[-1].data["show_id"] == "show1"
    assert evs[-1].data["transition"] == "active->hiatus"


def test_ledger_fault_does_not_block_table_write(registry):
    """NFR-LU-6: a ledger fault is swallowed; the canonical table write still lands."""
    _register(registry, "show1", persona_id="P", day=4, status=LINEUP_ACTIVE)
    ctl = LineupController(registry, ledger=_BoomLedger())
    result = ctl.to_hiatus("show1", now=1000.0)  # ledger.append raises internally
    assert result.ok is True
    assert registry.get("show1")["lineup_status"] == LINEUP_HIATUS  # table write survived
