---
id: SPEC-RADIO-YTREPLACE-057-plan
version: 0.1.0
status: draft
created: 2026-07-01
updated: 2026-07-01
author: charlie
spec: SPEC-RADIO-YTREPLACE-057
---

# SPEC-RADIO-YTREPLACE-057 — Implementation Plan

Implementation plan for the YouTube title normalization + provenance-tracked quality-upgrade swap.
Priority labels only (no time estimates). DDD posture: characterization-first, behavior-preserving
(the replacement worker defaults OFF so the disabled path is byte-identical to today).

---

## 1. Technical Approach

The subsystem is brain-only and additive. It hooks a conservative title-normalizer onto the yt-dlp
acquisition arm, captures provenance through the EXISTING `Library.note_source` seam + allowlist
provenance writer, and adds ONE new background worker (mirroring `FilenameWorker`) that re-searches
slskd for yt-dlp-sourced tracks and swaps in a verified, strictly-better, same-recording file through a
sanctioned atomic `Track.path` writer that preserves the track's identity + play history.

Seams to touch (all confirmed this session):
- `brain/ytdlp.py` `fetch()` — the yt-dlp arm that lands `%(title)s.%(ext)s` and KNOWS the source is
  YouTube (the normalization hook point, D-Y-1 recommended option A).
- `brain/acquire.py` `_acquire_one` — records `note_source(key, "yt-dlp")` + runs `_enrich_on_download`;
  provenance capture rides here; the worker reuses `RateLimiter` + `AttemptsIndex` posture.
- `brain/slskd.py` `SlskdClient` (`start_search`/`get_responses`/`collect_candidates`/`acceptable`/
  `best_candidate`) + `Candidate.rank_key` + `LOSSLESS_EXTS` — the re-search + quality signals.
- `brain/library.py` `note_source` → `provenance["source"]`, `set_provenance` (allowlist), `Track.key`
  frozen slug, and `rename_track_file` (`@MX:ANCHOR`, atomic under `self._lock`) — extend with an atomic
  cross-file `swap_track_file(key, new_path)` sibling (D-Y-2).
- `brain/state.py` `now_playing`/`last_committed_path`/prefetch horizon — the never-swap-in-flight guard.
- `brain/config.py` `_env` frozen `Config` — the new `BRAIN_*` knobs (replacement worker default OFF).
- `brain/main.py` worker-start block — construct + `.start()` the new worker alongside the others.
- `brain/enrich.py` / `brain/dedup.py` / `Acquirer.vetting_gate` — re-enrich + same-recording + vet.

New module: a `brain/ytupgrade.py` (or similarly named) holding the pure title-normalizer + the
`YtUpgradeWorker`, mirroring the `brain/filename.py` shape (pure functions + a worker class), so the
normalizer is unit-testable without the worker.

---

## 2. Milestones (priority-ordered, dependency-first)

### M1 — Title normalization (Group YN) — Priority High
- Pure `normalize_youtube_title()` in the new module: curated noise-pattern list (REQ-YN-003 fixture),
  conservative source-scoped strip (REQ-YN-001), idempotent + edge/empty-safe (REQ-YN-002).
- Hook it onto the yt-dlp arm (D-Y-1 option A) so it runs BEFORE the title becomes the clean
  artist/title. No behavior change for slskd/manual tracks.
- Characterization tests over the fixture (including non-YouTube-untouched + idempotency + edge cases).

### M2 — Provenance capture + upgrade-candidate set (Group YP) — Priority High
- Confirm the recorded source string (`"yt-dlp"`, R-Y-2) and capture the original YouTube title + fetch
  time via the allowlist provenance writer (REQ-YP-002).
- A queryable `upgrade_candidates()` over the library (source=ytdlp, not-upgraded, not-exhausted)
  (REQ-YP-003). No new datastore.

### M3 — The atomic cross-file swap writer (Group YS core) — Priority High [danger zone]
- Add `Library.swap_track_file(key, new_path)` (D-Y-2): under `self._lock`, repoint `Track.path` to the
  new (already-staged, verified) file, delete the old file, with rollback; preserve `Track.key` +
  play-history (REQ-YS-002). Extends the FILENAME-024 `@MX:ANCHOR` contract.
- `@MX:ANCHOR` on the writer + `@MX:WARN` on the old-file `os.remove` (spec Section 17).
- Characterization tests: atomic / rollback / collision / preserve-key-and-play-history / no
  scan-prune-then-re-add (Section B2).

### M4 — Quality gate + same-recording verification (Group YQ) — Priority High [invariant]
- Define the quality ordering + margin (REQ-YQ-001) reusing `is_lossless`/`effective_bitrate`; read the
  current file's quality (R-Y-5).
- Never-downgrade rule (REQ-YQ-002) + same-recording verification via `recording_mbid` else DEDUP-014
  fuzzy (REQ-YQ-003, R-Y-4). `@MX:ANCHOR` on the swap decision.

### M5 — Replacement worker + safe-swap orchestration (Groups YR, YS-001/003/004) — Priority High
- The `YtUpgradeWorker`: bounded occasional cadence, bounded batch, off the pull path, exception-isolated
  (REQ-YR-001/002); re-search slskd by clean artist+title (REQ-YR-003); select best candidate (REQ-YR-004).
- Staged download → verify-before-delete (REQ-YS-001); never-swap-in-flight guard (REQ-YS-003); provenance
  trail on success (REQ-YS-004). Wire into `main.py` (`@MX:NOTE`).

### M6 — Exhaustion + idempotency + config (Groups YX, YC) — Priority High
- Attempt counting + exhausted marker (REQ-YX-002); already-upgraded skip (REQ-YX-001); reuse rate limiter
  + cooldown (REQ-YX-003).
- `BRAIN_*` knobs (REQ-YC-001), replacement worker DEFAULT OFF.

### M7 — Interactions + observability + docs (Group YI, NFR-Y-8) — Priority Medium
- VETTING-027 gate on candidates (REQ-YI-001); DEDUP-014 compose (REQ-YI-002); LIKE-015/STATS-013
  integrity assertions (REQ-YI-003); ENRICH-012 re-enrich + FILENAME-024 re-flag (REQ-YI-004).
- Structured `log_event` for normalize / re-search / candidate / gate / swap-or-abort / exhaust.
- Docs-sync: `docs/components/*` + runtime-config for the new knobs.

---

## 3. Behavior-Preservation Contract [HARD]

- The replacement worker DEFAULT OFF: with `BRAIN_*` upgrade disabled, no re-search/swap runs and the
  system is byte-identical to today.
- Title normalization affects ONLY yt-dlp-sourced titles; slskd/manual tracks are untouched.
- No frozen `Track` identity field is written except `Track.path` via the sanctioned atomic writer.
- No sibling SPEC store/API observable behavior changes beyond provenance writes + the path repoint.

---

## 4. Risks (see spec.md Section 15 for full detail)

- D-Y-1 — normalization hook point (recommend: the yt-dlp arm, which knows the source).
- D-Y-2 — cross-file swap writer vs. same-dir `rename_track_file` (recommend: an atomic
  `swap_track_file` sibling preserving the `@MX:ANCHOR` contract).
- R-Y-2 — the recorded source string is `"yt-dlp"` (hyphen), not `"ytdlp"` — pin the candidate set to it.
- R-Y-4 — same-recording verification without an MBID — DEDUP-014 fuzzy + fail-toward-keep.
- R-Y-5 — reading the current file's quality — file is known-lossy; a lossless candidate is always
  strictly better.
- R-Y-6 — curating the noise list (exclude ambiguous `(Live)`/`(Acoustic)`/`(Remix)`).

---

## 5. Test Strategy

- Pure-function unit tests for the normalizer (fixture-driven, Section B5).
- Characterization tests for the atomic swap writer (Section B1/B2) and the never-downgrade +
  same-recording gate (Section B3).
- Worker tests with stubbed slskd/yt-dlp (no network): in-flight defer (B4), idempotency + exhaustion
  (B6), resilience/degrade (B7).
- Integration assertions that likes (LIKE-015) + play_events (STATS-013) resolve to the same key after a
  swap (B2 / AC-YI-003).
- Full `pytest brain/ -q` green + ruff clean + no regression to sibling suites.
