"""SPEC-RADIO-SEEDING-029 (Step 1, build-plan) — per-persona taste SEEDING.

This module gives each persona a DISTINCT, GROUNDED musical taste so an autonomously
minted persona is never empty. It is the foundation Step 2 (autonomous minting) consumes:
mint designs a persona's identity, this module designs its TASTE from the real library.

WHAT IT DOES
------------
1. CLUSTER the existing library into taste REGIONS using the ANALYSIS-006 feature
   dimensions already present on every ``Track`` (genre / sub_genre / era(year) / tags) —
   it builds NO new analysis pipeline; it only groups the in-memory catalog the library
   already holds.
2. CLUSTER-AND-EXPLORE a distinct ``TasteCharter`` per persona: each persona ANCHORS on a
   DIFFERENT genre region (so no two share a primary territory), and EXPLORES that region's
   real sub-genres / eras / tags to populate its in-bounds descriptors. Every descriptor is
   lifted from a real track — the charter is GROUNDED, never fabricated.
3. ENFORCE distinctness through the EXISTING anti-convergence firewall (``persona`` module's
   ``territory_collision`` + ``pool_overlap`` over the same ANALYSIS-006 dimensions, the
   ``DEFAULT_OVERLAP_CAP`` Jaccard cap). The firewall is REUSED, not reinvented: a derived
   charter that would overlap an already-accepted one beyond the cap is EXPLORED away from
   the overlap (shared tags trimmed) until it clears, or skipped if it cannot.
4. RANK "what I'd play": given a charter, return the library tracks it would air, ranked by
   how well each matches the charter — grounded in the real catalog, deterministic.

DISCIPLINE
----------
- READ-ONLY over the library: ``derive_charters`` / ``rank_tracks`` never mutate the catalog,
  the roster, or any store. They are pure functions over the existing seams.
- ADDITIVE: nothing here changes an existing code path, so the default/empty-roster station
  behaves byte-identically to before this module existed (the golden behavior-preservation
  rail). Personas + their seeded taste are opt-in.
- The firewall over the ANALYSIS-006 dimensions is the SINGLE distinctness oracle — this
  module defers to it rather than defining its own notion of "distinct".

SCOPE BOUNDARY
--------------
This module owns the catalog-clustering + charter-derivation + what-I'd-play ranking. It does
NOT mint personas (Step 2 — it CALLS this), does NOT schedule shows (OPS-004 / SHOWS-020), and
does NOT own the firewall (``persona`` module — referenced, not re-owned).
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from . import persona as P
from .logging_setup import log_event

log = logging.getLogger("brain.seeding")


# How many of a region's co-occurring sub-genres / eras / tags to lift into a charter. Kept
# small so a charter stays a CHARACTERFUL declaration (a few signature descriptors), not an
# exhaustive dump of everything the region contains. TUNABLE; the rail is only that the
# descriptors are grounded in real tracks.
_MAX_SECONDARY_GENRES = 3
_MAX_ERAS = 3
_MAX_TAGS = 5


def _norm(s: Any) -> str:
    """Lower/strip normalize, matching the persona firewall's ``_norm`` so the descriptor
    sets this module builds compare identically under ``candidate_descriptor_set``."""
    return str(s or "").strip().lower()


def _decade(year: Optional[int]) -> str:
    """Map a release year to an era label (e.g. 1994 -> ``"1990s"``). Empty for an unknown
    year — an unanalyzed track contributes no era, never a fabricated one."""
    if not isinstance(year, int) or year <= 0:
        return ""
    return f"{(year // 10) * 10}s"


def _all_tracks(library: Any) -> List[Any]:
    """Every track in the library, via the public ``query`` seam (no filter = all tracks).

    ``Library.query()`` with no criteria returns the whole catalog and owns no curation
    policy (REQ-AD-002/003); reusing it keeps this module off any private attribute. Returns
    an empty list (never raises) if the library cannot be read — a dry catalog simply yields
    no charters, consistent with the never-crash posture."""
    try:
        return list(library.query())
    except Exception as exc:  # noqa: BLE001 - never crash on a library hiccup
        log_event(log, "seeding.library_read_error", error=str(exc))
        return []


# --------------------------------------------------------------------------- #
# Clustering — group the catalog into genre-anchored taste regions.
# --------------------------------------------------------------------------- #


class _Region:
    """A genre-anchored taste region: the tracks sharing a primary genre, plus the
    co-occurring sub-genres / eras / tags EXPLORED from those real tracks. The genre is the
    region's ANCHOR (a persona's primary territory); the explored descriptors GROUND its
    in-bounds sets. Built only from real catalog content — no fabricated descriptors."""

    def __init__(self, genre: str) -> None:
        self.genre = genre
        self.count = 0
        self._sub_genres: Counter = Counter()
        self._eras: Counter = Counter()
        self._tags: Counter = Counter()

    def add(self, track: Any) -> None:
        self.count += 1
        sg = _norm(getattr(track, "sub_genre", ""))
        if sg and sg != _norm(self.genre):
            self._sub_genres[sg] += 1
        era = _decade(getattr(track, "year", None))
        if era:
            self._eras[era] += 1
        for tag in getattr(track, "tags", None) or []:
            t = _norm(tag)
            if t:
                self._tags[t] += 1

    def top_sub_genres(self, n: int) -> List[str]:
        return [g for g, _ in self._sub_genres.most_common(n)]

    def top_eras(self, n: int) -> List[str]:
        return [e for e, _ in self._eras.most_common(n)]

    def top_tags(self, n: int) -> List[str]:
        return [t for t, _ in self._tags.most_common(n)]


def cluster_library(library: Any) -> List[_Region]:
    """Group the catalog into genre-anchored taste regions, richest first (REQ-AD-003 dims).

    A REGION = the tracks sharing a normalized primary genre. Only tracks that carry a genre
    contribute (an unanalyzed/genre-less track has no taste territory to anchor). Regions are
    returned ordered by track count descending (the richest, most distinct taste regions
    first) so charter derivation anchors personas on the catalog's strongest territories.
    """
    regions: Dict[str, _Region] = {}
    for t in _all_tracks(library):
        g = _norm(getattr(t, "genre", ""))
        if not g:
            continue
        region = regions.get(g)
        if region is None:
            region = _Region(getattr(t, "genre", "").strip())
            regions[g] = region
        region.add(t)
    return sorted(regions.values(), key=lambda r: (-r.count, _norm(r.genre)))


# --------------------------------------------------------------------------- #
# Charter derivation — cluster-and-explore into DISTINCT grounded charters.
# --------------------------------------------------------------------------- #


def _charter_from_region(region: _Region) -> P.TasteCharter:
    """Build a grounded ``TasteCharter`` anchored on a region. The primary territory is the
    region's genre; the in-bounds genres/eras/tags are EXPLORED from the region's real tracks
    (every descriptor came from a catalog track — grounded, never invented)."""
    in_genres = [region.genre] + region.top_sub_genres(_MAX_SECONDARY_GENRES)
    return P.TasteCharter(
        primary_territory=region.genre,
        in_genres=in_genres,
        in_eras=region.top_eras(_MAX_ERAS),
        in_tags=region.top_tags(_MAX_TAGS),
    )


def _overlap_ok(candidate: P.TasteCharter, accepted: List[P.TasteCharter],
                overlap_cap: float) -> Tuple[bool, P.TasteCharter]:
    """Run the candidate charter against the EXISTING firewall's distinctness oracle
    (``territory_collision`` via primary-territory equality + ``pool_overlap`` Jaccard over
    the ANALYSIS-006 descriptor sets) against every accepted charter. When the only conflict
    is tag overlap, EXPLORE away from it by trimming the shared tags (the explore half of
    cluster-and-explore) and re-checking. Returns ``(ok, possibly_trimmed_charter)``."""
    cand = candidate
    for other in accepted:
        # Primary-territory collision is structural (genre regions are distinct by
        # construction) — if it ever fires, the candidate cannot be made distinct.
        if _norm(cand.primary_territory) == _norm(other.primary_territory):
            return False, cand
        if _pool_overlap_charters(cand, other) >= overlap_cap:
            # Explore away: drop tags shared with the conflicting charter, then re-measure.
            shared = {_norm(t) for t in cand.in_tags} & {_norm(t) for t in other.in_tags}
            if shared:
                cand = P.TasteCharter(
                    primary_territory=cand.primary_territory,
                    in_genres=list(cand.in_genres),
                    out_genres=list(cand.out_genres),
                    in_eras=list(cand.in_eras),
                    in_tags=[t for t in cand.in_tags if _norm(t) not in shared],
                    signature_artists=list(cand.signature_artists),
                    moods=list(cand.moods),
                )
            if _pool_overlap_charters(cand, other) >= overlap_cap:
                return False, cand
    return True, cand


def _pool_overlap_charters(a: P.TasteCharter, b: P.TasteCharter) -> float:
    """Jaccard over the two charters' in-bounds descriptor sets — the SAME measure the
    firewall's ``pool_overlap`` applies, reused here so derivation and admission agree."""
    sa = a.candidate_descriptor_set()
    sb = b.candidate_descriptor_set()
    if not sa and not sb:
        return 0.0
    union = len(sa | sb)
    return (len(sa & sb) / union) if union else 0.0


def derive_charters(library: Any, n: int,
                    *, overlap_cap: float = P.DEFAULT_OVERLAP_CAP) -> List[P.TasteCharter]:
    """Derive up to ``n`` DISTINCT, GROUNDED taste charters from the library (the Step 1 DoD).

    Cluster-and-explore: cluster the catalog into genre-anchored regions (richest first),
    then walk them assigning each persona a DIFFERENT region as its primary territory and
    EXPLORING that region's real sub-genres / eras / tags into its charter. Each derived
    charter is checked against the already-accepted ones with the EXISTING firewall's
    distinctness oracle (no shared primary territory + pool overlap under ``overlap_cap``);
    on a tag-only conflict it is explored away from the overlap before being accepted.

    Returns AT MOST ``n`` charters (fewer when the catalog has fewer distinct genre regions —
    grounding wins over fabricating a region that isn't in the library). Read-only; never
    mutates the library.
    """
    if n <= 0:
        return []
    accepted: List[P.TasteCharter] = []
    for region in cluster_library(library):
        if len(accepted) >= n:
            break
        candidate = _charter_from_region(region)
        ok, trimmed = _overlap_ok(candidate, accepted, overlap_cap)
        if ok:
            accepted.append(trimmed)
    log_event(log, "seeding.charters_derived", requested=n, derived=len(accepted))
    return accepted


# --------------------------------------------------------------------------- #
# "What I'd play" — rank the catalog by charter fit (grounded).
# --------------------------------------------------------------------------- #


def _track_score(track: Any, charter: P.TasteCharter) -> float:
    """Score how well a real library track fits a charter. Higher = the persona would more
    likely air it. An out-of-bounds genre scores below zero (actively avoided). Grounded:
    the score is computed only from the track's own descriptors against the charter's."""
    genre = _norm(getattr(track, "genre", ""))
    sub_genre = _norm(getattr(track, "sub_genre", ""))
    out_genres = {_norm(g) for g in charter.out_genres}
    if genre and genre in out_genres:
        return -1.0

    in_genres = {_norm(g) for g in charter.in_genres}
    score = 0.0
    if genre and genre == _norm(charter.primary_territory):
        score += 3.0
    elif genre and genre in in_genres:
        score += 2.0
    if sub_genre and sub_genre in in_genres:
        score += 1.0

    era = _decade(getattr(track, "year", None))
    if era and era in {_norm(e) for e in charter.in_eras}:
        score += 1.0

    in_tags = {_norm(t) for t in charter.in_tags}
    track_tags = {_norm(t) for t in (getattr(track, "tags", None) or [])}
    score += float(len(in_tags & track_tags))

    sig = {_norm(a) for a in charter.signature_artists}
    if sig and _norm(getattr(track, "artist", "")) in sig:
        score += 2.0
    return score


def rank_tracks(library: Any, charter: P.TasteCharter,
                *, limit: Optional[int] = None) -> List[Any]:
    """The persona's "what I'd play": library tracks ranked by charter fit, best first.

    Grounded in the REAL catalog — every returned track exists in the library. Out-of-bounds
    (charter ``out_genres``) tracks are excluded. Ties are broken deterministically by dedup
    key so the ranking is stable. Read-only; never mutates the library. A persona returns its
    set via ``rank_tracks(library, persona.charter)``.
    """
    scored: List[Tuple[float, str, Any]] = []
    for t in _all_tracks(library):
        s = _track_score(t, charter)
        if s <= 0.0:
            continue
        scored.append((s, _norm(getattr(t, "key", "")), t))
    scored.sort(key=lambda x: (-x[0], x[1]))
    out = [t for _, _, t in scored]
    if limit is not None and limit >= 0:
        out = out[:limit]
    return out
