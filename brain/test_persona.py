"""SPEC-RADIO-PROGRAMMING-007 Group PR — persona/host-entity model + roster tests.

These tests BUILD the new Group PR behaviour AND characterize the load-bearing
contracts:

  * the persona-entity model + tolerant store round-trip + durability (REQ-PR-012);
  * the SHARED both-axes anti-convergence + 1:1-voice firewall, run IDENTICALLY for the
    manual (REQ-PR-011) and AI-autonomous growth (REQ-PR-008) paths (REQ-PR-004);
  * gender + age attributes with the inclusive [22,70] age bound enforced by that SAME
    shared gate (REQ-PR-015);
  * the manual create / edit / disable / remove lifecycle + the golden rule (REQ-PR-013);
  * the full CASCADE-PURGE reset (entity + ALL per-persona data + freed voice) and the
    forward-cascade contract every future per-persona store honors (REQ-PR-016);
  * [HARD] DEFAULT-IDENTICAL: with zero/one persona, curation + talk are byte-identical to
    before this SPEC (persona=None overlay is a no-op).

Offline + deterministic: no network, no real LLM call, persona store on a temp SQLite file.
"""

from __future__ import annotations

import os
import sys

import pytest

if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "brain":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import llm  # noqa: E402
from brain import persona as P  # noqa: E402
from brain import sqlite_store  # noqa: E402


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _charter(primary="deep house", in_genres=None, in_eras=None, in_tags=None, **kw):
    return P.TasteCharter(
        primary_territory=primary,
        in_genres=in_genres if in_genres is not None else ["deep house", "electronic"],
        in_eras=in_eras if in_eras is not None else ["2010s"],
        in_tags=in_tags if in_tags is not None else ["hypnotic", "warm"],
        **kw,
    )


def _persona(pid="ember", name="Ember", voice="af_bella", age=34, gender="female",
             primary="deep house", anchors=None, **charter_kw):
    return P.Persona(
        id=pid, display_name=name, voice=voice, language="en",
        pov_seed=f"{name} runs a late-night deep-house show.",
        charter=_charter(primary=primary, **charter_kw),
        anchors=anchors if anchors is not None else [primary, "warm late-night"],
        gender=gender, age=age, origin="manual",
    )


@pytest.fixture
def store(tmp_path):
    sqlite_store.reset_registry_for_tests()
    s = sqlite_store.PersonaStore(str(tmp_path / "brain.db"))
    yield s
    sqlite_store.reset_registry_for_tests()


# --------------------------------------------------------------------------- #
# 1. Model + store round-trip + durability (REQ-PR-012)
# --------------------------------------------------------------------------- #

def test_persona_record_roundtrip_preserves_all_fields():
    p = _persona(in_tags=["hypnotic", "warm"], primary="deep house")
    rec = p.to_record()
    back = P.Persona.from_record(rec)
    assert back.id == p.id
    assert back.display_name == p.display_name
    assert back.voice == p.voice
    assert back.gender == "female"
    assert back.age == 34
    assert back.charter.primary_territory == "deep house"
    assert back.charter.in_tags == ["hypnotic", "warm"]
    assert back.anchors == p.anchors


def test_persona_from_record_is_tolerant_of_unknown_keys():
    rec = _persona().to_record()
    rec["totally_unknown_future_field"] = {"x": 1}
    back = P.Persona.from_record(rec)  # must not raise
    assert back.id == "ember"


def test_store_durable_across_restart(tmp_path):
    """REQ-PR-012: a created persona survives a brain/process restart and reloads."""
    sqlite_store.reset_registry_for_tests()
    path = str(tmp_path / "brain.db")
    s1 = sqlite_store.PersonaStore(path)
    roster1 = P.Roster(store=s1)
    created, res = roster1.create(_persona())
    assert created is not None and res.ok
    # Simulate a restart: drop the registry, reopen the SAME file, rebuild the roster.
    sqlite_store.reset_registry_for_tests()
    s2 = sqlite_store.PersonaStore(path)
    roster2 = P.Roster(store=s2)
    reloaded = roster2.get("ember")
    assert reloaded is not None
    assert reloaded.display_name == "Ember"
    assert reloaded.age == 34
    assert reloaded.charter.primary_territory == "deep house"
    sqlite_store.reset_registry_for_tests()


def test_store_tolerant_load_skips_corrupt_row(tmp_path):
    sqlite_store.reset_registry_for_tests()
    s = sqlite_store.PersonaStore(str(tmp_path / "brain.db"))
    s.upsert("ok", _persona(pid="ok").to_record())
    # Inject a corrupt blob directly.
    with s.handle.lock:
        s.handle.conn.execute(
            "INSERT INTO personas(id, voice, enabled, data) VALUES('bad','x',1,'{not json')")
        s.handle.conn.commit()
    rows = s.load_all()  # must not raise; bad row skipped
    ids = {r["id"] for r in rows}
    assert "ok" in ids and "bad" not in ids
    sqlite_store.reset_registry_for_tests()


# --------------------------------------------------------------------------- #
# 2. SHARED firewall: 1:1 voice + anti-convergence (REQ-PR-004 / PR-011)
# --------------------------------------------------------------------------- #

def test_create_valid_persona_passes_the_gate(store):
    roster = P.Roster(store=store)
    created, res = roster.create(_persona())
    assert created is not None
    assert res.ok and res.code == "ok"
    assert roster.get("ember") is not None


def test_reject_voice_already_bound(store):
    """REQ-PR-003: strict 1:1 — a voice bound to another persona is rejected."""
    roster = P.Roster(store=store)
    roster.create(_persona(pid="ember", name="Ember", voice="af_bella"))
    p2 = _persona(pid="pulse", name="Pulse", voice="af_bella",  # same voice
                  primary="1970s soul", in_genres=["soul", "funk"],
                  in_eras=["1970s"], in_tags=["vintage"])
    created, res = roster.create(p2)
    assert created is None
    assert res.code == "voice_already_bound"
    assert roster.get("pulse") is None  # never enters the roster


def test_reject_shared_primary_territory(store):
    """REQ-PR-004 Layer 1: no two personas share a PRIMARY genre territory."""
    roster = P.Roster(store=store)
    roster.create(_persona(pid="ember", voice="af_bella", primary="deep house"))
    p2 = _persona(pid="pulse", name="Pulse", voice="am_michael", primary="deep house",
                  in_genres=["techno"], in_eras=["2020s"], in_tags=["dark"])
    created, res = roster.create(p2)
    assert created is None
    assert res.code == "primary_territory_collision"


def test_reject_high_pool_overlap(store):
    """REQ-PR-004: candidate pools that overlap at/above the cap are rejected (hard)."""
    roster = P.Roster(store=store, overlap_cap=0.35)
    roster.create(_persona(pid="ember", voice="af_bella", primary="deep house",
                           in_genres=["deep house", "electronic"], in_eras=["2010s"],
                           in_tags=["hypnotic", "warm"]))
    # Distinct primary territory but a nearly-identical descriptor pool -> high overlap.
    p2 = _persona(pid="twin", name="Twin", voice="am_michael", primary="tech house",
                  in_genres=["deep house", "electronic"], in_eras=["2010s"],
                  in_tags=["hypnotic", "warm"])
    created, res = roster.create(p2)
    assert created is None
    assert res.code == "pool_overlap_too_high"


def test_distinct_charters_admitted(store):
    """Distinct primary territory AND low pool overlap -> admitted (slight crossover OK)."""
    roster = P.Roster(store=store)
    roster.create(_persona(pid="ember", voice="af_bella", primary="deep house",
                           in_genres=["deep house", "electronic"], in_eras=["2010s"],
                           in_tags=["hypnotic"]))
    hald = _persona(pid="hald", name="Hald", voice="bm_george", primary="1970s soul",
                    in_genres=["soul", "funk"], in_eras=["1970s"], in_tags=["vintage"])
    created, res = roster.create(hald)
    assert created is not None and res.ok


def test_manual_and_autonomous_paths_share_one_gate(store):
    """REQ-PR-008/PR-011: the SAME validate_candidate is the gate for both paths.

    Build an authored (growth-gate) persona and a manual persona that collide on the SAME
    firewall — the rejection code is identical because there is only ONE gate, never a fork."""
    roster = P.Roster(store=store)
    authored = _persona(pid="ember", voice="af_bella", primary="deep house")
    authored.origin = "authored"
    roster.create(authored)
    # The growth gate is exactly validate_candidate(): a colliding autonomous candidate fails.
    auto_candidate = _persona(pid="auto", voice="am_michael", primary="deep house")
    auto_candidate.origin = "authored"
    res_auto = roster.validate_candidate(auto_candidate)
    # A manual candidate colliding the same way fails with the SAME code.
    manual_candidate = _persona(pid="manual", voice="am_fenrir", primary="deep house")
    res_manual = roster.validate_candidate(manual_candidate)
    assert res_auto.code == res_manual.code == "primary_territory_collision"


# --------------------------------------------------------------------------- #
# 3. gender + age attributes + the [22,70] bound (REQ-PR-015)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("age,ok", [(21, False), (22, True), (34, True), (70, True), (71, False)])
def test_age_bound_is_inclusive_22_to_70(store, age, ok):
    roster = P.Roster(store=store)
    created, res = roster.create(_persona(age=age))
    if ok:
        assert created is not None, f"age {age} should be accepted"
        assert res.ok
    else:
        assert created is None, f"age {age} should be rejected"
        assert res.code == "age_out_of_range"


def test_age_bound_enforced_for_autonomous_path(store):
    """The age bound rides the SHARED gate, so the AI-autonomous path enforces it too."""
    roster = P.Roster(store=store)
    cand = _persona(pid="kid", age=19)
    cand.origin = "authored"
    res = roster.validate_candidate(cand)
    assert not res.ok and res.code == "age_out_of_range"


def test_gender_varies_across_roster(store):
    roster = P.Roster(store=store)
    roster.create(_persona(pid="ember", voice="af_bella", gender="female", primary="deep house"))
    roster.create(_persona(pid="hald", name="Hald", voice="bm_george", gender="male",
                           primary="1970s soul", in_genres=["soul"], in_eras=["1970s"],
                           in_tags=["vintage"]))
    roster.create(_persona(pid="nyx", name="Nyx", voice="am_fenrir", gender="non-binary",
                           primary="ambient drone", in_genres=["ambient"], in_eras=["2020s"],
                           in_tags=["drone"]))
    genders = {p.gender for p in roster.all()}
    assert genders == {"female", "male", "non-binary"}


def test_age_and_gender_persist(tmp_path):
    sqlite_store.reset_registry_for_tests()
    path = str(tmp_path / "brain.db")
    roster = P.Roster(store=sqlite_store.PersonaStore(path))
    roster.create(_persona(age=68, gender="non-binary"))
    sqlite_store.reset_registry_for_tests()
    roster2 = P.Roster(store=sqlite_store.PersonaStore(path))
    p = roster2.get("ember")
    assert p.age == 68 and p.gender == "non-binary"
    sqlite_store.reset_registry_for_tests()


# --------------------------------------------------------------------------- #
# 4. Lifecycle: edit / disable / remove + golden rule (REQ-PR-013)
# --------------------------------------------------------------------------- #

def test_edit_revalidates_and_rejects_invariant_break(store):
    roster = P.Roster(store=store)
    roster.create(_persona(pid="ember", voice="af_bella", primary="deep house"))
    roster.create(_persona(pid="hald", name="Hald", voice="bm_george", primary="1970s soul",
                           in_genres=["soul"], in_eras=["1970s"], in_tags=["vintage"]))
    # Editing Hald onto Ember's voice must be rejected (1:1 firewall re-runs on edit).
    edited, res = roster.edit("hald", voice="af_bella")
    assert edited is None and res.code == "voice_already_bound"
    # Hald is unchanged.
    assert roster.get("hald").voice == "bm_george"


def test_edit_age_below_bound_rejected(store):
    roster = P.Roster(store=store)
    roster.create(_persona())
    edited, res = roster.edit("ember", age=20)
    assert edited is None and res.code == "age_out_of_range"
    assert roster.get("ember").age == 34


def test_disable_removes_from_future_selection_keeps_record(store):
    roster = P.Roster(store=store)
    roster.create(_persona())
    roster.set_active("ember")
    assert roster.disable("ember") is True
    assert roster.get("ember") is not None          # record kept
    assert roster.get("ember").enabled is False
    assert roster.enabled() == []                   # excluded from future selection
    assert roster.active_persona() is None           # golden rule: dropped from next cycle
    # Re-enablable.
    assert roster.enable("ember") is True
    assert roster.get("ember").enabled is True


def test_disable_owns_no_playout_so_never_silences(store):
    """Golden rule (REQ-PR-013d / NFR-P-5): disable mutates only the roster/future selection;
    it has no handle on any in-flight clip/stream, so it cannot cut a live break."""
    roster = P.Roster(store=store)
    roster.create(_persona())
    # The Roster exposes no playout/clip/stream API at all — disabling only flips a flag.
    assert not hasattr(roster, "stop_stream")
    assert roster.disable("ember") is True  # returns cleanly, touches nothing on-air


# --------------------------------------------------------------------------- #
# 5. CASCADE-PURGE reset + forward-cascade contract (REQ-PR-016)
# --------------------------------------------------------------------------- #

class _FakePerPersonaStore:
    """A stand-in for a FUTURE per-persona data surface (shows / diary / taste-learning).
    Honors the forward-cascade convention: purge_persona(id) deletes everything for id."""

    def __init__(self):
        self.rows = {"ember": ["taste-1", "diary-1", "show-1"], "hald": ["taste-9"]}

    def purge_persona(self, persona_id):
        removed = self.rows.pop(persona_id, [])
        return len(removed)


def test_remove_is_full_cascade_purge_and_frees_voice(store):
    """REQ-PR-013c + REQ-PR-016: remove deletes the entity, purges ALL per-persona data via
    every registered purger, and frees the voice so a fresh persona can claim it."""
    fake = _FakePerPersonaStore()
    roster = P.Roster(store=store, cascade_purgers=[fake])
    roster.create(_persona(pid="ember", voice="af_bella", primary="deep house"))
    freed = roster.remove("ember")
    assert freed == "af_bella"
    # Entity gone everywhere.
    assert roster.get("ember") is None
    assert store.load_all() == [] or all(r["id"] != "ember" for r in store.load_all())
    # ALL ancillary per-persona data purged (zero residual).
    assert "ember" not in fake.rows
    # Voice freed: a NEW persona can immediately bind af_bella in the cleared slot.
    new_p = _persona(pid="fresh", name="Fresh", voice="af_bella", primary="dub techno",
                     in_genres=["dub techno"], in_eras=["2020s"], in_tags=["spacious"])
    created, res = roster.create(new_p)
    assert created is not None and res.ok


def test_reset_alias_is_the_same_cascade(store):
    fake = _FakePerPersonaStore()
    roster = P.Roster(store=store, cascade_purgers=[fake])
    roster.create(_persona())
    assert roster.reset.__func__ is roster.remove.__func__  # explicit destructive alias
    freed = roster.reset("ember")
    assert freed == "af_bella"
    assert "ember" not in fake.rows


def test_cascade_purger_error_is_isolated(store):
    """A failing purger logs and the reset still completes (never blocks the stream)."""
    class _Boom:
        def purge_persona(self, persona_id):
            raise RuntimeError("boom")
    roster = P.Roster(store=store, cascade_purgers=[_Boom()])
    roster.create(_persona())
    freed = roster.remove("ember")  # must not raise
    assert freed == "af_bella"
    assert roster.get("ember") is None


def test_registered_purger_participates(store):
    fake = _FakePerPersonaStore()
    roster = P.Roster(store=store)
    roster.register_cascade_purger(fake)
    roster.create(_persona())
    roster.remove("ember")
    assert "ember" not in fake.rows


def test_persona_store_purge_persona_is_idempotent(store):
    store.upsert("ember", _persona().to_record())
    assert store.purge_persona("ember") == 1
    assert store.purge_persona("ember") == 0  # idempotent (already gone)


# --------------------------------------------------------------------------- #
# 6. [HARD] DEFAULT-IDENTICAL: persona=None overlay is a no-op
# --------------------------------------------------------------------------- #

def test_curation_overlay_none_is_house_default():
    """With persona=None the curator system prompt + extra lines are byte-identical to the
    house default (the single-default-persona path is unchanged)."""
    sys_prompt, lines = llm._persona_curation_overlay(None)
    assert sys_prompt == llm.PERSONA
    assert lines == []


def test_talk_overlay_none_is_house_default():
    assert llm._persona_host_prompt(None) == llm.HOST_PERSONA


def test_active_persona_none_with_empty_roster(store):
    """An empty roster (the default) yields no active persona => engines behave as today."""
    roster = P.Roster(store=store)
    assert roster.active_persona() is None


def test_curation_overlay_active_persona_specializes():
    """With an active persona the overlay specializes the prompt (opt-in multi-persona)."""
    p = _persona()
    sys_prompt, lines = llm._persona_curation_overlay(p)
    assert sys_prompt != llm.PERSONA
    assert "Ember" in sys_prompt
    assert any("deep house" in ln for ln in lines)


def test_curate_batch_signature_back_compat():
    """curate_batch keeps the original 4 keyword params (director call + characterize fakes
    are unchanged) and adds persona as an optional keyword-only-style default."""
    import inspect
    params = inspect.signature(llm.curate_batch).parameters
    assert list(params)[:4] == ["model", "batch_size", "recent", "seed_reference"]
    assert params["persona"].default is None


def test_generate_talk_script_signature_back_compat():
    import inspect
    params = inspect.signature(llm.generate_talk_script).parameters
    assert list(params)[:2] == ["model", "context"]
    assert params["persona"].default is None
