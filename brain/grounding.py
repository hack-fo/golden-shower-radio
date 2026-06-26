"""Grounded host voice & two-tier quality gate (SPEC-RADIO-PROGRAMMING-007 Group PG).

This module OWNS the enforcement layer that keeps the on-air host knowledgeable but
honest. It is the load-bearing grounding gate the other groups reference as "the PG-005
forbidden-fact gate". It is deliberately a DETERMINISTIC, LLM-free core (so the whole
gate is testable without a live model) plus one thin injectable seam for the Tier-2
adversarial self-check.

What it implements (every Group PG requirement):

  REQ-PG-001  the closed-world FACT CONTRACT — exactly ONE fact bundle (a verified
              TrackContext + optional sourced ShowPrep facts) is the ONLY allowed source
              of fact for a break. ``FactContract`` wraps the talk-context bundle and
              exposes ``fact_tokens()`` (the permitted factual tokens) — the rail the
              forbidden-fact scan checks against.
  REQ-PG-002  the GROUNDING RULE — speak only from context; a fact absent from the
              contract is forbidden. Perceptual audio description is allowed; named
              factual attribution only if in context. Enforced mechanically by the
              forbidden-fact + quote-sourcing scans below.
  REQ-PG-003  COMPARISON DISCIPLINE — grounded comparisons only (similar_artists
              match_score >= ~0.6, a shared genre/tag, or a ShowPrep relation), fusion
              formulas ("X sounds like A meets B", "lovechild of") BANNED, at most one
              comparison per break.
  REQ-PG-004  the ANTI-SLOP REGISTER — banned music-slop + LLM-tells + banned
              constructions (negative-parallelism, rule-of-three adjective piles).
  REQ-PG-005  the TWO-TIER QUALITY GATE — Tier-1 deterministic lint (anti-slop +
              forbidden-fact + comparison + quote-sourcing) and Tier-2 adversarial LLM
              self-check. On FAIL: regenerate once; a second FAIL SKIPS the break. Never
              ships a FAIL. ``run_gate`` is the orchestration.
  REQ-PG-006  the per-persona VOICE CARD injected on every call — knowledgeable, dry,
              understated, length-capped, opinion only about the audible.
  REQ-PG-007  the episode-level Tier-3 COHERENCE gate for long-form — arc-beats-in-order,
              cross-segment non-contradiction, persona-charter consistency; on a second
              FAIL the whole episode is DEFERRED, never aired incoherent.
  REQ-PG-008  the QUOTE-SOURCING lint — an attributed quote needs source_url + speaker +
              date or it is a FAIL/dropped; verbatim lyrics are NOT gated.

Tunables (the banned lists, thresholds, the attempt bound, the voice-card traits) are
module-level constants per the SPEC ("the list is tunable; that a banned register is
rejected is the rail"). The behaviour rails are fixed: never ship a FAIL, grounded-only,
fusion-formula ban, lyrics-not-gated, silence beats a wrong fact.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Set

# Group PC (SPEC-RADIO-PROGRAMMING-007) is the AUTHORITATIVE owner of the REQ-PC-004 banned
# radio-filler list. This module READS it (single source of truth, no forked copy / drift).
from . import playbook as _pc

# =====================================================================================
# REQ-PG-004 — the anti-slop register (TUNABLE config; that it is rejected is the rail).
# =====================================================================================

# Music-slop phrases + LLM-tells. Matched case-insensitively as substrings/word-boundary
# tokens. The list is the SPEC's named set plus its siblings; it is config, not a rail.
# The CLICHE RADIO FILLER half (REQ-PV-006 / REQ-PC-004 firewall) is REFERENCED — not forked —
# from the Group PC-004 single source (``brain.playbook.BANNED_PHRASES``), so the cheese
# register has ONE owner (REQ-PC-004 supplies the filler list; this module owns only the
# music-slop half). The two are merged + de-duplicated below.
_MUSIC_SLOP_PHRASES: tuple = (
    # music-slop (REQ-PG-004)
    "sonic journey",
    "lush soundscapes",
    "lush soundscape",
    "effortlessly blends",
    "effortlessly blend",
    "a testament to",
    "needs no introduction",
    "sonic landscape",
    "aural journey",
    "tour de force",
    "auditory feast",
)

# REQ-PC-004 cliche radio filler — read from the Group PC single source (no fork).
BANNED_PHRASES: tuple = _MUSIC_SLOP_PHRASES + tuple(
    p for p in _pc.BANNED_PHRASES if p not in _MUSIC_SLOP_PHRASES
)

# LLM-tell single words (matched on word boundaries). "delve/leverage/elevate" are the
# canonical tells named in REQ-PG-004.
BANNED_WORDS: tuple = (
    "delve",
    "leverage",
    "elevate",
    "elevates",
    "elevating",
    "tapestry",
    "testament",
)

# REQ-PG-004 banned CONSTRUCTIONS: negative-parallelism ("it's not just X, it's Y") and
# the rule-of-three adjective pile. These are structural, matched by regex.
# Negative-parallelism: "not just ... , it's / but ..." (the classic LLM cadence).
_NEGATIVE_PARALLELISM = re.compile(
    r"\bit'?s not just\b[^.?!]{1,60}?[,]\s*it'?s\b", re.IGNORECASE
)
_NEGATIVE_PARALLELISM_ALT = re.compile(
    r"\bnot (?:just|merely|only)\b[^.?!]{1,60}?\bbut (?:also|rather)\b", re.IGNORECASE
)
# Rule-of-three adjective pile: "warm, hazy, and hypnotic" — three comma-separated
# adjective-ish words ending in "and <word>". A heuristic (one idea/break, REQ-PG-004).
_RULE_OF_THREE = re.compile(
    r"\b(\w+),\s+(\w+),\s+and\s+(\w+)\b", re.IGNORECASE
)

# REQ-PG-003 fusion-formula comparisons — ALWAYS banned (a fixed rail, never grounded-OK).
_FUSION_FORMULAS = (
    re.compile(r"\bsounds? like\b[^.?!]{1,40}?\bmeets\b", re.IGNORECASE),
    re.compile(r"\blovechild of\b", re.IGNORECASE),
    re.compile(r"\b(?:cross|mix|blend) between\b[^.?!]{1,40}?\band\b", re.IGNORECASE),
    re.compile(r"\bif\b[^.?!]{1,30}?\bhad a baby with\b", re.IGNORECASE),
)

# REQ-PG-003 generic comparison triggers (grounded-only, counted for the one-per-break cap).
_COMPARISON_TRIGGERS = (
    re.compile(r"\bsounds? like\b", re.IGNORECASE),
    re.compile(r"\breminiscent of\b", re.IGNORECASE),
    re.compile(r"\bin the vein of\b", re.IGNORECASE),
    re.compile(r"\bchannels?\b", re.IGNORECASE),
    re.compile(r"\bif you (?:like|love)\b", re.IGNORECASE),
)

# REQ-PG-008 attributed-speech triggers (TUNABLE). A quote near one of these is gated.
_QUOTE_ATTRIBUTION_TRIGGERS = (
    re.compile(r"\b(\w[\w .'-]{1,40}?)\s+(?:said|told|recalled|explained|put it)\b", re.IGNORECASE),
    re.compile(r"\bin an interview\b", re.IGNORECASE),
    re.compile(r"\baccording to\b", re.IGNORECASE),
    re.compile(r"\bin the liner notes\b", re.IGNORECASE),
    re.compile(r"\bonce (?:said|put it)\b", re.IGNORECASE),
)

# A quoted phrase (straight or curly quotes). Used to find candidate attributed quotes.
_QUOTED = re.compile(r"[\"“‘]([^\"”’]{3,})[\"”’]")

# A 4-digit year token (1000-2999) — the deterministic forbidden-fact spine (REQ-PG-005).
_YEAR_TOKEN = re.compile(r"\b(1\d{3}|2\d{3})\b")

# REQ-PG-003 grounding threshold (TUNABLE): a similar_artists match_score at/above this
# grounds a comparison.
COMPARISON_MATCH_FLOOR = 0.6
# REQ-PG-003 one-comparison-per-break cap (TUNABLE).
MAX_COMPARISONS_PER_BREAK = 1
# REQ-PG-005 attempt bound (TUNABLE): regenerate once, then skip.
MAX_REGENERATE_ATTEMPTS = 1


# =====================================================================================
# REQ-PG-001 — the closed-world fact contract.
# =====================================================================================

@dataclass
class FactContract:
    """The ONE closed-world fact bundle handed to the talk LLM (REQ-PG-001).

    This is the rail, not the fact source: its values come from the talk-context bundle
    (a TrackContext assembled from ANALYSIS-006 + optional ShowPrep facts from
    KNOWLEDGE-008). The contract's job is to expose ``fact_tokens()`` — the closed set of
    factual tokens that MAY appear in host copy — so the forbidden-fact scan (REQ-PG-005)
    can reject any year/album/personnel token NOT present here. The bundle is the ONLY
    permitted source of fact; the host draws no facts from free-recall.
    """

    # Identity of the just-played / current track (always airable — it is on air now).
    artist: str = ""
    title: str = ""
    album: str = ""
    year: Optional[int] = None
    genres: List[str] = field(default_factory=list)
    folksonomy_tags: List[str] = field(default_factory=list)
    mood: str = ""
    energy: str = ""
    bpm: str = ""
    musical_key: str = ""
    sonic_character: List[str] = field(default_factory=list)
    # similar_artists: [{"name": str, "match_score": float}] (ANALYSIS-006 edges).
    similar_artists: List[Dict[str, Any]] = field(default_factory=list)
    prior_track: str = ""
    # The next item is a MOOD hint, NOT a name (REQ-PG-001 / REQ-PV-007).
    next_mood: str = ""
    # KNOWLEDGE-008 grounded facts: [{"predicate","value","certain","hedge","sources",...}].
    grounded_facts: List[Dict[str, Any]] = field(default_factory=list)
    # KNOWLEDGE-008 relations: [{"rel","target",...}] — real edges only.
    grounded_relations: List[Dict[str, Any]] = field(default_factory=list)
    # ShowPrep / sourced quotes: [{"value"/"quote","source_url","speaker","date"}].
    showprep_facts: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_context(cls, context: Dict[str, Any]) -> "FactContract":
        """Assemble the closed-world contract from a talk-context dict (the bundle the
        existing _build_talk_prompt already consumes). Empty-safe: a sparse context yields
        a near-empty contract whose only airable facts are the on-air track identity."""
        ctx = context or {}
        year = ctx.get("last_year")
        try:
            year_int = int(str(year).strip()) if year not in (None, "") else None
            if year_int is not None and year_int <= 0:
                year_int = None
        except (TypeError, ValueError):
            year_int = None
        return cls(
            artist=str(ctx.get("last_artist") or "").strip(),
            title=str(ctx.get("last_title") or "").strip(),
            album=str(ctx.get("last_album") or "").strip(),
            year=year_int,
            genres=[str(g).strip() for g in (ctx.get("genres") or []) if str(g).strip()],
            folksonomy_tags=[str(t).strip() for t in (ctx.get("folksonomy_tags") or [])
                             if str(t).strip()],
            mood=str(ctx.get("mood") or "").strip(),
            energy=str(ctx.get("energy") or "").strip(),
            bpm=str(ctx.get("bpm") or "").strip(),
            musical_key=str(ctx.get("musical_key") or "").strip(),
            sonic_character=[str(s).strip() for s in (ctx.get("sonic_character") or [])
                             if str(s).strip()],
            similar_artists=[a for a in (ctx.get("similar_artists") or [])
                             if isinstance(a, dict)],
            prior_track=str(ctx.get("prior_track") or "").strip(),
            next_mood=str(ctx.get("next_mood") or "").strip(),
            grounded_facts=[f for f in (ctx.get("grounded_facts") or []) if isinstance(f, dict)],
            grounded_relations=[r for r in (ctx.get("grounded_relations") or [])
                                if isinstance(r, dict)],
            showprep_facts=[s for s in (ctx.get("showprep_facts") or []) if isinstance(s, dict)],
        )

    # -- the closed-world token set the forbidden-fact scan checks against ----------

    def year_tokens(self) -> Set[str]:
        """The set of YEAR tokens present in the contract (REQ-PG-005 forbidden-fact spine).

        Includes the track's own year plus any 4-digit year embedded in a grounded /
        ShowPrep fact value. A year in host copy that is NOT in this set is a FAIL — and a
        year that DISAGREES with the track year is the canonical confident-wrong-fact."""
        out: Set[str] = set()
        if self.year:
            out.add(str(self.year))
        for f in self.grounded_facts:
            for m in _YEAR_TOKEN.finditer(str(f.get("value") or "")):
                out.add(m.group(1))
        for s in self.showprep_facts:
            blob = " ".join(str(s.get(k) or "") for k in ("value", "quote", "date"))
            for m in _YEAR_TOKEN.finditer(blob):
                out.add(m.group(1))
        return out

    def fact_tokens(self) -> Set[str]:
        """The lower-cased closed set of all factual TEXT tokens the host may state — the
        airable vocabulary (REQ-PG-001). Used by the named-attribution check: a producer /
        label / personnel name in host copy must be drawn from here."""
        toks: Set[str] = set()

        def _add(text: str) -> None:
            for w in re.findall(r"[A-Za-z0-9&']+", str(text or "").lower()):
                if len(w) >= 2:
                    toks.add(w)

        for s in (self.artist, self.title, self.album, self.mood, self.energy,
                  self.bpm, self.musical_key, self.prior_track):
            _add(s)
        for lst in (self.genres, self.folksonomy_tags, self.sonic_character):
            for item in lst:
                _add(item)
        for a in self.similar_artists:
            _add(a.get("name", ""))
        for f in self.grounded_facts:
            _add(f.get("value", ""))
            _add(f.get("predicate", ""))
        for r in self.grounded_relations:
            _add(r.get("target", ""))
        for s in self.showprep_facts:
            for k in ("value", "quote", "speaker", "source_url", "date"):
                _add(s.get(k, ""))
        return toks

    def grounded_comparison_names(self) -> Set[str]:
        """The lower-cased set of artist names a comparison MAY reference (REQ-PG-003):
        a similar_artists entry whose match_score >= the floor, plus any relation target.
        A comparison naming an artist NOT in this set (and not sharing a tag/genre) is
        ungrounded."""
        out: Set[str] = set()
        for a in self.similar_artists:
            try:
                score = float(a.get("match_score", 0.0))
            except (TypeError, ValueError):
                score = 0.0
            name = str(a.get("name") or "").strip().lower()
            if name and score >= COMPARISON_MATCH_FLOOR:
                out.add(name)
        for r in self.grounded_relations:
            target = str(r.get("target") or "").strip().lower()
            if target:
                out.add(target)
        return out

    def shared_tags(self) -> Set[str]:
        """Lower-cased genres + folksonomy tags — a comparison is grounded if the named
        artist demonstrably shares one of these (REQ-PG-003 (b))."""
        return {t.strip().lower() for t in (self.genres + self.folksonomy_tags) if t.strip()}


# =====================================================================================
# Gate result type.
# =====================================================================================

@dataclass
class GateResult:
    """The outcome of a gate check. ``passed`` False means the script must NOT ship as-is
    (regenerate or skip per REQ-PG-005). ``violations`` lists the specific reasons (for the
    log + the regenerate feedback)."""

    passed: bool
    violations: List[str] = field(default_factory=list)
    tier: str = ""

    def __bool__(self) -> bool:  # truthy == passed, so callers can `if result:`
        return self.passed


# =====================================================================================
# REQ-PG-004 — anti-slop scan (Tier-1 component).
# =====================================================================================

def scan_anti_slop(text: str) -> List[str]:
    """Return the list of anti-slop violations in ``text`` (REQ-PG-004). Empty == clean.

    Catches banned music-slop phrases, LLM-tell words, negative-parallelism, and the
    rule-of-three adjective pile. Deterministic and LLM-free."""
    if not text:
        return []
    violations: List[str] = []
    low = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase in low:
            violations.append(f"banned-phrase: {phrase}")
    for word in BANNED_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", low):
            violations.append(f"banned-word: {word}")
    if _NEGATIVE_PARALLELISM.search(text) or _NEGATIVE_PARALLELISM_ALT.search(text):
        violations.append("banned-construction: negative-parallelism")
    m = _RULE_OF_THREE.search(text)
    if m and _looks_like_adjective_pile(m):
        violations.append("banned-construction: rule-of-three")
    return violations


def scan_word_minimum(script: str, min_words: int) -> List[str]:
    """Return a violation when ``script`` is below ``min_words`` total words (REQ-OF-006).

    0 (the default) == no minimum — byte-identical to before Group OF. Empty list == passes.
    The check rides the existing Tier-1 gate: a too-short script is regenerated once and, if
    still too short, the break is SKIPPED rather than aired (graceful-skip, never-block)."""
    if min_words <= 0 or not script:
        return []
    word_count = len(script.split())
    if word_count < min_words:
        return [f"word-minimum: {word_count} words < required {min_words}"]
    return []


def _looks_like_adjective_pile(match: "re.Match") -> bool:
    """A rule-of-three is slop only when it reads as an ADJECTIVE pile (warm, hazy, and
    hypnotic), not a plain list of nouns (drums, bass, and guitar). Heuristic: reject the
    match if any of the three is a common structural / list word so we don't over-flag."""
    structural = {"and", "or", "the", "a", "an", "it", "you", "we", "drums", "bass",
                  "guitar", "vocals", "keys", "synths", "strings", "horns"}
    words = [match.group(1).lower(), match.group(2).lower(), match.group(3).lower()]
    return not any(w in structural for w in words)


# =====================================================================================
# REQ-PG-005 / REQ-PG-002 — forbidden-fact scan (the mechanical guard).
# =====================================================================================

def scan_forbidden_facts(text: str, contract: FactContract) -> List[str]:
    """Return forbidden-fact violations (REQ-PG-005 Tier-1 / REQ-PG-002). Empty == clean.

    THE deterministic spine: every YEAR token spoken must appear in the fact contract;
    a year NOT in context — especially one that disagrees with the track year — is a FAIL.
    This is the mechanical guard against a confident wrong year (the canonical wrong fact).
    """
    if not text:
        return []
    violations: List[str] = []
    allowed_years = contract.year_tokens()
    for m in _YEAR_TOKEN.finditer(text):
        tok = m.group(1)
        if tok not in allowed_years:
            violations.append(f"forbidden-fact: year {tok} not in context")
    return violations


# =====================================================================================
# REQ-PG-003 — comparison-grounding scan (Tier-1 component).
# =====================================================================================

def scan_comparisons(text: str, contract: FactContract) -> List[str]:
    """Return comparison-discipline violations (REQ-PG-003). Empty == clean.

    Rails: fusion formulas are ALWAYS a FAIL; at most one comparison per break; a named
    comparison must be grounded (a >=0.6 similar_artist, a shared genre/tag, or a relation
    target). A comparison that names no artist (a generic "if you like this") is allowed."""
    if not text:
        return []
    violations: List[str] = []

    # Fusion formulas — always banned (a fixed rail, never grounded-OK).
    for pat in _FUSION_FORMULAS:
        if pat.search(text):
            violations.append("comparison: banned fusion-formula")
            break

    # Count comparison triggers (the one-per-break cap).
    trigger_hits = sum(1 for pat in _COMPARISON_TRIGGERS if pat.search(text))
    if trigger_hits > MAX_COMPARISONS_PER_BREAK:
        violations.append(
            f"comparison: {trigger_hits} comparisons exceed cap {MAX_COMPARISONS_PER_BREAK}"
        )

    # Grounding: if a comparison names an artist, that artist must be grounded.
    if trigger_hits:
        grounded = contract.grounded_comparison_names()
        tags = contract.shared_tags()
        for name in _candidate_compared_artists(text):
            low = name.lower()
            if low in grounded:
                continue
            # A shared genre/tag also grounds it (the artist appears alongside a known tag).
            if any(t in text.lower() for t in tags) and tags:
                continue
            violations.append(f"comparison: ungrounded artist '{name}'")
    return violations


def _candidate_compared_artists(text: str) -> List[str]:
    """Best-effort extraction of artist names that appear right after a comparison trigger
    ("sounds like Artist Y", "in the vein of Artist Z"). A heuristic to catch the common
    case; the Tier-2 adversarial check is the catch-all for the rest."""
    out: List[str] = []
    # Capture a run of Capitalized words (a proper-noun artist name) right after the
    # trigger. We stop at the first lower-case word so trailing prose ("at their iciest")
    # is excluded — an artist name is Capitalized Words, not a sentence tail.
    for pat in (r"sounds? like\s+((?:[A-Z][\w.&']*\s*)+)",
                r"reminiscent of\s+((?:[A-Z][\w.&']*\s*)+)",
                r"in the vein of\s+((?:[A-Z][\w.&']*\s*)+)"):
        for m in re.finditer(pat, text):
            name = m.group(1).strip().rstrip(".,;:!?")
            # Trim a trailing connective that got capitalized at a clause start.
            name = re.sub(r"\s+(?:And|But|Or|Meets|With)$", "", name).strip()
            if name:
                out.append(name)
    return out


# =====================================================================================
# REQ-PG-008 — quote-sourcing lint (Tier-1 component; extends forbidden-fact to quotes).
# =====================================================================================

def scan_quotes(text: str, contract: FactContract) -> List[str]:
    """Return quote-sourcing violations (REQ-PG-008). Empty == clean.

    An ATTRIBUTED quote ("X said '...'", "in an interview ...") is a fact-with-attribution:
    it must carry source_url + speaker + date in the ShowPrep facts or it is a FAIL (the
    quote is dropped / the break skipped). PIVOT: verbatim song LYRICS are NOT gated — a
    quoted phrase with NO attribution trigger nearby is treated as a lyric/aside and passes
    (the lyric is the on-air song itself, not an external claim)."""
    if not text:
        return []
    violations: List[str] = []
    has_attribution = any(pat.search(text) for pat in _QUOTE_ATTRIBUTION_TRIGGERS)
    if not has_attribution:
        return []  # no attributed speech -> lyrics/asides are free (the PIVOT rail)
    quotes = [m.group(1).strip() for m in _QUOTED.finditer(text)]
    if not quotes:
        # An attribution phrase with no actual quote (e.g. "according to the label, it sold
        # well") is still an attributed CLAIM — require a sourced ShowPrep fact to back it.
        if not _has_sourced_showprep(contract):
            violations.append("quote-sourcing: attributed claim with no sourced ShowPrep fact")
        return violations
    for q in quotes:
        if not _quote_is_sourced(q, contract):
            violations.append(f"quote-sourcing: unsourced attributed quote \"{q[:40]}\"")
    return violations


def _has_sourced_showprep(contract: FactContract) -> bool:
    """True if at least one ShowPrep fact carries the full source_url + speaker + date."""
    return any(_showprep_complete(s) for s in contract.showprep_facts)


def _showprep_complete(s: Dict[str, Any]) -> bool:
    return bool(str(s.get("source_url") or "").strip()
                and str(s.get("speaker") or "").strip()
                and str(s.get("date") or "").strip())


def _quote_is_sourced(quote: str, contract: FactContract) -> bool:
    """A quoted phrase is sourced when a ShowPrep fact (a) matches the quoted text AND
    (b) carries source_url + speaker + date. Matching is substring-tolerant (the host may
    paraphrase quote boundaries) so a complete ShowPrep quote grounds it."""
    q_low = quote.lower().strip()
    for s in contract.showprep_facts:
        if not _showprep_complete(s):
            continue
        val = str(s.get("quote") or s.get("value") or "").lower().strip()
        if not val:
            continue
        if q_low in val or val in q_low:
            return True
    return False


# =====================================================================================
# REQ-PG-005 Tier-1 — the deterministic lint (aggregate).
# =====================================================================================

def tier1_lint(script: str, contract: FactContract, pv_ctx: Any = None,
               ear_ctx: Any = None, min_words: int = 0,
               humandj_ctx: Any = None) -> GateResult:
    """Run the full Tier-1 deterministic lint (REQ-PG-005): anti-slop (REQ-PG-004) +
    forbidden-fact (REQ-PG-002) + comparison-grounding (REQ-PG-003) + quote-sourcing
    (REQ-PG-008) + optional word-minimum (REQ-OF-006). LLM-free. PASS == every sub-scan clean.

    ``pv_ctx`` (SPEC-RADIO-PROGRAMMING-007 Group PV) is OPTIONAL and DEFAULTS to None. When
    None the PV part is BYTE-IDENTICAL to the Group PG form (the PV delivery-craft lints do not
    run). When a ``persona_voice.PVLintContext`` is supplied (the host-voice path with PV on)
    the Group PV Tier-1 lints RIDE this gate: the warmth-transition crutch check
    (REQ-PV-010), the blunt-praise validity check (REQ-PV-012/016), and the dated/try-hard-
    slang check (REQ-PV-017).

    ``ear_ctx`` (SPEC-RADIO-PROGRAMMING-007 Group PS) is OPTIONAL and DEFAULTS to None. When
    None the gate is BYTE-IDENTICAL (the ear-writing lints do not run). When an
    ``ear_writing.EarLintContext`` is supplied the Group PS SCRIPT-side ear-writing lints RIDE
    this gate: over-long sentences (REQ-PS-001), missing contractions + crowd address
    (REQ-PS-002), rhythm/breath (REQ-PS-003), oversized blank-line blocks (REQ-PS-004), and raw
    digits (REQ-PS-005). PROGRAMMING owns all these checks; OPS-004 owns the base engine.

    ``min_words`` (OPS-004 Group OF REQ-OF-006): 0 == no minimum (default; byte-identical).
    When > 0, a script below this total word count FAILS and is regenerated like any other
    Tier-1 violation; graceful-skip if still failing after the bounded attempt count."""
    violations: List[str] = []
    violations += scan_word_minimum(script, min_words)      # REQ-OF-006
    violations += scan_anti_slop(script)
    violations += scan_forbidden_facts(script, contract)
    violations += scan_comparisons(script, contract)
    violations += scan_quotes(script, contract)
    if pv_ctx is not None:
        # The PV delivery-craft lints ride the PG-005 Tier-1 gate (REQ-PV-010/012/016/017).
        # Imported lazily so grounding.py carries no hard dependency on the PV module.
        from . import persona_voice as _pv
        violations += _pv.pv_tier1_lint(script, pv_ctx)
    if ear_ctx is not None:
        # The PS script-side ear-writing lints ride the SAME gate (REQ-PS-001..005). Lazy
        # import so grounding.py carries no hard dependency on the ear_writing module.
        from . import ear_writing as _ew
        violations += _ew.ear_tier1_lint(script, ear_ctx)
    if humandj_ctx is not None:
        # The humanizer lint rides the Tier-1 gate (SPEC-RADIO-HOSTVOICE-049 REQ-HL-005). Lazy
        # import so grounding.py carries no hard dependency on humanlint (byte-identical when None).
        from . import humanlint as _hl
        violations += [v.token for v in _hl.scan_ai_slop(script, humandj_ctx)]
    return GateResult(passed=not violations, violations=violations, tier="tier1")


# =====================================================================================
# REQ-PG-005 Tier-2 — the adversarial LLM self-check (injectable seam).
# =====================================================================================

# An adversarial checker is a callable (script, contract) -> list[str]; it returns the
# claims NOT supported by context (empty == all supported). Injecting it keeps the gate
# testable without a live LLM and lets the talk path wire the real LLM self-check in.
AdversarialChecker = Callable[[str, FactContract], List[str]]


def tier2_adversarial(
    script: str,
    contract: FactContract,
    checker: Optional[AdversarialChecker] = None,
) -> GateResult:
    """Run the Tier-2 adversarial self-check (REQ-PG-005). When ``checker`` is None the
    tier is a PASS no-op (the deterministic Tier-1 is the always-on guard; the adversarial
    pass is opt-in because it costs an LLM call). When a checker is supplied it lists every
    factual claim and flags any NOT supported by context; an unsupported claim is a FAIL."""
    if checker is None:
        return GateResult(passed=True, violations=[], tier="tier2")
    try:
        unsupported = checker(script, contract) or []
    except Exception as exc:  # noqa: BLE001 - the adversarial pass must never crash playout
        # Fail-OPEN on a checker fault: Tier-1 already caught the mechanical wrong facts;
        # an LLM-down adversarial pass must not block an otherwise-clean break (never-stops).
        return GateResult(passed=True, violations=[f"tier2-checker-error: {exc}"], tier="tier2")
    unsupported = [str(u).strip() for u in unsupported if str(u).strip()]
    return GateResult(passed=not unsupported,
                      violations=[f"unsupported-claim: {u}" for u in unsupported],
                      tier="tier2")


# =====================================================================================
# REQ-PG-005 — the two-tier gate orchestration (regenerate-once-then-skip).
# =====================================================================================

def run_gate(
    script: str,
    contract: FactContract,
    *,
    regenerate: Optional[Callable[[List[str]], str]] = None,
    adversarial: Optional[AdversarialChecker] = None,
    max_attempts: int = MAX_REGENERATE_ATTEMPTS,
    pv_ctx: Any = None,
    ear_ctx: Any = None,
    min_words: int = 0,
    humandj_ctx: Any = None,
) -> "GateOutcome":
    """The two-tier quality gate with regenerate-once-then-skip (REQ-PG-005 / REQ-OF-006).

    Runs Tier-1 then Tier-2 on ``script``. On a FAIL it calls ``regenerate(violations)``
    (which returns a fresh script) up to ``max_attempts`` times; if the regenerated script
    still FAILS, the break is SKIPPED. [HARD] NEVER ships a script that fails the gate —
    a skipped break keeps music playing (never-stops). Returns a ``GateOutcome`` carrying
    the final airable script (or None to skip) + the last GateResult + the attempt count.

    ``min_words`` (REQ-OF-006): 0 == no word-count minimum (default; byte-identical).
    With ``regenerate`` None there is no second attempt: a first FAIL goes straight to SKIP.
    """
    # @MX:ANCHOR: [AUTO] never-ship-a-FAIL is the fixed rail (REQ-PG-005 / REQ-OF-006)
    # @MX:REASON: this orchestration is THE guard that a script failing the two-tier gate
    #   never reaches air. Every talk break (and, via run_episode_gate, every long-form
    #   episode) funnels through this contract. A change that returns a failing script here
    #   would air a confident wrong fact — the exact failure mode the whole group prevents.
    attempts = 0
    current = script
    last_result = _check_once(current, contract, adversarial, pv_ctx, ear_ctx, min_words, humandj_ctx)
    while not last_result.passed and regenerate is not None and attempts < max_attempts:
        attempts += 1
        fresh = regenerate(list(last_result.violations))
        if not fresh:
            # Regeneration itself produced nothing -> skip (cannot ship a FAIL).
            return GateOutcome(script=None, result=last_result, attempts=attempts, skipped=True)
        current = fresh
        last_result = _check_once(current, contract, adversarial, pv_ctx, ear_ctx, min_words, humandj_ctx)
    if last_result.passed:
        return GateOutcome(script=current, result=last_result, attempts=attempts, skipped=False)
    # Still failing after the bounded retries -> SKIP (never ship a FAIL).
    return GateOutcome(script=None, result=last_result, attempts=attempts, skipped=True)


def _check_once(script: str, contract: FactContract,
                adversarial: Optional[AdversarialChecker],
                pv_ctx: Any = None, ear_ctx: Any = None,
                min_words: int = 0, humandj_ctx: Any = None) -> GateResult:
    """One pass of both tiers; the aggregate FAILS if any tier fails. With ``pv_ctx`` the
    Group PV Tier-1 lints ride Tier-1 and the PV deterministic Tier-2 smuggled-token scan
    (REQ-PV-016) rides Tier-2 (it runs LLM-free, alongside the adversarial pass). With
    ``ear_ctx`` the Group PS script-side ear-writing lints (REQ-PS-001..005) ride Tier-1.
    With ``min_words`` > 0, the REQ-OF-006 word-minimum check rides Tier-1."""
    t1 = tier1_lint(script, contract, pv_ctx, ear_ctx, min_words, humandj_ctx)
    if not t1.passed:
        return t1
    t2 = tier2_adversarial(script, contract, adversarial)
    if not t2.passed:
        return t2
    if pv_ctx is not None:
        from . import persona_voice as _pv
        smuggled = _pv.pv_tier2_lint(script, pv_ctx)
        if smuggled:
            return GateResult(passed=False,
                              violations=[f"unsupported-claim: {s}" for s in smuggled],
                              tier="tier2")
    return t2


@dataclass
class GateOutcome:
    """The result of running the two-tier gate: the airable script (or None to SKIP the
    break), the final GateResult, the regenerate-attempt count, and whether it skipped."""

    script: Optional[str]
    result: GateResult
    attempts: int = 0
    skipped: bool = False


# =====================================================================================
# REQ-PG-006 — the per-persona voice card (injected on every call).
# =====================================================================================

# The house voice card: knowledgeable, dry, understated, mild opinions, restraint, no
# gushing, talks like a person. TUNABLE wording; that a consistent, length-capped card is
# injected every call is the rail. Opinion ONLY about the audible (REQ-PG-002 / REQ-PG-006).
VOICE_CARD = (
    "Voice: a knowledgeable music head, dry and understated. Mild opinions, plainly stated. "
    "Restraint over gushing. Talk like a real person to one listener, not a crowd. "
    "You may have a genuine opinion about how the track SOUNDS (the audible) — never about a "
    "fact you cannot point to in your notes. Say little well rather than much."
)

# REQ-PG-006 HARD length cap (over-explaining is itself slop). Characters; TUNABLE value.
VOICE_CARD_MAX_CHARS = 400


def voice_card_for(persona: Any = None) -> str:
    """The per-persona VOICE CARD injected into EVERY talk-generation call (REQ-PG-006).

    Returns the SAME card for a given persona every call (consistency is the rail). The
    base card is the house voice; an active persona appends its authored POV (its own
    voice colour) — drawn ONLY from the persona's authored fields, never fabricated. The
    result is HARD length-capped (over-explaining is slop): a card longer than the cap is
    truncated at a word boundary."""
    card = VOICE_CARD
    if persona is not None:
        pov = str(getattr(persona, "pov_seed", "") or "").strip()
        name = str(getattr(persona, "display_name", "") or "").strip()
        extra = ""
        if name:
            extra += f" You are {name}."
        if pov:
            extra += f" Your standing point of view: {pov}"
        card = (card + extra).strip()
    return _cap_length(card, VOICE_CARD_MAX_CHARS)


# REQ-PV-009 extended-card length cap: the PV delivery-craft card carries more (energy band,
# pacing, register, tics, banter fields) so it gets a larger cap than the bare PG-006 card —
# but still HARD-capped (over-explaining is itself slop). TUNABLE.
PV_VOICE_CARD_MAX_CHARS = 900


def pv_voice_card_for(persona: Any = None, daypart: str = "") -> str:
    """The EXTENDED per-persona voice card (SPEC-RADIO-PROGRAMMING-007 REQ-PV-009).

    COMPOSES the Group PG-006 ``voice_card_for`` (the base knowledgeable/dry/understated card)
    with the Group PV delivery-craft fields — the per-daypart ENERGY BAND (REQ-PV-003), the
    PACING SIGNATURE, the REGISTER, and the disjoint VERBAL-TIC BANK (used sparingly) — drawn
    ONLY from the persona's authored VoiceCard (never fabricated). With ``persona`` None it
    returns the bare PG-006 house card unchanged, so the unhosted path is byte-identical to
    Group PG. Identical each call for consistency; HARD length-capped (over-explaining is slop).
    The card supplies delivery SHAPE + opinion-about-the-audible only — never a fact, never new
    claim-making latitude (grounding REQ-PG-002 untouched)."""
    base = voice_card_for(persona)
    from . import persona_voice as _pv
    from . import persona_identity as _pi
    card = _pv.card_for(persona)
    parts: List[str] = [base]
    # The FROZEN ANCHOR BLOCK (SPEC-RADIO-PROGRAMMING-007 REQ-PI-001): the persona's immutable
    # identity anchors, stated IDENTICALLY each call (consistency is the rail) so the host stays
    # recognizably ITSELF while the evolvable delivery below tunes within the distinctness rails.
    # Only renders for an active persona (the unhosted/house path carries no distinct anchors),
    # so the persona=None path stays byte-identical to Group PG.
    if persona is not None:
        block = _pi.AnchorBlock.for_persona(persona)
        focuses = [a for a in block.anchor_focuses if str(a).strip()]
        if focuses:
            parts.append("Your permanent identity anchors (these never change, every show): "
                         + "; ".join(focuses) + ".")
        if block.core_temperament and block.core_temperament not in base:
            parts.append(f"Core temperament: {block.core_temperament}.")
    # The per-daypart energy band (REQ-PV-003) is a delivery-craft rail that applies even on
    # the unhosted/house path (it is daypart-calibrated, not persona-specific) — so it is
    # injected whenever PV is on, persona or not. The persona-specific lines (pacing, register,
    # tics) below only render for an active persona.
    band = _pv.energy_band_for_daypart(daypart or "midday", card.energy_band)
    if band:
        parts.append(f"Delivery energy now ({daypart or 'midday'}): {band} — energy is a "
                     "WRITING property (rhythm, specifics, block length), never exclamation or hype.")
    if card.pacing_signature:
        parts.append(f"Pacing signature: {card.pacing_signature}.")
    if card.register:
        parts.append(f"Register: {card.register}.")
    tics = [t for t in card.verbal_tic_bank if t.strip()]
    if tics:
        parts.append("Your signature warmth-transitions (use AT MOST ONE per break, never the "
                     "same one two breaks running): " + "; ".join(tics) + ".")
    return _cap_length(" ".join(parts), PV_VOICE_CARD_MAX_CHARS)


def _cap_length(text: str, max_chars: int) -> str:
    """Hard-cap ``text`` at ``max_chars``, trimming at the last word boundary so the card
    never ends mid-word (REQ-PG-006 length cap)."""
    if len(text) <= max_chars:
        return text
    clipped = text[:max_chars]
    cut = clipped.rfind(" ")
    if cut > 0:
        clipped = clipped[:cut]
    return clipped.rstrip()


# =====================================================================================
# REQ-PG-007 — the episode-level Tier-3 coherence gate for long-form.
# =====================================================================================

@dataclass
class EpisodeSegment:
    """One segment of an assembled long-form episode (REQ-PG-007). ``beat`` is the planned
    narrative beat this segment realises; ``text`` is its host script; ``persona_id`` is
    the narrating persona (for the charter-consistency check)."""

    beat: str
    text: str
    persona_id: str = ""


def episode_coherence_gate(
    segments: Sequence[EpisodeSegment],
    plan_beats: Sequence[str],
    contract: FactContract,
    *,
    persona_anchor: Optional[Dict[str, Any]] = None,
) -> GateResult:
    """The episode-level Tier-3 COHERENCE gate (REQ-PG-007). Runs ABOVE the unchanged
    per-break Tier-1/Tier-2 gate (which still runs on every segment separately).

    Three checks, all [HARD]:
      (a) ARC-BEATS-IN-ORDER — the segments' beats appear in the planned order with none
          missing or duplicated.
      (b) CROSS-SEGMENT NON-CONTRADICTION — no segment states a year/date that contradicts
          another segment (or the episode fact contract): the same fact must not be told
          two different ways across the episode.
      (c) PERSONA-CHARTER CONSISTENCY — every segment is narrated by the SAME persona, and
          (when an anchor is supplied) that persona matches the frozen anchor.
    PASS == all three clean. The caller regenerates the failing segment once, then DEFERS
    the whole episode on a second FAIL (never airs incoherent)."""
    violations: List[str] = []
    violations += _check_arc_order(segments, plan_beats)
    violations += _check_cross_segment_contradiction(segments, contract)
    violations += _check_persona_consistency(segments, persona_anchor)
    return GateResult(passed=not violations, violations=violations, tier="tier3")


def _check_arc_order(segments: Sequence[EpisodeSegment], plan_beats: Sequence[str]) -> List[str]:
    """(a) The realised beats must equal the planned beats in order — none missing,
    duplicated, or reordered (REQ-PG-007 (a))."""
    planned = [str(b).strip() for b in plan_beats if str(b).strip()]
    if not planned:
        return []  # no plan supplied -> nothing to order-check
    realised = [str(s.beat).strip() for s in segments if str(s.beat).strip()]
    if realised != planned:
        # Distinguish the common failure shapes for a useful regenerate hint.
        if sorted(realised) == sorted(planned):
            return [f"arc-order: beats out of order (got {realised}, planned {planned})"]
        missing = [b for b in planned if b not in realised]
        dup = [b for b in realised if realised.count(b) > 1]
        msg = "arc-order: "
        if missing:
            msg += f"missing {missing} "
        if dup:
            msg += f"duplicated {sorted(set(dup))} "
        if not missing and not dup:
            msg += f"got {realised}, planned {planned}"
        return [msg.strip()]
    return []


def _check_cross_segment_contradiction(
    segments: Sequence[EpisodeSegment], contract: FactContract
) -> List[str]:
    """(b) No two segments may state a contradicting year for the same context. The
    canonical case (B-24): segment 2 says the debut album year is 1991 and segment 4 says
    1989. We flag when the episode's spoken year tokens are mutually inconsistent against
    the contract: a year in one segment that is NOT a contract year, while another segment
    speaks a different year, is a contradiction (REQ-PG-007 (b))."""
    allowed = contract.year_tokens()
    spoken: Dict[str, int] = {}
    for seg in segments:
        for m in _YEAR_TOKEN.finditer(seg.text or ""):
            spoken[m.group(1)] = spoken.get(m.group(1), 0) + 1
    # Years spoken across the episode that are NOT grounded in the contract.
    ungrounded_years = [y for y in spoken if y not in allowed]
    violations: List[str] = []
    # Two or more DIFFERENT ungrounded years for the same subject => a contradiction
    # (they cannot both be right and neither is grounded).
    if len(ungrounded_years) >= 2:
        violations.append(
            f"cross-segment: contradicting ungrounded years {sorted(ungrounded_years)}"
        )
    elif ungrounded_years and allowed:
        # One ungrounded year that disagrees with a grounded one is also a contradiction.
        violations.append(
            f"cross-segment: year {ungrounded_years[0]} contradicts context {sorted(allowed)}"
        )
    return violations


def _check_persona_consistency(
    segments: Sequence[EpisodeSegment], persona_anchor: Optional[Dict[str, Any]]
) -> List[str]:
    """(c) Every segment must be narrated by the same persona, consistent with the frozen
    anchor (REQ-PG-007 (c) / coordinates with REQ-PI-001 + REQ-PR-005). A segment whose
    persona_id differs from the rest (or from the supplied anchor id) breaks the persistent
    returning-person rail."""
    ids = [str(s.persona_id).strip() for s in segments if str(s.persona_id).strip()]
    if not ids:
        return []
    distinct = set(ids)
    violations: List[str] = []
    if len(distinct) > 1:
        violations.append(f"persona-consistency: mixed narrators {sorted(distinct)}")
    if persona_anchor:
        anchor_id = str(persona_anchor.get("id") or persona_anchor.get("persona_id") or "").strip()
        if anchor_id and any(i != anchor_id for i in distinct):
            violations.append(
                f"persona-consistency: narrator {sorted(distinct)} != anchor {anchor_id}"
            )
    return violations


def run_episode_gate(
    segments: List[EpisodeSegment],
    plan_beats: Sequence[str],
    contract: FactContract,
    *,
    regenerate_segment: Optional[Callable[[int, List[str]], Optional[str]]] = None,
    persona_anchor: Optional[Dict[str, Any]] = None,
    max_attempts: int = MAX_REGENERATE_ATTEMPTS,
) -> "EpisodeOutcome":
    """Orchestrate the episode-level gate (REQ-PG-007): run the Tier-3 coherence gate; on a
    FAIL regenerate the FAILING segment once (via ``regenerate_segment(index, violations)``);
    on a second FAIL DEFER the whole episode (return aired=False) so regular programming
    keeps playing — never airs an incoherent long-form piece. [HARD] An episode that fails
    the Tier-3 gate NEVER airs."""
    work = list(segments)
    attempts = 0
    result = episode_coherence_gate(work, plan_beats, contract, persona_anchor=persona_anchor)
    while not result.passed and regenerate_segment is not None and attempts < max_attempts:
        attempts += 1
        idx = _first_failing_segment_index(work, plan_beats, contract, persona_anchor)
        if idx is None:
            break
        fresh = regenerate_segment(idx, list(result.violations))
        if not fresh:
            break
        work[idx] = EpisodeSegment(beat=work[idx].beat, text=fresh,
                                   persona_id=work[idx].persona_id)
        result = episode_coherence_gate(work, plan_beats, contract,
                                        persona_anchor=persona_anchor)
    if result.passed:
        return EpisodeOutcome(segments=work, result=result, attempts=attempts, aired=True)
    return EpisodeOutcome(segments=None, result=result, attempts=attempts, aired=False)


def _first_failing_segment_index(
    segments: Sequence[EpisodeSegment], plan_beats: Sequence[str],
    contract: FactContract, persona_anchor: Optional[Dict[str, Any]]
) -> Optional[int]:
    """Pick the segment to regenerate: the first one carrying an ungrounded year, else the
    first whose beat is out of planned order, else the first whose narrator diverges."""
    allowed = contract.year_tokens()
    for i, seg in enumerate(segments):
        for m in _YEAR_TOKEN.finditer(seg.text or ""):
            if m.group(1) not in allowed:
                return i
    planned = [str(b).strip() for b in plan_beats if str(b).strip()]
    for i, seg in enumerate(segments):
        if i < len(planned) and str(seg.beat).strip() != planned[i]:
            return i
    ids = [str(s.persona_id).strip() for s in segments]
    if len(set(i for i in ids if i)) > 1:
        # Regenerate the minority narrator's first segment.
        from collections import Counter
        counts = Counter(i for i in ids if i)
        majority = counts.most_common(1)[0][0]
        for i, pid in enumerate(ids):
            if pid and pid != majority:
                return i
    return 0 if segments else None


@dataclass
class EpisodeOutcome:
    """The result of the episode-level gate: the airable segment list (or None to DEFER the
    whole episode), the final GateResult, the attempt count, and whether it airs."""

    segments: Optional[List[EpisodeSegment]]
    result: GateResult
    attempts: int = 0
    aired: bool = False
