"""Humanizer lint gate for DJ banter scripts (SPEC-RADIO-HOSTVOICE-049 Group HL).

LLM-free, fully unit-testable. Mirrors brain/ear_writing.py in shape.
Banned-phrase sets sourced from .claude/skills/humanizer/SKILL.md patterns 3, 4, 7, 8,
9, 10, 14, 27, 31, 32, 33 plus two radio-specific pattern rows.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# =====================================================================================
# REQ-HL-001/007 — HumanLintContext and LintResult dataclasses.
# =====================================================================================

@dataclass
class HumanLintContext:
    """Per-break context for the humanizer lint. Presence (not None) opts a break into
    the humanizer lints riding the grounding.tier1_lint gate (REQ-HL-005)."""
    break_type: str = ""
    banned_phrases: Tuple[str, ...] = field(default_factory=tuple)
    literary_adjectives: Tuple[str, ...] = field(default_factory=tuple)
    # REQ-HL-007: humanizer pattern numbers active for this context
    humanizer_patterns: Tuple[int, ...] = field(default_factory=tuple)


@dataclass
class LintResult:
    """A single lint violation. pattern_id traces back to the humanizer skill pattern number."""
    token: str
    pattern_id: int   # humanizer SKILL.md pattern number
    position: int     # char offset in the text


# =====================================================================================
# REQ-HL-003 — Default banned sets sourced from humanizer SKILL.md patterns.
# =====================================================================================

# Pattern 3 — -ing analyses (padding depth with participial clauses)
_PATTERN3: Tuple[str, ...] = ("showcasing", "highlighting", "symbolizing", "reflecting the")

# Pattern 4 — promotional language (marketing adjectives)
_PATTERN4: Tuple[str, ...] = ("breathtaking", "stunning", "nestled", "rich tapestry")

# Pattern 7 — AI vocabulary (over-used prestige words)
_PATTERN7: Tuple[str, ...] = (
    "testament", "pivotal", "ethereal", "profound", "interplay", "intricate",
    "tapestry", "vibrant", "showcase", "foster",
)

# Pattern 8 — copula avoidance (serves as / stands as / marks a)
_PATTERN8: Tuple[str, ...] = ("serves as", "stands as", "marks a")

# Pattern 9 — negative parallelisms
_PATTERN9: Tuple[str, ...] = ("it's not just", "it is not just", "not merely")

# Pattern 14 — em dashes (hard ban, zero tolerance)
_PATTERN14: Tuple[str, ...] = ("—", "–")

# Pattern 27 — persuasive authority tropes
_PATTERN27: Tuple[str, ...] = ("at its core", "what really matters", "the real question is", "fundamentally")

# Pattern 32 — aphorism formulas
_PATTERN32: Tuple[str, ...] = ("is the language of", "is the currency of", "becomes a trap")

# Pattern 33 — rhetorical openers
_PATTERN33: Tuple[str, ...] = ("real talk", "look,", "here's the thing", "let's be honest")

# Mood narrations (radio-specific — adapts pattern 4)
_MOOD_NARRATION: Tuple[str, ...] = (
    "does something to the room", "sonic journey", "going somewhere warmer",
    "going somewhere darker", "going somewhere heavier", "going somewhere dreamier",
    "shifts the mood",
)

# Music-journalism (radio-specific)
_MUSIC_JOURNALISM: Tuple[str, ...] = (
    "captivating", "masterpiece", "infectious", "undeniable", "something special",
    "testament to",
)

# Literary adjectives (pattern 7 + 4 overlap)
_LITERARY_ADJECTIVES: Tuple[str, ...] = (
    "ethereal", "profound", "vibrant", "breathtaking", "stunning",
)

# Mapping: token -> humanizer pattern number
_TOKEN_PATTERN_MAP: List[Tuple[Tuple[str, ...], int]] = [
    (_PATTERN3, 3),
    (_PATTERN4, 4),
    (_PATTERN7, 7),
    (_PATTERN8, 8),
    (_PATTERN9, 9),
    (_PATTERN14, 14),
    (_PATTERN27, 27),
    (_PATTERN32, 32),
    (_PATTERN33, 33),
    (_MOOD_NARRATION, 4),      # radio-specific mood narration maps to pattern 4
    (_MUSIC_JOURNALISM, 7),    # music-journalism maps to pattern 7
]

# Structural checks need their own pattern IDs
_PATTERN10_ID = 10   # rule of three (3+ adjectives in 10-word span)
_PATTERN31_ID = 31   # staccato drama (3+ consecutive short sentences <=5 words)


def _default_banned() -> Tuple[str, ...]:
    """All banned phrases from the humanizer pattern rows."""
    seen: set = set()
    result: list = []
    for tokens, _ in _TOKEN_PATTERN_MAP:
        for t in tokens:
            if t not in seen:
                seen.add(t)
                result.append(t)
    return tuple(result)


_DEFAULT_BANNED: Tuple[str, ...] = _default_banned()
_DEFAULT_ADJECTIVES: Tuple[str, ...] = _LITERARY_ADJECTIVES


def _pattern_id_for(token: str) -> int:
    """Return the humanizer pattern number for a banned token."""
    tl = token.lower()
    for tokens, pid in _TOKEN_PATTERN_MAP:
        for t in tokens:
            if t.lower() == tl or tl in t.lower() or t.lower() in tl:
                return pid
    return 7  # default to AI vocabulary


# =====================================================================================
# REQ-HL-002 — scan_ai_slop: phrase scan + structural checks.
# =====================================================================================

def _scan_phrases(text: str, banned: Tuple[str, ...], adjectives: Tuple[str, ...]) -> List[LintResult]:
    results: List[LintResult] = []
    tl = text.lower()
    for phrase in banned:
        pl = phrase.lower()
        pos = 0
        while True:
            idx = tl.find(pl, pos)
            if idx == -1:
                break
            pid = _pattern_id_for(phrase)
            results.append(LintResult(token=phrase, pattern_id=pid, position=idx))
            pos = idx + 1
    for adj in adjectives:
        al = adj.lower()
        pos = 0
        while True:
            idx = tl.find(al, pos)
            if idx == -1:
                break
            results.append(LintResult(token=adj, pattern_id=_pattern_id_for(adj), position=idx))
            pos = idx + 1
    return results


def _scan_staccato(text: str) -> List[LintResult]:
    """Pattern 31: 3+ consecutive sentences <=5 words each."""
    results: List[LintResult] = []
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    run = 0
    run_start = 0
    for i, sent in enumerate(sentences):
        wc = len(sent.split())
        if wc <= 5:
            if run == 0:
                run_start = i
            run += 1
            if run >= 3:
                results.append(LintResult(
                    token=sentences[run_start],
                    pattern_id=_PATTERN31_ID,
                    position=run_start,
                ))
                break
        else:
            run = 0
    return results


_PATTERN10_REGEX = re.compile(r'\b\w+,\s+\w+,\s+(?:and\s+)?\w+\b')


def _scan_rule_of_three(text: str) -> List[LintResult]:
    """Pattern 10: 3+ consecutive adjectives in a 10-word span."""
    results: List[LintResult] = []
    for m in _PATTERN10_REGEX.finditer(text):
        span_text = m.group()
        words = re.sub(r'[,\s]+', ' ', span_text).split()
        if len(words) >= 3:
            results.append(LintResult(token=span_text[:32], pattern_id=_PATTERN10_ID, position=m.start()))
    return results


def scan_ai_slop(text: str, ctx: Optional[HumanLintContext] = None) -> List[LintResult]:
    """REQ-HL-002: Scan text for AI-slop violations. Returns empty list if clean.

    Uses the ctx banned_phrases/literary_adjectives if provided; falls back to the
    default sets (_DEFAULT_BANNED, _DEFAULT_ADJECTIVES)."""
    if ctx is not None:
        banned = ctx.banned_phrases if ctx.banned_phrases else _DEFAULT_BANNED
        adjectives = ctx.literary_adjectives if ctx.literary_adjectives else _DEFAULT_ADJECTIVES
    else:
        banned = _DEFAULT_BANNED
        adjectives = _DEFAULT_ADJECTIVES
    results = _scan_phrases(text, banned, adjectives)
    results += _scan_staccato(text)
    results += _scan_rule_of_three(text)
    return results


# =====================================================================================
# REQ-HL-004 — humandj_rails: positive-framing prompt instructions.
# =====================================================================================

_RAILS: Tuple[str, ...] = (
    # Pattern 14 — em dashes
    "Use only commas, periods, and plain sentences. No em dashes.",
    # Pattern 7 — AI vocabulary
    "Say plain words. 'It was good.' not 'It was a vibrant testament.'",
    # Pattern 3 — -ing padding
    "Do not add '-ing' clauses to pad depth. If you don't have something to say, say less.",
    # Pattern 32 — aphorism formulas
    "State the concrete thing. Do not turn it into a slogan.",
    # Pattern 31 — staccato drama
    "Do not stack three or more short fragments for effect. If you need rhythm, use one short sentence.",
    # Pattern 27 — persuasive authority tropes
    "Do not announce you are about to say something important. Just say it.",
)


def humandj_rails() -> List[str]:
    """REQ-HL-004: Positive-framing prompt rails derived from the humanizer skill taxonomy.
    Parallel to ear_writing.ear_writing_rails(). Returns a list (not tuple) for mutability."""
    return list(_RAILS)
