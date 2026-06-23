"""yt-dlp fallback acquisition.

When slskd yields no acceptable result or the download fails/stalls, grab the
audio from YouTube. yt-dlp is installed in the brain image.

Command (exactly per brief):
  yt-dlp -x --audio-format mp3 --audio-quality 0 --no-playlist --no-progress \
    -o "<MUSIC_DIR>/%(title)s.%(ext)s" "ytsearch1:<artist title> audio"
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Set

from .logging_setup import log_event

log = logging.getLogger("brain.ytdlp")


def _snapshot(music_dir: str) -> Set[str]:
    try:
        return set(os.listdir(music_dir))
    except OSError:
        return set()


def fetch(
    artist: str,
    title: str,
    music_dir: str,
    timeout: int = 120,
    max_mb: int = 200,
    max_duration_seconds: int = 2400,
) -> bool:
    """Try to download the track via yt-dlp. Returns True if a new file appeared.

    Never raises; logs and returns False on any failure/timeout. The duration and
    file-size caps reject hour-long mixes / multi-hundred-MB rips BEFORE download.
    """
    query = f"{artist} {title}".strip()
    if not query:
        return False
    os.makedirs(music_dir, exist_ok=True)
    before = _snapshot(music_dir)

    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--no-playlist",
        "--no-progress",
    ]
    if max_duration_seconds > 0:
        cmd += ["--match-filter", f"duration < {max_duration_seconds}"]
    if max_mb > 0:
        cmd += ["--max-filesize", f"{max_mb}M"]
    cmd += [
        "-o", os.path.join(music_dir, "%(title)s.%(ext)s"),
        f"ytsearch1:{query} audio",
    ]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        log_event(log, "ytdlp.timeout", query=query, timeout=timeout)
        return False
    except FileNotFoundError:
        log_event(log, "ytdlp.not_installed", query=query)
        return False
    except Exception as exc:  # noqa: BLE001
        log_event(log, "ytdlp.error", query=query, error=str(exc))
        return False

    after = _snapshot(music_dir)
    new_files = after - before
    if new_files:
        log_event(log, "ytdlp.fetched", query=query, files=sorted(new_files))
        return True

    log_event(log, "ytdlp.no_result", query=query, returncode=proc.returncode)
    return False
