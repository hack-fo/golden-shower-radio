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
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from .config import AUDIO_EXTS, LOSSLESS_EXTS, LOSSY_EXTS
from .logging_setup import log_event

log = logging.getLogger("brain.slskd")


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

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:  # noqa: BLE001
            pass

    # -- search lifecycle --------------------------------------------------------

    def start_search(self, text: str) -> Optional[str]:
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
