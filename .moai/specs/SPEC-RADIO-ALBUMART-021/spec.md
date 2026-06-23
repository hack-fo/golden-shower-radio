---
id: SPEC-RADIO-ALBUMART-021
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: Medium
issue_number: 21
---

# SPEC-RADIO-ALBUMART-021 — Album-Art Acquisition + Embedding (Cover Art Archive)

## HISTORY

- 2026-06-23 (v0.1.1): DDD implementation slice (ANALYZE-PRESERVE-IMPROVE). Group AK was found ALREADY
  BUILT by ENRICH-012 Group EC — `release_group_mbid` is captured on both identification paths, carried
  on `Canonical`, persisted on `Track`, and in `_ENRICH_WRITABLE_FIELDS` — so the CAA key requirement was
  already satisfied (the `release_mbid` secondary fallback key is NOT yet captured, so the AF release-MBID
  fallback path exists in the fetcher but is dormant until that field lands; DEFERRED). Groups AF/AC/AS/AW/AG
  were UNBUILT and are now implemented additively in a new `brain/albumart.py`: CAA front-cover fetch
  (`fetch_front_cover`, httpx, bounded `front-500` thumbnail, polite throttle mirroring
  `metadata._mb_throttle`, 404/non-image/network all graceful-skip → None); per-format embed
  (`embed_front_cover` → id3 APIC / FLAC PICTURE / m4a covr, embed-only preserve-everything-else,
  idempotent skip-if-present, force-refresh override); the end-to-end art step (`embed_art_for_track`,
  shares `BRAIN_ENRICH_WRITE_FILES` gate with dry-run logging when off, fully exception-isolated). Wired
  into `enrich.EnrichmentWorker.enrich_one` via a new `_embed_art` step AFTER the tag write (rides the
  existing worker, never a second thread; reached by both the backfill loop and the acquire.py
  on-download hook through the same `enrich_one`). Added the INDEPENDENT `Track.art_version` skip-marker
  (REQ-AW-002, distinct from `enrich_version`) + `_ENRICH_WRITABLE_FIELDS` extension, and config knobs
  `BRAIN_ALBUMART_ENABLED` (default on), `BRAIN_ALBUMART_SIZE` (default `front-500`),
  `BRAIN_ALBUMART_FORCE_REFRESH` (default off). Note REQ-AS-002 "baseline-backup discipline": ENRICH-012
  has no separate `.bak` mechanism — its discipline IS the in-place-mutate-existing-tag-object (never
  rebuild) pattern, which the embed mirrors exactly. 31 offline/deterministic tests added
  (`brain/test_albumart.py`: mocked-CAA fetch incl. 404/network-error/non-image/release-fallback,
  real mutagen APIC+PICTURE+covr round-trips, idempotency, embed-only preservation incl. non-front
  pictures, gate-off dry-run, exception-isolation, and the enrich_one worker-wiring path). Full suite:
  210 → 241 passed, 1 deselected, 0 skips, 0 failures.
- 2026-06-23 (v0.1.0): Initial draft, occupying the new global-incrementing ALBUMART-021 id. The
  twenty-first authored SPEC in the golden-shower-radio RADIO series and a FOCUSED EXTENSION of the
  ENRICH-012 core-tag enrichment engine: where ENRICH-012 IDENTIFIES the canonical recording and
  CORRECTS a track's artist/title/album/year/genre on the file + library, ALBUMART-021 adds the missing
  visual identity — it FETCHES the front cover from the Cover Art Archive (coverartarchive.org,
  MetaBrainz's CC0/public-domain art DB), keyed by the MusicBrainz RELEASE-GROUP MBID, and EMBEDS it
  into the audio file (id3 APIC for .mp3, FLAC/Vorbis picture block for .flac, m4a `covr`). It runs in
  the SAME identification pass as ENRICH-012 (the EnrichmentWorker backfill + the on-download hook), so a
  track whose tags get corrected ALSO gets its art embedded in one pass. It is gated behind the SAME
  write-files gate (`BRAIN_ENRICH_WRITE_FILES`) and the same baseline-backup + exception-isolation
  discipline (the file is being mutated). [HARD][USER DECISION] The art is EMBEDDED IN THE FILE ONLY — it
  is NOT displayed or served on the website; the listener website stays art-free per the user's explicit
  decision. RADIO SPEC-IDs are GLOBAL-INCREMENTING (CORE-001, VOICE-002, CALLIN-003, OPS-004, ORCH-005,
  ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009, IMAGING-010, REQUEST-011, ENRICH-012,
  STATS-013, DEDUP-014, LIKE-015, HOSTCTX-016, MBMIRROR-017, WEBUI-018, ACQQUEUE-019, ALBUMART-021 = this;
  020 is reserved/used elsewhere in the series). It uses a DISTINCT REQ namespace — AK (release-group
  MBID capture), AF (Cover Art Archive fetch), AC (embed into file), AS (write safety), AW (worker
  wiring), AG (config) — to avoid collision with the sibling SPECs' prefixes (notably ANALYSIS-006's
  AE/AT/AM/AD/AP and CALLIN-003's CC). [HARD][DEPENDENCY] The art fetch needs the MB release-group MBID,
  which ENRICH-012 resolves internally but does NOT currently persist — this SPEC REQUIRES a small
  ENRICH-012 addition to capture + expose the release-group MBID (Group AK); see Section 2.
  Total: 15 REQ + 6 NFR = 21, 1:1 REQ↔AC (AK=2, AF=3, AC=3, AS=3, AW=2, AG=2).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "the tags are right; now the art is too — embedded, not on the website"

ENRICH-012 fixes the CORE IDENTITY tags that slskd / yt-dlp rips routinely get wrong (empty artist, the
artist folded into the title, missing album/year) by identifying the canonical recording (AcoustID
fingerprint, then MusicBrainz text-match) and writing corrected tags back to the file via mutagen. What
it does NOT do is give the file its VISUAL identity: the embedded front cover. A library of correctly
tagged but art-less files is a degraded artifact — a player, a phone, a car head-unit, or a future tool
all show a blank square.

ALBUMART-021 closes that gap with the narrowest possible scope: once ENRICH-012 has identified a track's
canonical recording, this SPEC fetches the front cover from the Cover Art Archive (keyed by the
MusicBrainz release-group MBID that the identification already resolved) and embeds it into the audio
file, in the SAME pass, under the SAME write-files gate and the SAME safety discipline. The result is a
self-describing file: correct artist/title/album/year/genre AND the right front cover, baked in.

[HARD][USER DECISION] The art is embedded IN THE FILE ONLY. It is deliberately NOT displayed or served
on the listener website — the website stays art-free. This SPEC builds the acquisition + embed engine,
nothing visual. The website non-goal is a fixed scope boundary (Section 4.2, Section 12), not a deferral.

### 1.2 The dependency that makes this possible (the load-bearing fact)

[HARD][DEPENDENCY] The Cover Art Archive is keyed by the MusicBrainz RELEASE-GROUP MBID (or a specific
release MBID). ENRICH-012's identification ALREADY obtains this id: the AcoustID lookup returns
`recordings[].releasegroups[].id`, and the MusicBrainz text-match returns the recording's
`release-list[].release-group.id`. But ENRICH-012 today reads only the release-group TITLE (the album
name) from those structures (`_canonical_from_acoustid` lifts `rg.get("title")`; `_release_album_year`
lifts the album title + year) — it never captures the MBID. Without the MBID, there is no key to query
the Cover Art Archive.

Therefore ALBUMART-021 REQUIRES a small, surgical ENRICH-012 addition (Group AK): capture the
release-group MBID (and, as a secondary fallback, the release MBID) on the `Canonical`/`Track` and expose
it to the art layer. This is the one cross-SPEC change this SPEC depends on; it is additive (a new
field + two extraction lines in the two existing identification paths) and changes no ENRICH-012 logic.

### 1.3 What this layer is, concretely

- A RELEASE-GROUP MBID CAPTURE addition to ENRICH-012 (Group AK): capture the release-group MBID from
  BOTH identification paths (AcoustID `releasegroups[].id`, MusicBrainz text `release-group.id`), persist
  it on the resolved identity, and expose it to the art layer. A release MBID is captured as a secondary
  fallback key.
- A COVER ART ARCHIVE FETCHER (Group AF): given a release-group MBID, GET
  `coverartarchive.org/release-group/{mbid}/front` at a BOUNDED thumbnail size (default `front-500`) to
  keep embedded file growth reasonable; fall back to a release MBID front if the release-group has none;
  a 404 / miss / empty response is a graceful skip (no art is fine); polite rate-limiting to CAA.
- AN EMBEDDER (Group AC): embed the fetched front cover into the audio file via mutagen — an id3 `APIC`
  frame for .mp3, a FLAC/Vorbis `PICTURE` block for .flac/.ogg/.opus, and an MP4 `covr` atom for .m4a/
  .mp4 — IDEMPOTENTLY (skip a file that already has a front cover unless a force/refresh flag; embedding
  identical art is a no-op), mutating ONLY the cover (every other tag/frame preserved byte-intact).
- A WRITE-SAFETY layer (Group AS): the embed is gated behind the SAME `BRAIN_ENRICH_WRITE_FILES` gate as
  ENRICH-012's tag write-back, follows the SAME baseline-backup discipline (the file is being mutated),
  and is exception-isolated so it never blocks the playout, never crashes the daemon, and a CAA/embed
  failure degrades to "no art" rather than an error.
- WORKER WIRING (Group AW): the art fetch + embed runs INSIDE / ALONGSIDE the ENRICH-012 EnrichmentWorker
  — both the bounded/throttled/resumable backfill pass over the existing library AND the on-download hook
  (acquire.py) — AFTER identification, so a track that gets its tags corrected also gets its art embedded
  in the same pass. It mirrors the worker's bounded/throttled/resumable pattern and uses its own
  idempotent skip-marker so a track that already has embedded art is not re-fetched.
- CONFIG (Group AG): an enable toggle for the art-embed engine, the art thumbnail size, and a
  force-refresh toggle; the file mutation shares the ENRICH-012 write-files gate.

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] ALBUMART-021 OWNS the Cover-Art-Archive front-cover acquisition + the file embed wired to the
ENRICH-012 identification pass. It MUST NOT restate, fork, or weaken any ENRICH-012, ANALYSIS-006,
TAGSTREAM-009, CORE-001, or OPS-004 requirement, and it MUST NOT re-own the canonical-recording
identification, the mutagen write seam, the EnrichmentWorker lifecycle, or the write-files gate — it
EXTENDS / CONSUMES them.

OWNS:
- The RELEASE-GROUP MBID CAPTURE requirement on ENRICH-012's identification output (Group AK) — the new
  field + the two extraction points + exposure to the art layer. (The IDENTIFICATION itself stays
  ENRICH-012's; ALBUMART-021 owns only the requirement that the already-resolved MBID is captured.)
- The COVER ART ARCHIVE FETCH: the `release-group/{mbid}/front` query, the bounded thumbnail size, the
  release-MBID fallback, the 404/miss graceful skip, and the polite CAA rate-limit (Group AF).
- The EMBED: the APIC / FLAC-picture / m4a-covr write, the skip-if-front-cover-present idempotency, the
  embed-only / preserve-everything-else discipline (Group AC).
- The WRITE-SAFETY for the art mutation: the shared-gate + baseline-backup + exception-isolation rules
  AS APPLIED to the cover embed (Group AS).
- The WORKER WIRING of the art step into the ENRICH-012 backfill + on-download pass and the art
  skip-marker (Group AW).
- The CONFIG knobs: enable toggle, art size, force-refresh, shared write-files gate (Group AG).

REFERENCES (consumes / extends; does not restate):
- **ENRICH-012 (`brain/enrich.py`) — `identify()` / `Canonical` / `identify_acoustid` /
  `identify_text` / `EnrichmentWorker` / `enrich_one` / `write_tags`** — the identification that resolves
  the canonical recording (and the MBID, after the Group AK addition); the worker the art step rides on;
  the mutagen write discipline (idempotent, preserve-other-frames, exception-isolated) the embed mirrors.
  ALBUMART-021 extends the identification output (Group AK) and rides the worker (Group AW); it does NOT
  re-own identification or the worker lifecycle.
- **`brain/config.py` — `enrich_write_files` (`BRAIN_ENRICH_WRITE_FILES`) + `enrich_tags_enabled` +
  `enrichment_http_timeout_seconds` + the MB throttle in `brain/metadata.py`** — the write gate the
  embed shares, the master enrich toggle, the HTTP timeout, and the polite request spacing the CAA fetch
  reuses; referenced, not re-owned.
- **`brain/library.py` — `Track` + `set_core_tags` + the `_ENRICH_WRITABLE_FIELDS` allowlist** — the
  Track record the captured MBID + the art skip-marker attach to, and the locked persistence accessor the
  bookkeeping is written through (allowlist EXTENDED additively for the new fields); referenced, not
  re-owned (it never touches the frozen `key`/`path`/play-history fields).
- **`brain/acquire.py` — the on-download `_enrich_on_download` / `enricher.enrich_one` hook** — the
  on-landing path the art step joins (it already calls `enrich_one`, which after this SPEC also embeds
  art); referenced, not re-owned.
- **TAGSTREAM-009 Group TA (artwork) + Group TX (listener exposure)** — the broader artwork concept.
  [HARD] ALBUMART-021 OWNS the concrete CAA-by-release-group-MBID fetch + embed-on-enrich path; it does
  NOT build any website/now-playing art display (TAGSTREAM-009 TX / WEBUI-018 territory), and the user
  has decided the website stays art-free, so there is no display conflict. See Section 2 + the decision
  surfaced to the orchestrator.

### 1.5 Fixed engineering rails (the only hard constraints)

- **Embedded in the file, NEVER on the website.** [HARD][USER DECISION] The art is embedded into the
  audio file only; it is not displayed, served, linked, or referenced on the listener website. The
  website stays art-free (REQ-AC-001, Section 12).
- **Cover Art Archive only; keyed by release-group MBID.** [HARD] The source is the Cover Art Archive
  (`coverartarchive.org/release-group/{mbid}/front`), keyed by the MB release-group MBID (release MBID as
  secondary fallback). No Last.fm images (non-commercial + frequently 404 per the SHOWS-020 research); no
  other source in v1 (REQ-AF-001).
- **The MBID dependency on ENRICH-012 is explicit.** [HARD][DEPENDENCY] The art fetch requires the
  release-group MBID; ENRICH-012 must capture + expose it (Group AK). Until that addition lands, the art
  layer has no key and is a graceful no-op (REQ-AK-001/002).
- **Bounded thumbnail size.** [HARD] The fetched cover uses a bounded thumbnail size (default
  `front-500`) so embedding does not balloon file size (REQ-AF-002, NFR-AA-6).
- **A miss is fine.** [HARD] A CAA 404 / empty / network failure is a graceful skip — no art embedded,
  no error raised; the track is simply art-less (REQ-AF-003, NFR-AA-3).
- **Idempotent embed.** [HARD] A file that already has a front cover is skipped (unless force-refresh);
  embedding identical art is a no-op (REQ-AC-002).
- **Embed-only mutation.** [HARD] The embed writes ONLY the cover; every other tag/frame (the
  ENRICH-012-corrected artist/title/album/year/genre, comments, ReplayGain) is preserved byte-intact
  (REQ-AC-003), mirroring ENRICH-012's write discipline.
- **Shares the write-files gate.** [HARD] The art mutation is gated behind the SAME
  `BRAIN_ENRICH_WRITE_FILES` gate as ENRICH-012's tag write-back; gate off → no file mutation
  (REQ-AS-001).
- **Same baseline-backup discipline.** [HARD] The file is being mutated, so the art embed follows the
  SAME baseline-backup discipline ENRICH-012 applies before a destructive in-place write (REQ-AS-002).
- **Never blocks / silences playout.** [HARD] The art fetch + embed is background, off the `<1s`
  `/api/next` pull path; it never blocks the picker or the audio path, and a slow/failing CAA fetch never
  stalls playout (REQ-AS-003, NFR-AA-1).
- **Rides the ENRICH-012 worker; never re-owns it.** [HARD] The art step runs inside / alongside the
  EnrichmentWorker backfill + on-download pass, AFTER identification, mirroring the worker's
  bounded/throttled/resumable pattern; it does not stand up a second worker (REQ-AW-001/002, NFR-AA-4).
- **Brain-only; additive.** [HARD] ALBUMART-021 adds an art-fetch + embed module to the existing `brain/`
  package, a field + a skip-marker to the existing `Track`, and config knobs; no new service, no new
  datastore (NFR-AA-4).

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-ENRICH-012 (the core-tag enrichment engine it extends) and references
SPEC-RADIO-CORE-001 (the library + the never-stop identity), SPEC-RADIO-ANALYSIS-006 (the analysis
worker pattern the EnrichmentWorker mirrors), and SPEC-RADIO-TAGSTREAM-009 (the broader artwork concept,
for boundary discipline) by CONCEPT and, where a cited symbol is a deliberately stable seam, by name.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any sibling SPEC requirement. Where it needs a
predecessor behavior it consumes it. Where an art action could conflict with continuous operation or the
file-safety discipline, the inherited behavior WINS — the music keeps playing and a file is never
mutated outside the write-files gate + the baseline-backup discipline.

### 2.1 [HARD][DEPENDENCY] The ENRICH-012 release-group-MBID capture addition (Group AK)

This is the one cross-SPEC change ALBUMART-021 requires. ENRICH-012 today resolves the canonical
recording and reads the release-group TITLE + year, but does NOT capture the release-group MBID:

- `brain/enrich.py` `_canonical_from_acoustid` iterates `rec.get("releasegroups")` and lifts
  `rg.get("title")` — it must ALSO lift `rg.get("id")` (the release-group MBID).
- `brain/enrich.py` `_release_album_year` iterates a recording's `release-list[].release-group` and reads
  the primary/secondary type + first-release-date — it must ALSO surface the chosen release-group's `id`
  (and the release `id` as a secondary fallback).
- `brain/enrich.py` `Canonical` must gain a `release_group_mbid` (and optional `release_mbid`) field, set
  on both paths; `enrich_track` / `enrich_one` must expose it to the art layer.
- `brain/library.py` `Track` must gain a `release_group_mbid` field (and the art skip-marker, Group AW);
  `_ENRICH_WRITABLE_FIELDS` must be EXTENDED to allow persisting them via `set_core_tags`.

Group AK (REQ-AK-001/002) encodes this requirement. It is additive (a new field + two extraction points +
allowlist extension), changes no ENRICH-012 identification/propose logic, and is the prerequisite for any
art fetch. Whether the AK change ships as a small ENRICH-012 amendment or inside this SPEC's
implementation is an orchestrator decision (Section 15); the REQUIREMENT that the MBID is captured +
exposed is owned here either way.

### 2.2 ENRICH-012 seams consumed (by name, deliberately)

- **`identify()` / `Canonical`** — the resolved canonical recording (and, post-AK, the MBID) the art
  fetch keys on.
- **`EnrichmentWorker` / `enrich_one` / the `_tick` backfill loop + the `_select_batch` schema gate** —
  the bounded/throttled/resumable worker the art step rides; the art step is invoked from the same
  `enrich_one` end-to-end path (Group AW).
- **`write_tags` / `_write_id3` / `_write_vorbis`** — the mutagen write discipline (idempotent,
  preserve-other-frames + APIC/picture art ALREADY preserved, exception-isolated) the embed mirrors. Note
  ENRICH-012's tag writes ALREADY preserve existing embedded art; ALBUMART-021 adds the art itself.
- **`acquire.py` `_enrich_on_download` → `enricher.enrich_one`** — the on-download hook the art step
  joins (no new hook needed; `enrich_one` gains the art step).

### 2.3 config seams consumed

- **`enrich_write_files` (`BRAIN_ENRICH_WRITE_FILES`)** — the SHARED gate the art mutation obeys.
- **`enrich_tags_enabled` (`BRAIN_ENRICH_TAGS_ENABLED`)** — the master enrich toggle the worker honors.
- **`enrichment_http_timeout_seconds` + `brain/metadata.py` `_mb_throttle`** — the HTTP timeout + the
  polite request spacing the CAA fetch reuses (CAA gets its own bounded spacing; see REQ-AF-003).

### bhive memory seam

bhive memory (AGENTS.md protocol) has no proven pattern for the Cover-Art-Archive-by-release-group-MBID
fetch + mutagen-embed-on-enrich pattern on this Python+mutagen stack (recorded gap). Re-run a bhive query
on the CAA front-endpoint + thumbnail-size + APIC/FLAC-picture/m4a-covr embed pattern during
implementation, and contribute the verified approach back per the AGENTS.md memory protocol.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Cover Art Archive (CAA)** | MetaBrainz's CC0/public-domain cover-art database at `coverartarchive.org`, keyed by MusicBrainz release / release-group MBIDs. The ONLY art source in v1 (REQ-AF-001). |
| **Release-group MBID** | The MusicBrainz identifier for an album as a creative work (across editions). The PRIMARY CAA key: `coverartarchive.org/release-group/{mbid}/front`. Resolved by ENRICH-012's identification; captured by Group AK. |
| **Release MBID** | The MusicBrainz identifier for a SPECIFIC release (edition) of an album. The SECONDARY fallback CAA key when the release-group has no front cover (REQ-AF-001, REQ-AK-002). |
| **Front cover** | The album's front-cover image. The only image type this SPEC fetches/embeds — `.../front` (not back, booklet, or medium) (REQ-AF-001). |
| **Bounded thumbnail size** | The CAA thumbnail variant requested (default `front-500` = ≤500px) so the embedded image keeps file growth reasonable rather than embedding a multi-MB full-resolution scan (REQ-AF-002, NFR-AA-6). |
| **APIC frame** | The id3v2 attached-picture frame embedding cover art in a `.mp3` (REQ-AC-001). |
| **FLAC/Vorbis picture block** | The `METADATA_BLOCK_PICTURE` / FLAC `Picture` embedding cover art in `.flac`/`.ogg`/`.opus` (REQ-AC-001). |
| **m4a `covr` atom** | The MP4 cover-art atom embedding cover art in `.m4a`/`.mp4` (REQ-AC-001). |
| **Idempotent embed** | A file that already carries a front cover is SKIPPED (unless force-refresh); embedding the identical image is a no-op (REQ-AC-002). |
| **Art skip-marker** | The per-track bookkeeping that records the art step has run for a track (cover embedded, or none found), so the backfill does not re-fetch it — distinct from ENRICH-012's `enrich_version` so the two passes are independent (REQ-AW-002). |
| **Write-files gate** | The shared `enrich_write_files` (`BRAIN_ENRICH_WRITE_FILES`) config. When False, no file is mutated (no art embedded); the art step still resolves what it WOULD embed for dry-run visibility (REQ-AS-001). |
| **Baseline-backup discipline** | The same pre-mutation backup discipline ENRICH-012 applies before a destructive in-place file write, applied here because the embed mutates the file (REQ-AS-002). |
| **Force-refresh** | A config toggle that overrides the idempotent skip, re-fetching + re-embedding the front cover even for a file that already has one (REQ-AG-002). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group AK — Release-group MBID capture (ENRICH-012 dependency).** Capture the release-group MBID (and
  release MBID fallback) from BOTH ENRICH-012 identification paths; persist + expose it to the art layer.
- **Group AF — Cover Art Archive fetch.** GET the front cover from
  `coverartarchive.org/release-group/{mbid}/front` (release fallback); bounded thumbnail size; 404/miss
  graceful skip; polite CAA rate-limit; CAA-only.
- **Group AC — Embed into file.** APIC (mp3) / FLAC-Vorbis picture (flac/ogg/opus) / m4a `covr`;
  idempotent skip-if-front-cover-present (unless force-refresh); embed-only / preserve-everything-else.
- **Group AS — Write safety.** Shared `BRAIN_ENRICH_WRITE_FILES` gate; baseline-backup discipline;
  exception-isolated, never blocks/silences playout, never crashes the daemon.
- **Group AW — Worker wiring.** Runs inside/alongside the ENRICH-012 EnrichmentWorker backfill + the
  on-download hook, AFTER identification, in the same pass; mirrors the bounded/throttled/resumable
  pattern; independent art skip-marker.
- **Group AG — Config.** Enable toggle + art size; force-refresh toggle; shared write-files gate.
- Plus **NFRs** (Section 14) and **Risks** (Section 15).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **Any website / now-playing art display or serving.** [HARD][USER DECISION] The art is embedded in the
  file ONLY; the listener website stays art-free. Any web display is owned elsewhere (TAGSTREAM-009 TX /
  WEBUI-018) and is a fixed NON-GOAL here, not a deferral.
- **The canonical-recording identification.** Owned by ENRICH-012 (`identify()` / AcoustID / MB
  text-match); ALBUMART-021 consumes the resolved identity + MBID, never re-owns identification.
- **The mutagen tag write-back of core fields (artist/title/album/year/genre).** Owned by ENRICH-012
  (`write_tags`); ALBUMART-021 adds ONLY the cover embed, in the same pass.
- **The EnrichmentWorker lifecycle (the daemon thread, the schema gate, the throttle).** Owned by
  ENRICH-012; ALBUMART-021 rides it, never re-owns it.
- **Art editing / upscaling / re-encoding / format conversion.** Out of scope: the fetched CAA thumbnail
  is embedded as-is; no resizing beyond requesting the bounded CAA thumbnail variant, no upscaling, no
  re-compression (Section 12).
- **Non-CAA art sources** (Discogs, Last.fm, iTunes, etc.). Out of scope in v1: CAA-only. Last.fm is
  explicitly excluded (non-commercial + frequently 404 per the SHOWS-020 research); Discogs art is noted
  as a POSSIBLE FUTURE fallback (Section 16), not built.
- **A new datastore or a new web service.** Brain-only + additive; the captured MBID + the art
  skip-marker live on the existing `Track`; the art module joins the existing worker (NFR-AA-4).

---

## 5. Constraints (confirmed, fixed)

- [HARD][USER DECISION] **Embedded in the file, never on the website.** The website stays art-free.
- [HARD] **Cover Art Archive only, keyed by release-group MBID** (release MBID fallback). No Last.fm, no
  other source in v1.
- [HARD][DEPENDENCY] **Requires the ENRICH-012 release-group-MBID capture addition** (Group AK).
- [HARD] **Bounded thumbnail size** (default `front-500`).
- [HARD] **A CAA miss/404/error is a graceful skip** (no art is fine; never raises).
- [HARD] **Idempotent embed** (skip if a front cover is present, unless force-refresh; identical art is a
  no-op).
- [HARD] **Embed-only mutation** (every other tag/frame preserved byte-intact).
- [HARD] **Shares the `BRAIN_ENRICH_WRITE_FILES` gate** (gate off → no file mutation).
- [HARD] **Same baseline-backup discipline** as ENRICH-012 before mutating the file.
- [HARD] **Never blocks / silences playout** (background, off the pull path).
- [HARD] **Rides the ENRICH-012 EnrichmentWorker** (backfill + on-download), AFTER identification; never
  a second worker.
- [HARD] **Reuse, don't re-own.** The identification (ENRICH-012), the mutagen write seam, the worker
  lifecycle, the write-files gate, and the MB throttle are referenced, never restated.
- [HARD] **Resilience.** A CAA fetch error, an embed error, a backup error, or a missing MBID logs and
  degrades gracefully; it never crashes the daemon and never silences the stream.
- [HARD] **Brain-only + additive.** A new field + skip-marker on `Track`; an art module on the existing
  worker; config knobs. No new service, no new datastore.

---

## 6. Requirement Group AK — Release-group MBID Capture (ENRICH-012 dependency)

Priority: High. [HARD][DEPENDENCY] This group is the prerequisite ENRICH-012 addition; without it the art
layer has no CAA key.

### REQ-AK-001 — Capture the release-group MBID from BOTH ENRICH-012 identification paths (Event-driven) [HARD]

When ENRICH-012 identifies a track's canonical recording, the system SHALL capture the MusicBrainz
RELEASE-GROUP MBID from BOTH identification paths: (a) the AcoustID path
(`recordings[].releasegroups[].id`, where ENRICH-012 today reads only `rg.get("title")`), and (b) the
MusicBrainz text-match path (the chosen recording's `release-list[].release-group.id`, alongside the
existing album-title/year selection in `_release_album_year`). [HARD] This is an ADDITIVE extension of
the existing extraction — it captures an id already present in the API responses; it changes no
identification, scoring, or propose logic. A track for which neither path yields a release-group MBID is
left without one (the art layer then gracefully skips it). The exact field plumbing is implementation
detail; that the release-group MBID is captured from both paths is the rail.

**Acceptance criteria:** see acceptance.md AC-AK-001.

### REQ-AK-002 — Persist the release-group MBID (and release-MBID fallback) on the identity + expose it to the art layer (Ubiquitous) [HARD]

The system SHALL carry the captured release-group MBID on the resolved identity (`Canonical`) and persist
it on the library `Track` (a new `release_group_mbid` field), and SHALL ALSO capture the specific RELEASE
MBID as a SECONDARY FALLBACK key (for when a release-group has no front cover). [HARD] The persistence
SHALL go through the ENRICH-012 `set_core_tags` accessor with the `_ENRICH_WRITABLE_FIELDS` allowlist
EXTENDED to permit the new field(s) — it MUST NOT touch the frozen `key`/`path`/play-history fields. The
captured MBID(s) SHALL be exposed to the art layer (Group AF) on the same `enrich_one`/`enrich_track`
end-to-end path. That the MBID is persisted (allowlist-gated) and exposed to the art layer is the rail.

**Acceptance criteria:** see acceptance.md AC-AK-002.

---

## 7. Requirement Group AF — Cover Art Archive Fetch

Priority: High.

### REQ-AF-001 — Fetch the front cover from the Cover Art Archive by release-group MBID (release fallback); CAA-only (Event-driven) [HARD]

When a track has a captured release-group MBID (REQ-AK-002) and the art step runs, the system SHALL fetch
the FRONT COVER from the Cover Art Archive at `coverartarchive.org/release-group/{mbid}/front`, and — if
the release-group has no front cover — SHALL fall back to the specific release MBID front
(`coverartarchive.org/release/{release_mbid}/front`). [HARD] The Cover Art Archive is the ONLY art source
in v1: the system SHALL NOT fetch art from Last.fm (non-commercial + frequently 404 per the SHOWS-020
research), iTunes, Discogs, or any other source. A track with no captured MBID is skipped (no fetch). The
endpoint path / fallback order is fixed; the exact HTTP client + redirect handling is implementation
detail; that the front cover comes from CAA keyed by the release-group MBID (release fallback), CAA-only,
is the rail.

**Acceptance criteria:** see acceptance.md AC-AF-001.

### REQ-AF-002 — Bounded thumbnail size to keep embedded file growth reasonable (Ubiquitous) [HARD]

The system SHALL fetch the cover at a BOUNDED THUMBNAIL SIZE (the CAA thumbnail variant, default
`front-500` ≈ ≤500px) rather than the full-resolution original, so embedding the image does not balloon
the audio file's size. [HARD] The default keeps a typical embedded cover in the tens-to-low-hundreds of
KB, not multiple MB. The chosen size is config (REQ-AG-001); that the fetched cover is a bounded
thumbnail (default `front-500`) is the rail.

**Acceptance criteria:** see acceptance.md AC-AF-002.

### REQ-AF-003 — A CAA miss/404/error is a graceful skip; polite rate-limiting to CAA (Unwanted) [HARD]

If a CAA fetch returns a 404, an empty body, a non-image response, or fails on the network/timeout, then
the system SHALL SKIP gracefully — no art is embedded, no exception is raised, the track is simply left
art-less (and marked done so the backfill does not retry it indefinitely, REQ-AW-002). [HARD] A missing
cover is an expected, normal outcome (not every release has CAA art), never an error that blocks the pass
or crashes the daemon. The system SHALL apply POLITE RATE-LIMITING to the Cover Art Archive (a bounded
request spacing, reusing/mirroring the ENRICH-012 MB throttle discipline) so the backfill does not hammer
CAA. The timeout / spacing are config; that a miss is a graceful skip and CAA is polled politely is the
rail.

**Acceptance criteria:** see acceptance.md AC-AF-003.

---

## 8. Requirement Group AC — Embed Into File

Priority: High.

### REQ-AC-001 — Embed the front cover via mutagen (APIC / FLAC-Vorbis picture / m4a covr); file-only, never the website (Event-driven) [HARD]

When a front cover has been fetched (Group AF) and the write-files gate is on (REQ-AS-001), the system
SHALL EMBED it into the audio file via mutagen, dispatched by extension: an id3 `APIC` frame (front-cover
type) for `.mp3`; a FLAC/Vorbis `PICTURE` block (front-cover type) for `.flac`/`.ogg`/`.opus`; an MP4
`covr` atom for `.m4a`/`.mp4`. [HARD][USER DECISION] The cover is embedded IN THE FILE ONLY — the system
SHALL NOT display, serve, link, or reference the art on the listener website; the website stays art-free.
A format the embed cannot handle is skipped (logged, never fatal), mirroring ENRICH-012's
`write_unsupported_format` behavior. The exact frame/atom construction is implementation detail; that the
front cover is embedded per-format via mutagen and NEVER surfaced on the website is the rail.

**Acceptance criteria:** see acceptance.md AC-AC-001.

### REQ-AC-002 — Idempotent: skip a file that already has a front cover unless force-refresh; identical art is a no-op (State-driven) [HARD]

While embedding, the system SHALL be IDEMPOTENT: a file that ALREADY carries a front cover SHALL be
skipped (no fetch, no embed) UNLESS the force-refresh toggle is set (REQ-AG-002); and embedding an image
identical to the one already present SHALL be a no-op (the file is not rewritten). [HARD] The idempotency
is what makes the backfill safe to re-run and the on-download hook safe to re-fire: a track that already
has art is not re-fetched or re-embedded. The skip-marker (REQ-AW-002) records the art step has run so
the backfill does not even re-evaluate it. The presence-detection (does the file already have a front
cover) is implementation detail; that the embed is idempotent (skip-if-present, no-op-if-identical) unless
force-refresh is the rail.

**Acceptance criteria:** see acceptance.md AC-AC-002.

### REQ-AC-003 — Embed-only mutation: preserve every other tag/frame byte-intact (Ubiquitous) [HARD]

The system SHALL mutate ONLY the cover art — every OTHER tag and frame (the ENRICH-012-corrected
`artist`/`title`/`album`/`year`/`genre`, comments, ReplayGain, and any existing non-front images) SHALL
be PRESERVED byte-intact — by adding/replacing the front-cover frame on the existing tag object and
re-saving it, NOT by rebuilding the tag. [HARD] This mirrors the ENRICH-012 write discipline (mutate the
existing tag object, never drop frames it does not know about). An embed SHALL NOT corrupt or strip the
core tags ALBUMART-021 depends on ENRICH-012 having corrected. That the embed preserves all other
tags/frames byte-intact is the rail.

**Acceptance criteria:** see acceptance.md AC-AC-003.

---

## 9. Requirement Group AS — Write Safety

Priority: High.

### REQ-AS-001 — The art mutation shares the SAME `BRAIN_ENRICH_WRITE_FILES` gate (Ubiquitous) [HARD]

The system SHALL gate the art file mutation behind the SAME `enrich_write_files`
(`BRAIN_ENRICH_WRITE_FILES`) config as ENRICH-012's tag write-back: when the gate is OFF, NO file is
mutated (no cover embedded). [HARD] When the gate is off the art step MAY still resolve + log what it
WOULD embed (dry-run visibility, mirroring ENRICH-012's dry-run logging), but it SHALL NOT write a single
byte to disk. ALBUMART-021 does NOT introduce a second independent write gate for art — the file-mutation
authority is the one shared ENRICH write-files gate. That the art mutation shares the write-files gate
(off → no mutation) is the rail.

**Acceptance criteria:** see acceptance.md AC-AS-001.

### REQ-AS-002 — Same baseline-backup discipline before mutating the file (Ubiquitous) [HARD]

Because the embed mutates the audio file in place, the system SHALL follow the SAME baseline-backup
discipline ENRICH-012 applies before a destructive in-place write — so a corrupted write can be recovered
and the original is never lost. [HARD] The art embed is a file mutation and inherits the file-safety
posture of the enrichment write path; it does NOT weaken or bypass the backup discipline. The exact
backup mechanism is the one ENRICH-012/CORE-001 already define (referenced, not re-owned); that the art
mutation observes the same baseline-backup discipline is the rail.

**Acceptance criteria:** see acceptance.md AC-AS-002.

### REQ-AS-003 — Exception-isolated; never blocks/silences playout; never crashes the daemon (Ubiquitous) [HARD]

The system SHALL run the art fetch + embed EXCEPTION-ISOLATED: any CAA error, embed error, backup error,
mutagen error, or missing MBID SHALL be caught and logged, degrading to "no art" rather than raising into
a caller. [HARD] The art step is BACKGROUND, off the `<1s` `/api/next` pull path; a slow or failing CAA
fetch or embed SHALL NEVER block the picker, stall the audio path, silence the stream, or crash the
daemon. It mirrors ENRICH-012's per-track + per-tick exception isolation. That the art step is
exception-isolated and never blocks/silences/crashes is the rail.

**Acceptance criteria:** see acceptance.md AC-AS-003.

---

## 10. Requirement Group AW — Worker Wiring

Priority: High.

### REQ-AW-001 — Runs inside/alongside the ENRICH-012 EnrichmentWorker backfill + on-download path, AFTER identification (Event-driven) [HARD]

The system SHALL run the art fetch + embed INSIDE / ALONGSIDE the ENRICH-012 EnrichmentWorker — both the
bounded backfill pass over the existing library AND the on-download hook (`acquire.py`
`_enrich_on_download` → `enricher.enrich_one`) — AFTER the canonical-recording IDENTIFICATION, so a track
that gets its core tags corrected ALSO gets its front cover embedded in the SAME pass. [HARD] The art
step keys on the release-group MBID the identification just captured (Group AK); it does NOT re-run
identification and does NOT stand up a second worker thread. The integration point (inside `enrich_one`
after the tag write, or an adjacent step on the same worker tick) is implementation detail; that the art
step rides the existing worker AFTER identification, in the same pass, is the rail.

**Acceptance criteria:** see acceptance.md AC-AW-001.

### REQ-AW-002 — Mirror the bounded/throttled/resumable pattern; independent art skip-marker (State-driven) [HARD]

While the worker runs, the art step SHALL mirror the EnrichmentWorker's BOUNDED / THROTTLED / RESUMABLE
pattern (bounded batch, back off while downloads are in flight, polite CAA spacing per REQ-AF-003) and
SHALL use its OWN idempotent SKIP-MARKER — distinct from ENRICH-012's `enrich_version` — recording that
the art step has run for a track (cover embedded, or none found) so the backfill does not re-fetch it.
[HARD] The art skip-marker is INDEPENDENT of `enrich_version` so the art backfill is resumable on its own
(e.g. art added later after a track was already enriched, or a force-refresh sweep) without forcing a
re-identification. A track whose art step has completed (or whose CAA fetch was a confirmed miss) is
skipped on the next pass unless force-refresh. The marker name/storage is implementation detail; that the
art step is bounded/throttled/resumable with an independent skip-marker is the rail.

**Acceptance criteria:** see acceptance.md AC-AW-002.

---

## 11. Requirement Group AG — Config

Priority: Medium.

### REQ-AG-001 — Enable toggle + art thumbnail size; shares the write-files gate (Optional/Ubiquitous) [HARD]

Where configured, the system SHALL provide (a) an ENABLE TOGGLE for the album-art acquisition + embed
engine (e.g. `BRAIN_ALBUMART_ENABLED`, default on), and (b) an ART THUMBNAIL SIZE config (e.g.
`BRAIN_ALBUMART_SIZE`, default `front-500`, REQ-AF-002). [HARD] The FILE MUTATION authority remains the
SHARED `BRAIN_ENRICH_WRITE_FILES` gate (REQ-AS-001) — the enable toggle controls whether the art step
runs at all; the write-files gate controls whether it may touch the file. When the enable toggle is off,
no art is fetched or embedded. That the engine has an enable toggle + size config and shares the
write-files gate is the rail.

**Acceptance criteria:** see acceptance.md AC-AG-001.

### REQ-AG-002 — Force-refresh toggle to re-embed (overriding the idempotent skip) (Optional) [HARD]

Where the operator wants to re-fetch + re-embed art (e.g. after upgrading the default size, or to fill
covers added to CAA after a prior pass), the system SHALL provide a FORCE-REFRESH toggle (e.g.
`BRAIN_ALBUMART_FORCE_REFRESH`, default off) that OVERRIDES the idempotent skip (REQ-AC-002) and the art
skip-marker (REQ-AW-002), re-fetching + re-embedding the front cover even for files that already have one.
[HARD] Force-refresh still obeys the write-files gate (REQ-AS-001) and the baseline-backup discipline
(REQ-AS-002) — it overrides only the skip, never the safety. When off (the default) the engine is
idempotent. That a force-refresh toggle exists and overrides only the skip (not the safety) is the rail.

**Acceptance criteria:** see acceptance.md AC-AG-002.

---

## 12. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 + the
Section 16 roadmap, as the mandatory exclusions list):

- **Any website / now-playing art display or serving** — [HARD][USER DECISION] the art is embedded in
  the file ONLY; the listener website stays art-free. No web display, no now-playing cover, no served art
  endpoint. Owned elsewhere (TAGSTREAM-009 TX / WEBUI-018) and a fixed NON-GOAL here (REQ-AC-001).
- **Non-CAA art sources** — Last.fm (excluded: non-commercial + frequently 404 per SHOWS-020), iTunes,
  Discogs, etc. CAA-only in v1; Discogs is noted as a POSSIBLE FUTURE fallback (Section 16), not built
  (REQ-AF-001).
- **Art editing / upscaling / re-encoding / format conversion** — the fetched CAA thumbnail is embedded
  as-is; no upscaling, no re-compression, no resizing beyond requesting the bounded CAA thumbnail variant
  (Section 4.2).
- **Full-resolution original art** — a bounded thumbnail (default `front-500`) is used to keep file
  growth reasonable; the multi-MB original is not embedded (REQ-AF-002).
- **The canonical-recording identification** — owned by ENRICH-012 (`identify()` / AcoustID / MB
  text-match); consumed by reference (REQ-AK-001, REQ-AF-001).
- **The mutagen core-tag write-back (artist/title/album/year/genre)** — owned by ENRICH-012
  (`write_tags`); ALBUMART-021 adds ONLY the cover embed (REQ-AC-001/003).
- **The EnrichmentWorker lifecycle (daemon thread, schema gate, throttle)** — owned by ENRICH-012; ridden
  by reference, never re-owned (REQ-AW-001/002).
- **A second/independent file-write gate for art** — the art mutation shares the one
  `BRAIN_ENRICH_WRITE_FILES` gate (REQ-AS-001).
- **A new datastore or a new web service** — brain-only + additive; the captured MBID + the art
  skip-marker live on the existing `Track`; the art module joins the existing worker (NFR-AA-4).

---

## 13. User-Provisioned Prerequisites (the real user must provide / decide)

[HARD] ALBUMART-021 does NOT provision any external account or hardware. The following are flagged so the
user knows what is required / decided.

- **The ENRICH-012 MBID-capture addition (Group AK).** This SPEC depends on it; whether it ships as a
  small ENRICH-012 amendment or inside this SPEC's implementation is an orchestrator decision (Section
  15). Either way the captured-MBID requirement is owned here.
- **The write-files gate posture.** The art mutation shares `BRAIN_ENRICH_WRITE_FILES`; the user controls
  whether files are mutated at all (already the ENRICH-012 posture).
- **The thumbnail size.** The default `front-500` is a sane balance; the user may raise it (larger,
  heavier embeds) or lower it (REQ-AG-001).
- **Force-refresh.** Off by default; the user enables it for a deliberate re-embed sweep (REQ-AG-002).
- **No AcoustID/MB account is added by THIS SPEC** — ENRICH-012 already owns the AcoustID key + the MB
  access; the CAA front endpoint needs no key (it is public/CC0). A polite rate-limit is still applied
  (REQ-AF-003).

---

## 14. Non-Functional Requirements

### NFR-AA-1 — Never blocks / silences the music playout (Ubiquitous) — Priority High
The art fetch + embed shall NEVER block or silence the music playout: it is a BACKGROUND step on the
ENRICH-012 worker, off the `<1s` `/api/next` pull path; the picker and the audio path are unaffected by a
slow or failing CAA fetch (REQ-AS-003). Inherits CORE-001's continuous-operation identity. See
acceptance.md AC-NFR-AA-1.

### NFR-AA-2 — Gated + non-destructive-by-default safety (Ubiquitous) — Priority High
No file shall be mutated outside the shared `BRAIN_ENRICH_WRITE_FILES` gate (REQ-AS-001) + the
baseline-backup discipline (REQ-AS-002); the embed is embed-only (preserves every other frame, REQ-AC-003)
and idempotent (skip-if-present / no-op-if-identical, REQ-AC-002). This is the load-bearing file-safety
NFR. See acceptance.md AC-NFR-AA-2.

### NFR-AA-3 — Resilience: a miss is fine; never crash, never silence (Ubiquitous) — Priority High
A CAA 404/miss, a network/timeout failure, an embed error, a backup error, or a missing MBID shall LOG
and degrade to "no art" (a normal, expected outcome) — without raising into a caller, crashing the
daemon/worker, or silencing the stream (REQ-AF-003, REQ-AS-003). See acceptance.md AC-NFR-AA-3.

### NFR-AA-4 — Single-source-of-truth: reference ENRICH-012, never re-own; brain-only + additive (Ubiquitous) — Priority High
No code path shall re-own or fork the ENRICH-012 identification, the mutagen write seam, the
EnrichmentWorker lifecycle, the `BRAIN_ENRICH_WRITE_FILES` gate, or the MB throttle; each is referenced
and consumed. ALBUMART-021 is brain-only + additive (a field + skip-marker on `Track`, an art module on
the existing worker, config knobs; no new service, no new datastore). See acceptance.md AC-NFR-AA-4.

### NFR-AA-5 — Bounded, throttled, resumable processing; polite CAA (Ubiquitous) — Priority Medium
The art fetch + embed shall be BOUNDED, THROTTLED, and RESUMABLE (mirroring the EnrichmentWorker pattern,
REQ-AW-002) with POLITE CAA rate-limiting (REQ-AF-003) so it does not jointly overload the modest box
alongside playout, acquisition, analysis, and tag enrichment, and so it never hammers the Cover Art
Archive. See acceptance.md AC-NFR-AA-5.

### NFR-AA-6 — Storage discipline: bounded thumbnail keeps embedded file growth reasonable (Ubiquitous) — Priority Medium
The embedded cover shall use a BOUNDED THUMBNAIL SIZE (default `front-500`, REQ-AF-002) so embedding does
not balloon the audio file — a typical embedded cover stays in the tens-to-low-hundreds of KB, not
multiple MB. See acceptance.md AC-NFR-AA-6.

---

## 15. Open Questions / Risks

- **R-AA-1 — The ENRICH-012 MBID-capture dependency (High, dependency).** The art fetch is impossible
  without the release-group MBID, which ENRICH-012 does not yet capture. Mitigated: Group AK encodes the
  small additive change (a field + two extraction points + allowlist extension), and until it lands the
  art layer is a graceful no-op (no key → no fetch). Open (orchestrator): land Group AK as a small
  ENRICH-012 amendment vs. inside this SPEC's implementation. (Surfaced as a decision.)
- **R-AA-2 — Boundary vs TAGSTREAM-009 Group TA (artwork) (Medium, ownership).** TAGSTREAM-009 specs a
  broader artwork concept (artwork + website exposure). Mitigated: ALBUMART-021 OWNS the concrete
  CAA-by-release-group-MBID fetch + embed-on-enrich path; it builds NO website display, and the user has
  decided the website stays art-free, so there is no display conflict. Open (orchestrator): confirm
  ALBUMART-021 is the embed engine and TAGSTREAM-009 TA defers to / references it. (Surfaced as a
  decision.)
- **R-AA-3 — Backfill re-touches already-enriched files (Medium, build-time).** The existing library was
  enriched (tags) without art; the art backfill must re-open those files to embed covers. Mitigated: the
  INDEPENDENT art skip-marker (REQ-AW-002) makes the art pass resumable on its own without
  re-identifying, and the embed is idempotent + gated + backed-up. Open: confirm the marker is distinct
  from `enrich_version` so an art-only sweep does not force re-identification.
- **R-AA-4 — Release-group has no front cover / wrong edition art (Medium, honesty).** Not every
  release-group has CAA art, and the release-group front may differ from the user's specific edition.
  Mitigated: the release-MBID fallback (REQ-AK-002, REQ-AF-001) tries the specific release; a genuine
  miss is a graceful skip (no art is fine, REQ-AF-003). Open: whether to prefer the release-MBID front
  over the release-group front for edition fidelity (config tunable).
- **R-AA-5 — Embedded-art file growth across a large library (Low/Medium, storage).** Embedding a cover
  in every file adds up. Mitigated: the bounded thumbnail (default `front-500`, REQ-AF-002, NFR-AA-6)
  keeps each embed small; idempotency avoids duplicate embeds. Open: confirm the default size against the
  library's disk budget.
- **R-AA-6 — m4a/MP4 covr support depth (Low, build-time).** ENRICH-012 currently treats m4a as an
  unsupported tag-write format; ALBUMART-021 adds m4a `covr` embed. Mitigated: per-format dispatch with a
  graceful skip for any format the embed cannot handle (REQ-AC-001). Open: confirm the m4a code path
  against real files.
- **R-AA-7 — bhive had no proven pattern for this stack (Low, recorded gap).** No bhive instruction
  exists for the CAA-by-MBID fetch + mutagen-embed-on-enrich pattern. Mitigated: grounded in the CAA
  public API + mutagen's APIC/picture/covr support. Action: re-run a bhive query during implementation
  and contribute back per AGENTS.md.

---

## 16. Out-of-Scope / Future SPEC Roadmap

- **A Discogs art fallback** — when a release-group/release has no CAA front cover, Discogs could be a
  secondary source. Deferred; CAA-only in v1 (a Discogs provider is forecast by MBMIRROR-017 and could be
  reused).
- **Website / now-playing art display** — if the user ever reverses the art-free decision, surfacing the
  embedded art on the website is TAGSTREAM-009 TX / WEBUI-018 territory; explicitly NOT this SPEC.
- **Back-cover / booklet / multi-image embedding** — front cover only in v1; richer image sets deferred.
- **Edition-aware art selection** — preferring the specific release's art over the release-group's for
  edition fidelity; v1 is release-group-first with a release fallback (REQ-AF-001), tunable later.

---

## 17. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements are in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-AK-001 | Release-group MBID Capture | High | Event | AC-AK-001 |
| REQ-AK-002 | Release-group MBID Capture | High | Ubiquitous | AC-AK-002 |
| REQ-AF-001 | Cover Art Archive Fetch | High | Event | AC-AF-001 |
| REQ-AF-002 | Cover Art Archive Fetch | High | Ubiquitous | AC-AF-002 |
| REQ-AF-003 | Cover Art Archive Fetch | High | Unwanted | AC-AF-003 |
| REQ-AC-001 | Embed Into File | High | Event | AC-AC-001 |
| REQ-AC-002 | Embed Into File | High | State | AC-AC-002 |
| REQ-AC-003 | Embed Into File | High | Ubiquitous | AC-AC-003 |
| REQ-AS-001 | Write Safety | High | Ubiquitous | AC-AS-001 |
| REQ-AS-002 | Write Safety | High | Ubiquitous | AC-AS-002 |
| REQ-AS-003 | Write Safety | High | Ubiquitous | AC-AS-003 |
| REQ-AW-001 | Worker Wiring | High | Event | AC-AW-001 |
| REQ-AW-002 | Worker Wiring | High | State | AC-AW-002 |
| REQ-AG-001 | Config | Medium | Optional | AC-AG-001 |
| REQ-AG-002 | Config | Medium | Optional | AC-AG-002 |
| NFR-AA-1 | Non-Functional | High | Ubiquitous | AC-NFR-AA-1 |
| NFR-AA-2 | Non-Functional | High | Ubiquitous | AC-NFR-AA-2 |
| NFR-AA-3 | Non-Functional | High | Ubiquitous | AC-NFR-AA-3 |
| NFR-AA-4 | Non-Functional | High | Ubiquitous | AC-NFR-AA-4 |
| NFR-AA-5 | Non-Functional | Medium | Ubiquitous | AC-NFR-AA-5 |
| NFR-AA-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-AA-6 |

Parity: 15 REQ + 6 NFR = 21 specified items; 21 acceptance entries (15 AC + 6 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: AK (Release-group MBID Capture) = 2, AF (Cover Art Archive Fetch) = 3, AC
(Embed Into File) = 3, AS (Write Safety) = 3, AW (Worker Wiring) = 2, AG (Config) = 2 → 2+3+3+3+2+2 = 15
REQ across 6 groups. NFR-AA-1…6 = 6 NFR. Total = 15 + 6 = 21 specified items, 21 acceptance entries, 1:1
REQ↔AC.
