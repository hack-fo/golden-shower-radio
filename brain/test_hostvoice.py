"""SPEC-RADIO-HOSTVOICE-049 Group HT — 11 acceptance tests."""

# ---------------------------------------------------------------------------
# REQ-HT-001 test 1: BREAK_TYPES weights sum to 1.0
# ---------------------------------------------------------------------------
def test_break_type_weights_sum_to_one():
    from brain.playbook import BREAK_TYPES
    total = sum(b.weight for b in BREAK_TYPES)
    assert abs(total - 1.0) < 0.001, f"weights sum {total} != 1.0"
    assert len(BREAK_TYPES) == 7
    names = {b.name for b in BREAK_TYPES}
    assert names == {"MICRO", "CASUAL_OBS", "FACT_DROP", "ANECDOTE", "THEME_NOTE", "STATION_IDENT", "REFLECTION"}


# ---------------------------------------------------------------------------
# REQ-HT-001 test 2: MICRO break prompt omits mood
# ---------------------------------------------------------------------------
def test_micro_break_prompt_omits_mood():
    from brain import llm, config as cfg_mod
    cfg = cfg_mod.Config.__new__(cfg_mod.Config)
    object.__setattr__(cfg, "human_dj_taxonomy_enabled", True)
    # Patch other required config attributes
    for attr in ["host_voice_pv_enabled", "craft_playbook_enabled", "quality_gate_enabled",
                 "shows_enabled", "showprep_enabled", "hostctx_enabled"]:
        object.__setattr__(cfg, attr, False)

    context = {
        "artist": "Burial",
        "title": "Archangel",
        "next_mood": "dark and heavy",
        "break_type": "MICRO",
    }
    prompt = llm._build_talk_prompt(context)
    # With MICRO + human_dj_taxonomy_enabled, next_mood tease must be absent
    assert "dark and heavy" not in prompt
    assert "mood" not in prompt.lower() or "no mood" in prompt.lower() or "plain words" in prompt.lower()


# ---------------------------------------------------------------------------
# REQ-HT-001 test 3: CASUAL_OBS break allows fragments
# ---------------------------------------------------------------------------
def test_casual_break_allows_fragments():
    from brain import llm, config as cfg_mod
    cfg = cfg_mod.Config.__new__(cfg_mod.Config)
    object.__setattr__(cfg, "human_dj_taxonomy_enabled", True)
    for attr in ["host_voice_pv_enabled", "craft_playbook_enabled", "quality_gate_enabled",
                 "shows_enabled", "showprep_enabled", "hostctx_enabled"]:
        object.__setattr__(cfg, attr, False)
    context = {
        "artist": "Burial",
        "title": "Archangel",
        "break_type": "CASUAL_OBS",
    }
    prompt = llm._build_talk_prompt(context)
    assert "complete thought" in prompt or "Anyway." in prompt or "fragment" in prompt.lower()


# ---------------------------------------------------------------------------
# REQ-HT-001 test 4: humanlint detects slop
# ---------------------------------------------------------------------------
def test_human_lint_detects_slop():
    from brain.humanlint import scan_ai_slop
    text = "That Burial track always does something to the room. It was a vibrant testament to his craft."
    results = scan_ai_slop(text)
    assert len(results) > 0
    tokens = [r.token for r in results]
    assert any("vibrant" in t or "testament" in t or "does something to the room" in t for t in tokens)


# ---------------------------------------------------------------------------
# REQ-HT-001 test 5: humanlint passes clean
# ---------------------------------------------------------------------------
def test_human_lint_passes_clean():
    from brain.humanlint import scan_ai_slop
    text = "That was Burial. Good track."
    results = scan_ai_slop(text)
    assert results == []


# ---------------------------------------------------------------------------
# REQ-HT-001 test 6: show prep has diversity instruction
# ---------------------------------------------------------------------------
def test_show_prep_has_diversity_instruction():
    from brain.llm import _build_show_prep_prompt
    prompt = _build_show_prep_prompt("Burial", "UK bass", [], [], spotlight_diversity=True)
    assert "deep cut" in prompt.lower()


# ---------------------------------------------------------------------------
# REQ-HT-001 test 7: HUMAN_HOST_PERSONA no journalism register
# ---------------------------------------------------------------------------
def test_human_host_persona_no_journalism_register():
    from brain.llm import HUMAN_HOST_PERSONA
    forbidden = ["journalist", "press release", "music criticism"]
    for token in forbidden:
        assert token not in HUMAN_HOST_PERSONA.lower(), f"Found '{token}' in HUMAN_HOST_PERSONA"


# ---------------------------------------------------------------------------
# REQ-HT-001 test 8: break_type rotation no repeat
# ---------------------------------------------------------------------------
def test_break_type_rotation_no_repeat():
    from brain.playbook import next_break_type
    # Run 100 pairs — no consecutive repeat allowed when >1 candidate
    prev = ""
    for _ in range(100):
        chosen = next_break_type(prev)
        if prev:
            assert chosen != prev, f"Got {chosen} twice in a row"
        prev = chosen


# ---------------------------------------------------------------------------
# REQ-HT-001 test 9: LintResult carries pattern_id
# ---------------------------------------------------------------------------
def test_lint_result_carries_pattern_id():
    from brain.humanlint import scan_ai_slop, LintResult
    text = "It was a vibrant testament to creativity."
    results = scan_ai_slop(text)
    assert all(isinstance(r, LintResult) for r in results)
    assert all(hasattr(r, "pattern_id") for r in results)
    pattern_ids = {r.pattern_id for r in results}
    # "vibrant" and "testament" are pattern 7
    assert 7 in pattern_ids


# ---------------------------------------------------------------------------
# REQ-HT-001 test 10: _BAN_TWINS covers all humanizer pattern categories
# ---------------------------------------------------------------------------
def test_ban_twins_cover_all_humanizer_pattern_categories():
    from brain.llm import _BAN_TWINS
    # Flatten all ban tokens
    if isinstance(_BAN_TWINS, dict):
        all_tokens = " ".join(str(k) for k in _BAN_TWINS.keys()).lower()
    else:
        all_tokens = " ".join(str(b) for b in _BAN_TWINS).lower()
    # One representative per category
    required = [
        "showcasing",     # pattern 3 -ing
        "vibrant",        # pattern 7 AI vocab
        "at its core",    # pattern 27 persuasive authority
        "—",              # pattern 14 em dash
        "does something to the room",  # mood narration
    ]
    for token in required:
        assert token.lower() in all_tokens, f"'{token}' not found in _BAN_TWINS"


# ---------------------------------------------------------------------------
# REQ-HT-001 test 11: humandj_rails positive framing
# ---------------------------------------------------------------------------
def test_humandj_rails_positive_framing():
    from brain.humanlint import humandj_rails
    rails = humandj_rails()
    assert len(rails) >= 6
    # All rails must be positive instructions, not ban lists
    for rail in rails:
        assert isinstance(rail, str)
        assert len(rail) > 10
    # Check at least one rail per pattern
    combined = " ".join(rails).lower()
    assert "em dash" in combined or "no em dash" in combined or "em dashes" in combined
    assert "plain" in combined
    assert "fragment" in combined or "short fragment" in combined or "say less" in combined


# ---------------------------------------------------------------------------
# REQ-HL-002 — structural scan coverage: staccato drama (pattern 31).
# ---------------------------------------------------------------------------
def test_human_lint_flags_staccato_drama():
    from brain.humanlint import scan_ai_slop
    # 3+ consecutive sentences <=5 words => pattern 31.
    text = "It hits hard. It does not stop. Pure energy. Then it goes."
    results = scan_ai_slop(text)
    assert any(r.pattern_id == 31 for r in results)


# ---------------------------------------------------------------------------
# REQ-HL-002 — structural scan coverage: rule of three (pattern 10).
# ---------------------------------------------------------------------------
def test_human_lint_flags_rule_of_three():
    from brain.humanlint import scan_ai_slop
    text = "It is warm, bright, and full."
    results = scan_ai_slop(text)
    assert any(r.pattern_id == 10 for r in results)


# ---------------------------------------------------------------------------
# REQ-HL-001 — HumanLintContext custom banned set overrides the default.
# ---------------------------------------------------------------------------
def test_human_lint_context_custom_banned_overrides_default():
    from brain.humanlint import scan_ai_slop, HumanLintContext
    # Both override sets are non-empty so neither falls back to the defaults
    # (scan_ai_slop only falls back when a ctx set is empty).
    ctx = HumanLintContext(break_type="MICRO", banned_phrases=("kumquat",),
                           literary_adjectives=("loquat",))
    # "vibrant" is in the DEFAULT set but NOT in either custom set => not flagged.
    results = scan_ai_slop("a vibrant kumquat", ctx)
    tokens = [r.token for r in results]
    assert "kumquat" in tokens
    assert "vibrant" not in tokens


# ---------------------------------------------------------------------------
# NFR-HV-6 — gate is byte-identical when humandj_ctx is None vs absent.
# ---------------------------------------------------------------------------
def test_gate_byte_identical_when_humandj_ctx_none():
    from brain import grounding
    contract = grounding.FactContract.from_context({})
    slop = "It was a vibrant testament."
    # humandj_ctx absent: the humanizer slop tokens are NOT scanned by the HL hook.
    r_absent = grounding.tier1_lint(slop, contract)
    r_none = grounding.tier1_lint(slop, contract, humandj_ctx=None)
    assert r_absent.violations == r_none.violations
