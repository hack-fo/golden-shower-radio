"""ENRICH-012: core-tag enrichment — identify the canonical recording and CORRECT a
track's artist / title / album / year / genre, then persist to the file + library.

This is DISTINCT from brain.metadata (ANALYSIS-006), which derives genre/mood/tags for the
analysis layer. ENRICH-012 fixes the *core identity* tags that downloads from slskd / yt-dlp
routinely get wrong: empty artist, the artist folded into the title, missing album/year.

Pipeline per track:
  1. IDENTIFY the canonical recording:
       a. AcoustID fingerprint (Chromaprint ``fpcalc`` -> AcoustID API -> MusicBrainz) when
          a key + the binary are available (the only reliable path for garbled/empty-artist
          files — it identifies by the actual audio, not the wrong tags).
       b. Text-match fallback (existing tags / filename -> MusicBrainz ``search_recordings``)
          when fingerprinting is unavailable or inconclusive.
  2. PROPOSE corrections under the locked write policy: fill every empty/missing field, and
     OVERWRITE an existing value only when it looks garbled AND the match is high-confidence;
     never clobber a clearly-good high-confidence existing tag.
  3. APPLY: write corrected tags to the file (mutagen) + update library.json, idempotently,
     recording provenance (field, old -> new, source, confidence).

Resilience: every external call is exception-isolated; nothing here raises into a caller.
Reuses brain.metadata's MusicBrainz access + the process-wide <=1 req/s throttle.
"""

from __future__ import annotations

import difflib
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import metadata
from .logging_setup import log_event

log = logging.getLogger("brain.enrich")

# Core identity fields this engine owns. (genre/year are shared with ANALYSIS-006 but a
# canonical MB resolution is authoritative for them too, so we fill them when empty.)
CORE_FIELDS = ("artist", "title", "album", "year", "genre")

SRC_ACOUSTID = "acoustid"
SRC_MUSICBRAINZ_TEXT = "musicbrainz-text"


@dataclass
class Canonical:
    """A resolved canonical recording from one identification path."""
    artist: str = ""
    title: str = ""
    album: str = ""
    year: Optional[int] = None
    genre: str = ""
    confidence: float = 0.0  # [0..1]
    source: str = ""


@dataclass
class Proposal:
    """The outcome of proposing corrections for one track (NON-destructive)."""
    changes: Dict[str, Any] = field(default_factory=dict)        # field -> new value
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    canonical: Optional[Canonical] = None

    def has_changes(self) -> bool:
        return bool(self.changes)


# --------------------------------------------------------------------------- #
# String normalization + similarity (pure, testable)
# --------------------------------------------------------------------------- #

# Editorial noise commonly appended to titles by YouTube/Soulseek rips. Stripped ONLY for
# similarity scoring + garbled detection — never written back (we keep MB's clean title).
_NOISE_RE = re.compile(
    r"\s*[\(\[]\s*(official\s*(audio|video|music\s*video|lyric\s*video)?|audio|hq\s*audio|"
    r"lyrics?|visualizer|remaster(ed)?(\s*\d{4})?|\d{4}\s*remaster)\s*[\)\]]\s*",
    re.IGNORECASE,
)


def normalize(s: str) -> str:
    """Lowercase, strip editorial noise + punctuation, collapse whitespace. For comparison
    only; never persisted."""
    if not s:
        return ""
    t = _NOISE_RE.sub(" ", s)
    t = re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


def similarity(a: str, b: str) -> float:
    """Normalized string similarity in [0..1] (0 if either side is empty)."""
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


def is_garbled(field_name: str, value: str) -> bool:
    """Standalone heuristic: does an EXISTING value look broken on its own (no canonical)?

    Empty -> True. An artist field holding an "X - Y" separator is almost always the title
    folded in. (Cross-field detection — title contains the artist, etc. — lives in
    ``_looks_wrong`` which also has the canonical to compare against.)
    """
    v = (value or "").strip()
    if not v:
        return True
    if field_name == "artist" and re.search(r"\s[-/|]\s", v):
        return True
    return False


def _contains(haystack: str, needle: str) -> bool:
    """Normalized substring test (needle present + non-trivial)."""
    nh, nn = normalize(haystack), normalize(needle)
    return bool(nn) and len(nn) >= 3 and nn in nh


def _looks_wrong(field_name: str, current: str, canonical: "Canonical") -> bool:
    """Cross-field garbled detection using the canonical match as the reference.

    The classic Soulseek/YouTube breakages: the artist and title get folded into one field
    (e.g. artist="" title="Chimacum Rain-Linda Perhacs", or artist="Linda Perhacs - Chimacum
    Rain"). We flag a field as wrong when it carries the OTHER field's canonical value.
    """
    if is_garbled(field_name, current):
        return True
    # Title field carrying the canonical ARTIST (and not already the canonical title) ->
    # the artist got folded into the title (e.g. "Chimacum Rain-Linda Perhacs").
    if field_name == "title" and canonical.artist and _contains(current, canonical.artist) \
            and normalize(current) != normalize(canonical.title):
        return True
    # Artist field carrying the canonical TITLE -> the title got folded into the artist.
    if field_name == "artist" and canonical.title and _contains(current, canonical.title):
        return True
    return False


# --------------------------------------------------------------------------- #
# Identification — text-match (MusicBrainz) and AcoustID fingerprint
# --------------------------------------------------------------------------- #

def _best_recording(recs: List[Dict[str, Any]], want_artist: str, want_title: str) -> Optional[Canonical]:
    """Pick the best MB recording for the wanted artist/title and lift canonical fields."""
    best: Optional[Canonical] = None
    best_score = -1.0
    for rec in recs:
        title = rec.get("title", "") or ""
        artist = _artist_credit(rec)
        # MB's own search score (0..100) blended with our normalized title+artist similarity.
        mb_score = float(rec.get("ext:score", rec.get("score", 0)) or 0) / 100.0
        sim_t = similarity(want_title, title) if want_title else 0.0
        sim_a = similarity(want_artist, artist) if want_artist else 0.0
        # If we have no usable artist (garbled/empty), lean on title + MB score only.
        sim = (sim_t + sim_a) / 2.0 if want_artist else sim_t
        album, year, rel_rank = _release_album_year(rec)
        # Small tie-breaker bonus so a recording that sits on a CLEAN STUDIO album outranks
        # the same song's compilation/live recording (whose only releases are comps). This
        # steers both the chosen identity AND the album toward the canonical studio release.
        rel_bonus = (3 - rel_rank) / 3.0  # 1.0 clean studio ... 0.0 no release
        score = 0.45 * mb_score + 0.45 * sim + 0.10 * rel_bonus
        if score > best_score:
            best_score = score
            best = Canonical(
                artist=artist, title=title, album=album, year=year,
                confidence=round(0.5 * mb_score + 0.5 * sim, 3),  # report identity confidence
                source=SRC_MUSICBRAINZ_TEXT,
            )
    return best


def _artist_credit(rec: Dict[str, Any]) -> str:
    """Flatten MB artist-credit into a display string (handles feat./collaborations)."""
    parts: List[str] = []
    for ac in rec.get("artist-credit", []) or []:
        if isinstance(ac, dict):
            art = ac.get("artist") or {}
            parts.append(art.get("name", "") or ac.get("name", ""))
        elif isinstance(ac, str):
            parts.append(ac)  # the literal joinphrase, e.g. " feat. "
    return "".join(parts).strip()


def _year_of(date_str: str) -> Optional[int]:
    """Leading 4-digit year from an MB date string ("1973", "1998-03-10"), else None."""
    m = re.match(r"\s*(\d{4})", date_str or "")
    if not m:
        return None
    y = int(m.group(1))
    return y if 1900 <= y <= 2100 else None


def _release_album_year(rec: Dict[str, Any]):
    """Pick the CANONICAL album + original year from a recording's releases.

    Preference order (lower is better): a clean STUDIO album (release-group primary-type
    "Album" with NO secondary-type like Compilation/Live/Soundtrack) beats a plain album
    beats anything else; ties broken by EARLIEST release year. This avoids tagging a track
    with a live bootleg or a "Sci-Fi Collection" compilation when the real studio album
    (and its original year) is present in the candidate list.
    """
    releases = rec.get("release-list") or []
    best = ("", None)
    best_rank = 3  # 0 clean studio album, 1 plain album, 2 other release, 3 none
    best_key = None
    for r in releases:
        g = r.get("release-group") or {}
        ptype = (g.get("primary-type") or "").lower()
        sec = g.get("secondary-type-list") or []
        is_album = ptype == "album"
        is_clean = is_album and not sec  # no Compilation/Live/Soundtrack/etc.
        yr = _year_of(r.get("date") or "") or _year_of(g.get("first-release-date") or "")
        rank = 0 if is_clean else (1 if is_album else 2)
        key = (rank, yr if yr is not None else 9999)
        if best_key is None or key < best_key:
            best_key = key
            best_rank = rank
            best = (r.get("title", "") or "", yr)
    album, year = best
    # CONSERVATIVE: only trust album NAME and YEAR from a clean studio album (rank 0). A
    # compilation/live bootleg name — or a reissue/comp year — is worse than blank, so below
    # rank 0 we surface neither. (Accurate-or-empty beats confidently-wrong.) AcoustID /
    # deeper release-group lookups can fill these later.
    if best_rank != 0:
        album = ""
        year = None
    return album, year, best_rank


def identify_text(artist: str, title: str, cfg: Any) -> Optional[Canonical]:
    """Text-match identification via MusicBrainz. Reuses metadata's MB access + throttle.
    NEVER raises -> returns None on any error/no-match."""
    if not title:
        return None
    try:
        import musicbrainzngs  # type: ignore  # noqa: PLC0415 - lazy by design
    except Exception:  # noqa: BLE001
        return None
    timeout = float(getattr(cfg, "enrichment_http_timeout_seconds", 10))
    try:
        metadata._mb_set_useragent(musicbrainzngs, cfg, timeout)
        metadata._mb_throttle()
        # Search by recording (+ artist when we have a trustworthy one). include releases so
        # we can lift the album + year in one call.
        kwargs: Dict[str, Any] = {"recording": title, "limit": 5}
        if artist and not is_garbled("artist", artist):
            kwargs["artist"] = artist
        result = musicbrainzngs.search_recordings(**kwargs)
        recs = result.get("recording-list") or []
        if not recs:
            return None
        return _best_recording(recs, artist, title)
    except Exception as exc:  # noqa: BLE001
        log_event(log, "enrich.text_failed", artist=artist, title=title, error=str(exc))
        return None


def identify_acoustid(path: str, cfg: Any) -> Optional[Canonical]:
    """AcoustID fingerprint identification: fpcalc -> AcoustID API -> MusicBrainz fields.

    Gated: requires both an AcoustID API key and the fpcalc binary. Returns None (graceful)
    when either is absent or the lookup is inconclusive. NEVER raises.
    """
    key = (getattr(cfg, "acoustid_api_key", "") or "").strip()
    if not key:
        return None
    fpcalc = getattr(cfg, "acoustid_fpcalc_path", "fpcalc") or "fpcalc"
    timeout = float(getattr(cfg, "enrichment_http_timeout_seconds", 10))
    try:
        duration, fingerprint = _fpcalc(path, fpcalc, timeout)
    except Exception as exc:  # noqa: BLE001 - fpcalc missing / decode error -> graceful skip
        log_event(log, "enrich.fpcalc_failed", path=os.path.basename(path), error=str(exc))
        return None
    if not fingerprint or not duration:
        return None
    try:
        import httpx  # noqa: PLC0415 - lazy; already a brain dep
        metadata._mb_throttle()  # AcoustID is friendlier but reuse a polite spacing
        resp = httpx.get(
            "https://api.acoustid.org/v2/lookup",
            params={
                "client": key,
                "duration": int(duration),
                "fingerprint": fingerprint,
                "meta": "recordings+releasegroups+compress",
            },
            timeout=timeout,
        )
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        log_event(log, "enrich.acoustid_failed", path=os.path.basename(path), error=str(exc))
        return None
    return _canonical_from_acoustid(data)


def _fpcalc(path: str, fpcalc: str, timeout: float):
    """Run Chromaprint fpcalc -> (duration_seconds:int, fingerprint:str). Raises on failure."""
    out = subprocess.run(
        [fpcalc, "-json", path],
        capture_output=True, text=True, timeout=max(15.0, timeout * 2), check=True,
    )
    import json  # noqa: PLC0415
    d = json.loads(out.stdout)
    return d.get("duration"), d.get("fingerprint")


def _canonical_from_acoustid(data: Dict[str, Any]) -> Optional[Canonical]:
    """Lift the best-scoring AcoustID result into a Canonical."""
    if (data or {}).get("status") != "ok":
        return None
    results = sorted(data.get("results", []), key=lambda r: r.get("score", 0), reverse=True)
    for res in results:
        score = float(res.get("score", 0) or 0)  # AcoustID score is already [0..1]
        recs = res.get("recordings") or []
        if not recs:
            continue
        rec = recs[0]
        artist = ", ".join(a.get("name", "") for a in (rec.get("artists") or []) if a.get("name"))
        title = rec.get("title", "") or ""
        album = ""
        year: Optional[int] = None
        for rg in rec.get("releasegroups") or []:
            album = rg.get("title", "") or album
            break
        if not title:
            continue
        return Canonical(
            artist=artist, title=title, album=album, year=year,
            confidence=round(score, 3), source=SRC_ACOUSTID,
        )
    return None


def identify(path: str, artist: str, title: str, cfg: Any) -> Optional[Canonical]:
    """Full identification: AcoustID fingerprint first (most reliable for garbled files),
    then text-match fallback. Returns the higher-confidence result, or None."""
    fp = identify_acoustid(path, cfg) if getattr(cfg, "acoustid_api_key", "") else None
    txt = identify_text(artist, title, cfg)
    candidates = [c for c in (fp, txt) if c is not None]
    if not candidates:
        return None
    return max(candidates, key=lambda c: c.confidence)


# --------------------------------------------------------------------------- #
# Proposal — the locked write policy (pure, NON-destructive)
# --------------------------------------------------------------------------- #

def propose(current: Dict[str, Any], canonical: Optional[Canonical], cfg: Any) -> Proposal:
    """Decide which core fields to change under the locked policy. Returns proposed changes
    WITHOUT touching anything. Pure + deterministic so it is unit-testable.

    Policy:
      - FILL: an empty/missing field is filled whenever the canonical has a value and the
        match clears a relaxed fill bar (threshold - 0.15, floored at 0.5).
      - FIX:  a NON-empty but garbled field is overwritten only when the match clears the
        full confidence threshold.
      - KEEP: a non-empty, non-garbled field is never overwritten.
    """
    p = Proposal(canonical=canonical)
    if canonical is None:
        return p
    threshold = float(getattr(cfg, "enrich_confidence_threshold", 0.85))
    fill_bar = max(0.5, threshold - 0.15)
    conf = canonical.confidence
    for fname in CORE_FIELDS:
        new = getattr(canonical, fname, None)
        if new in (None, "", 0):
            continue
        cur = current.get(fname)
        cur_str = "" if cur in (None, 0) else str(cur).strip()
        if not cur_str:
            decision = "fill" if conf >= fill_bar else None
        elif normalize(str(new)) == normalize(cur_str):
            decision = None  # already correct (idempotent no-op)
        elif _looks_wrong(fname, cur_str, canonical) and conf >= threshold:
            decision = "fix"
        else:
            decision = None  # keep a good existing value
        if decision:
            p.changes[fname] = new
            p.provenance.append({
                "field": fname, "old": cur_str, "new": new,
                "source": canonical.source, "confidence": conf, "action": decision,
            })
    return p
