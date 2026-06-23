"""HTTP server on :8080 (stdlib, ThreadingHTTPServer - no extra deps).

Endpoints:
  GET  /api/next        text/plain - a Liquidsoap ``annotate:`` URI for the next item
                        (clean ICY artist/title + mix_mode + the real /music path), or
                        EMPTY body (200) if nothing is ready. COMMITS rotation/cadence.
  POST /api/airing      Liquidsoap reports the item it JUST put on air (form fields:
                        artist, title, kind, [path]); sets the GROUND-TRUTH now_playing.
                        Also accepted as GET with the same query params.
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
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

from urllib.parse import parse_qs, urlsplit

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

    def __init__(self, cfg: Config, library: Library, state):
        self.cfg = cfg
        self.library = library
        self.state = state

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
        track = self.library.pick_next(exclude_path, recent_keys)
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
            elif path == "/api/personas":
                # SPEC-RADIO-PROGRAMMING-007 REQ-PR-010/011: create a persona.
                self._handle_persona_create()
            elif path.startswith("/api/personas/") and path.endswith("/disable"):
                self._handle_persona_lifecycle(path.split("/")[3], "disable")
            elif path.startswith("/api/personas/") and path.endswith("/enable"):
                self._handle_persona_lifecycle(path.split("/")[3], "enable")
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
            elif path == "/api/personas":
                self._handle_persona_list()
            elif path == "/health":
                self._send(200, b"ok", "text/plain; charset=utf-8")
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
        self._send(200, b"ok", "text/plain; charset=utf-8")

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
        self._json(
            {
                "now_playing": _enrich_now_playing(self.state.now_playing(), self.library),
                "recent": [_enrich_now_playing(r, self.library) for r in self.state.recent()],
                "library": self.library.count(),
                "downloading": self.state.downloading(),
            }
        )

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
                roster=None) -> ThreadingHTTPServer:
    picker = Picker(cfg, library, state)
    handler = type(
        "BoundHandler",
        (_Handler,),
        {"cfg": cfg, "library": library, "state": state, "picker": picker,
         "knowledge": knowledge, "roster": roster},
    )
    httpd = ThreadingHTTPServer((cfg.http_host, cfg.http_port), handler)
    httpd.daemon_threads = True
    return httpd
