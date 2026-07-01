---
id: SPEC-RADIO-YTREPLACE-057
version: 0.1.0
status: draft
created: 2026-07-01
updated: 2026-07-01
author: charlie
priority: Medium
issue_number: 57
---

# SPEC-RADIO-YTREPLACE-057 — YouTube Title Normalization + Provenance-Tracked Quality-Upgrade Swap

## HISTORY

- 2026-07-01 (v0.1.0): Initial draft, occupying the new global-incrementing YTREPLACE-057 id (the
  next free number in the RADIO series: the working tree ends at LINEUP-050, and 051–056 —
  PROMPTFMT-051, PROMPTSLIM-052, FEATUREGATE-053, 054, TLS-055, SLSKDVPN-056 — are authored on other
  branches, so 057 is the next unused). RADIO SPEC-IDs are GLOBAL-INCREMENTING. This is the
  YOUTUBE-QUALITY-UPGRADE subsystem of the autonomous AI radio station: it (1) strips marketing cruft
  from yt-dlp-sourced titles before they become a track's clean artist/title, (2) durably records
  every YouTube-fetched track's provenance so the set of "upgrade candidates" is queryable, and (3)
  runs an occasional background worker that re-searches slskd/Soulseek for those yt-dlp-sourced tracks
  and, on a verified-good higher-quality match, SWAPS the file — preserving the track's identity, play
  history, likes, and stats. It uses a DISTINCT REQ namespace — YN (YouTube title Normalization), YP
  (Provenance & upgrade-candidate set), YR (Replacement worker), YQ (Quality gate), YS (Safe swap), YX
  (eXhaustion & idempotency), YC (Config), YI (Interactions / integration) — deliberately Y-prefixed
  to avoid colliding with every sibling prefix (CORE A–E+D, VOICE V-*, CALLIN CT/CL/CD/CM/CC/CF/CS/CG,
  OPS OA/OB/OC/OD/OE/OF/OG/OH/OX/OY, ORCH RL/RW/RE/RC/RD/RA/RN/RI, ANALYSIS AE/AT/AM/AD/AP, PROGRAMMING
  PR/PC/PS/PT/PL/PG/PV/PI, KNOWLEDGE KS/KF/KR/KG/KI, TAGSTREAM TW/TA/TX, IMAGING IG/IB/IP/IL/IS/IH/IX,
  REQUEST RQ/RM/RA/RWL/RS/RV/RD, DATASTORE DE/DP/DX/DM/DC/DR, ALBUMART AK/AF/AC/AS/AW/AG, ACQQUEUE
  QR/QT/QP/QW/QO/QC, FILENAME FD/FR/FS/FF/FC/FX). Grounded in the real code: the yt-dlp fallback
  (`brain/ytdlp.py` `fetch()`) writes the landed file as `%(title)s.%(ext)s` — so a raw YouTube title
  like `Rick Astley - Never Gonna Give You Up (Official Video).mp3` becomes the filename verbatim; the
  acquisition orchestrator (`brain/acquire.py` `_acquire_one`) records the source via
  `Library.note_source(key, "yt-dlp")` → `provenance["source"] = "yt-dlp"` after a yt-dlp success; the
  slskd re-search seams are `SlskdClient.start_search` / `best_candidate` / `collect_candidates` /
  `acceptable` / `enqueue_download` (`brain/slskd.py`) with `Candidate.rank_key` = lossless >
  effective_bitrate > free_slot > size; and the ONLY sanctioned writer of the frozen `Track.path` is
  `Library.rename_track_file` (FILENAME-024, atomic under `self._lock` with rollback, `@MX:ANCHOR`) —
  the swap must extend this exact pattern. Totals: 27 REQ + 8 NFR = 35, 1:1 REQ↔AC (YN=5, YP=3, YR=4,
  YQ=3, YS=4, YX=3, YC=1, YI=4). NOTE: `issue_number: 57` is a same-as-number PLACEHOLDER; the real
  GitHub issue link is TBD (to be linked in a follow-up, as LINEUP-050 was linked to #52 post-hoc).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "keep playing the YouTube rip, but quietly upgrade it to a lossless slskd copy"

The station's acquisition pipeline is slskd-first with a yt-dlp fallback (`brain/acquire.py`): when
Soulseek can't find a wanted track, `brain/ytdlp.py` `fetch()` grabs the audio from YouTube
(`yt-dlp -x --audio-format mp3 --audio-quality 0 …`). This keeps the never-stop station fed, but it
leaves two lasting blemishes:

1. **Dirty titles.** yt-dlp writes the landed file as `%(title)s.%(ext)s`, so the RAW YouTube video
   title becomes the filename — carrying marketing cruft: `(Official Video)`, `(Official Music
   Video)`, `[Official Audio]`, `(Lyric Video)`, `(Lyrics)`, `(Visualizer)`, `(HD)`, `(4K)`,
   `(Audio)`, `(Remastered)`, a trailing `| Label` / `| Topic` handle, `feat.`/`ft.` spelling drift,
   etc. Because a yt-dlp mp3 has no embedded id3 tags, the library scan falls back to
   `library._parse_filename` (`Artist - Title` regex over the noisy stem), so this cruft leaks into
   the track's clean `artist`/`title` and into the ENRICH-012 identification query.
2. **Permanently second-rate audio.** A yt-dlp mp3 is a lossy re-encode of whatever the video's audio
   was. Once slskd later has a lossless/CD copy of the same recording available, the station keeps
   airing the inferior YouTube rip forever, because nothing ever re-checks.

The user wants both fixed, autonomously and safely: strip the cruft from a yt-dlp title BEFORE it
becomes the clean artist/title (conservatively, so legitimate parenthetical content on non-YouTube
tracks is never damaged); durably remember every YouTube-fetched track; and run an occasional
background worker that re-searches slskd for those tracks and REPLACES the file with a better,
higher-quality lossless/CD rip when a verified-good match is found — a quality-gated swap that keeps
the track's identity, play history, likes (LIKE-015), and stats (STATS-013) intact.

### 1.2 The load-bearing posture (the asymmetries that make this safe)

[HARD] Three asymmetries make this SPEC safe. The station is a live, never-stop broadcast; a
quality-upgrade is a nicety, never worth a risk to the stream or to a track's history.

- **Verified-before-delete; never downgrade.** [HARD] The yt-dlp file is NEVER deleted until the
  replacement has landed AND passed the quality gate AND been verified as the SAME recording. A swap
  only ever happens on a STRICTLY-BETTER candidate (lossless, or a materially higher-bitrate CD rip);
  a candidate that is equal-or-worse is discarded and the yt-dlp file is kept (REQ-YQ-002, REQ-YS-001,
  NFR-Y-3).
- **Identity-preserving swap; play-history is sacred.** [HARD] A swap improves the underlying FILE
  only; it preserves the frozen `Track.key` (the dedup slug), `play_count`, `last_played`, `added_at`,
  and every ANALYSIS-006 / LIKE-015 / STATS-013 record keyed off that track. The swap updates
  `Track.path` in place through a sanctioned atomic writer UNDER the library lock (the FILENAME-024
  `rename_track_file` `@MX:ANCHOR` pattern) so `Library.scan` never prunes-then-re-adds the track and
  the picker never resolves a stale path (REQ-YS-002, NFR-Y-2).
- **Conservative, source-scoped title normalization.** [HARD] The noise-strip applies ONLY to
  yt-dlp-sourced titles and uses a CURATED noise-pattern list (specific bracketed/parenthetical
  marketing tokens + trailing handle junk + feat./ft. normalization) — NOT blanket parenthetical
  stripping — so a legitimate parenthetical on a non-YouTube track (e.g. `(Live at Wembley)`,
  `(Remix)`, `(feat. …)` where meaningful) is never damaged (REQ-YN-001, NFR-Y-6).

### 1.3 What this layer is, concretely

- A YOUTUBE TITLE NORMALIZATION (Group YN): a conservative, curated noise-strip applied to a
  yt-dlp-derived title BEFORE it becomes the clean `artist`/`title` — removing bracketed/parenthetical
  marketing tokens (`(Official Video)`, `(Official Music Video)`, `(Official Lyric Video)`,
  `[Official Audio]`, `(Lyric Video)`, `(Lyrics)`, `(Visualizer)`, `(Audio)`, `(HD)`, `(4K)`,
  `(Full Album)` / `(Full Video)`, `(Remastered)`, …), trailing `| Label` / `- Topic` handle junk, and
  normalizing `feat.`/`ft.` — scoped to `source=ytdlp`, idempotent, and empty/edge-safe. The cleaned
  title is the SINGLE stored `Track.title`, so it propagates to the ICY StreamTitle, `/api/nowplaying`
  now_playing, and the Recently Played history (no uncleaned copy lingers). Ships a concrete, extensible
  noise-pattern list (an acceptance fixture), and BACKFILLS existing yt-dlp-sourced titles that already
  carry cruft — identity-preservingly (display-title only, never re-keys) and idempotently.
- A PROVENANCE RECORD + UPGRADE-CANDIDATE SET (Group YP): every YouTube-fetched track is durably
  tagged with its acquisition source (`provenance["source"] == "yt-dlp"`, LEVERAGING the existing
  `Library.note_source` seam — not a new field) plus enough metadata to find a replacement later (the
  ORIGINAL YouTube title and the fetch time). The set of "upgrade candidates" = tracks with
  `source=ytdlp` that have not yet been upgraded and are not exhausted — queryable.
- AN OCCASIONAL REPLACEMENT WORKER (Group YR): a background worker mirroring the existing acquisition-
  worker lifecycle (`brain/main.py` constructs + `.start()`s `Acquirer` / `EnrichmentWorker` /
  `FilenameWorker`) that, on a bounded cadence off the pull path, takes upgrade candidates and
  re-searches slskd (`SlskdClient.start_search`) by the CLEAN artist + title.
- A QUALITY GATE (Group YQ): a defined quality ordering (lossless FLAC/WAV/AIFF/ALAC > a materially
  higher-bitrate CD-rip mp3/aac > the current yt-dlp mp3) plus a SAME-RECORDING verification (the
  candidate must be the same recording, not a different/live/remix version) so the swap is a genuine
  upgrade of the same track, never a substitution.
- A SAFE SWAP (Group YS): download the replacement to a staging location, verify it plays / is
  non-empty / matches, then atomically repoint `Track.path` to the new file UNDER the library lock and
  only THEN delete the old yt-dlp file; preserve the track identity + play history; write a provenance
  trail (`was ytdlp → now slskd`, `replaced_at`, `original_source`, `original_youtube_title`); never
  swap the in-flight (on-air / handed-out / prefetch-horizon) file — defer it.
- EXHAUSTION & IDEMPOTENCY (Group YX): an already-upgraded track is NEVER re-processed; a track that
  cannot be found/upgraded after a bounded number of attempts is marked EXHAUSTED (not searched
  forever); the worker respects the existing attempts-cooldown + slskd rate limits.
- CONFIG (Group YC): `brain/config.py` `_env`-style `BRAIN_*` knobs — enable/disable (default OFF),
  worker cadence, the quality threshold, and max attempts per track.
- INTERACTIONS (Group YI): explicit boundaries with VETTING-027 (the replacement candidate passes the
  same vet gate; a swap never resurrects a banned track), DEDUP-014 (an upgrade of the SAME key is not
  a duplicate-to-reject; version-awareness decides same-vs-different recording), LIKE-015 + STATS-013
  (identity preservation keeps likes/play-history from being orphaned), and ENRICH-012 + FILENAME-024
  (the swapped file is re-enriched / re-flagged; the swap uses the sanctioned `Track.path` writer).

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] YTREPLACE-057 OWNS the YouTube title normalization, the yt-dlp provenance + upgrade-candidate
set, the replacement worker, the quality gate + same-recording verification, the safe identity-
preserving swap, the exhaustion/idempotency bookkeeping, the config knobs, and the integration events.
It MUST NOT re-own, fork, or weaken the yt-dlp fetch command, the slskd search/rank/enqueue client,
the acquisition pipeline shape, the `Library`/`Track` schema, the ENRICH-012 identification engine, the
FILENAME-024 rename/`Track.path` writer, the VETTING-027 gate/ban-list, the DEDUP-014 version-aware
gate, the LIKE-015 signals, or the STATS-013 store — it CONSUMES / extends them.

OWNS:
- The YOUTUBE TITLE NORMALIZATION: the curated noise-pattern list, the conservative source-scoped
  strip, the feat./ft. normalization, the idempotent + edge-safe transform (Group YN).
- The PROVENANCE + UPGRADE-CANDIDATE SET: the durable `source=ytdlp` tag (via the existing
  `note_source` seam), the captured original YouTube title + fetch time, and the queryable
  upgrade-candidate set (Group YP).
- The REPLACEMENT WORKER: the background worker lifecycle, the bounded cadence, the candidate
  selection, and the slskd re-search by clean artist+title (Group YR).
- The QUALITY GATE: the quality ordering (lossless > higher-bitrate CD rip > yt-dlp mp3), the
  strictly-better rule (never downgrade), and the same-recording verification (Group YQ).
- The SAFE SWAP: the staged download, the verify-before-delete, the atomic identity-preserving
  `Track.path` repoint + old-file cleanup, the never-swap-in-flight guard, and the provenance trail
  (Group YS).
- The EXHAUSTION / IDEMPOTENCY bookkeeping (Group YX), the CONFIG knobs (Group YC), and the
  INTEGRATION boundaries + events (Group YI).

REFERENCES (consumes / extends; does not restate):
- **`brain/ytdlp.py` (`fetch()`)** — the yt-dlp fallback that lands `%(title)s.%(ext)s`. The
  source point at which a track is KNOWN to be YouTube-sourced. YTREPLACE-057 hooks the title
  normalization onto the yt-dlp arm (which knows the source) and reads the raw title for provenance;
  it does NOT change the fetch command (Group YN/YP).
- **`brain/acquire.py` (`_acquire_one` / `note_source(key, "yt-dlp")` / `_enrich_on_download` /
  `RateLimiter` / `AttemptsIndex`)** — the orchestrator that records the source and runs the
  enrichment/dedup/filename hooks after a download. YTREPLACE-057 reuses the source-marking seam and
  the bounded/rate-limited posture; it does NOT re-own the pipeline (Group YP/YR/YX).
- **`brain/slskd.py` (`SlskdClient.start_search` / `wait_for_search` / `get_responses` /
  `collect_candidates` / `acceptable` / `best_candidate` / `enqueue_download` + `Candidate.rank_key` =
  lossless > effective_bitrate > free_slot > size + `LOSSLESS_EXTS`)** — the search/rank/enqueue
  client the re-search reuses. The quality ordering is READ from / layered on this ranking; the client
  is not re-owned (Group YR/YQ).
- **`brain/library.py` (`Track` / `normalize_key` / `Track.key` frozen slug / `has_key` / `query` /
  `scan` / `note_source` → `provenance["source"]` / `set_analysis` / `set_provenance` / the
  `rename_track_file` `@MX:ANCHOR` — the ONLY sanctioned `Track.path` writer, atomic under `self._lock`
  with rollback)** — the store the provenance is recorded in, the identity that is preserved, and the
  atomic `Track.path` writer the swap extends. The schema is not re-owned; only `Track.path` changes on
  a swap, plus provenance fields via the allowlist writers (Group YP/YS).
- **`brain/state.py` (`now_playing()` / `last_committed_path()` / the prefetch horizon / `_recent`)** —
  the live airing state the never-swap-in-flight guard consults (Group YS).
- **`brain/config.py` (the `_env` / frozen `Config` `BRAIN_*` family)** — the config surface the new
  knobs are added beside (Group YC).
- **ENRICH-012 (`brain/enrich.py` + `set_core_tags`)** — the identification/correction engine; the
  swapped file is re-enriched so its tags are corrected, and the same-recording verification MAY use
  the ENRICH-012 `recording_mbid`. Referenced, never re-owned (Group YQ/YI).
- **FILENAME-024 (`brain/filename.py` + `Library.rename_track_file`)** — the sanctioned atomic
  `Track.path` writer + the post-enrich filename re-flag. The swap extends the writer pattern and
  triggers the re-flag (Group YS/YI).
- **VETTING-027 (`Acquirer.vetting_gate` / the ban-list)** — the pre-download vet cascade the
  replacement candidate must pass; a swap never resurrects a banned track (Group YI).
- **DEDUP-014 (`brain/dedup.py` version-aware gate)** — decides same-vs-different recording; an upgrade
  of the same key is NOT a duplicate-reject (Group YQ/YI).
- **LIKE-015 / STATS-013** — the like signals + the play/airtime ledger keyed off the track; identity
  preservation keeps them from being orphaned (Group YI).

### 1.5 Fixed engineering rails (the only hard constraints)

- **Never blocks / silences playout.** [HARD] Normalization runs on the (already background)
  acquisition arm; the replacement worker is a separate background worker on a bounded cadence, off the
  `<1s /api/next` pull path; neither ever blocks the picker, the director loop, or the audio path
  (REQ-YR-002, NFR-Y-1).
- **Verified-before-delete.** [HARD] The yt-dlp file is deleted ONLY after the replacement has landed,
  passed the quality gate, and been verified; a failed/aborted swap leaves the original untouched
  (REQ-YS-001, NFR-Y-2).
- **Never downgrade.** [HARD] A swap happens ONLY on a strictly-better candidate per the defined
  quality ordering; equal-or-worse is discarded (REQ-YQ-002, NFR-Y-3).
- **Identity-preserving, atomic, in-flight-safe swap.** [HARD] The swap preserves `Track.key` +
  play-history and repoints `Track.path` atomically under the library lock via a sanctioned writer;
  it never swaps the on-air / handed-out / prefetch-horizon file (REQ-YS-002, REQ-YS-003, NFR-Y-2).
- **Same recording, not a substitution.** [HARD] The candidate must be verified as the SAME recording
  (MBID or fuzzy version-awareness); a different/live/remix version is not an upgrade (REQ-YQ-003).
- **Conservative, source-scoped title normalization.** [HARD] Curated noise list, `source=ytdlp` only,
  never blanket paren-stripping, never touches non-YouTube tracks; idempotent + edge-safe (REQ-YN-001,
  REQ-YN-002, NFR-Y-6).
- **Idempotent + bounded.** [HARD] An already-upgraded track is never re-processed; an unfindable
  track is marked exhausted after max attempts; the worker respects the attempts cooldown + slskd rate
  limits (REQ-YX-001, REQ-YX-002, NFR-Y-4).
- **Compose, do not re-own.** [HARD] Reuses the slskd client, the acquisition posture, ENRICH-012,
  FILENAME-024's `Track.path` writer, VETTING-027, DEDUP-014; brain-only + additive; no new service,
  no new datastore (NFR-Y-5).
- **Resilience.** [HARD] Any yt-dlp/slskd/enrich/swap error logs and degrades gracefully (keep the
  yt-dlp file, defer/exhaust the track) — never crashes the daemon, never silences the stream
  (NFR-Y-7).

---

## 2. Dependencies

This SPEC DEPENDS ON the acquisition subsystem (`brain/acquire.py` + `brain/ytdlp.py` +
`brain/slskd.py`), SPEC-RADIO-CORE-001 (the `Library` / `Track` / `scan` / picker air path +
`brain/state.py`), the ENRICH-012 identification/correction engine (`brain/enrich.py` +
`brain/library.py`), SPEC-RADIO-FILENAME-024 (the sanctioned atomic `Track.path` writer
`rename_track_file` + the filename re-flag), SPEC-RADIO-VETTING-027 (the pre-download vet gate +
ban-list), SPEC-RADIO-DEDUP-014 (the version-aware same-vs-different-recording gate), SPEC-RADIO-
LIKE-015 (listener likes keyed off the track), and SPEC-RADIO-STATS-013 (the play/airtime ledger). It
is the YouTube-quality-upgrade subsystem layered on top of them, and composes with SPEC-RADIO-
ACQQUEUE-019 (queue-aware source selection) when it re-searches slskd.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any sibling SPEC requirement, and MUST NOT
change the observable behavior of any public store API beyond (a) recording provenance via the
existing allowlist writers and (b) repointing `Track.path` on a verified swap through a sanctioned
atomic writer. Where a predecessor behavior is consumed it is preserved; where a swap decision could
conflict with continuous operation or a track's history, the inherited behavior WINS — the music keeps
playing, the air path is never orphaned, and a track's play history / likes / stats are never lost.

Consumed concepts:
- **`brain/ytdlp.py` `fetch()`** — lands `%(title)s.%(ext)s`; the point where a track is known
  YouTube-sourced. The title normalization + provenance capture hook here (Group YN/YP).
- **`brain/acquire.py` `note_source(key, "yt-dlp")` + `RateLimiter` + `AttemptsIndex` +
  `_enrich_on_download`** — the source-marking seam + the bounded/rate-limited posture the worker
  reuses (Group YP/YR/YX).
- **`brain/slskd.py` `SlskdClient` + `Candidate.rank_key` + `LOSSLESS_EXTS`** — the re-search /
  rank / enqueue client + the quality signals the quality ordering layers on (Group YR/YQ).
- **`brain/library.py` `Track.key` (frozen slug) + `note_source` → `provenance["source"]` +
  `set_analysis` / `set_provenance` + `rename_track_file` (`@MX:ANCHOR`, atomic under `self._lock`)** —
  the identity preserved + the provenance recorded + the atomic `Track.path` writer the swap extends
  (Group YP/YS).
- **`brain/state.py` `now_playing` / `last_committed_path` / the prefetch horizon** — the in-flight
  state the never-swap-in-flight guard consults (Group YS).
- **ENRICH-012 `set_core_tags` + `recording_mbid`** — re-enrich the swapped file; the MBID feeds the
  same-recording verification (Group YQ/YI).
- **VETTING-027 `vetting_gate` + ban-list** — the replacement candidate must pass; never resurrect a
  ban (Group YI).
- **DEDUP-014 version-aware gate** — same-vs-different-recording verdict (Group YQ/YI).
- **LIKE-015 + STATS-013** — like signals + play/airtime ledger keyed off the preserved track (Group
  YI).

### bhive memory seam

bhive memory (AGENTS.md protocol) has no proven pattern for "live-radio-safe verified-before-delete
file swap that preserves a track's dedup key + play history while repointing the about-to-be-fetched
air path" on this Python + slskd + yt-dlp + Liquidsoap stack (consistent with the recorded bhive Stack
Gap). Re-run a bhive query on (a) the exact slskd search-response quality field spellings, (b) the
robust yt-dlp title-cruft pattern set, and (c) the atomic path-swap-under-lock + verify-before-delete
pattern during implementation, and contribute the verified approach back per the AGENTS.md protocol.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **yt-dlp-sourced track** | A track whose recorded acquisition source is the yt-dlp value — `provenance["source"] == "yt-dlp"` as written by `Library.note_source` in `acquire.py`'s `_acquire_one` after a yt-dlp success. The exact string (`"yt-dlp"`, hyphenated) is what the code records; the upgrade-candidate set keys off it (REQ-YP-001). |
| **YouTube title cruft / noise** | Marketing tokens a raw YouTube title carries that are NOT part of the song's artist/title: bracketed/parenthetical `(Official Video)` / `(Official Music Video)` / `[Official Audio]` / `(Lyric Video)` / `(Lyrics)` / `(Visualizer)` / `(HD)` / `(4K)` / `(Audio)` / `(Full Album)` / `(Remastered)` …, a trailing `| Label` / `| Topic` handle, and `feat.`/`ft.` spelling drift (REQ-YN-001, REQ-YN-003). |
| **Curated noise-pattern list** | The explicit, EXTENSIBLE allowlist of cruft patterns the strip removes (an acceptance fixture, acceptance.md AC-YN-003). NOT blanket parenthetical stripping — a pattern must be on the list to be removed, so legitimate parentheticals survive (NFR-Y-6). |
| **Clean artist/title** | The artist/title after the yt-dlp noise-strip (Group YN) — what becomes `Track.artist`/`Track.title` and the ENRICH-012 identification query. |
| **Upgrade candidate** | A yt-dlp-sourced track that has NOT yet been upgraded (no successful swap) and is NOT exhausted (REQ-YX-002). The queryable set the replacement worker draws from (REQ-YP-003). |
| **Quality ordering** | The defined preference used by the gate: lossless (`.flac`/`.wav`/`.aiff`/`.alac`, per `LOSSLESS_EXTS`) > a materially higher-bitrate lossy CD rip > the current yt-dlp mp3. A swap requires the candidate to be STRICTLY better (REQ-YQ-001). |
| **Strictly-better / never-downgrade** | The rule that a swap happens ONLY when the candidate is unambiguously higher quality than the current yt-dlp file; equal-or-worse is discarded, the yt-dlp file kept (REQ-YQ-002, NFR-Y-3). |
| **Same-recording verification** | The check that a candidate is the SAME recording as the track being upgraded (via ENRICH-012 `recording_mbid` when known, else DEDUP-014 version-aware fuzzy match) — a different/live/remix version is NOT an upgrade (REQ-YQ-003). |
| **Safe swap** | Download the replacement to staging → verify (non-empty, plays, matches) → atomically repoint `Track.path` under the library lock → only THEN delete the old yt-dlp file. Verified-before-delete, identity-preserving, in-flight-safe (Group YS). |
| **Identity preservation** | The swap keeps `Track.key` (frozen slug), `play_count`, `last_played`, `added_at`, and every ANALYSIS-006 / LIKE-015 / STATS-013 record keyed off the track — only the underlying FILE (and `Track.path`) changes (REQ-YS-002, NFR-Y-2). |
| **In-flight file** | The on-air file (`state.now_playing()['path']`), the just-handed-out file (`state.last_committed_path()`), or a file in the prefetch horizon. NEVER swapped; deferred (REQ-YS-003). |
| **Provenance trail (upgrade)** | The recorded history of a swap: `was ytdlp → now slskd`, `replaced_at`, `original_source`, `original_youtube_title` — written via the allowlist provenance writer so it never touches frozen identity (REQ-YS-004). |
| **Exhausted** | A yt-dlp-sourced track that could not be upgraded after the configured max attempts; marked so it is never searched again (until an operator resets it), preventing an unfindable track from being searched forever (REQ-YX-002). |
| **Occasional / bounded cadence** | The replacement worker runs on a slow, configurable cadence (not on every acquisition, not on the pull path) and processes a bounded batch per tick, reusing the slskd rate limiter (REQ-YR-002, REQ-YC-001, NFR-Y-4). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group YN — YouTube Title Normalization.** The conservative curated noise-strip applied to a
  yt-dlp-derived title before it becomes the clean artist/title; scoped to `source=ytdlp`; idempotent +
  edge/empty-safe; the extensible noise-pattern list (fixture); feat./ft. normalization.
- **Group YP — Provenance & Upgrade-Candidate Set.** The durable `source=ytdlp` tag (via the existing
  `note_source` seam); the captured original YouTube title + fetch time; the queryable upgrade-candidate
  set (source=ytdlp, not-yet-upgraded, not-exhausted).
- **Group YR — Replacement Worker.** The background worker mirroring the acquisition-worker lifecycle;
  the bounded cadence off the pull path; the candidate selection from the upgrade-candidate set; the
  slskd re-search by clean artist+title.
- **Group YQ — Quality Gate.** The quality ordering (lossless > higher-bitrate CD rip > yt-dlp mp3);
  the strictly-better / never-downgrade rule; the same-recording verification.
- **Group YS — Safe Swap.** The staged download + verify-before-delete; the atomic identity-preserving
  `Track.path` repoint under the lock via a sanctioned writer; the never-swap-in-flight guard; the
  provenance trail.
- **Group YX — Exhaustion & Idempotency.** The already-upgraded skip; the max-attempts → exhausted
  marker; the attempts-cooldown + rate-limit respect.
- **Group YC — Config.** enable/disable (default OFF), worker cadence, quality threshold, max attempts
  per track.
- **Group YI — Interactions / Integration.** The explicit VETTING-027 / DEDUP-014 / LIKE-015 +
  STATS-013 / ENRICH-012 + FILENAME-024 boundaries + the structured swap/normalize/exhaust events.
- Plus **NFRs** (Section 14) and **Risks** (Section 15).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **The yt-dlp fetch command / the acquisition pipeline shape (slskd-first/yt-dlp-last)** — owned by
  `brain/ytdlp.py` + OPS-004; unchanged. YTREPLACE-057 hooks normalization/provenance onto the yt-dlp
  arm and adds a separate worker; it does not change how the fallback fetches.
- **The slskd search/rank/enqueue client + the private/quality acceptability rules** — owned by
  `brain/slskd.py` + ACQQUEUE-019; the re-search reuses them, never re-owns them.
- **The ENRICH-012 identification / correction engine** — owned by ENRICH-012; the swapped file is
  re-enriched through the existing hook; YTREPLACE-057 never re-identifies from scratch.
- **The FILENAME-024 rename/consistency subsystem + the `Track.path` writer internals** — owned by
  FILENAME-024; the swap extends the sanctioned atomic writer pattern, it does not fork it.
- **The VETTING-027 vet cascade + ban-list schema** — owned by VETTING-027; the candidate passes the
  existing gate; YTREPLACE-057 does not re-own vetting.
- **The DEDUP-014 version-aware gate internals** — owned by DEDUP-014; consulted for same-vs-different
  recording; not re-owned.
- **The LIKE-015 signal store + the STATS-013 play/airtime ledger** — owned by their SPECs; identity
  preservation keeps them intact; YTREPLACE-057 never writes to them directly.
- **A general "re-download everything better" sweep of slskd-sourced (non-yt-dlp) tracks** — EXCLUDED:
  the upgrade set is yt-dlp-sourced only (the known-lossy population). Upgrading already-slskd tracks
  is a future SPEC (Section 16).
- **Deleting / pruning tracks, or evicting for disk** — owned by CORE-001/OPS-004 `evict_low_value`;
  a swap deletes ONLY the superseded yt-dlp file it just replaced, never a library-management prune.
- **Multi-source / swarm / resuming downloads** — one candidate at a time in rank order; owned/aligned
  with ACQQUEUE-019's one-source-at-a-time posture.
- **A new datastore or a new web service** — brain-only, additive; provenance lives in the existing
  store seam.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Never blocks / silences playout; off the `<1s /api/next` pull path.** Normalization on the
  background acquisition arm; the replacement worker a separate bounded-cadence background worker.
- [HARD] **Verified-before-delete.** The yt-dlp file is deleted only after the replacement lands +
  passes the quality gate + is verified; a failed swap leaves the original untouched.
- [HARD] **Never downgrade.** Swap only on a strictly-better candidate per the quality ordering.
- [HARD] **Same recording, not a substitution.** The candidate is verified as the same recording; a
  different/live/remix version is never swapped in.
- [HARD] **Identity-preserving + atomic + in-flight-safe swap.** Preserve `Track.key` + play-history;
  repoint `Track.path` atomically under the library lock via a sanctioned writer; never swap the
  on-air / handed-out / prefetch-horizon file.
- [HARD] **Conservative source-scoped title normalization.** Curated noise list; `source=ytdlp` only;
  never blanket paren-strip; never touch non-YouTube tracks; idempotent + edge-safe.
- [HARD] **Idempotent + bounded.** Already-upgraded → skip; unfindable → exhausted after max attempts;
  respect the attempts cooldown + slskd rate limits.
- [HARD] **Compose, do not re-own.** Reuse the slskd client, the acquisition posture, ENRICH-012,
  FILENAME-024's `Track.path` writer, VETTING-027, DEDUP-014; brain-only + additive; no new service /
  datastore.
- [HARD] **Resilience.** Any error logs + degrades gracefully (keep the yt-dlp file, defer/exhaust);
  never crashes the daemon, never silences the stream.

---

## 6. Requirement Group YN — YouTube Title Normalization

Priority: High.

### REQ-YN-001 — Strip curated YouTube cruft from a yt-dlp title BEFORE it becomes the clean artist/title; scoped to source=ytdlp (Event-driven) [HARD]

When a track is acquired via the yt-dlp fallback (the arm that KNOWS the source is YouTube), the system
SHALL apply a CONSERVATIVE, CURATED noise-strip to the yt-dlp-derived title BEFORE it becomes the
track's clean `artist`/`title` (and before it becomes the ENRICH-012 identification query), removing
only patterns on the curated noise list (bracketed/parenthetical marketing tokens, a trailing
`| Label` / `| Topic` handle) and normalizing `feat.`/`ft.` (REQ-YN-003). [HARD] The strip is SCOPED to
yt-dlp-sourced tracks: it SHALL NOT alter the artist/title of a track acquired via slskd or a manual
drop, and it SHALL NOT perform blanket parenthetical stripping — only listed patterns are removed, so a
legitimate parenthetical on any track survives (NFR-Y-6). The exact hook point (in the yt-dlp arm vs. a
source-scoped pre-enrich pass) is an implementation decision (D-Y-1) bounded by the source-scoping
rail; that a curated, source-scoped strip cleans the yt-dlp title before it becomes the clean
artist/title is the rail.

**Acceptance criteria:** see acceptance.md AC-YN-001.

### REQ-YN-002 — The normalization is idempotent and empty/edge-safe (Ubiquitous) [HARD]

The system SHALL make the title normalization IDEMPOTENT — applying it to an already-clean title
yields the same title (no churn, safe to re-run) — and EMPTY/EDGE-SAFE — an empty title, a
title-that-is-only-cruft, a title with no separator, unicode, and unusual bracketing all produce a
valid (possibly-unchanged) result and NEVER an empty artist AND empty title where a usable value
existed, and NEVER a crash. [HARD] If stripping the cruft would leave nothing usable, the strip SHALL
degrade to the pre-strip value rather than emit an empty name. That the normalization is idempotent and
never produces a worse-than-input or crashing result is the rail.

**Acceptance criteria:** see acceptance.md AC-YN-002.

### REQ-YN-003 — Ship a concrete, extensible noise-pattern list (fixture) incl. feat./ft. normalization (Ubiquitous)

The system SHALL ship a CONCRETE, EXTENSIBLE noise-pattern list covering at minimum: `(Official
Video)`, `(Official Music Video)`, `(Official Lyric Video)`, `[Official Audio]` / `(Official Audio)`,
`(Lyric Video)` / `(Lyrics)`, `(Visualizer)`, `(HD)` / `(4K)` / `(1080p)`, `(Audio)`, `(Full Album)` /
`(Full Video)` (the token is stripped from a single-track title; the album-SPLIT is deferred to the
long-form path — see Section 16), `(Remastered)` / `(Remaster)` / `(YYYY Remaster)`, `(Explicit)`, a
trailing `| <handle>` / `- Topic` YouTube-channel suffix, and the `feat.`/`ft.`/`featuring` spelling
normalization — and this list SHALL be structured so new patterns can be added without a code redesign.
[HARD] The list is CURATED (each entry is a known marketing/handle token), not a generic
"remove-anything-in-parens" rule. The exact regex/token forms are implementation detail bounded by the
curated-not-blanket rail; that a concrete, extensible, curated list (the acceptance fixture) exists is
the rail.

**Acceptance criteria:** see acceptance.md AC-YN-003.

### REQ-YN-004 — The cleaned title is the single stored Track.title and propagates to the ICY StreamTitle, now_playing, and Recently Played (Ubiquitous) [HARD]

The system SHALL store the normalized/cleaned title as the track's `Track.title` — the SINGLE source of
truth for the clean title — so that every surface that displays the clean title shows the CLEANED value:
the in-stream ICY `StreamTitle` (built by the picker from `item.title` in `brain/server.py`), the
`/api/nowplaying` `now_playing` (driven by the `state.set_on_air(artist, title, …)` airing report — the
`@MX:ANCHOR` sole writer of `now_playing`), AND the Recently Played history (`brain/state.py` `_recent`,
populated from the aired title on rotation). [HARD] There SHALL be NO separate, uncleaned copy of the
title lingering on any of these surfaces — cruft like "Official Audio" MUST NOT appear in now-playing or
recently-played. Because the picker reads `Track.title` to build BOTH the ICY StreamTitle and the airing
report, cleaning `Track.title` is sufficient AND required; the requirement forbids any parallel
uncleaned-title path. That the cleaned title is the single stored `Track.title` and propagates to all
three surfaces (StreamTitle, now_playing, Recently Played) is the rail.

**Acceptance criteria:** see acceptance.md AC-YN-004.

### REQ-YN-005 — Backfill: re-normalize EXISTING source=ytdlp titles — identity-preserving, idempotent, repeatable (State-driven) [HARD]

While tracks ALREADY in the library that were fetched from YouTube (`provenance["source"] == "yt-dlp"`)
still carry cruft in `Track.title`, the system SHALL run a BOUNDED backfill pass that re-runs the Group
YN normalizer over those existing titles and PERSISTS the cleaned result — so the normalization applies
not only to NEW yt-dlp downloads going forward but also to the already-landed YouTube-sourced catalog.
[HARD] The backfill is IDENTITY-PRESERVING: it edits ONLY the DISPLAY `Track.title` (via the ENRICH-012
`set_core_tags` allowlist writer, which corrects artist/title without EVER touching the frozen
`key`/`path`/play-history — the same discipline as the YS swap group), so it NEVER changes the dedup key
or orphans play-history / likes / stats. [HARD] It is IDEMPOTENT — an already-clean title is left
BYTE-IDENTICAL (no write, no churn) — and SAFE TO RUN REPEATEDLY (a one-time pass and an incremental
re-scan both converge to the clean title). The backfill is SCOPED to `source=ytdlp` tracks; a
non-YouTube track's title is never touched (NFR-Y-6). It runs off the `<1s /api/next` pull path and
never blocks playout (NFR-Y-1). The exact pass mechanism (a one-time marker vs. an incremental horizon
on the existing analysis/enrich backfill) is implementation detail; that existing yt-dlp titles are
re-normalized identity-preservingly, idempotently, and repeatably is the rail.

**Acceptance criteria:** see acceptance.md AC-YN-005.

---

## 7. Requirement Group YP — Provenance & Upgrade-Candidate Set

Priority: High.

### REQ-YP-001 — Every YouTube-fetched track is durably tagged source=ytdlp via the existing note_source seam (Event-driven) [HARD]

When a track is successfully fetched via yt-dlp, the system SHALL durably record its acquisition source
as the yt-dlp value using the EXISTING `Library.note_source(key, "yt-dlp")` seam (which persists
`provenance["source"]` via the allowlist writer, never touching frozen identity), so the track is
later identifiable as YouTube-sourced. [HARD] YTREPLACE-057 SHALL LEVERAGE this existing seam — it
SHALL NOT introduce a parallel/duplicate source field for the same fact. The exact recorded string is
what `note_source` writes (`"yt-dlp"`); the upgrade-candidate set (REQ-YP-003) keys off it. That every
yt-dlp fetch is durably source-tagged through the existing seam is the rail.

**Acceptance criteria:** see acceptance.md AC-YP-001.

### REQ-YP-002 — Capture enough metadata to find a replacement later: original YouTube title + fetch time (Event-driven) [HARD]

When a track is recorded as yt-dlp-sourced (REQ-YP-001), the system SHALL also durably capture, via the
allowlist provenance writer, enough metadata to later find and audit a replacement: the ORIGINAL
YouTube title (pre-normalization) and the FETCH TIME. [HARD] This metadata is written to provenance
fields (never frozen identity) and is what the replacement worker + the provenance trail (REQ-YS-004)
read. The exact field names are implementation detail; that the original YouTube title and the fetch
time are durably captured for each yt-dlp-sourced track is the rail.

**Acceptance criteria:** see acceptance.md AC-YP-002.

### REQ-YP-003 — The upgrade-candidate set is queryable: source=ytdlp, not-yet-upgraded, not-exhausted (Ubiquitous) [HARD]

The system SHALL expose a QUERYABLE set of UPGRADE CANDIDATES — the tracks that are yt-dlp-sourced
(REQ-YP-001) AND have not yet been successfully upgraded (no completed swap) AND are not marked
exhausted (REQ-YX-002) — built by filtering the existing library over the recorded provenance. [HARD]
The set is derived from the store (no new datastore); an already-upgraded or exhausted track is
excluded so the worker never re-processes it (REQ-YX-001). The query mechanism is implementation detail;
that the upgrade-candidate set (yt-dlp-sourced, not-yet-upgraded, not-exhausted) is queryable is the
rail.

**Acceptance criteria:** see acceptance.md AC-YP-003.

---

## 8. Requirement Group YR — Replacement Worker

Priority: High.

### REQ-YR-001 — A background replacement worker mirroring the acquisition-worker lifecycle (Ubiquitous) [HARD]

The system SHALL run the replacement logic as a BACKGROUND WORKER whose lifecycle mirrors the existing
acquisition workers — constructed and `.start()`ed alongside `Acquirer` / `EnrichmentWorker` /
`FilenameWorker` in `brain/main.py`, exception-isolated per tick (a worker must never die), and shut
down cleanly on the shared `stop_event`. [HARD] The worker is a NEW background thread, not a change to
the synchronous audio path or the acquisition worker pool. The exact class/threading shape is
implementation detail (mirroring `FilenameWorker`); that the replacement logic runs as a lifecycle-
mirrored, exception-isolated background worker is the rail.

**Acceptance criteria:** see acceptance.md AC-YR-001.

### REQ-YR-002 — Bounded, occasional cadence; off the pull path; never blocks playout (State-driven) [HARD]

While enabled, the worker SHALL run on a BOUNDED, OCCASIONAL cadence (a configurable slow interval,
REQ-YC-001) processing a BOUNDED batch of upgrade candidates per tick, entirely OFF the `<1s /api/next`
pull path, so it NEVER blocks or silences the picker, the director loop, or the audio path. [HARD] The
worker is "occasional" by design — it is not triggered on every acquisition and does not scan the whole
library on the hot path; it processes a small batch per slow tick, reusing the slskd rate limiter so it
never storms the network (NFR-Y-4). The interval + batch size are config; that the worker is bounded,
occasional, off-pull-path, and never blocks playout is the rail.

**Acceptance criteria:** see acceptance.md AC-YR-002.

### REQ-YR-003 — Re-search slskd by the CLEAN artist + title (Event-driven) [HARD]

When the worker processes an upgrade candidate, the system SHALL re-search slskd using the CLEAN
`artist` + `title` (the ENRICH-012-corrected / YN-normalized values, not the raw YouTube title) via the
EXISTING `SlskdClient` search seam (`start_search` / `wait_for_search` / `get_responses` /
`collect_candidates`), honoring the existing `acceptable()` quality + private/locked skip rules. [HARD]
The re-search reuses the slskd client unchanged; it does not re-implement search. The query construction
is implementation detail; that the worker re-searches slskd by the clean artist+title through the
existing client is the rail.

**Acceptance criteria:** see acceptance.md AC-YR-003.

### REQ-YR-004 — Select the best replacement candidate reusing the existing slskd ranking (Event-driven)

When slskd returns candidates for an upgrade re-search, the system SHALL select the best candidate
reusing the EXISTING `Candidate.rank_key` / `best_candidate` ranking (lossless > effective_bitrate >
free_slot > size), composing with ACQQUEUE-019 queue-aware selection where enabled, and SHALL then
apply the quality gate (Group YQ) before any download-to-swap. [HARD] Candidate selection is the slskd
client's job; YTREPLACE-057 layers the quality gate + same-recording verification on top of the chosen
candidate. That the best candidate is selected via the existing ranking (then gated) is the rail.

**Acceptance criteria:** see acceptance.md AC-YR-004.

---

## 9. Requirement Group YQ — Quality Gate

Priority: High.

### REQ-YQ-001 — Define the quality ordering: lossless > higher-bitrate CD rip > yt-dlp mp3 (Ubiquitous) [HARD]

The system SHALL define an explicit QUALITY ORDERING for the swap decision: a lossless candidate
(`.flac`/`.wav`/`.aiff`/`.alac`, per the existing `LOSSLESS_EXTS`) ranks above a materially
higher-bitrate lossy CD rip, which ranks above the current yt-dlp mp3. [HARD] The current file's
quality is established from the yt-dlp fetch (a lossy mp3 at `--audio-quality 0`) and/or the file's
actual format/bitrate; the candidate's quality from the slskd `Candidate` (is_lossless /
effective_bitrate). The exact "materially higher" bitrate margin is config (REQ-YC-001, a threshold so
a trivially-higher lossy file does not trigger a churny swap); that the quality ordering (lossless >
higher-bitrate CD rip > yt-dlp mp3) is defined and drives the swap decision is the rail.

**Acceptance criteria:** see acceptance.md AC-YQ-001.

### REQ-YQ-002 — NEVER downgrade: swap only on a strictly-better candidate; else keep the yt-dlp file (Unwanted) [HARD]

If no available candidate is STRICTLY BETTER than the current yt-dlp file per the quality ordering
(REQ-YQ-001) and the configured margin, then the system SHALL NOT swap — it SHALL keep the existing
yt-dlp file untouched and leave the track an upgrade candidate for a future attempt (subject to the
exhaustion bound, REQ-YX-002). [HARD] A swap NEVER lowers quality: an equal-or-worse candidate (a lossy
file no better than the yt-dlp mp3, a smaller/lower-bitrate file, an unverifiable-quality file) is
discarded. That the system never downgrades and only swaps on a strictly-better candidate is the rail.

**Acceptance criteria:** see acceptance.md AC-YQ-002.

### REQ-YQ-003 — Same-recording verification: the candidate must be the SAME recording, not a different/live/remix version (Unwanted) [HARD]

If a quality-superior candidate is NOT verified to be the SAME recording as the track being upgraded,
then the system SHALL NOT swap it in. [HARD] The verification SHALL use the ENRICH-012 `recording_mbid`
when known on both sides, and otherwise the DEDUP-014 version-aware match (which already distinguishes a
studio recording from a live/remix/alternate version — live-vs-studio is always distinct), so a swap is
always an upgrade of the SAME recording, never a substitution of a different version. A candidate whose
sameness cannot be established is treated as NOT-verified and skipped (fail toward keeping the original).
That a swap only occurs on a verified same-recording candidate is the rail.

**Acceptance criteria:** see acceptance.md AC-YQ-003.

---

## 10. Requirement Group YS — Safe Swap

Priority: High.

### REQ-YS-001 — NEVER delete the yt-dlp file until the replacement is downloaded AND verified (Unwanted) [HARD]

The system SHALL NOT delete or overwrite the existing yt-dlp file until the replacement has (a) fully
downloaded to a staging location, (b) passed the quality gate (Group YQ), and (c) been VERIFIED
(non-empty, a readable audio file, and — where checkable — matching the expected recording). [HARD] If
the download fails, stalls, fails the gate, or fails verification, the swap is ABORTED and the original
yt-dlp file is left entirely untouched (the track remains playable and remains an upgrade candidate).
There is NO window in which the track has no file. The staging/verification mechanism is implementation
detail; that the original is never deleted before a verified replacement exists is the rail.

**Acceptance criteria:** see acceptance.md AC-YS-001.

### REQ-YS-002 — Identity-preserving atomic swap: repoint Track.path under the lock; preserve key + play history (Ubiquitous) [HARD]

When a verified, strictly-better, same-recording replacement exists (REQ-YQ/YS-001), the system SHALL
perform the swap as an ATOMIC, IDENTITY-PRESERVING operation: it SHALL repoint `Track.path` to the new
file through a SANCTIONED atomic writer UNDER the library lock (the FILENAME-024 `rename_track_file`
`@MX:ANCHOR` pattern — extended for a cross-file swap), and it SHALL PRESERVE the frozen `Track.key`
(dedup slug), `play_count`, `last_played`, `added_at`, and every ANALYSIS-006 / LIKE-015 / STATS-013
record keyed off the track. [HARD] Because `Library.scan` detects new-vs-vanished by PATH, the swap MUST
update `Track.path` in place under the lock so `scan` NEVER prunes-then-re-adds the track (which would
orphan its play history) and the picker never resolves a stale path. Only the underlying FILE and
`Track.path` change; the track's identity and history are untouched. That the swap is atomic,
identity-preserving, and repoints `Track.path` via a sanctioned under-lock writer is the rail.

**Acceptance criteria:** see acceptance.md AC-YS-002.

### REQ-YS-003 — NEVER swap the in-flight file (on-air / handed-out / prefetch horizon); defer it (Unwanted) [HARD]

If an upgrade candidate track is IN FLIGHT — it is the on-air file (`state.now_playing()['path']`), the
just-handed-out file (`state.last_committed_path()`), or within the prefetch horizon — then the system
SHALL NOT swap its file and SHALL DEFER it to a later tick (when it is no longer in flight). [HARD] This
mirrors the FILENAME-024 never-rename-in-flight guard and is REQUIRED because `Track.path` is the path
Liquidsoap is about to fetch: swapping an in-flight file would 404 the air path mid-broadcast. That an
in-flight track is never swapped but deferred is the rail.

**Acceptance criteria:** see acceptance.md AC-YS-003.

### REQ-YS-004 — Write an upgrade provenance trail: was ytdlp → now slskd, replaced_at, original_source, original_youtube_title (Event-driven) [HARD]

When a swap succeeds, the system SHALL write a durable PROVENANCE TRAIL via the allowlist provenance
writer: the source transition (`was ytdlp → now slskd`, i.e. update `provenance["source"]` to the new
source while recording the prior one), `replaced_at`, `original_source`, and the `original_youtube_title`
(from REQ-YP-002). [HARD] The trail is written to provenance fields (never frozen identity), so a swap
is auditable (an operator/STATS-013 can see the track was upgraded from a YouTube rip). That a successful
swap records an auditable was-ytdlp→now-slskd provenance trail is the rail.

**Acceptance criteria:** see acceptance.md AC-YS-004.

---

## 11. Requirement Group YX — Exhaustion & Idempotency

Priority: High.

### REQ-YX-001 — Idempotent: an already-upgraded track is NEVER re-processed (Unwanted) [HARD]

If a track has already been successfully upgraded (its provenance shows a completed swap /
`source != "yt-dlp"` after an upgrade), then the system SHALL NOT re-process it — it is excluded from
the upgrade-candidate set (REQ-YP-003) and no further re-search/swap is attempted. [HARD] The upgrade is
a one-way improvement per track; re-running the worker never re-swaps or churns an already-upgraded
track. That an already-upgraded track is never re-processed (idempotent) is the rail.

**Acceptance criteria:** see acceptance.md AC-YX-001.

### REQ-YX-002 — Bounded attempts: mark a track EXHAUSTED after max attempts; never search forever (State-driven) [HARD]

While a track remains a yt-dlp-sourced upgrade candidate, the system SHALL bound the number of
replacement ATTEMPTS by a configurable maximum (REQ-YC-001); when a track has been attempted that many
times without a successful swap, the system SHALL mark it EXHAUSTED (recorded via the allowlist
provenance writer) so it is excluded from the upgrade-candidate set and NEVER searched again (until an
operator explicitly resets it). [HARD] An unfindable track (no better copy exists on slskd) is not
searched forever — the attempt count + the exhausted marker cap the effort. The max value + the
attempt-counting mechanism are config/implementation detail; that a track is marked exhausted after
bounded attempts and never re-searched is the rail.

**Acceptance criteria:** see acceptance.md AC-YX-002.

### REQ-YX-003 — Respect the existing attempts cooldown + slskd rate limits (Ubiquitous) [HARD]

The system SHALL respect the EXISTING acquisition bounds when re-searching: the slskd `RateLimiter`
search budget and the `AttemptsIndex` cooldown posture, so the replacement worker never causes a search
storm and never re-hammers a source faster than the acquisition pipeline allows. [HARD] The worker
reuses the same rate-limited, cooldown-respecting discipline as `Acquirer`; the occasional cadence
(REQ-YR-002) is an additional throttle on top. That the worker respects the existing rate limits +
cooldown is the rail.

**Acceptance criteria:** see acceptance.md AC-YX-003.

---

## 12. Requirement Group YC — Config

Priority: Medium.

### REQ-YC-001 — brain/config.py BRAIN_* knobs: enable (default OFF), cadence, quality margin, max attempts (Ubiquitous) [HARD]

The system SHALL expose, in the `brain/config.py` `_env` / frozen `Config` `BRAIN_*` style (the same
`_env("BRAIN_...", default)` pattern as the existing acquisition knobs), config knobs for: (a) an
ENABLE/DISABLE switch (default OFF — the whole replacement subsystem is opt-in, consistent with the
station's conservative posture and the fact slskd is off by default per the user); (b) the WORKER
CADENCE (the occasional interval + the per-tick batch size, REQ-YR-002); (c) the QUALITY MARGIN /
THRESHOLD (how much better a candidate must be to trigger a swap, REQ-YQ-001); and (d) the MAX ATTEMPTS
per track before exhaustion (REQ-YX-002). [HARD] The knobs live on the existing frozen `Config` with
sane defaults; the ENABLE default is OFF; they require no new config file or service. The title
normalization (Group YN) MAY have its own always-on-or-toggled knob but is independent of the
replacement-worker enable (normalization is cheap + non-destructive; the swap is the gated part). The
exact env-var names + defaults are implementation detail; that these knobs exist in the `BRAIN_*` style
with a default-OFF replacement worker is the rail.

**Acceptance criteria:** see acceptance.md AC-YC-001.

---

## 13. Requirement Group YI — Interactions / Integration

Priority: High.

### REQ-YI-001 — VETTING-027: the replacement candidate passes the same vet gate; a swap never resurrects a banned track (Unwanted) [HARD]

Where VETTING-027 is enabled, the system SHALL subject a replacement candidate to the SAME vet cascade /
ban check the acquisition pipeline applies (`Acquirer.vetting_gate`), and SHALL NOT swap in a candidate
that the vet gate would reject, and SHALL NOT re-acquire (via a swap) a track whose key is on the
ban-list. [HARD] The upgrade path is NOT a bypass of vetting: a banned or unvettable candidate is
skipped (the yt-dlp file kept). Where VETTING-027 is disabled the check is a no-op (today's behavior).
That the replacement candidate passes the same vet gate and a swap never resurrects a ban is the rail.

**Acceptance criteria:** see acceptance.md AC-YI-001.

### REQ-YI-002 — DEDUP-014: an upgrade of the same key is NOT a duplicate-reject; version-awareness decides sameness (Ubiquitous) [HARD]

The system SHALL treat a same-recording quality upgrade as an UPGRADE of the existing track, NOT as a
new acquisition to be duplicate-rejected: because the swap preserves the existing `Track.key` and
repoints its path in place (REQ-YS-002), it SHALL NOT trip the DEDUP-014 gate into rejecting the better
file as a "duplicate", and it SHALL use DEDUP-014's version-awareness (REQ-YQ-003) to confirm sameness
before swapping. [HARD] DEDUP-014 decides same-vs-different recording (live/remix stays distinct); the
swap is only ever an in-place file improvement of one key, so no duplicate row is created and no dedup
rejection applies. That an in-place same-key upgrade composes with (and never fights) DEDUP-014 is the
rail.

**Acceptance criteria:** see acceptance.md AC-YI-002.

### REQ-YI-003 — LIKE-015 + STATS-013 play-history integrity: the swap preserves identity so likes/stats are never orphaned (Ubiquitous) [HARD]

The system SHALL guarantee that a swap NEVER orphans a track's listener likes (LIKE-015) or its
play/airtime history (STATS-013): because the swap preserves the frozen `Track.key` and the
play-history fields (REQ-YS-002), every like and every play/airtime record keyed off that track remains
attached to the SAME track after the swap. [HARD] The swap SHALL NOT create a new track identity, reset
`play_count`/`last_played`/`added_at`, or re-key the track — any of which would orphan the likes/stats.
That the swap preserves identity so likes + play-history are never orphaned is the load-bearing
integrity rail.

**Acceptance criteria:** see acceptance.md AC-YI-003.

### REQ-YI-004 — ENRICH-012 + FILENAME-024: re-enrich the swapped file; use the sanctioned Track.path writer; re-flag filename (Event-driven)

When a swap completes, the system SHALL (a) trigger the EXISTING ENRICH-012 on-download correction for
the new file so its embedded tags are corrected (reusing `_enrich_on_download` / the enrichment hook),
(b) have performed the `Track.path` repoint through the FILENAME-024 sanctioned atomic writer
(REQ-YS-002), and (c) allow the FILENAME-024 consistency check to re-flag the new file's name as usual.
[HARD] YTREPLACE-057 does not re-implement enrichment, the path writer, or the filename check — it
triggers/reuses them. That the swapped file is re-enriched, repointed via the sanctioned writer, and
re-flagged through the existing subsystems is the rail.

**Acceptance criteria:** see acceptance.md AC-YI-004.

---

## 14. Non-Functional Requirements

### NFR-Y-1 — Never blocks / silences playout; off the `<1s /api/next` pull path (Ubiquitous) — Priority High
The normalization (on the background acquisition arm) and the replacement worker (a separate
bounded-cadence background worker) shall NEVER block or silence the music playout, and no work shall run
on the synchronous `<1s /api/next` pull path. Inherits CORE-001's continuous-operation identity. See
acceptance.md AC-NFR-Y-1.

### NFR-Y-2 — Verified-before-delete + identity-preserving atomic swap (the load-bearing safety NFR) (Ubiquitous) — Priority High
No code path shall delete the yt-dlp file before a verified replacement exists (REQ-YS-001), and every
swap shall be atomic + identity-preserving (repoint `Track.path` under the library lock via a sanctioned
writer; preserve `Track.key` + play-history; never prune-then-re-add via `scan`; never swap the
in-flight file). This is the load-bearing safety NFR — the asymmetry that makes the swap safe. See
acceptance.md AC-NFR-Y-2.

### NFR-Y-3 — Never downgrade (Ubiquitous) — Priority High
No swap shall lower a track's audio quality: a swap occurs ONLY on a candidate that is strictly better
per the quality ordering + margin (REQ-YQ-001/002); an equal-or-worse candidate is discarded and the
yt-dlp file kept. See acceptance.md AC-NFR-Y-3.

### NFR-Y-4 — Idempotent + bounded (Ubiquitous) — Priority High
An already-upgraded track is never re-processed (REQ-YX-001); an unfindable track is marked exhausted
after bounded attempts (REQ-YX-002); the worker runs on an occasional cadence, processes a bounded batch
per tick, and reuses the slskd rate limiter + attempts cooldown (REQ-YR-002/YX-003) so it never storms
the network or loops forever. See acceptance.md AC-NFR-Y-4.

### NFR-Y-5 — Single-source-of-truth: compose siblings, never re-own; brain-only additive (Ubiquitous) — Priority High
No code path shall re-own or fork the yt-dlp fetch command, the slskd client, the acquisition pipeline,
the `Library`/`Track` schema, the ENRICH-012 engine, the FILENAME-024 `Track.path` writer, the
VETTING-027 gate, the DEDUP-014 gate, or the LIKE-015/STATS-013 stores; each is referenced/composed.
YTREPLACE-057 is brain-only + additive (a title-normalization hook + a provenance capture + a new
background worker + config knobs; no new service, no new datastore). See acceptance.md AC-NFR-Y-5.

### NFR-Y-6 — Conservative title normalization: scoped to ytdlp, never damages legit content (Ubiquitous) — Priority High
The title normalization shall be conservative and source-scoped: it applies ONLY to yt-dlp-sourced
tracks, uses a CURATED noise list (never blanket parenthetical stripping), and shall NEVER damage
legitimate parenthetical/bracketed content on a non-YouTube track or a genuinely-titled parenthetical
(e.g. a meaningful `(Live …)` / `(Remix)` on a track whose title truly contains it). See acceptance.md
AC-NFR-Y-6.

### NFR-Y-7 — Resilience: never crash, never silence; an error degrades to keep-the-ytdlp-file (Unwanted) — Priority High
A normalization error, a yt-dlp/slskd error, an enrich/verify/swap failure, or a store error shall LOG
via `log_event` and DEGRADE GRACEFULLY — leaving the yt-dlp file untouched and the track an upgrade
candidate (or exhausted) — without crashing the daemon, the acquisition worker, the replacement worker,
or the picker, and without silencing the stream. See acceptance.md AC-NFR-Y-7.

### NFR-Y-8 — Observability: structured events for normalize / candidate / gate / swap / exhaust (Ubiquitous) — Priority Medium
The subsystem shall emit STRUCTURED `log_event(...)` events (not free text only) for the title
normalization applied, the upgrade re-search + chosen candidate + quality decision, the swap
success/abort (with reason), and the exhaustion marking, so the operator + STATS-013 can see upgrade
health (upgrades performed, swaps aborted, tracks exhausted, average quality gain) without parsing
prose. See acceptance.md AC-NFR-Y-8.

---

## 15. Open Questions / Risks

- **D-Y-1 / R-Y-1 — Where to hook the title normalization (Medium, design).** At scan time the Track is
  built from the noisy yt-dlp filename BEFORE `note_source(key, "yt-dlp")` marks the source, so scoping
  the strip to "source=ytdlp" at scan time is awkward (source not yet set). Options: (A) apply the strip
  in the yt-dlp arm itself (which KNOWS the source deterministically) before/at the title→track
  mapping; (B) apply it as a source-scoped pre-ENRICH pass in `_enrich_on_download` on the yt-dlp
  branch. Recommended: (A) — the yt-dlp path is the one place the source is known for certain.
  Surfaced as decision D-Y-1.
- **R-Y-2 — The recorded source string is `"yt-dlp"`, not `"ytdlp"` (Low, build-time precision).**
  `note_source` is CALLED with `"yt-dlp"` (hyphen) in `acquire.py`, though its docstring lists
  `'ytdlp'`. The upgrade-candidate set MUST key off the exact recorded value (`"yt-dlp"`). Mitigated:
  the SPEC pins the candidate set to what `note_source` actually records; confirm the live string
  during implementation.
- **R-Y-3 — The `Track.path` writer is a same-dir RENAME, the swap is a cross-file MOVE (Medium,
  design).** FILENAME-024's `rename_track_file(key, new_basename)` renames within the same directory;
  the swap points `Track.path` at a DIFFERENT downloaded file. Mitigated: extend the sanctioned writer
  with an atomic-under-lock cross-file `swap_track_file(key, new_path)` sibling that (a) repoints
  `Track.path`, (b) deletes the old file, both under `self._lock` with rollback, preserving the
  `@MX:ANCHOR` "only-sanctioned-Track.path-writer" contract. Open: whether to generalize
  `rename_track_file` or add a sibling. Surfaced as decision D-Y-2.
- **R-Y-4 — Same-recording verification when no MBID exists (Medium, correctness).** Not every yt-dlp
  track gets a `recording_mbid` from ENRICH-012, and slskd candidates carry only a filename. Mitigated:
  fall back to DEDUP-014 version-aware fuzzy matching (which already distinguishes live/studio) and
  fail toward NOT-verified (keep the original) when sameness cannot be established (REQ-YQ-003). Open:
  tune the fuzzy sameness threshold so genuine upgrades are not blocked while substitutions are.
- **R-Y-5 — Establishing the CURRENT file's quality (Low/Medium, correctness).** The quality gate needs
  the current yt-dlp file's format/bitrate to know a candidate is strictly better. Mitigated: the file
  is known-lossy (yt-dlp `--audio-format mp3 --audio-quality 0`), and its actual bitrate can be read
  from the file (mutagen) or inferred from provenance; a lossless candidate is always strictly better.
  Open: confirm the cheapest reliable current-quality read.
- **R-Y-6 — Conservative-vs-aggressive noise list (Low, tuning).** Too aggressive a list could strip a
  legitimate `(Live)` / `(Acoustic)` that IS part of the title; too timid leaves cruft. Mitigated: the
  list is curated + extensible (REQ-YN-003) and source-scoped to yt-dlp (NFR-Y-6); the ambiguous tokens
  (`(Live)`, `(Acoustic)`, `(Remix)`) are DELIBERATELY excluded from the default strip list (they carry
  meaning), leaving only unambiguous marketing tokens. Open: curate the exact default list against real
  landed filenames.
- **R-Y-7 — bhive had no proven pattern for this stack (Low, recorded gap).** No bhive instruction
  exists for verified-before-delete identity-preserving swap on this stack. Action: re-run a bhive query
  during implementation and contribute the verified approach back per AGENTS.md.

---

## 16. Out-of-Scope / Future SPEC Roadmap

- **Upgrading already-slskd (non-yt-dlp) tracks to lossless** — a broader "best-copy sweep" over the
  whole library; deferred (v1 targets only the known-lossy yt-dlp population).
- **A `(Full Album)` / long-mix split-and-tag path** — a yt-dlp album/mix upload is a different problem
  (segmenting one file into tracks); the `(Full Album)` token is listed but the SPLIT is deferred to a
  future long-form SPEC; v1 only strips the token from a single-track title.
- **An operator "re-arm exhausted tracks" affordance** — a UI/command to reset the exhausted marker so
  a periodically-refreshing Soulseek pool gets re-checked; a future operator surface on top of the
  exhausted marker (REQ-YX-002).
- **An upgrade-health panel** in the operator/STATS-013 surface (upgrades performed, swaps aborted,
  average quality gain, exhausted count) — a future surface on top of the Group YI structured events.
- **A ReplayGain / loudness re-analysis on swap** — the swapped file changes the audio; re-running the
  ANALYSIS-006 loudness/cue analysis is desirable but deferred to the existing analyzer's backfill
  (the swap triggers a re-scan; deep re-analysis rides the analyzer horizon).

---

## 17. @MX Tag Targets (new-code danger zones / high fan_in)

[HARD] The following are the mandatory @MX annotation targets for the Run phase (per the @MX protocol),
because they are the danger zones + invariant contracts this SPEC introduces:

- **`@MX:ANCHOR` — the atomic cross-file swap writer** (`Library.swap_track_file` / the extended
  `rename_track_file`): the ONLY sanctioned path that repoints `Track.path` at a DIFFERENT file and
  deletes the old one, under `self._lock`, preserving `Track.key` + play-history. High fan_in / the
  identity-integrity contract (REQ-YS-002, NFR-Y-2). `@MX:REASON` required: a non-atomic or
  non-identity-preserving swap orphans play history / likes / stats or 404s the air path.
- **`@MX:WARN` — the old-file deletion** in the swap: an IRREVERSIBLE `os.remove` of the yt-dlp file
  that must happen ONLY after the replacement is verified (REQ-YS-001, NFR-Y-2). `@MX:REASON` required:
  deleting before verification leaves a track with no file.
- **`@MX:ANCHOR` — the never-downgrade quality gate** (the swap decision): the load-bearing invariant
  that a swap only ever raises quality on a verified same recording (REQ-YQ-002/003, NFR-Y-3).
  `@MX:REASON` required: a wrong gate downgrades quality or substitutes a different version.
- **`@MX:NOTE` — the replacement worker loop** and the title-normalization function: context for the
  bounded-cadence background lifecycle (REQ-YR-001/002) and the conservative source-scoped strip
  (REQ-YN-001).

---

## 18. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements are in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-YN-001 | YouTube Title Normalization | High | Event | AC-YN-001 |
| REQ-YN-002 | YouTube Title Normalization | High | Ubiquitous | AC-YN-002 |
| REQ-YN-003 | YouTube Title Normalization | Medium | Ubiquitous | AC-YN-003 |
| REQ-YN-004 | YouTube Title Normalization | High | Ubiquitous | AC-YN-004 |
| REQ-YN-005 | YouTube Title Normalization | High | State | AC-YN-005 |
| REQ-YP-001 | Provenance & Upgrade-Candidate Set | High | Event | AC-YP-001 |
| REQ-YP-002 | Provenance & Upgrade-Candidate Set | High | Event | AC-YP-002 |
| REQ-YP-003 | Provenance & Upgrade-Candidate Set | High | Ubiquitous | AC-YP-003 |
| REQ-YR-001 | Replacement Worker | High | Ubiquitous | AC-YR-001 |
| REQ-YR-002 | Replacement Worker | High | State | AC-YR-002 |
| REQ-YR-003 | Replacement Worker | High | Event | AC-YR-003 |
| REQ-YR-004 | Replacement Worker | Medium | Event | AC-YR-004 |
| REQ-YQ-001 | Quality Gate | High | Ubiquitous | AC-YQ-001 |
| REQ-YQ-002 | Quality Gate | High | Unwanted | AC-YQ-002 |
| REQ-YQ-003 | Quality Gate | High | Unwanted | AC-YQ-003 |
| REQ-YS-001 | Safe Swap | High | Unwanted | AC-YS-001 |
| REQ-YS-002 | Safe Swap | High | Ubiquitous | AC-YS-002 |
| REQ-YS-003 | Safe Swap | High | Unwanted | AC-YS-003 |
| REQ-YS-004 | Safe Swap | High | Event | AC-YS-004 |
| REQ-YX-001 | Exhaustion & Idempotency | High | Unwanted | AC-YX-001 |
| REQ-YX-002 | Exhaustion & Idempotency | High | State | AC-YX-002 |
| REQ-YX-003 | Exhaustion & Idempotency | High | Ubiquitous | AC-YX-003 |
| REQ-YC-001 | Config | Medium | Ubiquitous | AC-YC-001 |
| REQ-YI-001 | Interactions / Integration | High | Unwanted | AC-YI-001 |
| REQ-YI-002 | Interactions / Integration | High | Ubiquitous | AC-YI-002 |
| REQ-YI-003 | Interactions / Integration | High | Ubiquitous | AC-YI-003 |
| REQ-YI-004 | Interactions / Integration | Medium | Event | AC-YI-004 |
| NFR-Y-1 | Non-Functional | High | Ubiquitous | AC-NFR-Y-1 |
| NFR-Y-2 | Non-Functional | High | Ubiquitous | AC-NFR-Y-2 |
| NFR-Y-3 | Non-Functional | High | Ubiquitous | AC-NFR-Y-3 |
| NFR-Y-4 | Non-Functional | High | Ubiquitous | AC-NFR-Y-4 |
| NFR-Y-5 | Non-Functional | High | Ubiquitous | AC-NFR-Y-5 |
| NFR-Y-6 | Non-Functional | High | Ubiquitous | AC-NFR-Y-6 |
| NFR-Y-7 | Non-Functional | High | Unwanted | AC-NFR-Y-7 |
| NFR-Y-8 | Non-Functional | Medium | Ubiquitous | AC-NFR-Y-8 |

Parity: 27 REQ + 8 NFR = 35 specified items; 35 acceptance entries (27 AC + 8 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: YN (YouTube Title Normalization) = 5, YP (Provenance & Upgrade-Candidate
Set) = 3, YR (Replacement Worker) = 4, YQ (Quality Gate) = 3, YS (Safe Swap) = 4, YX (Exhaustion &
Idempotency) = 3, YC (Config) = 1, YI (Interactions / Integration) = 4 → 5+3+4+3+4+3+1+4 = 27 REQ across
8 groups. NFR-Y-1…8 = 8 NFR. Total = 27 + 8 = 35 specified items, 35 acceptance entries, 1:1 REQ↔AC.

---

## Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 + the
Section 16 roadmap + the fixed rails, as the mandatory exclusions list):

- **Downgrading quality, ever** — a swap only happens on a strictly-better candidate; equal-or-worse is
  discarded, the yt-dlp file kept (REQ-YQ-002, NFR-Y-3).
- **Deleting the yt-dlp file before a verified replacement exists** — verified-before-delete; a failed
  swap leaves the original untouched (REQ-YS-001, NFR-Y-2).
- **Substituting a different recording** (a live/remix/alternate version) for the original — same-
  recording verification is required; a different version is not an upgrade (REQ-YQ-003).
- **Re-keying / re-identifying the track, or resetting its play history** — the swap preserves
  `Track.key` + `play_count`/`last_played`/`added_at`; likes (LIKE-015) + stats (STATS-013) are never
  orphaned (REQ-YS-002, REQ-YI-003).
- **Swapping the in-flight file** (on-air / handed-out / prefetch horizon) — never swapped, deferred
  (REQ-YS-003).
- **Blanket parenthetical stripping / normalizing non-YouTube titles** — the strip is curated + scoped
  to `source=ytdlp`; legitimate parentheticals and non-YouTube tracks are never touched (REQ-YN-001,
  NFR-Y-6). The backfill of existing yt-dlp titles edits ONLY the display `Track.title` (never the
  dedup key / path / play-history) and is idempotent + repeatable (REQ-YN-005).
- **Searching an unfindable track forever** — bounded attempts → exhausted marker (REQ-YX-002).
- **Re-processing an already-upgraded track** — idempotent; excluded from the candidate set
  (REQ-YX-001).
- **Bypassing VETTING-027 / DEDUP-014** — the candidate passes the same vet gate; the swap composes
  with (never fights) the version-aware dedup gate (REQ-YI-001, REQ-YI-002).
- **Upgrading already-slskd (non-yt-dlp) tracks** — the candidate set is yt-dlp-sourced only; a broader
  best-copy sweep is a future SPEC (Section 16).
- **Splitting a `(Full Album)` / long-mix yt-dlp upload into tracks** — deferred to a future long-form
  SPEC; v1 only strips the token from a single-track title (Section 16).
- **Re-owning the yt-dlp fetch command, the slskd client, the acquisition pipeline, the ENRICH-012
  engine, the FILENAME-024 `Track.path` writer, the VETTING-027 / DEDUP-014 gates, or the
  LIKE-015/STATS-013 stores** — all referenced/composed, never forked (NFR-Y-5).
- **A new datastore or a new web service** — brain-only + additive; provenance in the existing store
  seam (NFR-Y-5).
- **Blocking / silencing playout for a normalization or a swap** — everything runs background, off the
  pull path (REQ-YR-002, NFR-Y-1).

---

## 19. User-Provisioned Prerequisites (the real user must provide / decide)

[HARD] YTREPLACE-057 provisions no external account or hardware. The following are flagged so the user
knows what is required / decided.

- **The replacement-worker enable decision.** The replacement worker is OFF by default (REQ-YC-001);
  turning it on is the operator's explicit choice. Title normalization (cheap, non-destructive) MAY
  default on independently.
- **slskd availability.** The re-search only works WHEN slskd is enabled (slskd is OFF by default per
  the user, started on-demand); with slskd off, the worker simply finds no candidates and defers.
- **The quality margin + cadence + max-attempts tuning.** The knobs have sane defaults; the operator
  may tune how much better a candidate must be, how often the worker runs, and how many attempts before
  a track is exhausted (REQ-YC-001).
- **The curated noise list.** The default list ships (REQ-YN-003); the operator may extend it for
  channel-specific cruft they observe.
