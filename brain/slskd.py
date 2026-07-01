"""slskd (Soulseek daemon) REST client.

Defensive about JSON shapes across slskd versions: every field access uses .get()
with multiple key fallbacks. The acceptable() predicate + ranking decide which
candidate file to download.

API (slskd v0):
  POST /api/v0/searches              {"searchText": "artist title"} -> {"id": ...}
  GET  /api/v0/searches/{id}                                        -> {"state": ..., ...}
  GET  /api/v0/searches/{id}/responses                              -> [responses]
  POST /api/v0/transfers/downloads/{username}  [{"filename","size"}]
  GET  /api/v0/transfers/downloads/{username}                       -> [transfers]

Auth: header ``X-API-Key: <SLSKD_API_KEY>``.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from .config import AUDIO_EXTS, LOSSLESS_EXTS
from .logging_setup import log_event

log = logging.getLogger("brain.slskd")

# Throttle for the Soulseek login preflight: only re-probe GET /api/v0/server at
# most once per this many seconds. A cached recent "logged in" short-circuits so a
# healthy connection costs nothing on the search hot path.
LOGIN_CHECK_INTERVAL_SEC = 30.0


def _first(d: Dict[str, Any], *keys, default=None):
    """Return the first present, non-None key from a dict (version-tolerant)."""
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def _ext(filename: str) -> str:
    # slskd often uses Windows-style backslash paths.
    base = filename.replace("\\", "/").rsplit("/", 1)[-1]
    _, dot, ext = base.rpartition(".")
    return ("." + ext.lower()) if dot else ""


@dataclass
class Candidate:
    username: str
    filename: str
    size: int
    bitrate: int            # 0 if unknown
    length: int             # seconds, 0 if unknown
    is_lossless: bool
    has_free_slot: bool
    estimated: bool = False  # True when bitrate was estimated from size/length

    @property
    def effective_bitrate(self) -> int:
        """Bitrate used for ranking - real if known, else estimate, else 0."""
        if self.bitrate:
            return self.bitrate
        if self.length > 0:
            return int((self.size * 8) / self.length / 1000)
        return 0

    def rank_key(self):
        # Prefer lossless, then higher (effective) bitrate, then a free upload slot.
        # Unknown-bitrate lossy files are KEPT but downranked: known/estimated > 0
        # sorts above 0, and we subtract a penalty for purely-unknown bitrate.
        downrank = 0 if (self.bitrate or self.length) else 1
        return (
            1 if self.is_lossless else 0,
            self.effective_bitrate - (downrank * 1000),
            1 if self.has_free_slot else 0,
            self.size,
        )


class SlskdClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"X-API-Key": api_key, "Accept": "application/json"},
            timeout=timeout,
        )
        # Login preflight throttle state (see ensure_logged_in / LOGIN_CHECK_INTERVAL_SEC).
        self._last_login_check: float = 0.0
        self._last_login_ok: bool = False

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:  # noqa: BLE001
            pass

    # -- connection health -------------------------------------------------------

    def server_state(self) -> Optional[Dict[str, Any]]:
        """GET /api/v0/server -> the ServerState dict, or None on any error.

        Fields are camelCased and version-dependent; callers use _first() to read them.
        """
        try:
            resp = self._client.get("/api/v0/server")
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, dict) else None
        except Exception as exc:  # noqa: BLE001
            log_event(log, "slskd.server_state_error", error=str(exc))
            return None

    def is_logged_in(self) -> bool:
        """True when slskd is connected AND logged into the Soulseek network.

        Authoritative signal is the boolean ``isLoggedIn``. When that key is absent
        (older/variant slskd), fall back to the ``state`` flags string containing
        "LoggedIn". False when the server state can't be read.
        """
        state = self.server_state()
        if not state:
            return False
        if "isLoggedIn" in state and state["isLoggedIn"] is not None:
            return bool(state["isLoggedIn"])
        return "loggedin" in str(_first(state, "state", default="")).lower().replace(" ", "")

    def reconnect(self) -> bool:
        """PUT /api/v0/server (empty body) -> slskd Connect(): kick its reconnect
        watchdog. Returns True on a 2xx, False (+ log) on error."""
        try:
            resp = self._client.put("/api/v0/server")
            return 200 <= resp.status_code < 300
        except Exception as exc:  # noqa: BLE001
            log_event(log, "slskd.reconnect_error", error=str(exc))
            return False

    # @MX:NOTE: [AUTO] the Soulseek-login preflight — exists because an empty/missing
    # SLSKD_SLSK_USERNAME left slskd Disconnected and every search threw
    # InvalidOperationException server-side (silent failure). Throttled so a healthy
    # connection is ~free on the hot path; heals by kicking slskd's ConnectionWatchdog.
    def ensure_logged_in(self, *, heal: bool = True) -> bool:
        """Preflight the Soulseek login before a search.

        Returns True when logged in. When not, logs an actionable event and (if
        ``heal`` and slskd isn't already transitioning) kicks the reconnect watchdog,
        then returns False. Throttled: a recent successful check short-circuits without
        re-hitting the server (see LOGIN_CHECK_INTERVAL_SEC), so a healthy connection
        costs nothing on the hot path.
        """
        now = time.time()
        if self._last_login_ok and (now - self._last_login_check) < LOGIN_CHECK_INTERVAL_SEC:
            return True
        logged = self.is_logged_in()
        self._last_login_check = now
        self._last_login_ok = logged
        if logged:
            return True
        log_event(
            log,
            "slskd.not_logged_in",
            message=(
                "slskd is Disconnected / not logged into the Soulseek network — searches "
                "will be skipped; check SLSKD_SLSK_USERNAME/SLSKD_SLSK_PASSWORD in secrets/.env"
            ),
        )
        if heal:
            transitioning = bool(_first(self.server_state() or {}, "isTransitioning", default=False))
            if not transitioning:
                self.reconnect()
        return False

    # -- search lifecycle --------------------------------------------------------

    # @MX:ANCHOR: [AUTO] the slskd search entry point — the external-system integration
    # boundary between the acquirer and the Soulseek network.
    # @MX:REASON: external integration point + fan_in (acquire._try_slskd + the health/
    # acquire tests); its None-return-on-failure contract is relied on by every caller.
    def start_search(self, text: str) -> Optional[str]:
        # Preflight: a Disconnected / not-logged-in slskd otherwise raises
        # InvalidOperationException server-side and every search fails silently.
        # Convert that into a clear log + heal attempt, and skip gracefully (None).
        if not self.ensure_logged_in():
            log_event(log, "slskd.search_skipped_not_connected", text=text)
            return None
        try:
            resp = self._client.post("/api/v0/searches", json={"searchText": text})
            resp.raise_for_status()
            data = resp.json()
            sid = _first(data, "id", "searchId", "Id")
            return str(sid) if sid is not None else None
        except Exception as exc:  # noqa: BLE001
            log_event(log, "slskd.search_start_failed", text=text, error=str(exc))
            return None

    def _search_complete(self, sid: str) -> bool:
        try:
            resp = self._client.get(f"/api/v0/searches/{sid}")
            resp.raise_for_status()
            data = resp.json()
        except Exception:  # noqa: BLE001
            return False
        if _first(data, "isComplete", "IsComplete", default=False):
            return True
        state = str(_first(data, "state", "State", default="")).lower()
        # state strings vary: "Completed", "Completed, ResponsesReceived", ...
        return "complete" in state or "ended" in state

    def wait_for_search(self, sid: str, timeout: float = 25.0, poll: float = 1.5) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._search_complete(sid):
                return True
            time.sleep(poll)
        # Even if not flagged complete, responses may already be usable.
        return False

    def get_responses(self, sid: str) -> List[Dict[str, Any]]:
        try:
            resp = self._client.get(f"/api/v0/searches/{sid}/responses")
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                data = _first(data, "responses", "Responses", default=[])
            return data if isinstance(data, list) else []
        except Exception as exc:  # noqa: BLE001
            log_event(log, "slskd.responses_failed", sid=sid, error=str(exc))
            return []

    # -- candidate extraction + acceptability ------------------------------------

    @staticmethod
    def acceptable(
        username: str,
        response: Dict[str, Any],
        file: Dict[str, Any],
        min_bitrate: int,
        max_size_bytes: int = 0,
    ) -> bool:
        """Decide whether a single file is an acceptable download candidate.

        Rules (see SPEC brief):
          - skip [PRIVATE] / private / locked users entirely.
          - lossless (.flac/.wav/.aiff/.alac) -> always OK.
          - lossy -> require bitrate >= min_bitrate WHEN KNOWN.
          - bitrate MISSING/0 -> do NOT skip; keep it (it gets downranked later).
            Many Soulseek clients don't broadcast bitrate; skipping starves the lib.
          - non-audio extensions -> skip.
          - size > max_size_bytes (when both known and cap > 0) -> skip. Guards
            against multi-GB rips. Unknown size (0) -> keep (the cap can't apply).
        """
        # Private / locked users.
        if "[private]" in (username or "").lower():
            return False
        if _first(response, "isPrivate", "IsPrivate", default=False):
            return False
        filename = str(_first(file, "filename", "Filename", "name", default=""))
        if not filename:
            return False
        # A locked file (behind a share lock) is effectively private.
        if _first(file, "isLocked", "IsLocked", "locked", default=False):
            return False

        ext = _ext(filename)
        if ext not in AUDIO_EXTS:
            return False

        # Size cap: reject anything over the cap when both the size and the cap
        # are known (applies to lossless and lossy alike, before the ext gate).
        size = int(_first(file, "size", "Size", default=0) or 0)
        if max_size_bytes > 0 and size > max_size_bytes:
            return False

        if ext in LOSSLESS_EXTS:
            return True

        # Lossy: enforce min bitrate only when we actually know it.
        bitrate = int(_first(file, "bitRate", "bitrate", "BitRate", default=0) or 0)
        if bitrate and bitrate < min_bitrate:
            return False
        return True  # unknown bitrate -> keep, downranked in rank_key()

    def collect_candidates(
        self, responses: List[Dict[str, Any]], min_bitrate: int, max_size_bytes: int = 0
    ) -> List[Candidate]:
        candidates: List[Candidate] = []
        for response in responses:
            if not isinstance(response, dict):
                continue
            username = str(_first(response, "username", "Username", default=""))
            free_slot = bool(
                _first(response, "hasFreeUploadSlot", "HasFreeUploadSlot", default=False)
                or (int(_first(response, "freeUploadSlots", "FreeUploadSlots", default=0) or 0) > 0)
            )
            files = _first(response, "files", "Files", default=[]) or []
            for file in files:
                if not isinstance(file, dict):
                    continue
                if not self.acceptable(username, response, file, min_bitrate, max_size_bytes):
                    continue
                filename = str(_first(file, "filename", "Filename", "name", default=""))
                ext = _ext(filename)
                bitrate = int(_first(file, "bitRate", "bitrate", "BitRate", default=0) or 0)
                length = int(_first(file, "length", "Length", default=0) or 0)
                size = int(_first(file, "size", "Size", default=0) or 0)
                candidates.append(
                    Candidate(
                        username=username,
                        filename=filename,
                        size=size,
                        bitrate=bitrate,
                        length=length,
                        is_lossless=(ext in LOSSLESS_EXTS),
                        has_free_slot=free_slot,
                        estimated=(not bitrate and length > 0),
                    )
                )
        return candidates

    def best_candidate(
        self, responses: List[Dict[str, Any]], min_bitrate: int, max_size_bytes: int = 0
    ) -> Optional[Candidate]:
        candidates = self.collect_candidates(responses, min_bitrate, max_size_bytes)
        if not candidates:
            return None
        candidates.sort(key=lambda c: c.rank_key(), reverse=True)
        best = candidates[0]
        # Final guard: never enqueue a download over the cap (size known + cap set).
        if max_size_bytes > 0 and best.size > max_size_bytes:
            return None
        return best

    # -- download ----------------------------------------------------------------

    def enqueue_download(self, candidate: Candidate) -> bool:
        body = [{"filename": candidate.filename, "size": candidate.size}]
        try:
            resp = self._client.post(
                f"/api/v0/transfers/downloads/{candidate.username}", json=body
            )
            resp.raise_for_status()
            log_event(
                log,
                "slskd.download_enqueued",
                user=candidate.username,
                file=candidate.filename,
                lossless=candidate.is_lossless,
                bitrate=candidate.effective_bitrate,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            log_event(log, "slskd.download_failed", user=candidate.username, error=str(exc))
            return False
