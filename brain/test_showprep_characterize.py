"""Characterization tests for the pre-OC baseline — PRESERVE phase (DDD).

These pin the EXACT behaviour Group OC must not disturb. With the OC show-prep pass
OFF (the default), every consuming surface — the FactContract, the grounding gate, the
OY segment production pipeline's research seam, and the cheap Mode-A LLM path — must be
BYTE-IDENTICAL to before this SPEC. They are deliberately written against the existing
modules (no OC import) so they keep passing unchanged after OC lands.
"""

from __future__ import annotations

from brain import grounding as G
from brain import segment_registry as SR
from brain.ledger import EventLedger


# --------------------------------------------------------------------------------------
# FactContract — the closed-world bundle OC feeds via ``showprep_facts`` (default empty).
# --------------------------------------------------------------------------------------

def test_factcontract_empty_context_has_no_showprep_facts():
    """An empty talk context yields a contract with NO show-prep facts (OC OFF baseline)."""
    contract = G.FactContract.from_context({})
    assert contract.showprep_facts == []
    assert contract.fact_tokens() == set()


def test_factcontract_carries_showprep_when_present():
    """When show-prep facts ARE supplied the contract carries them verbatim (the seam OC fills)."""
    ctx = {
        "last_artist": "Sade",
        "showprep_facts": [
            {"value": "released in 1984", "source_url": "https://mb.org/x",
             "speaker": "MusicBrainz", "date": "2026-01-01"},
        ],
    }
    contract = G.FactContract.from_context(ctx)
    assert len(contract.showprep_facts) == 1
    assert "1984" in contract.year_tokens()


def test_factcontract_drops_non_dict_showprep():
    """Defensive: non-dict show-prep entries are filtered (tolerant of a malformed bundle)."""
    contract = G.FactContract.from_context({"showprep_facts": ["bad", 7, {"value": "ok"}]})
    assert contract.showprep_facts == [{"value": "ok"}]


# --------------------------------------------------------------------------------------
# Grounding gate — a clean script with no facts still PASSES (OC adds no new gate).
# --------------------------------------------------------------------------------------

def test_run_gate_clean_script_passes_with_empty_contract():
    contract = G.FactContract.from_context({"last_artist": "Sade", "last_title": "Smooth Operator"})
    out = G.run_gate("Sade there, Smooth Operator. Lovely stuff.", contract)
    assert not out.skipped
    assert out.script is not None


def test_run_gate_unsourced_year_fails_without_showprep():
    """An invented year with NO grounding is a forbidden-fact FAIL — the rail OC must preserve."""
    contract = G.FactContract.from_context({"last_artist": "Sade", "last_title": "X"})
    out = G.run_gate("That track from 1984 is a classic.", contract,
                     regenerate=lambda issues: "")
    # No regen content -> the gate skips rather than ship the unsourced fact.
    assert out.skipped or out.script is None


# --------------------------------------------------------------------------------------
# OY segment production pipeline — the research seam DEFAULTS to a no-op (OC fills it).
# --------------------------------------------------------------------------------------

def _clean_ctx():
    return {"last_artist": "Sade", "last_title": "Smooth Operator", "script": "Sade there."}


def test_pipeline_research_seam_defaults_to_noop(tmp_path):
    """With no research callable injected the pipeline runs research as a pass-through:
    the context is unchanged and the segment still produces. This is the OC-OFF baseline."""
    ledger = EventLedger(str(tmp_path / "events.db"))
    reg = SR.SegmentRegistry(ledger)
    reg.seed()
    pipe = SR.SegmentProductionPipeline(reg, write=lambda t, ctx: str(ctx.get("script", "")))
    out = pipe.produce("deep_dive", _clean_ctx(), persona_id="dusk")
    assert "research" in out.stages
    assert not out.skipped


def test_pipeline_research_fault_degrades_never_blocks(tmp_path):
    """A raising research seam is swallowed — the pipeline keeps going (never-block rail)."""
    ledger = EventLedger(str(tmp_path / "events.db"))
    reg = SR.SegmentRegistry(ledger)
    reg.seed()

    def boom(t, ctx):
        raise RuntimeError("research provider down")

    pipe = SR.SegmentProductionPipeline(reg, research=boom,
                                        write=lambda t, ctx: str(ctx.get("script", "")))
    out = pipe.produce("deep_dive", _clean_ctx(), persona_id="dusk")
    assert "research" in out.stages
    assert not out.skipped
