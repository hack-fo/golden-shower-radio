"""Script-side EAR-WRITING rules (SPEC-RADIO-PROGRAMMING-007 Group PS).

This module is the AUTHORITATIVE owner of the SCRIPT side of host talk — how the talk-script
generator writes "for the EAR" so flat TTS reads naturally. It owns the RULES; the SYNTHESIS
side (the chunk+silence render, the synthesis speed, the ducked bed) is VOICE-002's
(``voice.py``). These requirements REFERENCE that synthesis side; the blank-line blocks
(REQ-PS-004) are written to ALIGN WITH VOICE-002's synthesis chunk boundaries — a coordination
contract, not a redefinition.

It is the SINGLE SOURCE OF TRUTH for:

  REQ-PS-001  ONE thought per sentence at or under ~20 words. ``MAX_WORDS_PER_SENTENCE`` (TUNABLE)
              + ``scan_long_sentences``. The word target is TUNABLE config; synthesis is VOICE-002's.
  REQ-PS-002  ALWAYS contractions + address ONE listener in the SECOND person (never a crowd).
              ``scan_missing_contractions`` + ``scan_crowd_address`` (the no-crowd rail complements
              REQ-PC-004 write-to-one-listener — referenced, not re-owned).
  REQ-PS-003  PUNCTUATE FOR BREATH (commas / em-dashes / ellipses) + VARY sentence length.
              ``scan_breath_punctuation`` + ``scan_monotone_length``.
  REQ-PS-004  1-2 sentence BLOCKS separated by BLANK LINES = the VOICE-002 synthesis chunk
              boundaries. ``split_into_blocks`` (the coordination helper) + ``scan_block_structure``.
              [HARD coordination] VOICE-002 owns the chunk+silence RENDER (~100-200 token chunking);
              this module owns writing the block boundaries so the synthesizer chunks at sentence-
              group boundaries. The synthesis render is the deferred VOICE-002 sibling (voice.py
              currently synthesizes the whole script); this module owns + tests the SCRIPT half.
  REQ-PS-005  SPELL numbers/dates as SPOKEN ("twenty twenty-six", "nineteen seventy-three") +
              attach an IPA / phoneme-spelling OVERRIDE for a hard name. ``spell_numbers_as_spoken``
              + ``PhonemeOverride`` / ``attach_override`` / ``scan_raw_digits``. The IPA-override
              CAPABILITY is the rail; WHICH names get overrides is the AI's call. VOICE-002 consumes
              the override at synthesis.

It is ALSO the single source of the EAR-WRITING RAILS prompt block carried IN the live talk
prompt (REQ-PV-002/004 carry these rails; this module OWNS the rails text). ``ear_writing_rails``
replaces the inline fork that previously lived in ``llm._EAR_WRITING_RAILS`` — PV now reads the
rails from here (the same single-source pattern as the PC daypart presets and the PI anchor block).

The deterministic LINTS are LLM-FREE and fully testable; they RIDE the Group PG-005 Tier-1 gate
via the optional ``ear_ctx`` hook in ``grounding.tier1_lint`` (so with no PS context the PG gate
is BYTE-IDENTICAL). Enforcement is the quality gate (OPS-004 REQ-OF-006) — the SAME never-ship-a-
FAIL orchestration the Group PG/PV lints already use; this module adds the SCRIPT-side lints, it
does not fork the gate.

All thresholds here are TUNABLE module-level config per the SPEC idiom ("the word target is
tunable; that scripts are written for the ear is the rail").
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple


# =====================================================================================
# REQ-PS-001 — one thought per sentence, <= ~20 words (TUNABLE word target).
# =====================================================================================

# The per-sentence word ceiling (REQ-PS-001). TUNABLE: the SPEC's "~20 words" default; the
# rail is that a flat-TTS sentence stays a clean breath unit, the number is config.
MAX_WORDS_PER_SENTENCE: int = 20

# A sentence terminator set (spoken-script punctuation). An ellipsis is a breath mark, NOT a
# hard terminator, so it does not split a sentence here (REQ-PS-003 treats it as a pause).
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[A-Za-z0-9'’\-]+")


def split_sentences(text: str) -> List[str]:
    """Split a block of script into spoken sentences on .!? boundaries (ellipsis is a breath
    mark, not a terminator — REQ-PS-003). Blank-line block structure is handled separately
    (``split_into_blocks``); this splits WITHIN a block. Empty input -> empty list."""
    if not text or not text.strip():
        return []
    # Collapse the ellipsis to a placeholder so "..." is not seen as three terminators.
    guarded = text.replace("...", "…").replace("…", " … ")
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(guarded) if p.strip()]
    return [p.replace("…", "...") for p in parts]


def count_words(sentence: str) -> int:
    """Count spoken words in a sentence (REQ-PS-001). A hyphenated word and a contraction
    each count as ONE word (they are one breath unit)."""
    return len(_WORD.findall(sentence or ""))


def scan_long_sentences(text: str, max_words: int = MAX_WORDS_PER_SENTENCE) -> List[str]:
    """REQ-PS-001 lint. Empty == clean. FLAGS any sentence over ``max_words`` words — an over-
    long sentence loses the listener in a long clause and reads as one strained TTS breath.
    The gate (OPS-004 REQ-OF-006) regenerates/rejects a flagged break; the ceiling is TUNABLE."""
    violations: List[str] = []
    for block in split_into_blocks(text):
        for sent in split_sentences(block):
            n = count_words(sent)
            if n > max_words:
                violations.append(
                    f"long-sentence: {n} words exceed {max_words} -> \"{_clip(sent)}\""
                )
    return violations


# =====================================================================================
# REQ-PS-002 — always contractions + singular second person (never a crowd).
# =====================================================================================

# Expanded forms whose contraction is the spoken default (REQ-PS-002). The PAIR is matched as
# a whole word so "we are" -> flagged but "aware" is not. TUNABLE list; that scripts contract
# is the rail. Each entry is (expanded-regex, the contraction it should be).
_CONTRACTION_PAIRS: Tuple[Tuple[re.Pattern, str], ...] = tuple(
    (re.compile(rf"\b{pat}\b", re.IGNORECASE), short)
    for pat, short in (
        (r"you are", "you're"),
        (r"it is", "it's"),
        (r"that is", "that's"),
        (r"we are", "we're"),
        (r"they are", "they're"),
        (r"do not", "don't"),
        (r"does not", "doesn't"),
        (r"did not", "didn't"),
        (r"is not", "isn't"),
        (r"was not", "wasn't"),
        (r"are not", "aren't"),
        (r"will not", "won't"),
        (r"cannot", "can't"),
        (r"can not", "can't"),
        (r"would not", "wouldn't"),
        (r"could not", "couldn't"),
        (r"should not", "shouldn't"),
        (r"have not", "haven't"),
        (r"has not", "hasn't"),
        (r"i am", "I'm"),
        (r"let us", "let's"),
        (r"there is", "there's"),
        (r"here is", "here's"),
        (r"what is", "what's"),
        (r"who is", "who's"),
    )
)

# Crowd-address tells (REQ-PS-002): a script addressing MANY listeners breaks the intimate one-
# listener register (complements REQ-PC-004 write-to-one-listener). TUNABLE; matched whole-phrase.
_CROWD_PHRASES: Tuple[str, ...] = (
    "everyone",
    "everybody",
    "all you listeners",
    "all of you",
    "you all",
    "you guys",
    "you folks",
    "listeners",
    "folks out there",
    "people out there",
    "hey all",
    "you lot",
)


def scan_missing_contractions(text: str) -> List[str]:
    """REQ-PS-002 (a) lint. Empty == clean. FLAGS an EXPANDED form whose contraction is the
    spoken default ("you are" -> should be "you're"), so the script reads as spoken speech, not
    written prose. The rule is the rail; the copy is the AI's."""
    if not text:
        return []
    violations: List[str] = []
    for pat, short in _CONTRACTION_PAIRS:
        for m in pat.finditer(text):
            violations.append(
                f"missing-contraction: \"{m.group(0)}\" -> \"{short}\""
            )
    return violations


def scan_crowd_address(text: str) -> List[str]:
    """REQ-PS-002 (b) lint. Empty == clean. FLAGS addressing a CROWD ("everyone", "all you
    listeners") instead of ONE listener in the second person — the intimacy rail. Matched
    whole-phrase, case-insensitively. TUNABLE phrase set."""
    if not text:
        return []
    low = text.lower()
    violations: List[str] = []
    for phrase in _CROWD_PHRASES:
        if re.search(rf"\b{re.escape(phrase)}\b", low):
            violations.append(f"crowd-address: \"{phrase}\" (write to ONE listener)")
    return violations


# =====================================================================================
# REQ-PS-003 — punctuate for breath; vary sentence length.
# =====================================================================================

# A script of this many or more sentences must show breath punctuation SOMEWHERE (REQ-PS-003):
# a single short line need not. TUNABLE.
MIN_SENTENCES_FOR_BREATH: int = 3
# Breath marks: comma, em-dash (or " - " spaced hyphen), ellipsis. TUNABLE set.
_BREATH_MARK = re.compile(r",|—| - |\.\.\.|…")
# A monotone script is one where every sentence is within this word-count spread of every
# other (no variation). TUNABLE: scripts of >= MIN_SENTENCES_FOR_VARIANCE sentences must vary.
MIN_SENTENCES_FOR_VARIANCE: int = 4
MIN_LENGTH_SPREAD_WORDS: int = 3


def scan_breath_punctuation(text: str) -> List[str]:
    """REQ-PS-003 (a) lint. Empty == clean. FLAGS a multi-sentence script that carries NO
    breath punctuation at all (no comma, em-dash, or ellipsis to mark a speaker's natural
    pause) — punctuation that serves the EAR, not the page. A single short line is exempt."""
    if not text or not text.strip():
        return []
    sents = [s for b in split_into_blocks(text) for s in split_sentences(b)]
    if len(sents) < MIN_SENTENCES_FOR_BREATH:
        return []
    if _BREATH_MARK.search(text):
        return []
    return ["no-breath-punctuation: script marks no natural pauses (punctuate for the ear)"]


def scan_monotone_length(text: str) -> List[str]:
    """REQ-PS-003 (b) lint. Empty == clean. FLAGS a longer script whose sentences are all the
    SAME length (monotone rhythm). Varying sentence length is the rail; the specific rhythm is
    the AI's. A script under ``MIN_SENTENCES_FOR_VARIANCE`` sentences is exempt (too short to
    be monotone)."""
    if not text:
        return []
    lengths = [
        count_words(s) for b in split_into_blocks(text) for s in split_sentences(b)
    ]
    if len(lengths) < MIN_SENTENCES_FOR_VARIANCE:
        return []
    if (max(lengths) - min(lengths)) < MIN_LENGTH_SPREAD_WORDS:
        return [
            "monotone-length: every sentence is the same length (vary the rhythm)"
        ]
    return []


# =====================================================================================
# REQ-PS-004 — 1-2 sentence blocks separated by blank lines = synthesis chunk boundaries.
# =====================================================================================

# The max sentences a single blank-line block may hold (REQ-PS-004 "1-2 sentence BLOCKS").
# TUNABLE; the rail is that blocks are SHORT sentence groups the synthesizer chunks cleanly.
MAX_SENTENCES_PER_BLOCK: int = 2
# A blank line is one-or-more empty lines between blocks.
_BLANK_LINE_SPLIT = re.compile(r"\n[ \t]*\n+")


def split_into_blocks(text: str) -> List[str]:
    """The REQ-PS-004 coordination helper. Split a script into its BLANK-LINE BLOCKS — the
    boundaries at which VOICE-002 chunks the script for synthesis (with inter-chunk silence).

    [HARD coordination] This is the explicit contract between the SCRIPT side (this SPEC) and
    the SYNTHESIS side (VOICE-002): the generator writes blocks here, VOICE-002 chunks at these
    boundaries and inserts natural silence between them. VOICE-002 owns the actual chunk+silence
    render (the synthesis half is the deferred sibling); this helper owns the BLOCK split so the
    two align. A script with no blank lines is a single block (degrades safely). Empty -> []."""
    if not text or not text.strip():
        return []
    return [b.strip() for b in _BLANK_LINE_SPLIT.split(text.strip()) if b.strip()]


def scan_block_structure(text: str, max_sentences: int = MAX_SENTENCES_PER_BLOCK) -> List[str]:
    """REQ-PS-004 lint. Empty == clean. FLAGS a script structured so a single blank-line BLOCK
    holds MORE than ``max_sentences`` sentences — a block that big would not chunk cleanly at
    a sentence-group boundary, defeating the VOICE-002 silence-between-blocks pacing. A short
    single-block script (within the cap) is fine; the rail is 1-2 sentence blocks."""
    if not text or not text.strip():
        return []
    violations: List[str] = []
    for i, block in enumerate(split_into_blocks(text)):
        n = len(split_sentences(block))
        if n > max_sentences:
            violations.append(
                f"oversized-block: block {i + 1} has {n} sentences (max {max_sentences} "
                "per blank-line block)"
            )
    return violations


# =====================================================================================
# REQ-PS-005 — spell numbers/dates as spoken; IPA phoneme override for hard names.
# =====================================================================================

# A spoken-number map for the small integers a host says inline (REQ-PS-005). The rail is that
# DIGITS are spelled as spoken; the AI authors the copy. We spell the common small cases and the
# year/decade forms below; the lint flags any remaining raw multi-digit run so the generator
# rewrites it. TUNABLE.
_ONES = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
)
_TENS = (
    "", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
)
# Years a station actually says out loud (music history); outside this the lint still flags
# raw digits but the speller leaves them (the AI spells the unusual case). TUNABLE.
_YEAR_MIN, _YEAR_MAX = 1000, 2099
_RAW_DIGITS = re.compile(r"\d[\d,]*")


def _spell_two_digits(n: int) -> str:
    """Spell 0-99 as spoken ("twenty-six", "seven", "nineteen")."""
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] if ones == 0 else f"{_TENS[tens]}-{_ONES[ones]}"


def _spell_year(n: int) -> str:
    """Spell a 4-digit year as a radio host says it: "nineteen seventy-three", "twenty
    twenty-six", "two thousand" / "two thousand five" for the 2000-2009 band."""
    hi, lo = divmod(n, 100)
    if 2000 <= n <= 2009:
        return "two thousand" if lo == 0 else f"two thousand {_ONES[lo]}"
    if lo == 0:
        return f"{_spell_two_digits(hi)} hundred"
    hi_words = _spell_two_digits(hi)
    lo_words = _ONES[lo] if lo < 10 else _spell_two_digits(lo)
    # "nineteen oh five" for the 1901-1909 / 2001-2009-style single-digit tail.
    if 1 <= lo <= 9:
        return f"{hi_words} oh {_ONES[lo]}"
    return f"{hi_words} {lo_words}"


def spell_numbers_as_spoken(text: str) -> str:
    """REQ-PS-005 (a). Rewrite raw digit runs as a host SPEAKS them so flat TTS does not misread
    them: a 4-digit year in range -> "nineteen seventy-three"; a small integer -> "twenty-six";
    a comma-grouped or out-of-range number is left to the AI to spell (the rail is the speller
    capability + the lint, not exhaustive numeral coverage). Idempotent on already-spoken text."""
    if not text:
        return text

    def _sub(m: "re.Match") -> str:
        raw = m.group(0)
        digits = raw.replace(",", "")
        if not digits.isdigit():
            return raw
        n = int(digits)
        if "," in raw:
            return raw  # large grouped number: AI spells it (kept honest, not faked)
        if len(digits) == 4 and _YEAR_MIN <= n <= _YEAR_MAX:
            return _spell_year(n)
        if n <= 99:
            return _spell_two_digits(n)
        return raw  # 3-digit / large bare number: left for the AI to spell

    return _RAW_DIGITS.sub(_sub, text)


def scan_raw_digits(text: str) -> List[str]:
    """REQ-PS-005 (a) lint. Empty == clean. FLAGS any remaining RAW digit run a host would read
    aloud — digits the synthesizer may misread. The generator spells them as spoken
    (``spell_numbers_as_spoken``) before airing. The rail is digits-as-spoken; the copy is the AI's."""
    if not text:
        return []
    return [
        f"raw-digits: \"{m.group(0)}\" (spell numbers/dates as spoken)"
        for m in _RAW_DIGITS.finditer(text)
    ]


@dataclass(frozen=True)
class PhonemeOverride:
    """REQ-PS-005 (b). A per-WORD pronunciation override the script generator attaches for a
    name TTS is likely to mispronounce, so the synthesizer (VOICE-002) says it correctly.

    ``written`` is the name as it appears in the script; ``ipa`` is the IPA / phoneme spelling
    VOICE-002 consumes at synthesis. The override CAPABILITY is the rail; WHICH names get an
    override is the AI's call (informed by observed mispronunciations). VOICE-002 owns applying
    the override at synthesis (the consuming half is the deferred sibling)."""

    written: str
    ipa: str

    def __post_init__(self) -> None:
        if not str(self.written).strip() or not str(self.ipa).strip():
            raise ValueError("PhonemeOverride needs a written name and an IPA spelling")


def attach_override(
    overrides: Optional[Sequence[PhonemeOverride]],
    written: str,
    ipa: str,
) -> List[PhonemeOverride]:
    """REQ-PS-005 (b). Return a new override list with ``written`` -> ``ipa`` attached (an
    existing override for the same name is replaced, last-write-wins). The AI calls this for a
    hard name; VOICE-002 consumes the resulting list at synthesis. Pure + side-effect-free."""
    name = str(written).strip()
    kept = [o for o in (overrides or []) if o.written.strip().lower() != name.lower()]
    kept.append(PhonemeOverride(written=name, ipa=str(ipa).strip()))
    return kept


# =====================================================================================
# The ear-writing RAILS prompt block (the SINGLE SOURCE PV reads — REQ-PV-002/004 carry it).
# =====================================================================================

# REQ-PS-001..005 as the live-prompt RAILS. This is the SINGLE SOURCE OF TRUTH for the rails
# text; ``llm._EAR_WRITING_RAILS`` reads from here (the inline fork is eliminated, the same
# single-source pattern as the PC daypart presets and the PI anchor block). The blank-line block
# instruction is the REQ-PS-004 coordination contract (VOICE-002 chunks at the blank lines) — it
# MUST be present and not broken. TUNABLE wording; that the rails are carried is the rail.
_RAILS: Tuple[str, ...] = (
    "Always use contractions. One thought per sentence, about twenty words or fewer. "
    "Punctuate for breath — commas for short pauses, an em-dash for a beat, an ellipsis for a "
    "longer one — and vary your sentence length. Spell numbers and dates as you'd say them. "
    "Structure the script as one- or two-sentence blocks separated by blank lines.",
    "Lead with one plain, owned reaction, then one concrete grounded detail you can actually "
    "point to — a flat true sentence beats an impressive one. At most one vivid detail; never "
    "an adjective pile. Talk to one listener, never a crowd. Hook, then body, then a clean exit.",
)


def ear_writing_rails() -> Tuple[str, ...]:
    """The Group PS ear-writing RAILS as live-prompt blocks (REQ-PS-001..005). The SINGLE
    SOURCE PV carries IN the talk prompt (REQ-PV-002/004 reference these rails). Returns a copy
    so a caller cannot mutate the source tuple's backing."""
    return tuple(_RAILS)


# =====================================================================================
# The aggregate ear-writing Tier-1 lint (rides the PG-005 gate via grounding.tier1_lint).
# =====================================================================================

@dataclass
class EarLintContext:
    """The per-break context the PS Tier-1 lint needs beyond the script. All optional so a
    sparse context degrades to the always-safe subset. Presence of this context (not None) is
    what opts a break into the PS lints riding the PG-005 gate; absent => the gate is byte-
    identical to the Group PG/PV form."""

    max_words: int = MAX_WORDS_PER_SENTENCE
    max_sentences_per_block: int = MAX_SENTENCES_PER_BLOCK
    # When False, the rhythm/variation lints (REQ-PS-003) are skipped (they are the softer,
    # Medium-priority checks); the HARD rails (PS-001/002/004) always run. TUNABLE.
    check_rhythm: bool = True
    check_numbers: bool = True


def ear_tier1_lint(script: str, ctx: Optional["EarLintContext"] = None) -> List[str]:
    """The aggregate Group PS Tier-1 deterministic lint (REQ-PS-001..005). Empty == clean.

    Runs the HARD ear-writing rails — over-long sentences (PS-001), missing contractions +
    crowd address (PS-002), oversized blocks (PS-004) — plus the softer rhythm checks
    (PS-003 breath punctuation + monotone length) and the raw-digit check (PS-005 (a)) when
    enabled. LLM-FREE and fully testable. RIDES the Group PG-005 Tier-1 gate via the optional
    ``ear_ctx`` hook in ``grounding.tier1_lint`` (so with no PS context the PG gate is byte-
    identical). The IPA override (PS-005 (b)) is a generator capability, not a script lint."""
    ctx = ctx or EarLintContext()
    violations: List[str] = []
    violations += scan_long_sentences(script, ctx.max_words)          # REQ-PS-001
    violations += scan_missing_contractions(script)                   # REQ-PS-002 (a)
    violations += scan_crowd_address(script)                          # REQ-PS-002 (b)
    violations += scan_block_structure(script, ctx.max_sentences_per_block)  # REQ-PS-004
    if ctx.check_rhythm:
        violations += scan_breath_punctuation(script)                # REQ-PS-003 (a)
        violations += scan_monotone_length(script)                   # REQ-PS-003 (b)
    if ctx.check_numbers:
        violations += scan_raw_digits(script)                        # REQ-PS-005 (a)
    return violations


def _clip(text: str, max_chars: int = 48) -> str:
    """Clip a sentence for a violation message (keep messages short + readable)."""
    s = " ".join(str(text or "").split())
    return s if len(s) <= max_chars else s[: max_chars - 1].rstrip() + "…"
