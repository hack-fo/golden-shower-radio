#!/usr/bin/env python3
"""Golden Shower Radio - the Python brain. Entrypoint.

Phase 1: AI-curated music acquisition + library + pull-based playout + website,
driven by Claude via the host's MAX subscription (no API key). Replaces the
retired Go ``radiod``.

Run: ``python radio-brain.py`` (the Dockerfile.brain ENTRYPOINT does exactly this).
The brain reads env: SLSKD_URL, SLSKD_API_KEY, STATION_NAME, ANTHROPIC_MODEL,
MUSIC_DIR (/music), DB_DIR (/db). It MUST NOT require ANTHROPIC_API_KEY.
"""

import os
import sys

# Allow running as a bare script (the `brain` package sits next to this file).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brain.main import run  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(run())
