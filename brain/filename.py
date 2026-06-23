"""SPEC-RADIO-FILENAME-024 — filename <-> id3 consistency: detect-and-flag (default) + optional
gated rename.

The station already CORRECTS the core identity tags of every track (ENRICH-012); after that the
in-file id3 tags + ``Track.artist`` / ``Track.title`` are TRUSTWORTHY. The FILENAMES are not —
slskd / yt-dlp rips land as ``09 - track.mp3`` / ``final_master.flac`` / a YouTube id. This layer
makes every music filename SAY at least who + what, using the ENRICH-012-corrected tags as the
source of truth, with a deliberate asymmetry:

  - DETECT + FLAG is the DEFAULT (Group FD): a cheap, background, exception-isolated, read-only
    check — is the normalized basename carrying both the canonical artist AND title? — that FLAGS
    the misses and records the verdict on the track (queryable). It renames NOTHING.
  - OPTIONAL RENAME is opt-in surgery (Group FR): OFF by default, behind a dedicated toggle AND the
    write-files discipline. When on it renames a flagged file to the canonical scheme ATOMICALLY
    with the ``Track.path`` update (via ``Library.rename_track_file``), never the in-flight file
    (Group FS), filesystem-safe + collision-safe (Group FF), idempotent + reversible (REQ-FR-004).

Because the tags are the truth and the filename is COSMETIC, the system NEVER trades broadcast
safety for a cosmetic filename. This module OWNS the consistency definition + the canonical-name
build + the safety/filesystem rules; it CONSUMES ``library.normalize_key`` (the shared
normalization), the ENRICH-012-corrected ``Track`` fields, ``Library.rename_track_file`` (the
atomic path writer), and ``StationState`` (the playout-safety guard). It NEVER re-identifies a
track and adds no new datastore — the flag lives on the existing ``Track.provenance`` seam.

Everything here is best-effort + exception-isolated: a detection or rename error LOGS and degrades
to leaving the file as-is + a logged flag. It never crashes the daemon and never silences the
stream.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .logging_setup import log_event

log = logging.getLogger("brain.filename")

# Consistency verdicts (REQ-FD-001/003). Recorded on Track.provenance['filename_flag'].
CONSISTENT = "consistent"
FLAGGED = "flagged"
INDETERMINATE = "indeterminate"

# Filesystem name length bound (REQ-FF-001). Conservative vs the 255-byte common limit so a
# multibyte unicode stem + the disambiguator + extension stay safely within bounds.
_MAX_BASENAME_LEN = 200

# Characters illegal/reserved on common filesystems (REQ-FF-001). The path separators MUST go
# (a "/" in a basename would change the directory — forbidden, REQ-FX-002); the rest are
# Windows-reserved so a renamed file stays portable. Control chars are stripped separately.
_ILLEGAL_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')

# A leading disc/track-number prefix to PRESERVE (REQ-FR-002): "09 - ", "1-05 ", "01_", "3. ".
# Captured (not stripped) so the canonical name keeps it.
_LEADING_NUM_RE = re.compile(r"^(\s*\d{1,3}(?:[-.]\d{1,3})?\s*[-_.)\s]\s*)")


# --------------------------------------------------------------------------- #
# Normalization (reuses the library.normalize_key transform on a single string)
# --------------------------------------------------------------------------- #

def normalized(s: str) -> str:
    """Case-fold + NFKD diacritic-strip + non-alphanumeric->space + collapse — the SAME transform
    ``library.normalize_key`` applies, here on a SINGLE string (REQ-FD-001).

    Reused for both the filename basename and the canonical artist/title before the contains-test,
    so the match is case/diacritic/separator-insensitive. A parity test
    (``test_filename_normalized_matches_normalize_key``) locks it to ``normalize_key``.
    """
    raw = (s or "").lower()
    raw = unicodedata.normalize("NFKD", raw)
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    raw = re.sub(r"[^a-z0-9]+", " ", raw).strip()
    return raw


# --------------------------------------------------------------------------- #
# Consistency check (Group FD) — pure, testable
# --------------------------------------------------------------------------- #

# @MX:ANCHOR: [AUTO] The FILENAME-024 consistency definition — the Group FD rail.
# @MX:REASON: every detect-and-flag verdict flows through this. A filename is CONSISTENT iff the
#   normalized basename contains BOTH the normalized canonical artist AND title; an unknown/empty
#   artist OR title is INDETERMINATE (never flagged, never renamed — REQ-FD-003/FF-003); else
#   FLAGGED. The canonical artist/title are READ from the ENRICH-012-corrected fields; this NEVER
#   re-identifies a track. Changing the contains/indeterminate logic silently re-defines what the
#   station flags + renames. Characterized in brain/test_characterize_filename.py.
# @MX:SPEC: SPEC-RADIO-FILENAME-024 REQ-FD-001 / REQ-FD-003
def classify_consistency(basename: str, artist: str, title: str) -> str:
    """Classify a filename basename against the canonical artist/title (REQ-FD-001/003).

    Returns ``INDETERMINATE`` if either canonical field is unknown/empty (cannot be evaluated;
    never flagged, never rename-eligible); ``CONSISTENT`` if the normalized basename contains both
    the normalized artist AND title; ``FLAGGED`` otherwise.
    """
    na = normalized(artist)
    nt = normalized(title)
    if not na or not nt:
        return INDETERMINATE
    nb = normalized(os.path.splitext(os.path.basename(basename or ""))[0])
    if na in nb and nt in nb:
        return CONSISTENT
    return FLAGGED


# --------------------------------------------------------------------------- #
# Canonical name build (Group FR/FF) — pure, testable
# --------------------------------------------------------------------------- #

def leading_number_prefix(basename: str) -> str:
    """The leading disc/track-number prefix to PRESERVE, normalized to ``<num> - `` form, or "".

    Recognizes ``09 - ``, ``1-05 ``, ``01_``, ``3. `` on the original stem; emits a clean
    ``<captured-digits> - `` prefix so the canonical name keeps the ordinal (REQ-FR-002).
    """
    stem = os.path.splitext(os.path.basename(basename or ""))[0]
    m = _LEADING_NUM_RE.match(stem)
    if not m:
        return ""
    # Pull the numeric token out of the matched prefix and render it as "<num> - ".
    num = re.match(r"\s*(\d{1,3}(?:[-.]\d{1,3})?)", m.group(1))
    return f"{num.group(1)} - " if num else ""


def sanitize_component(s: str) -> str:
    """Make a single name component filesystem-safe: drop illegal/reserved + control chars,
    collapse whitespace, trim trailing dots/spaces (REQ-FF-001). Unicode letters are KEPT (a
    non-ASCII artist/title yields a valid unicode filename, not mojibake)."""
    if not s:
        return ""
    out = _ILLEGAL_RE.sub(" ", s)
    out = re.sub(r"\s+", " ", out).strip()
    out = out.strip(". ")  # no trailing dot/space (Windows-hostile)
    return out


def build_canonical_basename(
    artist: str, title: str, ext: str, leading_prefix: str = "", template: str = "{artist} - {title}",
) -> Optional[str]:
    """Build the canonical basename ``<prefix><template-filled><ext>`` or None when impossible.

    Returns None (rename SKIPPED) when the canonical artist OR title is unknown/empty — never a
    garbage/partial/empty name like `` - Title.ext`` / ``Artist - .ext`` / ``.ext`` (REQ-FF-003).
    The filled stem is filesystem-sanitized (REQ-FF-001) and length-bounded with the extension +
    leading prefix preserved. A still-empty sanitized stem -> None (cannot be made valid).
    """
    a = sanitize_component(artist)
    t = sanitize_component(title)
    if not a or not t:
        return None  # FF-003: never a garbage/partial name from an unknown tag.
    try:
        stem = template.format(artist=a, title=t)
    except (KeyError, IndexError, ValueError):
        stem = f"{a} - {t}"  # a malformed template degrades to the default scheme.
    stem = sanitize_component(stem)
    if not stem:
        return None
    ext = ext or ""
    prefix = sanitize_component(leading_prefix)
    prefix = (prefix + " ") if prefix and not prefix.endswith(" ") else prefix
    # Length bound: reserve room for the prefix + extension, truncate the stem if needed.
    budget = _MAX_BASENAME_LEN - len(prefix) - len(ext)
    if budget < 1:
        return None
    if len(stem) > budget:
        stem = stem[:budget].strip()
        if not stem:
            return None
    return f"{prefix}{stem}{ext}"


def disambiguate(target_path: str, *, max_tries: int = 99) -> Optional[str]:
    """A non-existing variant of ``target_path``: append `` (2)``, `` (3)`` ... (REQ-FF-002).

    Returns ``target_path`` itself when it does not exist; a `` (n)`` variant otherwise; None when
    no unique name can be formed within ``max_tries`` (caller then SKIPS — never overwrites)."""
    if not os.path.exists(target_path):
        return target_path
    d = os.path.dirname(target_path)
    base = os.path.basename(target_path)
    stem, ext = os.path.splitext(base)
    for n in range(2, max_tries + 1):
        cand = os.path.join(d, f"{stem} ({n}){ext}")
        if not os.path.exists(cand):
            return cand
    return None


# --------------------------------------------------------------------------- #
# Per-track rename plan (pure given a Track + cfg)
# --------------------------------------------------------------------------- #

@dataclass
class RenamePlan:
    """A proposed rename for one track (computed without touching disk)."""
    key: str
    verdict: str                       # consistent | flagged | indeterminate
    old_basename: str
    new_basename: str = ""             # "" when no rename is proposed (consistent/indeterminate/unbuildable)

    @property
    def would_rename(self) -> bool:
        return bool(self.new_basename) and self.new_basename != self.old_basename


def plan_for_track(track: Any, cfg: Any) -> RenamePlan:
    """Compute the consistency verdict + (for a flagged track) the canonical basename. Pure.

    Returns a ``RenamePlan``. A CONSISTENT or INDETERMINATE track gets no ``new_basename`` (nothing
    to rename). A FLAGGED track gets the canonical basename when one can be built (else "" — the
    unbuildable/unknown-tag skip, REQ-FF-003). Does NOT consult the filesystem for collisions (the
    live rename path disambiguates under the lock); a dry-run reports this proposed name.
    """
    old_basename = os.path.basename(getattr(track, "path", "") or "")
    artist = getattr(track, "artist", "") or ""
    title = getattr(track, "title", "") or ""
    verdict = classify_consistency(old_basename, artist, title)
    if verdict != FLAGGED:
        return RenamePlan(key=getattr(track, "key", ""), verdict=verdict, old_basename=old_basename)
    ext = os.path.splitext(old_basename)[1]
    template = str(getattr(cfg, "filename_scheme_template", "{artist} - {title}") or "{artist} - {title}")
    new_basename = build_canonical_basename(
        artist, title, ext, leading_prefix=leading_number_prefix(old_basename), template=template,
    ) or ""
    return RenamePlan(
        key=getattr(track, "key", ""), verdict=verdict,
        old_basename=old_basename, new_basename=new_basename,
    )


# --------------------------------------------------------------------------- #
# The hygiene engine — detect/flag (default) + optional gated rename
# --------------------------------------------------------------------------- #

class FilenameHygiene:
    """Detect-and-flag (default) + optional gated rename over a Library, playout-safe.

    Construction takes the same (cfg, library, state) the other workers do. Every public method is
    best-effort + exception-isolated: a fault LOGS and degrades to leaving the file as-is (NFR-F-5),
    never raising into the caller. Detection records a per-track flag on ``Track.provenance`` via
    the ANALYSIS-writable allowlist (never touches a frozen identity field). The rename is gated on
    BOTH ``filename_rename_enabled`` AND the write-files discipline, never touches the in-flight
    file, and uses ``Library.rename_track_file`` for the atomic path update.
    """

    def __init__(self, cfg: Any, library: Any, state: Any = None):
        self.cfg = cfg
        self.library = library
        self.state = state

    # -- gating ------------------------------------------------------------------

    def rename_active(self) -> bool:
        """True only when rename is opt-in ON *and* the write-files discipline permits a write.

        The asymmetry that makes the SPEC safe (REQ-FR-001, NFR-F-6): a fresh install (rename OFF)
        renames ZERO files; even with the rename toggle on, the SHARED ``enrich_write_files`` write
        discipline must also permit an on-disk write.
        """
        return bool(getattr(self.cfg, "filename_rename_enabled", False)) and \
            bool(getattr(self.cfg, "enrich_write_files", False))

    # -- detection (always-on default) -------------------------------------------

    def detect(self, key: str) -> str:
        """Classify ONE track + record its consistency flag on provenance. Returns the verdict.

        Read-only w.r.t. the filesystem (REQ-FD-002): it inspects the name + records a per-track
        flag, it renames nothing. Exception-isolated: any fault logs + returns INDETERMINATE.
        """
        try:
            track = self._track(key)
            if track is None:
                return INDETERMINATE
            verdict = classify_consistency(
                getattr(track, "path", "") or "",
                getattr(track, "artist", "") or "",
                getattr(track, "title", "") or "",
            )
            self._record_flag(key, track, verdict)
            log_event(
                log, "filename.flag", key=key, verdict=verdict,
                basename=os.path.basename(getattr(track, "path", "") or ""),
            )
            return verdict
        except Exception as exc:  # noqa: BLE001 - detection is best-effort; never fatal.
            log_event(log, "filename.detect_error", key=key, error=str(exc))
            return INDETERMINATE

    def _record_flag(self, key: str, track: Any, verdict: str) -> None:
        """Persist the consistency verdict on Track.provenance via the ANALYSIS allowlist writer.

        provenance is an ANALYSIS-006-writable field, so set_analysis can never touch a frozen
        identity field (NFR-F-4). The flag is queryable for the report by reading provenance.
        """
        try:
            prov = dict(getattr(track, "provenance", {}) or {})
            prov["filename_flag"] = verdict
            self.library.set_analysis(key, {"provenance": prov})
        except Exception as exc:  # noqa: BLE001 - flag write is best-effort.
            log_event(log, "filename.flag_write_error", key=key, error=str(exc))

    # -- playout-safety guard (Group FS) -----------------------------------------

    def in_flight(self, track: Any) -> bool:
        """True if the file is on air / just handed out / in the (conservatively-bounded) prefetch
        horizon and so MUST NOT be renamed (REQ-FS-001).

        Consults ``now_playing()['path']`` + ``last_committed_path()`` directly, and — because
        ``state.py`` tracks only ONE handed-out path but ``/api/next`` runs up to prefetch=2 ahead
        (R-F-1) — ALSO defers any track whose dedup key is still in the recent-keys window (which
        unions the just-committed keys). That conservative union never renames a path Liquidsoap is
        about to fetch. No state -> nothing is considered in flight (still safe in tests).
        """
        if self.state is None:
            return False
        path = getattr(track, "path", "") or ""
        try:
            np = self.state.now_playing() or {}
            if path and np.get("path") == path:
                return True
            if path and self.state.last_committed_path() == path:
                return True
            key = getattr(track, "key", "") or ""
            if key:
                from .library import normalize_key  # noqa: PLC0415 - lazy; avoids an import cycle.
                if key in set(self.state.recent_keys(normalize_key)):
                    return True
        except Exception as exc:  # noqa: BLE001 - a state read fault -> treat as in flight (safe).
            log_event(log, "filename.inflight_check_error", error=str(exc))
            return True
        return False

    # -- preview / dry-run (REQ-FR-005) ------------------------------------------

    def preview(self) -> List[Dict[str, str]]:
        """Compute every ``old -> new`` rename that WOULD be performed, WITHOUT touching disk and
        WITHOUT updating any Track.path, regardless of the rename toggle (REQ-FR-005).

        Returns a list of ``{key, old, new}`` for flagged tracks with a buildable canonical name.
        """
        out: List[Dict[str, str]] = []
        try:
            for track in self.library.query(limit=None):
                plan = plan_for_track(track, self.cfg)
                if plan.would_rename:
                    out.append({"key": plan.key, "old": plan.old_basename, "new": plan.new_basename})
        except Exception as exc:  # noqa: BLE001 - preview is best-effort.
            log_event(log, "filename.preview_error", error=str(exc))
        return out

    # -- the gated rename of ONE track (Group FR/FS/FF) --------------------------

    def rename_one(self, key: str) -> Dict[str, Any]:
        """Rename ONE flagged, eligible, not-in-flight track to its canonical name (gated).

        Returns ``{renamed, reason, old, new}``. ``reason``: ``disabled`` (gate off), ``missing``,
        ``not-flagged`` (consistent/indeterminate -> idempotent skip, REQ-FR-004), ``unbuildable``
        (unknown tags / can't form a valid name -> skip, REQ-FF-003), ``in-flight`` (deferred,
        REQ-FS-001), ``collision`` (no unique name -> skip, never overwrite, REQ-FF-002), ``ok``,
        or ``error`` (rolled back). NEVER raises; never blocks playout.
        """
        result = {"renamed": False, "reason": "disabled", "old": "", "new": ""}
        if not self.rename_active():
            return result
        try:
            track = self._track(key)
            if track is None:
                result["reason"] = "missing"
                return result
            plan = plan_for_track(track, self.cfg)
            result["old"] = plan.old_basename
            if plan.verdict != FLAGGED:
                result["reason"] = "not-flagged"  # idempotent: consistent/indeterminate -> skip.
                return result
            if not plan.new_basename:
                result["reason"] = "unbuildable"  # FF-003: unknown tag / invalid name -> skip.
                return result
            if self.in_flight(track):
                result["reason"] = "in-flight"     # FS-001: defer the on-air/handed-out file.
                return result
            # FF-002 collision: disambiguate to a non-existing target (never overwrite). Library
            # re-checks the collision under the lock too (race-safe).
            directory = os.path.dirname(getattr(track, "path", "") or "") or "."
            unique = disambiguate(os.path.join(directory, plan.new_basename))
            if unique is None:
                result["reason"] = "collision"
                return result
            final_basename = os.path.basename(unique)
            result["new"] = final_basename
            outcome = self.library.rename_track_file(key, final_basename)
            result["renamed"] = bool(outcome.get("renamed"))
            result["reason"] = "ok" if outcome.get("renamed") else outcome.get("reason", "error")
            if result["renamed"]:
                self._record_rename(key, plan.old_basename, final_basename)
                # The file's flag is now consistent (its name carries the canonical tags).
                self._record_flag(key, self._track(key) or track, CONSISTENT)
            log_event(
                log, "filename.rename", key=key, old=plan.old_basename,
                new=final_basename, renamed=result["renamed"], reason=result["reason"],
            )
            return result
        except Exception as exc:  # noqa: BLE001 - rename is best-effort; degrade to leave-as-is.
            log_event(log, "filename.rename_error", key=key, error=str(exc))
            result["reason"] = "error"
            return result

    def _record_rename(self, key: str, old_basename: str, new_basename: str) -> None:
        """Record the reversible old->new mapping on provenance (REQ-FR-004)."""
        try:
            track = self._track(key)
            if track is None:
                return
            prov = dict(getattr(track, "provenance", {}) or {})
            history = list(prov.get("filename_renames", []) or [])
            history.append({"old": old_basename, "new": new_basename})
            prov["filename_renames"] = history
            self.library.set_analysis(key, {"provenance": prov})
        except Exception as exc:  # noqa: BLE001 - the reversible record is best-effort.
            log_event(log, "filename.rename_record_error", key=key, error=str(exc))

    # -- bounded pass over the library (detect-and-flag + optional rename) --------

    def run_once(self) -> Dict[str, int]:
        """One bounded pass: detect+flag every track; when rename is active, rename flagged,
        eligible, not-in-flight tracks. Returns coarse counters. Exception-isolated per track."""
        counts = {"consistent": 0, "flagged": 0, "indeterminate": 0, "renamed": 0}
        try:
            keys = [getattr(t, "key", "") for t in self.library.query(limit=None)]
        except Exception as exc:  # noqa: BLE001 - a read fault -> empty pass.
            log_event(log, "filename.run_error", error=str(exc))
            return counts
        active = self.rename_active()
        for key in keys:
            if not key:
                continue
            verdict = self.detect(key) if getattr(self.cfg, "filename_detect_enabled", True) else INDETERMINATE
            counts[verdict] = counts.get(verdict, 0) + 1
            if active and verdict == FLAGGED:
                if self.rename_one(key).get("renamed"):
                    counts["renamed"] += 1
        return counts

    # -- helpers -----------------------------------------------------------------

    def _track(self, key: str) -> Optional[Any]:
        """Best-effort snapshot of one track by key via the library's locked read accessor."""
        try:
            for t in self.library.query(limit=None):
                if getattr(t, "key", "") == key:
                    return t
        except Exception:  # noqa: BLE001 - a read fault -> no track.
            return None
        return None


# --------------------------------------------------------------------------- #
# Background backfill worker (mirrors EnrichmentWorker)
# --------------------------------------------------------------------------- #

class FilenameWorker:
    """Background, serialized, NON-BLOCKING filename-hygiene worker (mirrors EnrichmentWorker).

    One daemon thread. Each tick runs ``FilenameHygiene.run_once`` (detect-and-flag, plus the gated
    rename when active), off the <1s ``/api/next`` pull path, throttled while downloads are in
    flight. Started only when detection is enabled; the rename half stays OFF until the operator
    opts in (REQ-FR-001). Every tick is exception-isolated so it never crashes the daemon or stalls
    playout (NFR-F-5).
    """

    def __init__(self, cfg: Any, library: Any, state: Any, stop_event: threading.Event):
        self.cfg = cfg
        self.library = library
        self.state = state
        self.stop_event = stop_event
        self.hygiene = FilenameHygiene(cfg, library, state)
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if not getattr(self.cfg, "filename_detect_enabled", True):
            log_event(log, "filename.disabled")
            return
        self._thread = threading.Thread(target=self._loop, name="filename", daemon=True)
        self._thread.start()
        log_event(
            log, "filename.started",
            interval=int(getattr(self.cfg, "analysis_interval_seconds", 30)),
            rename_active=self.hygiene.rename_active(),
        )

    def _loop(self) -> None:
        poll = max(1, int(getattr(self.cfg, "analysis_interval_seconds", 30)))
        while not self.stop_event.is_set():
            self.stop_event.wait(poll)
            if self.stop_event.is_set():
                break
            try:
                self._tick()
            except Exception as exc:  # noqa: BLE001 - resilience: never crash the loop.
                log_event(log, "filename.tick_error", error=str(exc))

    def _tick(self) -> None:
        # THROTTLE: back off while downloads are in flight (mirror the analysis/enrich rule —
        # compare the LENGTH of the list, never ``list >= int``).
        active = len(self.state.downloading()) if self.state is not None else 0
        if active >= max(0, int(getattr(self.cfg, "analysis_max_concurrent_downloads", 1))):
            return
        counts = self.hygiene.run_once()
        if counts.get("flagged") or counts.get("renamed"):
            log_event(log, "filename.pass_done", **counts)
