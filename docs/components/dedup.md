# Download Deduplication

SPEC-RADIO-DEDUP-014. Version-aware acquisition deduplication: determines whether a candidate from Soulseek or yt-dlp is a true duplicate of something already in the library, or a valid distinct version that should be allowed through.

---

## The problem

Soulseek searches return many copies of the same recording: the original 1978 release, a 2023 remaster, a mono single, a radio edit, a live bootleg from Montreux. Without dedup, the brain downloads multiples, wastes disk, and the library fills with functionally-identical files. But a blanket "same artist+title = duplicate" rule is wrong — a live recording and a studio recording ARE different things and both may be wanted.

---

## Identity model

**Primary key — MusicBrainz Recording MBID (post-enrichment)**
ENRICH-012 lifts a canonical `recording_mbid` onto each `Track`. Two tracks with the same Recording MBID are the same recording, regardless of filename, bitrate, or release year.

**Fallback key — normalized artist+title slug**
When a candidate has no MBID (pre-enrichment, or enrichment failed), the gate falls back to `normalize_key(artist, title)` — the same dedup slug used for rotation.

---

## Version-awareness (the load-bearing rule)

| Situation | Decision |
|---|---|
| Same `recording_mbid`, no version signal in title | `reject-duplicate` — same recording, no valid reason to download again |
| Different `recording_mbid` (even if artist+title slug matches) | `allow-distinct-version` — a live/remaster/remix IS a different recording |
| No MBID on either side, title contains version signal ("live", "remaster", "acoustic", "remix", etc.) | `allow-distinct-version` |
| No MBID on either side, no version signal | `reject-duplicate` (slug match) |
| MBID absent on candidate side only | `allow` (fail-open) |

**Version signal tokens** (whole-word match against title, case-insensitive):
`live`, `concert`, `unplugged`, `session`, `remaster`, `remastered`, `remix`, `mix`, `dub`, `instrumental`, `acoustic`, `demo`, `take`, `version`, `edit`, `single`, `extended`

---

## Fail-open cardinal rule

When identity or distinctness **cannot be established with positive evidence**, the decision is `allow`. A missed duplicate (one extra download) is a tolerated outcome; wrongly blocking a wanted track is the defect this module prevents (REQ-DV-003, NFR-D-1).

A missing MBID **never** blocks a candidate.

---

## Wiring

The gate runs inside `brain/acquire.py` (`Acquirer`) before queueing a download. It reads the `DedupStore` index (a rebuildable in-memory index backed by the library's track records) and returns a `GateDecision`:

```python
@dataclass(frozen=True)
class GateDecision:
    decision: str        # "allow-new" | "reject-duplicate" | "allow-distinct-version"
    basis: str           # "mbid" | "slug" | "none"
    identity_key: str    # the key that matched (or "")
    version_signals: frozenset[str]   # version tokens found in candidate title
    reason: str          # human-readable audit line
```

---

## What this module does NOT own

- Resolving MusicBrainz IDs from fingerprints — that is ENRICH-012.
- Querying the MusicBrainz mirror — that is MBMIRROR-017.
- Pruning duplicate files already in the library — explicitly deferred (out of DEDUP-014 scope).
