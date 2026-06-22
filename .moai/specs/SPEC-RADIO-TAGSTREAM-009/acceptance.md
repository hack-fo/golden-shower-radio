# SPEC-RADIO-TAGSTREAM-009 — Acceptance Criteria

Acceptance for the track-tagging, artwork, and listener-exposure layer. Section A is the
1:1 REQ↔AC table (every `spec.md` requirement has exactly one entry here). Section B gives
detailed Given-When-Then scenarios for the load-bearing requirements. Section C is the
Definition of Done + quality gate.

Parity: 20 REQ + 7 NFR = 27 specified items ↔ 27 acceptance entries (AC-TW-001…008,
AC-TA-001…006, AC-TX-001…006, AC-NFR-T-1…7). 1:1 preserved.

---

## A. REQ ↔ AC Mapping (1:1)

### Group TW — Tag Write

**AC-TW-001 (REQ-TW-001 — storage-agnostic feature read)**
- GIVEN the per-track features computed by ANALYSIS-006 and stored on the `Track`,
- WHEN the tag-write reads the features it needs (`bpm`, `musical_key`, `camelot`, `energy`,
  `key_confidence`),
- THEN it reads them THROUGH the library/`Track` accessor, not by parsing the concrete
  `library.json` file directly;
- AND a unit test demonstrates the read path depends only on the `Track` feature fields, so
  a hypothetical store swap (JSON → SQLite) would not require changing the tag-write code;
- AND the tag-write never recomputes a feature (no DSP call in the write path).

**AC-TW-002 (REQ-TW-002 — feature→tag value mapping)**
- GIVEN a track with `bpm=95.7`, `musical_key="D# minor"`, `camelot="2A"`, `energy=0.667`,
- WHEN the values are derived,
- THEN BPM → `"96"` (`str(round(bpm))`, integer); KEY → `"D#m"` (≤3 chars, "<root> minor" →
  "<root>m"); a `"A minor"` → `"Am"` and `"C major"` → `"C"`; CAMELOT → `"2A"` verbatim in a
  SEPARATE field; ENERGY LEVEL → `"7"` (`str(round(0.667*9)+1)`, in 1-10);
- AND the key value NEVER contains a Camelot code;
- AND the same derived values are reused for both the mp3 and flac write paths.

**AC-TW-003 (REQ-TW-003 — mp3 ID3 write, idempotent)** — see Section B, Scenario 1.
- GIVEN an MP3 track with derived values,
- WHEN it is tagged,
- THEN `TBPM`, `TKEY`, `TXXX:EnergyLevel`, `TXXX:CAMELOT` are written via raw
  `mutagen.id3.ID3` (a fresh container created on `ID3NoHeaderError`), saved as ID3v2.3;
- AND re-reading the file shows exactly those frames with the expected values;
- AND running the write TWICE produces NO duplicate frames (`setall` for TBPM/TKEY, `delall`+`add` by desc for TXXX).

**AC-TW-004 (REQ-TW-004 — flac Vorbis-comment write, idempotent)**
- GIVEN a FLAC track with derived values,
- WHEN it is tagged,
- THEN `BPM`, `INITIALKEY`, `ENERGYLEVEL`, `CAMELOT` Vorbis comments are written via raw
  `mutagen.flac.FLAC` and saved;
- AND re-reading shows those comments with the expected values;
- AND running the write twice yields no duplicated/ambiguous values (case-insensitive
  key-replace).

**AC-TW-005 (REQ-TW-005 — low key-confidence gating)** — see Section B, Scenario 2.
- GIVEN a track whose `key_confidence` is below the configured threshold,
- WHEN it is tagged,
- THEN the key tag (`TKEY`/`INITIALKEY`) AND the Camelot tag are SKIPPED (not written), and
  the skip is recorded/flagged;
- AND the BPM and EnergyLevel tags ARE still written;
- GIVEN a track at or above the threshold, THEN the key + Camelot tags ARE written.

**AC-TW-006 (REQ-TW-006 — per-file batch safety + idempotent skip marker)** — see Section B,
Scenario 3.
- GIVEN a batch containing one corrupt/unreadable/read-only file,
- WHEN the batch runs,
- THEN that file is logged + counted as a failure and the batch CONTINUES (the other 282 are
  tagged);
- AND a `tagged` marker is set only on a verified write, so a re-run SKIPS already-tagged
  files;
- AND no single-file failure raises out of the batch.

**AC-TW-007 (REQ-TW-007 — one-shot backfill)**
- GIVEN the existing library of 205 mp3 + 78 flac analyzed files,
- WHEN the backfill is invoked,
- THEN all analyzed files are tagged in one bounded, resumable pass under the per-file guard +
  confidence gate;
- AND a file with no analysis record is left untagged (to be tagged later by the auto-hook);
- AND the backfill does not block `/api/next` (NFR-T-1) and is resumable after interruption
  via the `tagged` markers.

**AC-TW-008 (REQ-TW-008 — auto-tag hook)** — see Section B, Scenario 4.
- GIVEN a newly ingested track that has just finished analysis (`set_analysis` written),
- WHEN `Analyzer._analyze_one` reaches its end,
- THEN the track is tagged automatically, off the pull path, under the per-file guard + the
  confidence gate + the idempotent skip marker;
- AND a tag failure logs but does NOT crash the analysis worker or silence the stream;
- AND a re-analyzed track re-tags idempotently.

### Group TA — Artwork

**AC-TA-001 (REQ-TA-001 — source chain + legality)** — see Section B, Scenario 5.
- GIVEN a track needing a cover,
- WHEN the artwork source chain runs,
- THEN it tries Cover Art Archive (if a release MBID is present) → TheAudioDB album lookup
  (`searchalbum.php`, free-text) → already-embedded `APIC`/Picture, in that legality order;
- AND art from iTunes or Deezer is NEVER embedded (a test asserts no embed call is reachable
  from a no-store source);
- AND Last.fm covers are skipped.

**AC-TA-002 (REQ-TA-002 — capture release MBID)**
- GIVEN the existing `search_recordings(... limit=1)` MusicBrainz call,
- WHEN it returns a recording with a `release-list`,
- THEN the release MBID (`rec["release-list"][n]["id"]`) is CAPTURED and persisted with the
  track (no longer discarded after the year extraction);
- AND that MBID is used to query Cover Art Archive (`/release/{mbid}/front`);
- AND a track with no MBID match falls through to TheAudioDB free-text without error.

**AC-TA-003 (REQ-TA-003 — embed front cover only, idempotent)**
- GIVEN a validated, resized front cover for a track,
- WHEN it is embedded,
- THEN MP3 gets a single `APIC` (`type=COVER_FRONT`, `image/jpeg`) via `setall('APIC', [apic])`
  saved as v2.3, and FLAC gets a single `Picture` (`type=COVER_FRONT`) after `clear_pictures()`;
- AND ONLY the front cover is embedded (no artist picture);
- AND re-running the embed produces no duplicate/accumulated pictures.

**AC-TA-004 (REQ-TA-004 — resize + validate ceiling)** — see Section B, Scenario 6.
- GIVEN downloaded image bytes,
- WHEN they are processed for embed,
- THEN they are validated as a real image (HTML/truncated input rejected), resized to
  max(w,h) ≤ 600px, re-encoded JPEG q85 with EXIF stripped;
- AND an encoded image > 200KB is hard-rejected (skip + log) rather than embedded;
- AND PNG is not used for the embed (JPEG only).

**AC-TA-005 (REQ-TA-005 — artist images website-only)**
- GIVEN an artist with an MBID in KNOWLEDGE-008 `entities.mbid`,
- WHEN an artist image is acquired (fanart.tv primary; TheAudioDB free-text fallback),
- THEN it is served as a website/sidecar asset and is NEVER embedded in any music file;
- AND fanart.tv usage honors its free-key + attribution requirement on the site;
- AND Last.fm artist images (placeholder) are skipped.

**AC-TA-006 (REQ-TA-006 — idempotent skip + guard + backfill + auto-art hook)**
- GIVEN a track already arted (`has_cover` set, embedded image still decodes),
- WHEN the art pass re-runs,
- THEN the track is SKIPPED (no re-fetch/re-embed) unless a forced-refresh flag is set;
- AND the entire download+validate+resize+embed per file is wrapped in try/except so one
  failure logs and the batch continues;
- AND the art pass runs as an offline backfill AND an auto-art hook at end-of-analysis, never
  on the on-air path.

### Group TX — Stream/Site Exposure

**AC-TX-001 (REQ-TX-001 — website now-playing fields + art)** — see Section B, Scenario 7.
- GIVEN an on-air analyzed track,
- WHEN the website now-playing player renders,
- THEN it shows labeled BPM / musical key / Camelot / energy fields and renders the cover art
  (and artist image where available), driven by `/api/nowplaying` (polled ~5s);
- AND the `%mp3(320)` audio stream is unchanged;
- AND the rich view is reachable by any browser, independent of the listener's audio player.

**AC-TX-002 (REQ-TX-002 — recently-played sortable columns + thumbnails)**
- GIVEN the `recent[]` history in `/api/nowplaying`,
- WHEN the recently-played view renders,
- THEN it is a client-side-SORTABLE table with artist/title/BPM/key/Camelot/energy/played-at
  columns and art thumbnails;
- AND sorting is a property of OUR web player's history view, applied to a finite client-side
  list — explicitly NOT the singleton now-playing item and NOT columns from any off-the-shelf
  player on a live stream (cross-ref AC-TX-005).

**AC-TX-003 (REQ-TX-003 — now-playing enrichment wiring)** — see Section B, Scenario 8.
- GIVEN the airing report already carries the on-air `path` (`set_on_air` stores it,
  `now_playing()` returns it),
- WHEN the brain assembles `/api/nowplaying`,
- THEN it looks up the on-air track BY PATH and enriches the now-playing (and recent) objects
  with bpm/musical_key/camelot/energy + a cover URL, WITHOUT widening the Liquidsoap
  `report_airing` payload;
- AND the audio path, the `_annotate_uri` pull contract, and the airing report are unchanged
  (additive only);
- AND an unanalyzed/unresolved path (or a talk clip with no `Track`) yields the existing
  artist/title only — no crash, no stale enrichment.

**AC-TX-004 (REQ-TX-004 — enriched ICY StreamTitle)**
- GIVEN an on-air track with bpm/camelot/energy,
- WHEN the streamed title is formed,
- THEN the ICY `StreamTitle` reads "Artist - Title [96 BPM | 2A | E7]" (one decorated
  string), visible in every player's now-playing line;
- AND it is explicitly NOT separate sortable columns (it lands in the single StreamTitle
  string, split only on the first hyphen);
- AND a clean artist/title remains available for downstream parsing; the suffix template is
  config-driven.

**AC-TX-005 (REQ-TX-005 — NON-GOAL: no live per-field columns)** — see Section B, Scenario 9.
- GIVEN the verified protocol limits (research.md, refuted 3/3),
- WHEN the SPEC, its acceptance criteria, the implementation, and any website copy are
  reviewed,
- THEN NONE of them claims, implements, or accepts separate sortable BPM/KEY/ENERGY columns
  over a live stream to an off-the-shelf player;
- AND the documented capability is: sortable columns via the web history view (AC-TX-002) and
  local tagged files (Group TW) ONLY;
- AND this non-goal is stated explicitly so no downstream work overstates the stream.

**AC-TX-006 (REQ-TX-006 — OPTIONAL Ogg-FLAC art spike, gated)**
- GIVEN the optional Ogg-FLAC art exploration,
- WHEN it is considered,
- THEN it is recorded as an OPTIONAL, integration-test-gated SPIKE that leaves `%mp3(320)`
  unchanged and is NOT a committed deliverable or a pass/fail SPEC acceptance criterion;
- AND any reliance is gated on an integration test of per-track updates (foobar2000 v2.26
  Ogg-chaining-off; use `%vorbis`/`%ffmpeg` libopus, never native `%opus`);
- AND it is documented that even success does NOT yield sortable columns;
- AND this AC is satisfied by the spike being SCOPED + GATED, not by the mount shipping.

### Non-Functional

**AC-NFR-T-1 (NFR-T-1 — never blocks the pull)**
- A load test confirms `/api/next` latency is unaffected while a backfill, an auto-hook tag/art
  write, and an art fetch are in progress; the backfill is an offline batch, the auto-hook
  rides the background analysis worker, and the now-playing enrichment is a cheap by-path read.

**AC-NFR-T-2 (NFR-T-2 — bounded/throttled/ToS-respecting art fetches)**
- TheAudioDB fetches stay ≤30/min (back off on 429); fanart.tv uses a config-gated free key +
  the site honors its attribution; CAA 307/404/503 are handled; a source outage backs off and
  the music keeps playing (no retry storm).

**AC-NFR-T-3 (NFR-T-3 — never crash the batch; in-place resilience)**
- A batch with injected corrupt/read-only/HTML-download cases completes (the bad files skipped
  + logged), the analysis worker and daemon do not crash, the stream is not silenced, and an
  interrupted write does not set the `tagged`/`has_cover` marker (verify-after-save gate).

**AC-NFR-T-4 (NFR-T-4 — no no-store art embedded)**
- A code/dataflow review + test confirms no embed call is reachable from iTunes or Deezer
  sources; embeds originate only from CAA / TheAudioDB / already-embedded; Last.fm covers are
  skipped.

**AC-NFR-T-5 (NFR-T-5 — honest capability)**
- A review of the SPEC, ACs, implementation, README, and website copy finds NO claim of
  sortable BPM/KEY/ENERGY columns over a live stream and NO claim of in-band live-stream
  artwork rendering; the stated ceilings match the verified findings.

**AC-NFR-T-6 (NFR-T-6 — idempotent + bloat-bounded)**
- Re-running the full tag/art pass over a done library produces no duplicate frames/pictures
  and re-fetches nothing (markers honored); total embedded art overhead across 283 files
  measures within the bounded budget (~25-35MB; each image ≤200KB).

**AC-NFR-T-7 (NFR-T-7 — simplicity / no over-engineering)**
- A design review confirms: a single tag-write module + a single artwork module + additive
  now-playing/website fields; no new service, no second HTTP client, no primary Liquidsoap
  change, no HLS player, no artist-image embedding; the Ogg-FLAC mount exists only as a gated
  spike if at all.

---

## B. Detailed Given-When-Then Scenarios (load-bearing requirements)

### Scenario 1 — MP3 tag write is correct, standard, and idempotent (REQ-TW-003)

```
GIVEN an MP3 file "/music/<artist> - <title>.mp3" with an analyzed Track
  (bpm=95.7, musical_key="D# minor", camelot="2A", energy=0.667, key_confidence=0.82)
WHEN the tag-write tags it
THEN it opens the file with raw mutagen.id3.ID3 (creating a fresh container on
     ID3NoHeaderError), and writes:
       TBPM = "96"
       TKEY = "D#m"            (musical notation, <= 3 chars; NOT "2A")
       TXXX:EnergyLevel = "7"
       TXXX:CAMELOT = "2A"
     and saves with save(v2_version=3)
AND re-reading via mutagen returns exactly those four frames with those values
AND running the tag-write AGAIN over the same file leaves exactly one of each frame
    (setall for TBPM/TKEY; delall('TXXX:EnergyLevel')/delall('TXXX:CAMELOT') then add) —
    no duplicates
AND the file's existing artist/title/album frames are untouched (scope discipline)
```

### Scenario 2 — Low key-confidence gates the key, not the rest (REQ-TW-005)

```
GIVEN a Track with key_confidence = 0.251 and a configured threshold of 0.50
WHEN the track is tagged
THEN no TKEY/INITIALKEY frame and no Camelot frame is written (both derive from the
     uncertain key estimate)
AND the skip is recorded/flagged (e.g. a key_skipped reason logged)
AND TBPM and TXXX:EnergyLevel ARE still written (BPM/energy are independent of key)
GIVEN another Track with key_confidence = 0.82 (>= 0.50)
WHEN it is tagged
THEN TKEY and the Camelot frame ARE written
RATIONALE a wrong key is worse than no key for harmonic mixing (R-T-2)
```

### Scenario 3 — One corrupt file never aborts the batch of 283 (REQ-TW-006)

```
GIVEN a backfill batch of 283 files, one of which is corrupt (mutagen raises) and one of
  which is read-only
WHEN the batch runs
THEN each file's read+derive+write is wrapped in its own try/except
AND the corrupt file and the read-only file are logged + counted as failures
AND the batch CONTINUES and tags the other 281 files
AND no single-file exception propagates out of the batch
AND the per-track `tagged` marker is set ONLY for files whose write was verified by
    re-opening, so a re-run skips them and retries the two failures
```

### Scenario 4 — Auto-tag hook rides the analysis worker (REQ-TW-008)

```
GIVEN a newly dropped file that the ANALYSIS-006 watch scan picks up and the analysis
  worker analyzes (Analyzer._analyze_one runs, set_analysis writes the feature record)
WHEN _analyze_one reaches its end
THEN the auto-tag hook tags the track using the same write path as the backfill, off the
     /api/next pull path, under the per-file guard + confidence gate + idempotent marker
AND if the tag write fails, it is logged but the analysis worker does NOT crash and the
    stream is NOT silenced (inherits ANALYSIS-006 NFR-A-4)
AND if the file is later re-analyzed (schema bump / content change), the auto-tag re-runs
    idempotently
```

### Scenario 5 — Artwork source chain respects legality (REQ-TA-001, REQ-TA-002)

```
GIVEN a track whose enrichment captured a MusicBrainz release MBID
WHEN the artwork source chain runs
THEN it queries Cover Art Archive /release/{mbid}/front first (storage-safe)
AND on a 404 (no front art designated) it falls through to TheAudioDB searchalbum.php
    (free-text artist+album, storage-safe)
AND on a miss there it falls through to any already-embedded APIC/Picture
AND at NO point can the chain reach an embed call with iTunes or Deezer bytes (no-store) —
    those sources are not wired into the embed path at all
GIVEN a track with no release MBID
WHEN the chain runs
THEN it skips CAA and goes straight to the TheAudioDB free-text branch without error
```

### Scenario 6 — Resize + validate ceiling bounds embedded bloat (REQ-TA-004)

```
GIVEN downloaded bytes that are actually an HTML error page
WHEN they are processed for embed
THEN image validation (Image.open(...).verify()) rejects them and nothing is embedded
GIVEN a valid 1200x1200 PNG cover download
WHEN it is processed
THEN it is resized to max(w,h) <= 600px and re-encoded as JPEG q85 with EXIF stripped
AND if the encoded result exceeds 200KB it is hard-rejected (skip + log), else embedded
AND the embedded mime is image/jpeg (never PNG)
```

### Scenario 7 — Website now-playing shows the fields + art, stream unchanged (REQ-TX-001)

```
GIVEN an analyzed track on air (bpm=128, musical_key="A minor", camelot="8A", energy=0.73)
WHEN a listener opens the station website
THEN the now-playing panel shows labeled fields: BPM 128, Key Am, Camelot 8A, Energy 8
     (or the raw/derived display the layout chooses), and renders the cover art image
AND the data comes from /api/nowplaying (polled ~5s), not from the audio stream
AND the %mp3(bitrate=320) Icecast output and the request.dynamic pull contract are unchanged
AND a browser on any OS / any audio player sees the rich view (it is the website, not the
    raw stream URL)
```

### Scenario 8 — Now-playing enrichment is an additive by-path lookup (REQ-TX-003)

```
GIVEN radio.liq POSTs /api/airing with artist/title/kind/path and set_on_air stores path
WHEN the brain builds the /api/nowplaying response
THEN it resolves now_playing()["path"] to the analyzed Track and adds bpm/musical_key/
     camelot/energy + a cover URL to the now_playing (and recent[]) objects
AND it does NOT widen the Liquidsoap report_airing payload (the wiring lives in the brain)
AND _annotate_uri, the airing report, and the audio path are byte-for-byte unchanged
GIVEN a talk clip on air (no Track) or an unanalyzed/unresolved path
WHEN the response is built
THEN the now_playing carries the existing artist/title only (no feature fields, no crash)
```

### Scenario 9 — The live-columns non-goal is explicit and enforced (REQ-TX-005)

```
GIVEN the verified finding that no live stream + off-the-shelf player can deliver separate
  sortable BPM/KEY/ENERGY columns (research.md, refuted 3/3)
WHEN the SPEC, ACs, implementation, README, and website copy are reviewed
THEN none of them promises or attempts live per-field sortable columns over the stream
AND the only places sortable per-field columns appear are: the web history view (our own
    player) and a listener's LOCAL playback of the tagged files
AND the enriched StreamTitle (REQ-TX-004) is documented as one decorated string, not columns
RATIONALE encode the honesty as a fixed non-goal so no downstream work overstates capability
```

---

## C. Definition of Done + Quality Gate

A TAGSTREAM-009 increment is DONE when:

1. **All 27 acceptance entries pass** (20 AC + 7 AC-NFR), 1:1 with the requirements.
2. **Tag write** — the backfill tags all analyzed mp3 + flac files in place via raw mutagen
   (ID3v2.3 / Vorbis comments) with correct standard values (TBPM integer, TKEY ≤3-char
   notation, TXXX:EnergyLevel 1-10, TXXX:CAMELOT verbatim; flac BPM/INITIALKEY/ENERGYLEVEL/
   CAMELOT), idempotently, under the per-file guard + the key-confidence gate; the auto-tag
   hook tags newly analyzed tracks going forward.
3. **Artwork** — front covers are acquired from storage-safe sources only (CAA via the now-captured
   release MBID → TheAudioDB → already-embedded), validated + resized (≤600px JPEG q85, >200KB
   rejected), embedded front-cover-only (picture type 3) idempotently; artist images are
   website/sidecar only (never embedded); iTunes/Deezer art is never embedded.
4. **Exposure** — the website now-playing player shows labeled BPM/key/camelot/energy fields +
   rendered cover/artist art (fed by the additive by-path now-playing enrichment), the
   recently-played view is a sortable table with thumbnails, and the ICY StreamTitle is
   enriched to "Artist - Title [96 BPM | 2A | E7]"; the `%mp3(320)` stream is unchanged.
5. **Honesty** — no claim, code, or copy promises live per-field sortable columns over the
   stream or in-band live-stream artwork; the Ogg-FLAC mount, if touched, exists only as a
   gated spike.
6. **Continuity rails hold** — nothing blocks the `/api/next` pull; art fetches are
   bounded/throttled/ToS-respecting; one corrupt file never aborts the batch; the analysis
   worker and daemon never crash and the stream is never silenced.
7. **Boundary discipline** — no CORE-001/OPS-004/ANALYSIS-006/KNOWLEDGE-008 requirement is
   restated or forked; features are read storage-agnostically, the OPS-004 HTTP clients are
   reused, and the auto-hook attaches to the ANALYSIS-006 worker — all referenced by number.

**Quality gate (TRUST 5):**
- **Tested** — unit tests for the value mapping, idempotency, confidence gating, per-file
  guard, source-chain legality, resize/validate ceiling, and the by-path now-playing
  enrichment; integration tests for the backfill over a fixture library, the auto-hook, and
  (if pursued) the Ogg-FLAC per-track-update spike.
- **Readable** — clear module boundaries (tag-write vs artwork vs exposure), English comments,
  no duplication of the ANALYSIS-006 read or the OPS-004 HTTP client.
- **Unified** — mirrors the existing brain patterns (per-file try/except like `_read_tags`/
  `_load`, off-lock work like the analyzer, additive JSON like `/status`'s knowledge block).
- **Secured** — no no-store art embedded; external fetches bounded/throttled/key-gated;
  in-place writes guarded + verified; no secrets in code.
- **Trackable** — changes reference SPEC-RADIO-TAGSTREAM-009 and the specific REQ IDs;
  research.md records the decisive capability findings.
