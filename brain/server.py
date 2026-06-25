"""HTTP server on :8080 (stdlib, ThreadingHTTPServer - no extra deps).

Endpoints:
  GET  /api/next        text/plain - a Liquidsoap ``annotate:`` URI for the next item
                        (clean ICY artist/title + mix_mode + the real /music path), or
                        EMPTY body (200) if nothing is ready. COMMITS rotation/cadence.
  POST /api/airing      Liquidsoap reports the item it JUST put on air (form fields:
                        artist, title, kind, [path]); sets the GROUND-TRUTH now_playing.
                        Also accepted as GET with the same query params.
  POST /api/skip        SKIP-028 forceful on-air skip, gated by SkipGovernor. Returns
                        JSON {accepted, reason, refusal_cause, airing_path, expect_path}.
  GET  /status          JSON station state.
  GET  /api/nowplaying  JSON {now_playing, recent, library, downloading}.
  GET  /                the station website (swappable HTML from StationState).
  GET  /health          "ok".

The next-item picker is intentionally factored so a FUTURE phase can return either
a music track OR a pre-rendered talk clip (see brain.voice). /api/next must respond
in <1s and never block on acquisition - it only reads the library + commits.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

from urllib.parse import parse_qs, unquote, urlsplit

from .config import Config
from .library import Library, Track, normalize_key
from .logging_setup import log_event

log = logging.getLogger("brain.server")


def _annotate_uri(
    artist: str,
    title: str,
    mix_mode: str,
    path: str,
    extra: Optional[dict] = None,
    album: str = "",
) -> str:
    """Build a Liquidsoap ``annotate:`` URI carrying the brain's CLEAN metadata.

    Players (VLC etc.) show the in-stream ICY StreamTitle, which otherwise comes from
    each file's embedded tags - sometimes garbled (e.g. "Sly & the Familt Stone").
    Returning ``annotate:artist="...",title="...",mix_mode="...":/path`` lets Liquidsoap
    override the file tags with the brain's clean artist/title for the ICY metadata, and
    carries ``mix_mode`` so radio.liq can pick the right transition (music vs talk).

    ANALYSIS-006 (REQ-AT-005 / AT-006): ``extra`` carries the per-item transition
    metadata (``liq_cue_in`` / ``liq_cue_out`` / ``bpm`` / ``camelot`` / ``energy``) that
    the analysis pipeline produced. It is appended to the SAME annotate string only when
    a track has an analysis record. [HARD AT-006] When ``extra`` is None/empty the output
    is BYTE-IDENTICAL to the legacy form, so an unanalyzed track gets exactly the
    transition behaviour it got before this SPEC (no regression). The caller passes
    ``extra`` ONLY when ``track.schema_version > 0``.

    Values are JSON-escaped and wrapped in double quotes (Liquidsoap's annotate parser
    accepts double-quoted values; this safely handles embedded quotes, commas, colons,
    backslashes and ampersands). The trailing ``:`` separates the annotation from the
    real file path, which Liquidsoap then resolves normally via request.create.
    """
    def q(s: str) -> str:
        # json.dumps yields a double-quoted, fully-escaped string literal, which is
        # exactly the token form Liquidsoap's annotate: parser expects for a value.
        return json.dumps(s if s else "", ensure_ascii=False)

    # Album (from id3 tags) is appended as a core annotate field when present, so
    # radio.liq can fold it into the player ICY StreamTitle and report it to the brain
    # for the website. Empty-safe: an untagged track omits it and the string is unchanged.
    base = f"artist={q(artist)},title={q(title)},mix_mode={q(mix_mode)}"
    if album:
        base += f",album={q(album)}"
    if not extra:
        # AT-006: legacy form, byte-identical to the pre-ANALYSIS-006 string.
        return f"annotate:{base}:{path}"

    # Numeric annotate values are emitted UNQUOTED (Liquidsoap reads them as floats in
    # the transition function). Only finite, present values are appended so a missing
    # field never injects an empty/garbage token.
    extra_parts = []
    for name in ("liq_cue_in", "liq_cue_out", "bpm", "camelot", "energy"):
        val = extra.get(name)
        if val is None:
            continue
        if name == "camelot":
            if not str(val).strip():
                continue
            extra_parts.append(f"{name}={q(str(val))}")
        else:
            try:
                num = float(val)
            except (TypeError, ValueError):
                continue
            if num != num:  # NaN guard
                continue
            extra_parts.append(f"{name}={num}")
    if not extra_parts:
        # Nothing usable to add → fall back to the byte-identical legacy form.
        return f"annotate:{base}:{path}"
    return f"annotate:{base},{','.join(extra_parts)}:{path}"


def _analysis_extra(track: Optional[Track]) -> Optional[dict]:
    """Per-item transition metadata for an ANALYZED track, or None (AT-006).

    Returns the ``liq_cue_in`` / ``liq_cue_out`` / ``bpm`` / ``camelot`` / ``energy``
    dict ONLY when the track carries an analysis record (``schema_version > 0``). For an
    unanalyzed track (or a talk clip, which has no Track) it returns None so the caller
    emits the byte-identical legacy annotate string with the safe-default crossfade.
    ``cue_in`` / ``cue_out`` map to Liquidsoap's native ``liq_cue_in`` / ``liq_cue_out``.
    """
    if track is None or track.schema_version <= 0:
        return None
    return {
        "liq_cue_in": track.cue_in,
        "liq_cue_out": track.cue_out,
        "bpm": track.bpm if track.bpm else None,
        "camelot": track.camelot or None,
        "energy": track.energy if track.energy else None,
    }


def _feature_fields(track: Optional[Track]) -> dict:
    """TAGSTREAM-009 REQ-TX-003: the listener-facing feature fields for an ANALYZED track.

    Returns the bpm / musical_key / camelot / energy (+ a has_cover hint) for the now-playing
    panel — DISTINCT from ``_analysis_extra`` (the Liquidsoap crossfade math). Returns {} for a
    talk clip (no Track), an unanalyzed track, or an unresolved path, so the caller adds nothing
    and the now-playing object keeps its existing artist/title-only shape (graceful degradation).
    Only PRESENT, meaningful values are emitted — a missing feature is omitted, never a 0/"".
    """
    if track is None or getattr(track, "schema_version", 0) <= 0:
        return {}
    out: dict = {}
    bpm = getattr(track, "bpm", 0.0) or 0.0
    if bpm:
        out["bpm"] = round(float(bpm), 1)
    musical_key = (getattr(track, "musical_key", "") or "").strip()
    if musical_key:
        out["musical_key"] = musical_key
    camelot = (getattr(track, "camelot", "") or "").strip()
    if camelot:
        out["camelot"] = camelot
    energy = getattr(track, "energy", 0.0) or 0.0
    if energy:
        out["energy"] = round(float(energy), 3)
    out["has_cover"] = bool(getattr(track, "art_version", 0) or 0)
    return out


def _enrich_now_playing(obj: Optional[dict], library: Library) -> Optional[dict]:
    """ADDITIVELY enrich a now-playing/recent object with the on-air track's features (REQ-TX-003).

    Resolves the object's ``path`` (carried by set_on_air / now_playing) to the analyzed Track
    via the by-path lookup and merges in bpm/musical_key/camelot/energy + has_cover. [HARD]
    Additive only: the existing artist/title/album/path/kind keys are NEVER removed or renamed;
    feature keys are only ADDED when the track resolves AND is analyzed. None / a missing path /
    an unresolved or unanalyzed track yields the object UNCHANGED — never a crash, never a stale
    enrichment. This wiring lives entirely in the brain; the Liquidsoap airing payload is
    UNCHANGED (the audio path / _annotate_uri pull contract are untouched).
    """
    if not obj:
        return obj
    path = obj.get("path") or ""
    if not path:
        return obj
    try:
        track = library.track_for_path(path)
    except Exception:  # noqa: BLE001 - a lookup error must never break the now-playing surface
        return obj
    feats = _feature_fields(track)
    if not feats:
        return obj
    enriched = dict(obj)
    enriched.update(feats)
    return enriched


@dataclass
class NextItem:
    """What /api/next will serve. ``kind`` is "music" or "talk" (phase 2a)."""
    container_path: str
    artist: str
    title: str
    album: str = ""  # from id3 tags (mutagen) via Track.album; "" for talk / untagged
    kind: str = "music"  # "music" | "talk"
    track: Optional[Track] = None  # set for music, for play-history commit


class Picker:
    """Chooses the next item to broadcast: a music track or a host talk clip.

    MUST stay fast and non-blocking (<1s) - it only READS state + the library and
    commits. Talk clips are pre-rendered by brain.talk.TalkDirector and parked in
    StationState; the picker just consumes a ready one. If a break is due but no clip
    is ready yet, it falls through to music (talk is strictly best-effort), so Liquidsoap
    plays the talk MP3 like any other pulled file - no radio.liq change needed.
    """

    def __init__(self, cfg: Config, library: Library, state, refiner=None, no_orphan=None):
        self.cfg = cfg
        self.library = library
        self.state = state
        # SPEC-RADIO-OPS-004 Group OA (REQ-OA-003*): the soft+hard separation SelectionRefiner +
        # the no-orphan bootstrap (the is_unscheduled gate for REQ-OA-003d). [HARD] OFF by default:
        # when None (cfg.scheduling_enabled off) the music branch calls library.pick_next UNCHANGED
        # — the <1s playout pull is BYTE-IDENTICAL to before this SPEC. When wired, the refiner
        # re-scores the SAME legal-and-LRP-ranked candidate set; the hard no-repeat/LRP rail
        # (REQ-OA-003a, produced by the library) is never relaxed by the soft layer.
        self.refiner = refiner
        self.no_orphan = no_orphan

    def pick(self) -> Optional[NextItem]:
        # --- Talk-clip branch: if a break is due AND a clip is pre-rendered, serve it.
        # take_pending_talk() atomically removes the clip and resets the cadence counter,
        # so we never double-serve and never block on generation here.
        # The first-run welcome is force-served the instant it is parked, BEFORE the first
        # song (it does not wait for the songs-since-talk cadence). A normal break is served
        # when the cadence counter says one is due. Capture is_welcome BEFORE take (take
        # clears the flag) so we can persist the genesis marker on serve.
        is_welcome = self.cfg.talk_enabled and self.state.pending_is_welcome()
        break_due = self.cfg.talk_enabled and \
            self.state.songs_since_talk() >= max(1, self.cfg.talk_every_n_tracks)
        if is_welcome or break_due:
            clip = self.state.take_pending_talk()
            if clip is not None:
                if is_welcome:
                    # Once-per-genesis: clear the debt and persist the marker so a brain
                    # restart mid-broadcast never re-welcomes listeners.
                    self.state.note_welcome_served()
                    self._mark_welcomed()
                # Talk clips already carry a container path under /music/.talk.
                title = clip.text if len(clip.text) <= 80 else clip.text[:77] + "..."
                return NextItem(
                    container_path=clip.container_path,
                    artist=self.state.station_name,
                    title=title,
                    kind="talk",
                    track=None,
                )
            # Break is due but the clip isn't ready -> just play music this time.

        # --- Music branch (default): least-recently-played, avoiding the recent window.
        # Exclude the LAST COMMITTED path (not the on-air now_playing): /api/next is
        # called up to prefetch=2 ahead, so the just-handed-out file has not reached
        # air yet and is what we must avoid re-picking on the very next prefetch.
        exclude_path = self.state.last_committed_path()
        recent_keys = self.state.recent_keys(normalize_key)
        if self.refiner is None:
            # [HARD] BYTE-IDENTICAL default path (REQ-OA-003a): the unchanged LRP picker.
            track = self.library.pick_next(exclude_path, recent_keys)
        else:
            track = self._pick_refined(exclude_path, recent_keys)
        if track is None:
            return None
        return NextItem(
            container_path=self.cfg.container_music_path(track.path),
            artist=track.artist,
            title=track.title,
            album=track.album,
            kind="music",
            track=track,
        )

    def _pick_refined(self, exclude_path, recent_keys):
        """The OPS-004 refined pick (REQ-OA-003*): re-score the library's legal-and-LRP-ranked
        candidate set with the hard artist rails + soft separations + (off-schedule only) the
        genre-family balance + smooth adjacency. Best-effort: any fault degrades to the unchanged
        LRP head (continuity wins, REQ-OA-008). The is_unscheduled gate (REQ-OA-003d(c)) comes
        from the no-orphan bootstrap; with none wired we default to the unscheduled lane."""
        candidates = self.library.legal_candidates(exclude_path, recent_keys)
        if not candidates:
            return None
        try:
            recent = self.state.recent()
            recent_artists = [r.get("artist", "") for r in recent if r.get("artist")]
            last_track = None
            if recent:
                last_path = recent[0].get("path")
                if last_path:
                    last_track = self.library.track_for_path(last_path)
            from . import schedule as _schedule
            window_families = [
                _schedule.genre_family(t)
                for t in (self.library.track_for_path(r.get("path"))
                          for r in recent if r.get("path")) if t is not None
            ]
            is_unscheduled = (self.no_orphan.is_unscheduled_now()
                              if self.no_orphan is not None else True)
            result = self.refiner.refine(
                candidates, last_track=last_track, recent_artists=recent_artists,
                window_families=window_families, is_unscheduled=is_unscheduled)
            return result.track if result is not None else candidates[0]
        except Exception:  # noqa: BLE001 - the refiner is best-effort; the LRP head always plays
            return candidates[0]

    def commit(self, item: NextItem) -> None:
        """Advance ROTATION state at hand-out time so successive /api/next calls move
        forward. This does NOT set the displayed now_playing - that is ground-truth and
        driven by airing reports (POST /api/airing -> state.set_on_air), so the website
        never leads the broadcast. Rotation, play-history and talk cadence MUST stay
        here (at commit), because /api/next prefetches up to 2 items ahead of air."""
        self.state.note_committed(
            item.artist, item.title, item.container_path, item.kind, normalize_key
        )
        if item.track is not None:
            self.library.mark_played(item.track)
        # Cadence: count music plays toward the next talk break. (Serving a talk clip
        # already reset the counter in take_pending_talk, so we only bump on music.)
        if item.kind == "music":
            self.state.note_song_played()

    def _mark_welcomed(self) -> None:
        """Persist the once-per-genesis welcome marker (DB_DIR/welcomed). Best-effort: a
        write failure only risks re-welcoming on the next restart, never breaks playout."""
        try:
            path = self.cfg.welcome_marker_path
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("welcomed\n")
            log_event(log, "picker.welcome_marker_written", path=path)
        except Exception as exc:  # noqa: BLE001 - marker is best-effort
            log_event(log, "picker.welcome_marker_error", error=str(exc))


class _Handler(BaseHTTPRequestHandler):
    # Injected on the server instance (see make_server).
    cfg: Config
    library: Library
    state = None
    picker: Picker = None  # type: ignore
    knowledge = None  # KNOWLEDGE-008 store (optional; None when disabled) for /status
    roster = None  # SPEC-RADIO-PROGRAMMING-007 Group PR persona roster (optional; None = none configured)
    skip_governor = None  # SPEC-RADIO-SKIP-028 SkipGovernor (optional; None = skip disabled)
    like_gate = None  # SPEC-RADIO-LIKE-015 LikeGate (optional; None when like_enabled off)
    like_tokener = None  # SPEC-RADIO-LIKE-015 LikeTokener (optional; None when like_enabled off)
    drop_off_engine = None  # SPEC-RADIO-LIKE-015 DropOffEngine (optional; None when off)
    analytics = None  # SPEC-RADIO-STATS-013 PlayEventsStore (optional; None when stats disabled)

    # SPEC-RADIO-ADMIN-041: station-wide emergency flags. Class-level on purpose — they are
    # shared across every handler instance (one ThreadingHTTPServer spawns a handler per
    # request) so a toggle from one admin POST affects the next /api/next pull.
    # @MX:WARN: mutable class-level flags shared across all request-handler threads
    # @MX:REASON: a station-wide silence/inject signal must outlive a single request handler instance
    _silence_mode: bool = False
    _injected_uri: str = ""

    server_version = "GSRBrain/1.0"

    def log_message(self, fmt, *args):  # silence default stderr logging
        return

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        # Liquidsoap and the browser poller both want fresh data.
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_HEAD(self):  # noqa: N802
        self.do_GET()

    def do_POST(self):  # noqa: N802 - airing reports come in as POST from radio.liq
        split = urlsplit(self.path)
        path = split.path.rstrip("/") or "/"
        try:
            if path == "/api/airing":
                self._handle_airing(split.query)
            elif path == "/api/skip":
                self._handle_skip()
            elif path == "/api/like":
                self._handle_like()
            elif path == "/api/personas":
                # SPEC-RADIO-PROGRAMMING-007 REQ-PR-010/011: create a persona.
                self._handle_persona_create()
            elif path.startswith("/api/personas/") and path.endswith("/disable"):
                self._handle_persona_lifecycle(path.split("/")[3], "disable")
            elif path.startswith("/api/personas/") and path.endswith("/enable"):
                self._handle_persona_lifecycle(path.split("/")[3], "enable")
            elif path.startswith("/admin/"):
                self._handle_admin_post(path, split.query)
            else:
                self._send(404, b"not found", "text/plain; charset=utf-8")
        except Exception as exc:  # noqa: BLE001 - never let a request crash the server
            log_event(log, "server.request_error", path=path, error=str(exc))
            # Airing is best-effort: ack with 200 so the streaming thread never stalls.
            self._send(200, b"error", "text/plain; charset=utf-8")

    def do_PUT(self):  # noqa: N802 - persona EDIT (REQ-PR-013a)
        split = urlsplit(self.path)
        path = split.path.rstrip("/") or "/"
        try:
            if path.startswith("/api/personas/"):
                self._handle_persona_edit(path.split("/")[3])
            else:
                self._send(404, b"not found", "text/plain; charset=utf-8")
        except Exception as exc:  # noqa: BLE001
            log_event(log, "server.request_error", path=path, error=str(exc))
            self._send(500, b"error", "text/plain; charset=utf-8")

    def do_DELETE(self):  # noqa: N802 - persona RESET / cascade-purge (REQ-PR-013c/PR-016)
        split = urlsplit(self.path)
        path = split.path.rstrip("/") or "/"
        try:
            if path.startswith("/api/personas/"):
                self._handle_persona_reset(path.split("/")[3])
            else:
                self._send(404, b"not found", "text/plain; charset=utf-8")
        except Exception as exc:  # noqa: BLE001
            log_event(log, "server.request_error", path=path, error=str(exc))
            self._send(500, b"error", "text/plain; charset=utf-8")

    def do_GET(self):  # noqa: N802
        split = urlsplit(self.path)
        path = split.path.rstrip("/") or "/"
        try:
            if path == "/api/next":
                self._handle_next()
            elif path == "/api/airing":
                # GET fallback so radio.liq may report via either verb.
                self._handle_airing(split.query)
            elif path == "/status":
                self._handle_status()
            elif path == "/api/nowplaying":
                self._handle_nowplaying()
            elif path == "/api/like-token":
                self._handle_like_token()
            elif path == "/api/personas":
                self._handle_persona_list()
            elif path == "/health":
                self._send(200, b"ok", "text/plain; charset=utf-8")
            elif path == "/stats":
                self._handle_stats(split.query)
            elif path.startswith("/stats/track/"):
                self._handle_stats_track(path[len("/stats/track/"):])
            elif path == "/admin" or path.startswith("/admin/"):
                self._handle_admin_get(path, split.query)
            elif path == "/":
                self._handle_root()
            else:
                self._send(404, b"not found", "text/plain; charset=utf-8")
        except Exception as exc:  # noqa: BLE001 - never let a request crash the server
            log_event(log, "server.request_error", path=path, error=str(exc))
            # For /api/next, an empty 200 keeps Liquidsoap retrying gracefully.
            if path == "/api/next":
                self._send(200, b"", "text/plain; charset=utf-8")
            else:
                self._send(500, b"error", "text/plain; charset=utf-8")

    # -- handlers ----------------------------------------------------------------

    def _handle_next(self) -> None:
        # ADMIN-041 silence mode: hold on the current track — serve nothing new. Liquidsoap
        # treats the empty 200 as "retry later" and keeps the current item playing out.
        if _Handler._silence_mode:
            self._json({"silence": True})
            return
        # ADMIN-041 inject: an operator-queued URI plays once, ahead of the normal picker.
        if _Handler._injected_uri:
            uri = _Handler._injected_uri
            _Handler._injected_uri = ""
            log_event(log, "server.next_injected", uri=uri)
            self._send(200, uri.encode("utf-8"), "text/plain; charset=utf-8")
            return
        item = self.picker.pick()
        if item is None:
            # Nothing ready: empty 200 so Liquidsoap retries (per radio.liq).
            self._send(200, b"", "text/plain; charset=utf-8")
            return
        self.picker.commit(item)
        extra = None
        album = ""
        if item.kind == "talk":
            # During a host break players just show the station identity — NOT a noisy
            # script line and NOT a "— host break" suffix. Just the station name: empty
            # artist + station name as the title yields a clean "<Station>" StreamTitle.
            mix_mode = "talk"
            icy_artist = ""
            icy_title = self.state.station_name
        else:
            mix_mode = "music"
            icy_artist = item.artist
            icy_title = item.title
            album = item.album
            # ANALYSIS-006 (AT-006): attach transition metadata ONLY when the track has
            # an analysis record (schema_version > 0). An unanalyzed track gets the
            # byte-identical legacy annotate string (no regression, safe defaults).
            extra = _analysis_extra(item.track)
        uri = _annotate_uri(icy_artist, icy_title, mix_mode, item.container_path, extra, album=album)
        log_event(
            log, "server.next",
            path=item.container_path, kind=item.kind, title=icy_title, mix_mode=mix_mode,
        )
        # Return the annotate: URI (clean ICY metadata + transition hint) instead of a
        # bare path. Liquidsoap's request.create resolves the trailing real file path.
        self._send(200, uri.encode("utf-8"), "text/plain; charset=utf-8")

    def _handle_airing(self, query: str) -> None:
        """Ground-truth now-playing: Liquidsoap POSTs (or GETs) the item it JUST put on
        air. We update the displayed now_playing the instant the track changes, so the
        website / /api/nowplaying / /status reflect what is airing RIGHT NOW - never the
        prefetched (up to 2-ahead) committed item, and never a stale hang between hands.

        Accepts both POST body (application/x-www-form-urlencoded) and GET query so the
        radio.liq side can use whichever http verb is simplest/non-blocking. Fields:
        artist, title, kind (music|talk), optional path. Always returns 200 quickly so
        the streaming-thread caller never stalls; a bad report is logged, not fatal."""
        params: dict = {}
        # POST body (preferred): form-encoded fields.
        if self.command == "POST":
            try:
                length = int(self.headers.get("Content-Length", "0") or "0")
            except ValueError:
                length = 0
            body = self.rfile.read(length) if length > 0 else b""
            params.update(parse_qs(body.decode("utf-8", "replace"), keep_blank_values=True))
        # Also fold in any query-string params (GET fallback / belt-and-braces).
        if query:
            params.update(parse_qs(query, keep_blank_values=True))

        def first(name: str, default: str = "") -> str:
            v = params.get(name)
            return v[0] if v else default

        artist = first("artist")
        title = first("title")
        album = first("album")
        kind = first("kind", "music") or "music"
        path = first("path")
        if not artist and not title:
            # Nothing useful (e.g. an empty metadata packet) - ack and ignore.
            self._send(200, b"ignored", "text/plain; charset=utf-8")
            return
        changed = self.state.set_on_air(artist, title, kind=kind, path=path, album=album)
        if changed:
            log_event(log, "server.airing", artist=artist, title=title, kind=kind)
            # REQ-SG-008: a new airing report that was not from a skip = natural completion.
            # We notify the governor to reset the consecutive counter.
            if self.skip_governor is not None:
                try:
                    self.skip_governor.on_natural_completion()
                except Exception:  # noqa: BLE001
                    pass
            # SPEC-RADIO-LIKE-015 REQ-LD-001: snapshot the audience at the moment a MUSIC track
            # starts on air, so the bounded drop-off poll can measure disconnects in the window.
            # Best-effort: never blocks/raises into the airing ack (the streaming thread must
            # never stall). Only music airings have a likeable/drop-off-measurable recording key.
            if self.drop_off_engine is not None and (kind or "music") == "music":
                try:
                    self.drop_off_engine.note_track_start(normalize_key(artist, title))
                except Exception:  # noqa: BLE001
                    pass
            # STATS-013 Group SE: close out the previous airing (stamp measured playtime)
            # and open a row for the one now on air. [HARD] OFF the pull path, best-effort:
            # any fault is logged-and-swallowed so a stats hiccup NEVER blocks the airing ack
            # nor silences the stream. ALL kinds are logged (music | talk | imaging) so total
            # airtime is honest; only the rankings filter to music downstream.
            if self.analytics is not None:
                try:
                    now = time.time()
                    prev = self.analytics.last_open_event()
                    if prev is not None:
                        self.analytics.close_event(
                            prev["id"], max(0.0, now - float(prev["started_at"])))
                    tk = normalize_key(artist, title) if (kind or "music") == "music" else ""
                    track = self.library.track_for_key(tk) if tk else None
                    self.analytics.open_event(
                        artist=artist, title=title, kind=kind, started_at=now,
                        track_key=tk,
                        expected_seconds=(getattr(track, "cue_out", None)
                                          or getattr(track, "true_end", None)),
                        grab_reason=getattr(track, "grab_reason", None),
                    )
                except Exception as exc:  # noqa: BLE001 - stats never blocks the stream
                    log_event(log, "server.stats_closeout_error", error=str(exc))
        self._send(200, b"ok", "text/plain; charset=utf-8")

    def _handle_skip(self) -> None:
        """SKIP-028 POST /api/skip — governor-gated restart-free forceful skip (REQ-SK-001).

        Body: JSON {reason, expect_path?}. Returns JSON accept/refuse verdict (REQ-SK-004).
        A refused skip is a normal outcome (200) with accepted=false — not a server error.
        """
        if self.skip_governor is None:
            self._json({"accepted": False, "reason": "",
                        "refusal_cause": "skip_not_configured",
                        "airing_path": "", "expect_path": ""})
            return
        body = self._read_json_body()
        reason = str(body.get("reason", "") or "").strip()
        expect_path = str(body.get("expect_path", "") or "").strip()
        decision = self.skip_governor.decide(reason, expect_path=expect_path, source="api")
        self._json({
            "accepted": decision.accepted,
            "reason": decision.reason,
            "refusal_cause": decision.refusal_cause,
            "airing_path": decision.airing_path,
            "expect_path": decision.expect_path,
            "skip_count": decision.skip_count,
        })

    def _handle_status(self) -> None:
        self._json(
            {
                "station": self.state.station_name,
                "brain_mode": "phase2a-music+talk" if self.cfg.talk_enabled else "phase1-music",
                "now_playing": _enrich_now_playing(self.state.now_playing(), self.library),
                "recent": [_enrich_now_playing(r, self.library) for r in self.state.recent()],
                "library": self.library.count(),
                "downloading": self.state.downloading(),
                "talk": {
                    "enabled": self.cfg.talk_enabled,
                    "every_n_tracks": self.cfg.talk_every_n_tracks,
                    "songs_since_talk": self.state.songs_since_talk(),
                    "clip_ready": self.state.has_pending_talk(),
                },
                "analysis": self.library.analysis_stats(),
                "knowledge": self._knowledge_stats(),
                "uptime_seconds": int(__import__("time").time() - self.state.started_at),
            }
        )

    def _knowledge_stats(self) -> dict:
        """KNOWLEDGE-008 counts for /status, mirroring the analysis block (REQ-KI-003).

        Returns the disabled marker when the store is absent so the surface is consistent
        whether or not the SPEC is enabled. Read-safe (store.stats never raises)."""
        if self.knowledge is None:
            return {"enabled": False}
        stats = self.knowledge.stats()
        stats["enabled"] = True
        return stats

    def _handle_nowplaying(self) -> None:
        payload = {
            "now_playing": _enrich_now_playing(self.state.now_playing(), self.library),
            "recent": [_enrich_now_playing(r, self.library) for r in self.state.recent()],
            "library": self.library.count(),
            "downloading": self.state.downloading(),
        }
        # SPEC-RADIO-LIKE-015: tell the frontend where to mint a like-token, but ONLY when the
        # feature is enabled (REQ-LH-002). Absent the key the player shows no heart (graceful).
        if getattr(self.cfg, "like_enabled", False) and self.like_tokener is not None:
            payload["like_token_url"] = "/api/like-token"
        self._json(payload)

    # -- like API (SPEC-RADIO-LIKE-015 Group LH/LA/LX) --------------------------- #

    def _handle_like_token(self) -> None:
        """GET /api/like-token — mint an HMAC token bound to the currently-airing track
        (REQ-LH-002 / REQ-LA-001). 404 when the feature is disabled (REQ-LX/never-half-exist).
        The token binds to the on-air now_playing's canonical recording key + issue time + nonce,
        so a like can only be cast for what is actually airing."""
        if not getattr(self.cfg, "like_enabled", False) or self.like_tokener is None:
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        np = self.state.now_playing() or {}
        if (np.get("kind", "music") or "music") != "music":
            # No like target during a talk/news/imaging break — nothing to heart.
            self._json({"token": "", "expires_at": 0, "available": False})
            return
        track_key = normalize_key(np.get("artist", ""), np.get("title", ""))
        if not track_key:
            self._json({"token": "", "expires_at": 0, "available": False})
            return
        minted = self.like_tokener.mint(track_key)
        self._json({"token": minted.get("token", ""),
                    "expires_at": minted.get("expires_at", 0),
                    "available": bool(minted.get("token"))})

    def _handle_like(self) -> None:
        """POST /api/like — validate the token + identity + rate-limit + dedup, record the soft
        like, and confirm per-listener receipt only (REQ-LA-002 / REQ-LX-001). 404 when disabled.
        Body: JSON {token}; the listener identity comes from the persistent cookie (REQ-LP-001).
        A rejected like is a normal 200 with received=false — not a server error."""
        if not getattr(self.cfg, "like_enabled", False) or self.like_gate is None:
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        body = self._read_json_body()
        token = str(body.get("token", "") or "")
        cookie_value = self._like_cookie(body)
        result = self.like_gate.record_like(token, cookie_value)
        if result.received:
            # REQ-LX-001: per-listener receipt only; no aggregate count is ever surfaced.
            self._json({"received": True})
            return
        self._json({"received": False, "reason": result.cause})

    def _like_cookie(self, body: dict) -> str:
        """Derive the listener identity source (REQ-LP-001/D-L-6): prefer a persistent cookie
        from the Cookie header (``gsr_id``); fall back to an explicit ``cookie`` body field for
        clients that cannot set cookies. The RAW value is hashed downstream — never stored."""
        raw = self.headers.get("Cookie", "") or ""
        for part in raw.split(";"):
            name, _, val = part.strip().partition("=")
            if name == "gsr_id" and val:
                return val
        return str(body.get("cookie", "") or "")

    def _handle_root(self) -> None:
        html = self.state.website_html() or "<h1>Golden Shower Radio</h1>"
        self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")

    # -- persona API (SPEC-RADIO-PROGRAMMING-007 Group PR, REQ-PR-010..016) ------ #
    #
    # The OPERATOR-driven companion to the AI-autonomous growth gate (REQ-PR-008): a
    # DIFFERENT ENTRY into the SAME persona-entity model + the SAME shared 1:1 + anti-
    # convergence validation gate (Roster.validate_candidate) — never a bypass or fork.
    # The UI/transport is deferred to implementation; this minimal JSON API is the seam.
    # Every handler returns 503 when no roster is configured (the default single-house path)
    # so the API never half-exists. DELETE is the explicit, deliberate cascade-RESET.

    def _read_json_body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except (TypeError, ValueError):
            length = 0
        raw = self.rfile.read(length) if length > 0 else b""
        if not raw:
            return {}
        try:
            obj = json.loads(raw.decode("utf-8"))
            return obj if isinstance(obj, dict) else {}
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            return {}

    @staticmethod
    def _persona_public(p) -> dict:
        """The JSON view of a persona (entity fields, no internal-only state)."""
        rec = p.to_record()
        return rec

    def _handle_persona_list(self) -> None:
        if self.roster is None:
            self._json({"enabled": False, "personas": []})
            return
        self._json({"enabled": True,
                    "personas": [self._persona_public(p) for p in self.roster.all()]})

    def _handle_persona_create(self) -> None:
        if self.roster is None:
            self._json({"ok": False, "error": "no roster configured"}, code=503)
            return
        from . import persona as persona_mod
        body = self._read_json_body()
        candidate = _persona_from_request(persona_mod, body)
        if candidate is None:
            self._json({"ok": False, "error": "invalid persona payload (id required)"}, code=400)
            return
        created, result = self.roster.create(candidate)
        if created is None:
            # Rejected by the SHARED gate (1:1 voice / anti-convergence / fields / age).
            self._json({"ok": False, "code": result.code, "reason": result.reason}, code=409)
            return
        self._json({"ok": True, "persona": self._persona_public(created)}, code=201)

    def _handle_persona_edit(self, persona_id: str) -> None:
        if self.roster is None:
            self._json({"ok": False, "error": "no roster configured"}, code=503)
            return
        from . import persona as persona_mod
        body = self._read_json_body()
        # An edit re-runs the FULL REQ-PR-011 validation (REQ-PR-013a). Charter may arrive
        # as a nested dict; rebuild it into a TasteCharter so the gate sees real fields.
        changes = dict(body)
        if isinstance(changes.get("charter"), dict):
            valid = set(persona_mod.TasteCharter.__dataclass_fields__)
            changes["charter"] = persona_mod.TasteCharter(
                **{k: v for k, v in changes["charter"].items() if k in valid})
        edited, result = self.roster.edit(persona_id, **changes)
        if edited is None:
            code = 404 if result.code == "not_found" else 409
            self._json({"ok": False, "code": result.code, "reason": result.reason}, code=code)
            return
        self._json({"ok": True, "persona": self._persona_public(edited)})

    def _handle_persona_lifecycle(self, persona_id: str, action: str) -> None:
        if self.roster is None:
            self._json({"ok": False, "error": "no roster configured"}, code=503)
            return
        ok = self.roster.disable(persona_id) if action == "disable" else self.roster.enable(persona_id)
        if not ok:
            self._json({"ok": False, "error": "persona not found"}, code=404)
            return
        self._json({"ok": True, "id": persona_id, "action": action})

    def _handle_persona_reset(self, persona_id: str) -> None:
        """DELETE = the explicit, deliberate CASCADE-RESET (REQ-PR-013c / REQ-PR-016): purge
        the entity + ALL its per-persona data and FREE its voice. Destructive — surfaced as an
        explicit DELETE verb, never an accidental side effect. Golden-rule safe (owns no
        playout)."""
        if self.roster is None:
            self._json({"ok": False, "error": "no roster configured"}, code=503)
            return
        freed_voice = self.roster.remove(persona_id)
        if freed_voice is None:
            self._json({"ok": False, "error": "persona not found"}, code=404)
            return
        self._json({"ok": True, "id": persona_id, "freed_voice": freed_voice,
                    "reset": "cascade-purge"})

    # -- STATS-013 Group SW: read-only analytics site (never controls playout) ----

    def _handle_stats(self, query: str) -> None:
        """GET /stats — server-rendered analytics page (read-only, inline SVG)."""
        if self.analytics is None:
            self._send(503, b"stats not available", "text/plain; charset=utf-8")
            return
        from .analytics import StatsAggregator, StatsRenderer

        params = parse_qs(query or "", keep_blank_values=True)
        window = (params.get("window") or ["month"])[0]
        if window not in ("month", "year", "all"):
            window = "month"
        agg = StatsAggregator(self.analytics, self.library, window_default=window)
        html = StatsRenderer.render_stats_page(self.cfg, agg, self.library, window=window)
        self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")

    def _handle_stats_track(self, raw_key: str) -> None:
        """GET /stats/track/<key> — per-track airtime drill-down (read-only)."""
        if self.analytics is None:
            self._send(503, b"stats not available", "text/plain; charset=utf-8")
            return
        from .analytics import StatsAggregator, StatsRenderer

        track_key = unquote(raw_key or "").strip()
        if not track_key:
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        agg = StatsAggregator(self.analytics, self.library)
        html = StatsRenderer.render_track_page(self.cfg, track_key, agg, self.library)
        self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")

    # -- ADMIN-041: bearer-token-gated operator panel ---------------------------- #

    def _check_admin_auth(self) -> bool:
        """REQ-AD-1 auth gate. Returns True if authorized; otherwise sends the
        appropriate response (404 when the feature is disabled, 401 otherwise) and
        returns False. The caller MUST stop processing when this returns False."""
        token = getattr(self.cfg, "admin_token", "") or ""
        if not token:
            # Feature disabled -> the admin surface does not exist (no token oracle).
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return False
        auth = self.headers.get("Authorization", "")
        if auth != f"Bearer {token}":
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Bearer realm="admin"')
            self.send_header("Content-Length", "0")
            self.end_headers()
            return False
        return True

    def _handle_admin_get(self, path: str, query: str) -> None:
        if path == "/admin/stream":
            self._handle_admin_stream()
            return
        if not self._check_admin_auth():
            return
        if path == "/admin" or path == "/admin/":
            html = _admin_page(self.cfg, "overview", self._admin_overview_body())
        elif path == "/admin/cost":
            html = _admin_page(self.cfg, "cost", self._admin_cost_body())
        elif path == "/admin/llmlog":
            html = _admin_page(self.cfg, "llmlog", self._admin_llmlog_body())
        elif path == "/admin/controls":
            html = _admin_page(self.cfg, "controls", self._admin_controls_body())
        elif path == "/admin/research":
            html = _admin_page(self.cfg, "research", self._admin_research_body())
        else:
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")

    def _handle_admin_post(self, path: str, query: str) -> None:
        if not self._check_admin_auth():
            return
        if path == "/admin/controls/skip":
            self._handle_admin_controls_skip()
        elif path == "/admin/controls/inject":
            self._handle_admin_controls_inject(query)
        elif path == "/admin/controls/silence":
            self._handle_admin_controls_silence()
        elif path == "/admin/controls/flushtalk":
            self._handle_admin_controls_flushtalk()
        elif path == "/admin/reset":
            self._handle_admin_reset(query)
        else:
            self._send(404, b"not found", "text/plain; charset=utf-8")

    # -- admin controls (REQ-AD-5) ---------------------------------------------- #

    def _handle_admin_controls_skip(self) -> None:
        """Force-skip the current track via the SkipGovernor when configured."""
        if self.skip_governor is None:
            self._json({"ok": False, "error": "skip not configured"})
            return
        try:
            decision = self.skip_governor.decide("operator", source="admin")
            self._json({"ok": bool(getattr(decision, "accepted", False)),
                        "refusal_cause": getattr(decision, "refusal_cause", "")})
        except Exception as exc:  # noqa: BLE001
            self._json({"ok": False, "error": str(exc)})

    def _handle_admin_controls_inject(self, query: str) -> None:
        """Queue a URI to be served as the next /api/next pull (REQ-AD-5 inject)."""
        params = parse_qs(query or "", keep_blank_values=True)
        uri = (params.get("uri") or [""])[0]
        uri = unquote(uri).strip()
        if not uri:
            self._json({"ok": False, "error": "uri required"}, code=400)
            return
        _Handler._injected_uri = uri
        log_event(log, "admin.inject", uri=uri)
        self._json({"ok": True, "uri": uri})

    def _handle_admin_controls_silence(self) -> None:
        """Toggle station-wide silence mode (no new tracks queued; current plays out)."""
        _Handler._silence_mode = not _Handler._silence_mode
        log_event(log, "admin.silence", active=_Handler._silence_mode)
        self._json({"ok": True, "silence": _Handler._silence_mode})

    def _handle_admin_controls_flushtalk(self) -> None:
        """Clear any pending host-talk clip so a stale break never airs (REQ-AD-5)."""
        try:
            tq = getattr(self.state, "talk_queue", None)
            if tq is not None and hasattr(tq, "clear"):
                tq.clear()
            elif hasattr(self.state, "take_pending_talk"):
                # The real StationState parks a single pending clip; draining it clears the slot.
                self.state.take_pending_talk()
        except Exception as exc:  # noqa: BLE001
            self._json({"ok": False, "error": str(exc)})
            return
        log_event(log, "admin.flushtalk")
        self._json({"ok": True, "flushed": "talk"})

    # -- admin reset (REQ-AD-6) ------------------------------------------------- #

    def _handle_admin_reset(self, query: str) -> None:
        """Scoped in-memory reset, guarded by a ?confirm=yes double-submit (REQ-AD-6)."""
        params = parse_qs(query or "", keep_blank_values=True)
        scope = (params.get("scope") or [""])[0].strip().lower()
        confirm = (params.get("confirm") or [""])[0].strip().lower()
        if confirm != "yes":
            self._json({"error": "confirm=yes required"}, code=400)
            return
        valid = {"wishlist", "rotation", "talk", "research_queue", "all"}
        if scope not in valid:
            self._json({"ok": False, "error": f"unknown scope: {scope}"}, code=400)
            return
        cleared = self._admin_apply_reset(scope)
        log_event(log, "admin.reset", scope=scope, cleared=",".join(cleared))
        self._json({"ok": True, "scope": scope, "cleared": cleared})

    def _admin_apply_reset(self, scope: str) -> list:
        """Apply one (or all) reset scopes. Best-effort: a missing substrate is skipped,
        never fatal. In-memory only — never touches brain.db / events.db (REQ §7)."""
        cleared: list = []
        targets = ["wishlist", "rotation", "talk", "research_queue"] if scope == "all" else [scope]
        for tgt in targets:
            try:
                if tgt == "wishlist":
                    wl = getattr(self.picker, "wishlist", None)
                    if wl is not None and hasattr(wl, "clear"):
                        wl.clear()
                    cleared.append("wishlist")
                elif tgt == "rotation":
                    for name in ("clear_recent", "reset_rotation"):
                        fn = getattr(self.state, name, None)
                        if callable(fn):
                            fn()
                    cleared.append("rotation")
                elif tgt == "talk":
                    if hasattr(self.state, "take_pending_talk"):
                        self.state.take_pending_talk()
                    cleared.append("talk")
                elif tgt == "research_queue":
                    rsch = getattr(self, "researcher", None)
                    if rsch is not None and hasattr(rsch, "clear_queues"):
                        rsch.clear_queues()
                    cleared.append("research_queue")
            except Exception:  # noqa: BLE001 - a per-scope fault never aborts the whole reset
                pass
        return cleared

    # -- admin SSE live log (REQ-AD-4) ------------------------------------------ #

    def _handle_admin_stream(self) -> None:
        if not self._check_admin_auth():
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        import dataclasses

        from brain.llm_counter import LLMCallCounter
        counter = LLMCallCounter.instance()
        seen = len(counter.records)
        deadline = time.time() + 60  # 60s of INACTIVITY before the stream closes
        try:
            while time.time() < deadline:
                current = list(counter.records)
                if len(current) > seen:
                    for rec in current[seen:]:
                        payload = json.dumps(dataclasses.asdict(rec))
                        self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                    self.wfile.flush()
                    seen = len(current)
                    deadline = time.time() + 60  # reset idle timeout on activity
                time.sleep(0.5)
        except (BrokenPipeError, ConnectionResetError):
            return

    # -- admin HTML bodies ------------------------------------------------------ #

    def _admin_overview_body(self) -> str:
        from brain.llm_counter import LLMCallCounter
        totals = LLMCallCounter.instance().session_totals
        rows = [
            ("Station", _esc(getattr(self.cfg, "station_name", "Golden Shower Radio"))),
            ("LLM calls (session)", str(totals["calls"])),
            ("Total tokens", f"{int(totals['total_tokens']):,}"),
            ("Est. session cost", f"${totals['cost_usd']:.4f}"),
            ("Silence mode", "ON" if _Handler._silence_mode else "off"),
            ("Library tracks", str(self.library.count())),
        ]
        cells = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)
        return f"<table class='kv'>{cells}</table>"

    def _admin_cost_body(self) -> str:
        from brain.llm_counter import LLMCallCounter
        counter = LLMCallCounter.instance()
        records = list(counter.records)
        head = ("<tr><th>#</th><th>Timestamp (UTC)</th><th>Caller</th>"
                "<th>Input</th><th>Output</th><th>Total</th><th>Est. cost</th></tr>")
        body_rows = []
        for i, r in enumerate(records, 1):
            body_rows.append(
                f"<tr><td>{i}</td><td>{_ts(r.ts)}</td><td>{_esc(r.caller)}</td>"
                f"<td>{r.input_tokens:,}</td><td>{r.output_tokens:,}</td>"
                f"<td>{r.total_tokens:,}</td><td>${r.cost_usd:.5f}</td></tr>")
        totals = counter.session_totals
        foot = (f"<tr class='total'><td colspan='3'>SESSION TOTAL</td>"
                f"<td>{int(totals['input_tokens']):,}</td>"
                f"<td>{int(totals['output_tokens']):,}</td>"
                f"<td>{int(totals['total_tokens']):,}</td>"
                f"<td>${totals['cost_usd']:.5f}</td></tr>")
        if not records:
            return "<p class='muted'>No LLM calls recorded this session yet.</p>"
        return f"<table class='log'>{head}{''.join(body_rows)}{foot}</table>"

    def _admin_llmlog_body(self) -> str:
        from brain.llm_counter import LLMCallCounter
        records = list(LLMCallCounter.instance().records)
        if not records:
            return "<p class='muted'>No LLM interactions recorded this session yet.</p>"
        items = []
        for r in reversed(records):  # newest first
            items.append(
                f"<div class='entry'><div class='entry-head'>[{_ts(r.ts)} UTC] "
                f"caller={_esc(r.caller)} | {r.total_tokens:,} tokens</div>"
                f"<details><summary>PROMPT</summary><pre>{_esc(r.prompt)}</pre></details>"
                f"<details><summary>RESPONSE</summary><pre>{_esc(r.response)}</pre></details></div>")
        return "<div class='llmlog'>" + "".join(items) + "</div>"

    def _admin_controls_body(self) -> str:
        silence = "ON" if _Handler._silence_mode else "off"
        return (
            "<p class='muted'>Emergency controls act immediately on the live station.</p>"
            "<form method='post' action='/admin/controls/skip'>"
            "<button>Skip current track</button></form>"
            "<form method='post' action='/admin/controls/silence'>"
            f"<button>Toggle silence mode (currently {silence})</button></form>"
            "<form method='post' action='/admin/controls/flushtalk'>"
            "<button>Flush talk queue</button></form>"
            "<form method='post' action='/admin/controls/inject'>"
            "<input name='uri' placeholder='annotate:/music/...' size='48'/>"
            "<button>Inject next URI</button></form>"
            "<hr/><p class='muted'>Reset scopes require confirm=yes.</p>"
            "<form method='post' action='/admin/reset?scope=wishlist&confirm=yes'>"
            "<button>Reset wishlist</button></form>"
            "<form method='post' action='/admin/reset?scope=rotation&confirm=yes'>"
            "<button>Reset rotation window</button></form>"
            "<form method='post' action='/admin/reset?scope=talk&confirm=yes'>"
            "<button>Reset talk</button></form>"
            "<form method='post' action='/admin/reset?scope=research_queue&confirm=yes'>"
            "<button>Reset research queue</button></form>"
            "<form method='post' action='/admin/reset?scope=all&confirm=yes'>"
            "<button class='danger'>Reset ALL</button></form>")

    def _admin_research_body(self) -> str:
        rsch = getattr(self, "researcher", None)
        if rsch is None:
            return "<p class='muted'>Research subsystem not wired in this build.</p>"
        try:
            stats = rsch.stats() if hasattr(rsch, "stats") else {}
        except Exception:  # noqa: BLE001
            stats = {}
        rows = "".join(f"<tr><th>{_esc(str(k))}</th><td>{_esc(str(v))}</td></tr>"
                       for k, v in stats.items())
        return f"<table class='kv'>{rows or '<tr><td>no data</td></tr>'}</table>"


def _esc(s: str) -> str:
    """Minimal HTML escape for admin panel content (no external dep)."""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _ts(epoch: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(epoch))


# ADMIN-041: shared dark-mode HTML shell. Inline CSS only, no external CDN (REQ-AD-2).
_ADMIN_TABS = [
    ("overview", "/admin", "Overview"),
    ("cost", "/admin/cost", "Cost"),
    ("llmlog", "/admin/llmlog", "LLM Log"),
    ("controls", "/admin/controls", "Controls"),
    ("research", "/admin/research", "Research"),
]


def _admin_page(cfg, active: str, body: str) -> str:
    station = _esc(getattr(cfg, "station_name", "Golden Shower Radio"))
    now = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    nav = "".join(
        f"<a href='{href}' class='{'on' if key == active else ''}'>{label}</a>"
        for key, href, label in _ADMIN_TABS
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{station} — admin</title><style>"
        "body{background:#0d0d0d;color:#e0e0e0;font-family:'JetBrains Mono','Fira Code',monospace;"
        "margin:0;padding:0;font-size:13px}"
        "header{padding:12px 18px;border-bottom:1px solid #333}"
        "header h1{font-size:15px;margin:0 0 4px}header .t{color:#888}"
        "nav{display:flex;gap:2px;background:#161616;border-bottom:1px solid #333}"
        "nav a{padding:10px 16px;color:#aaa;text-decoration:none}"
        "nav a:hover{background:#222;color:#fff}nav a.on{background:#0d0d0d;color:#6cf;border-bottom:2px solid #6cf}"
        "main{padding:18px}"
        "table{border-collapse:collapse;width:100%}"
        "th,td{text-align:left;padding:5px 10px;border-bottom:1px solid #222}"
        "table.kv th{width:220px;color:#888}"
        "table.log th{color:#6cf}tr.total td{border-top:2px solid #444;color:#fc6;font-weight:bold}"
        ".muted{color:#777}.danger{color:#f66}"
        "form{display:inline-block;margin:0 6px 8px 0}"
        "button{background:#222;color:#ddd;border:1px solid #444;padding:7px 12px;cursor:pointer;font-family:inherit}"
        "button:hover{background:#333}input{background:#111;color:#ddd;border:1px solid #444;padding:6px;font-family:inherit}"
        ".entry{border-bottom:1px solid #222;padding:8px 0}.entry-head{color:#6cf}"
        "details summary{cursor:pointer;color:#9a9;padding:3px 0}"
        "pre{background:#111;padding:8px;overflow-x:auto;white-space:pre-wrap;word-break:break-word;color:#ccc}"
        "hr{border:0;border-top:1px solid #333;margin:14px 0}"
        "</style></head><body>"
        f"<header><h1>{station} — admin</h1><div class='t'>{now}</div></header>"
        f"<nav>{nav}</nav><main>{body}</main></body></html>"
    )


def _persona_from_request(persona_mod, body: dict):
    """Build a Persona candidate from a create-request JSON body (REQ-PR-010 captured
    fields). Returns None when no id is supplied. Tolerant: a nested ``charter`` dict is
    rebuilt into a TasteCharter; unknown keys are ignored by Persona.from_record. The
    validation gate (not this builder) enforces the invariants."""
    if not isinstance(body, dict) or not str(body.get("id") or "").strip():
        return None
    rec = dict(body)
    if isinstance(rec.get("charter"), dict):
        valid = set(persona_mod.TasteCharter.__dataclass_fields__)
        rec["charter"] = {k: v for k, v in rec["charter"].items() if k in valid}
    rec.setdefault("origin", "manual")
    try:
        return persona_mod.Persona.from_record(rec)
    except (TypeError, ValueError):
        return None


def make_server(cfg: Config, library: Library, state, knowledge=None,
                roster=None, refiner=None, no_orphan=None,
                skip_governor=None, offensive_verdict=None,
                like_gate=None, like_tokener=None, drop_off_engine=None,
                analytics=None) -> ThreadingHTTPServer:
    # VETTING-027 REQ-VG-003: offensive_verdict is the OffensiveRequestVerdict instance.
    # It is a no-op stub here until REQUEST-011 (listener request feature) ships and
    # calls self.offensive_verdict.check(text) before honoring a listener request.
    # SPEC-RADIO-LIKE-015: like_gate + like_tokener are None unless cfg.like_enabled, in which
    # case GET /api/like-token + POST /api/like 404 (the feature never half-exists).
    picker = Picker(cfg, library, state, refiner=refiner, no_orphan=no_orphan)
    handler = type(
        "BoundHandler",
        (_Handler,),
        {"cfg": cfg, "library": library, "state": state, "picker": picker,
         "knowledge": knowledge, "roster": roster, "skip_governor": skip_governor,
         "offensive_verdict": offensive_verdict,
         "like_gate": like_gate, "like_tokener": like_tokener,
         "drop_off_engine": drop_off_engine, "analytics": analytics},
    )
    httpd = ThreadingHTTPServer((cfg.http_host, cfg.http_port), handler)
    httpd.daemon_threads = True
    return httpd
