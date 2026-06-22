"""Golden Shower Radio - the Python brain.

Phase 1: AI-curated music acquisition + library + pull-based playout + website.
Driven by Claude via the host's MAX subscription (no API key).

This package replaces the retired Go ``radiod``. Liquidsoap PULLS each track via
``GET http://brain:8080/api/next``; the brain decides every track, acquires music
via slskd (yt-dlp fallback), manages the library, and serves the station website.

SEAMS for later phases (documented, NOT built here):
  - voice/TTS: see ``brain.voice`` - pre-rendered talk clips returned by /api/next.
  - live call-in: see ``brain.voice`` docstring - realtime caller<->host loop.
  - seed enrichment (Spotify/YouTube liked): see ``brain.director`` config stubs.
"""

__all__ = ["__version__"]

__version__ = "1.0.0"
