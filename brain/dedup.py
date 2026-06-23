"""DEDUP-014: version-aware acquisition de-duplication (the GATE DECISION only).

This module owns SPEC-RADIO-DEDUP-014's *decision* — "is this candidate a TRUE
DUPLICATE of something already owned, or a VALID DISTINCT VERSION?" — and nothing
else. It does NOT resolve MusicBrainz ids (that is ENRICH-012's spine), does NOT
query the MB mirror (MBMIRROR-017), and does NOT prune the existing library
(explicitly deferred, spec Section 4.2). It is a pure, in-memory, testable
primitive plus a rebuildable index; the wiring into acquisition lives in
``brain/acquire.py``.

Identity model (spec Group DK):
  - PRIMARY key  = the canonical MusicBrainz **recording MBID** ENRICH-012 lifts onto
    ``Track.recording_mbid`` (post-enrichment). Two tracks with the SAME recording MBID
    are the same recording.
  - FALLBACK key = the existing ``normalize_key`` artist-title slug, retained verbatim
    (REQ-DK-002). DEDUP-014 NEVER redefines the slug.

Version-awareness (spec Group DV) — the load-bearing rule:
  - SAME recording_mbid + NO distinguishing version signal  -> TRUE DUPLICATE (reject).
  - DIFFERENT recording_mbid (even under the same artist/title slug) -> VALID DISTINCT
    VERSION (allow): a live/remaster/remix/acoustic IS a different recording, and MUST
    NOT be collapsed into the studio cut. This is the whole point of the SPEC.
  - ABSENT/empty recording_mbid on either side -> fall back; with no confident fuzzy
    evidence the gate ALLOWS (fail-open, REQ-DV-003 / REQ-DG-002 / NFR-D-1). A missing
    MBID NEVER blocks a wanted track.

Fail-open is the cardinal rail: when identity/distinctness cannot be established with
POSITIVE evidence, the decision is ALLOW. A missed duplicate (one extra download) is a
tolerated outcome; a wrongly-blocked wanted track is the defect this module prevents.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

# Decision constants (spec Glossary "Gate decision").
ALLOW_NEW = "allow-new"                       # not owned at all
REJECT_DUPLICATE = "reject-duplicate"         # same recording already owned, no version signal
ALLOW_DISTINCT_VERSION = "allow-distinct-version"  # owned, but a valid distinct version

# Identity basis recorded on the decision (REQ-DO-001 "identity basis").
BASIS_MBID = "mbid"
BASIS_SLUG = "slug"
BASIS_NONE = "none"

# Default version-distinguishing token set (REQ-DV-002/004). DATA, not curation policy:
# it decides duplicate-vs-variant, never which variants the station should want. Tunable by
# passing a custom set to ``version_signals``. These are matched against the candidate title
# (and, for the symmetric live/studio case, the owned title) as whole-word tokens.
DEFAULT_VERSION_TOKENS: frozenset[str] = frozenset({
    "live", "concert", "unplugged", "session", "sessions",
    "remaster", "remastered",
    "remix", "mix", "dub", "instrumental",
    "acoustic",
    "demo", "take", "version",
    "edit", "single", "extended",
})

_WORD_RE = re.compile(r"[a-z0-9]+")


def version_signals(title: str, tokens: Iterable[str] = DEFAULT_VERSION_TOKENS) -> frozenset[str]:
    """Version-distinguishing tokens present in a title (lowercased whole-word match).

    Pure + side-effect free. A title like "Feeling Good (Live at Montreux)" yields
    {"live"}; "Feeling Good" yields the empty set. Used to decide whether a same-slug or
    same-identity match is actually a DISTINCT version rather than a true duplicate.
    """
    if not title:
        return frozenset()
    want = {t.lower() for t in tokens}
    found = {w for w in _WORD_RE.findall(title.lower()) if w in want}
    return frozenset(found)


@dataclass(frozen=True)
class GateDecision:
    """The outcome of a dedup check: decision + why (REQ-DO-001 audit record).

    ``allowed`` is the single boolean the caller acts on; the rest is the structured
    reason logged so a human can audit after the fact why a track was/was not a dup.
    """
    decision: str
    allowed: bool
    basis: str                       # mbid | slug | none
    matched_key: Optional[str] = None  # the owned track's slug we matched (if any)
    signals: Tuple[str, ...] = ()      # distinguishing version tokens that made it distinct


# @MX:ANCHOR: [AUTO] The version-aware dedup decision — the single DEDUP-014 invariant.
# @MX:REASON: every acquisition-side de-dup decision flows through this function; its
#   same-mbid=dup / different-mbid=distinct / absent-mbid=fail-open contract is the whole
#   SPEC. A change here silently re-defines what counts as a duplicate across acquisition.
# @MX:SPEC: SPEC-RADIO-DEDUP-014 REQ-DV-001/002/003, REQ-DG-002
def classify(
    candidate_mbid: str,
    candidate_title: str,
    owned: "Iterable[Tuple[str, str, str]]",
    *,
    tokens: Iterable[str] = DEFAULT_VERSION_TOKENS,
) -> GateDecision:
    """Decide whether ``candidate`` duplicates one of ``owned`` (version-aware, fail-open).

    ``owned`` is an iterable of ``(key, recording_mbid, title)`` for the tracks already in
    the library — exactly what ``DedupIndex.owned()`` yields. ``candidate_mbid`` is the
    candidate's resolved recording MBID ("" if unresolved); ``candidate_title`` is its
    display title (carries the live/remaster/... version signal when no MBID exists).

    Rules (in order):
      1. Candidate has a recording MBID that EXACTLY matches an owned track's MBID, AND the
         candidate carries NO version-distinguishing signal the owned track lacks
         -> REJECT_DUPLICATE (the same recording, basis=mbid). [REQ-DV-001]
      2. Candidate has a recording MBID that matches NO owned MBID -> ALLOW (a different
         recording is, by definition, a distinct version; basis=mbid). [REQ-DV-001/002]
      3. Candidate has NO recording MBID -> fall back to the slug/fuzzy world: this module
         does NOT block on the bare slug (the existing ``has_key`` gate already owns the
         exact-slug case at enqueue). With no confident positive evidence here the decision
         is ALLOW_NEW, basis=none -> FAIL-OPEN. [REQ-DG-002 / REQ-DV-003 / NFR-D-1]

    A version signal present on the candidate that the matched owned track lacks downgrades a
    would-be reject to ALLOW_DISTINCT_VERSION (live-vs-studio is always allowed, REQ-DV-002).
    """
    cand_mbid = (candidate_mbid or "").strip()
    cand_sig = version_signals(candidate_title, tokens)

    if not cand_mbid:
        # No identity to match on here. The exact-slug gate (has_key) and a future fuzzy
        # fallback own this case; absent positive evidence, fail open.
        return GateDecision(ALLOW_NEW, allowed=True, basis=BASIS_NONE)

    for key, owned_mbid, owned_title in owned:
        if (owned_mbid or "").strip() != cand_mbid:
            continue
        # Same recording MBID. Is the candidate a distinct version of it anyway?
        owned_sig = version_signals(owned_title, tokens)
        distinguishing = cand_sig - owned_sig
        if distinguishing:
            # e.g. candidate is the "live"/"remaster" cut, owned is the plain studio cut.
            return GateDecision(
                ALLOW_DISTINCT_VERSION, allowed=True, basis=BASIS_MBID,
                matched_key=key, signals=tuple(sorted(distinguishing)),
            )
        # Same recording, no extra version signal -> a true duplicate.
        return GateDecision(REJECT_DUPLICATE, allowed=False, basis=BASIS_MBID, matched_key=key)

    # Candidate's MBID matches nothing owned -> a different recording -> distinct/new. Allow.
    return GateDecision(ALLOW_NEW, allowed=True, basis=BASIS_MBID)


class DedupIndex:
    """Rebuildable in-memory map: recording MBID -> owned track slug(s) (REQ-DK-003).

    Derived from the persisted library (rebuilt on load), so a duplicate check is an O(1)
    in-memory lookup with NO per-check network call and NO separate datastore. Restart-safe:
    rebuilding from the same library yields the same index (idempotent, NFR-D-3). Tracks with
    an empty recording_mbid are simply absent from the MBID map (they fall back to the
    slug/fuzzy world); we keep their (key,title) so ``owned()`` can surface them too.
    """

    def __init__(self) -> None:
        # recording_mbid -> set of slugs that resolve to it.
        self._by_mbid: Dict[str, set] = {}
        # key -> (recording_mbid, title) for every owned track (mbid may be "").
        self._records: Dict[str, Tuple[str, str]] = {}

    # -- construction ------------------------------------------------------------

    @classmethod
    def from_library(cls, library) -> "DedupIndex":
        """Build the index from a Library via its read-only ``query`` accessor.

        ``query(limit=None)`` returns every Track under the library lock; we read only the
        identity fields (key / recording_mbid / title) and never mutate anything (NFR-D-4).
        """
        idx = cls()
        try:
            tracks = library.query(limit=None)
        except Exception:  # noqa: BLE001 - a read fault degrades to an empty index, never crashes
            return idx
        for t in tracks:
            idx.register(
                getattr(t, "key", "") or "",
                getattr(t, "recording_mbid", "") or "",
                getattr(t, "title", "") or "",
            )
        return idx

    def register(self, key: str, recording_mbid: str, title: str) -> None:
        """Add/refresh one owned track in the index (REQ-DG-003 admission consistency)."""
        if not key:
            return
        mbid = (recording_mbid or "").strip()
        self._records[key] = (mbid, title or "")
        if mbid:
            self._by_mbid.setdefault(mbid, set()).add(key)

    # -- queries -----------------------------------------------------------------

    def owned(self, *, exclude_key: Optional[str] = None) -> "List[Tuple[str, str, str]]":
        """Yield ``(key, recording_mbid, title)`` for owned tracks (optionally excluding one).

        ``exclude_key`` lets a just-admitted track classify itself against the REST of the
        library without matching its own record.
        """
        out: List[Tuple[str, str, str]] = []
        for key, (mbid, title) in self._records.items():
            if exclude_key is not None and key == exclude_key:
                continue
            out.append((key, mbid, title))
        return out

    def duplicate_of(self, key: str, *, tokens: Iterable[str] = DEFAULT_VERSION_TOKENS) -> GateDecision:
        """Classify an ALREADY-INDEXED track against the rest of the library.

        Used by the post-enrichment detection in acquire.py: after ENRICH-012 stamps a
        just-landed track's recording_mbid, we ask "does this now duplicate an existing
        recording?". Excludes the track's own record so it never matches itself.
        """
        rec = self._records.get(key)
        if rec is None:
            return GateDecision(ALLOW_NEW, allowed=True, basis=BASIS_NONE)
        mbid, title = rec
        return classify(mbid, title, self.owned(exclude_key=key), tokens=tokens)

    def stats(self) -> Dict[str, int]:
        """Coarse counters for the health/status surface (REQ-DO-002 substrate)."""
        with_mbid = sum(1 for m, _ in self._records.values() if m)
        return {
            "tracks": len(self._records),
            "with_recording_mbid": with_mbid,
            "distinct_recordings": len(self._by_mbid),
        }
