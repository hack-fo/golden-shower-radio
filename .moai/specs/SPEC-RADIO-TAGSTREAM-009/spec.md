---
id: SPEC-RADIO-TAGSTREAM-009
version: 0.1.1
status: draft
created: 2026-06-22
updated: 2026-06-22
author: charlie
priority: High
issue_number: 9
---

# SPEC-RADIO-TAGSTREAM-009 — Track Tagging, Artwork & Listener Exposure

## HISTORY

- 2026-06-22 (v0.1.0): Initial draft. The seventh authored SPEC in the
  golden-shower-radio RADIO series and the PRESENTATION / file-tagging layer of the
  autonomous AI radio station. Where SPEC-RADIO-CORE-001 owns the music engine + library
  store + program-director loop + website; SPEC-RADIO-VOICE-002 owns TTS; SPEC-RADIO-OPS-004
  owns the autonomous program director, imaging, the self-learning playbook, newscasting,
  and library/acquisition policy + the external-metadata HTTP CLIENTS (REQ-OA-011);
  SPEC-RADIO-ORCH-005 owns the director-loop / world-model / event-reaction nervous system;
  SPEC-RADIO-ANALYSIS-006 owns the per-TRACK audio-feature DATA MODEL + the ENGINE that
  COMPUTES bpm/musical_key/camelot/energy/integrated_lufs (Groups AE/AT/AM), the library
  auto-ingest scan (REQ-AP-007), and the queryable catalog (Group AD); and
  SPEC-RADIO-KNOWLEDGE-008 owns the researched editorial knowledge base (artist facts +
  entities.mbid) — TAGSTREAM-009 owns (A) WRITING the already-computed audio features into
  the music FILES as standard tags, (B) acquiring + EMBEDDING album front-cover ARTWORK in
  those files (and acquiring artist images for website display), and (C) EXPOSING the
  tags + art to LISTENERS via the live stream's now-playing surface (the station website
  player) and an enriched ICY StreamTitle. It answers a direct user goal: "write
  BPM/TEMPO/KEY/ENERGY tags to all the music, get cover art onto the files, and let
  listeners SEE that data while they listen." RADIO SPEC-IDs are GLOBAL-INCREMENTING
  (CORE-001, VOICE-002, CALLIN-003 reserved, OPS-004, ORCH-005, ANALYSIS-006,
  PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009 = next free 009; TAGSTREAM-001 was rejected
  to preserve the proven global pattern). It uses a DISTINCT REQ namespace — TW (tag-write),
  TA (artwork), TX (stream/site exposure) — to avoid collision with CORE (A-E + D), VOICE
  (V-A…V-F), OPS (OA/OB/OC/OD/OE/OF/OG/OH), ORCH (RL/RW/RE/RC/RD/RA), ANALYSIS (AE/AT/AM/
  AD/AP), and KNOWLEDGE (KS/KF/KR/KG/KI). Built on the BRAIN-ONLY seam: it extends the
  existing Python `brain/` package (a new tag-write module + an artwork acquisition/embed
  module + additive now-playing-JSON + website fields) WITHOUT forking the library store
  and WITHOUT changing the primary `%mp3(bitrate=320)` Liquidsoap output. The three
  research dossiers (research.md) are DECISIVE on capability honesty: per-field/binary
  payloads CANNOT ride the live MP3/ICY stream — the station's own JSON-driven website
  now-playing player is the canonical live surface, file tags give real columns only for
  LOCAL/downstream playback, and an Ogg-FLAC in-band-art mount is a fragile SPIKE, not a
  committed deliverable. Total: 20 REQ + 7 NFR = 27, 1:1 REQ↔AC.
- 2026-06-22 (v0.1.1): Applied plan-auditor fixes (verdict SHIP-WITH-FIXES). MUST-FIX MF-1:
  REQ-TW-005 normative text no longer self-contradicts on low-confidence Camelot — the lead
  clause now states only BPM + energy MAY still be written while the Camelot tag is gated by
  the same key-confidence threshold and NOT written below it, matching AC-TW-005 + Scenario 2.
  SHOULD-FIX SF-1: REQ-TX-005 EARS label corrected from "Unwanted" to "Ubiquitous prohibition"
  (it is an always-active prohibition with no "If…then" trigger) in both the header and the
  Traceability Index. SHOULD-FIX SF-2: Group TX header now notes that per-REQ priorities in the
  Traceability Index override the group's High default (REQ-TX-004 Medium, REQ-TX-006 Low).
  SHOULD-FIX SF-3: REQ-TA-002 gained an explicit boundary/coordination note that the
  `metadata.py` release-MBID capture is an additive field-capture that must not alter OPS-004
  REQ-OA-011's shared-client behavior. Net: 0 REQ/NFR change — counts stay 20 REQ + 7 NFR = 27,
  1:1 REQ↔AC preserved.

---

## 1. Overview & Background

### 1.1 Why this SPEC — "tag the music, art the files, let listeners see it"

ANALYSIS-006 already COMPUTES the perception the station was missing: every analyzed
track carries `bpm`, `bpm_confidence`, `musical_key` (e.g. "D# minor"), `camelot` (e.g.
"2A"), `key_confidence`, `energy` (0..1), and `integrated_lufs` in the `Track` record
(`brain/library.py`). But that intelligence lives ONLY inside the brain's library index.
It is NOT written back into the music FILES (so a DJ-tool, a portable player, or the
user's own foobar2000 library sees nothing), the files mostly carry NO cover ART (the
metadata enrichment discards the data needed to fetch it), and a LISTENER on the live
stream sees only "Artist - Title" — none of the BPM/key/energy/art the brain knows.

This SPEC closes those three gaps, and ONLY those three:

1. **Write the features as file TAGS.** Map the computed features to the standard tag
   frames every music tool reads — ID3v2 `TBPM`/`TKEY`/`TXXX:EnergyLevel`/`TXXX:CAMELOT`
   for the 205 MP3s, Vorbis comments `BPM`/`INITIALKEY`/`ENERGYLEVEL`/`CAMELOT` for the
   78 FLACs — in place, idempotently, with per-file safety, so the tagged files yield real
   sortable columns in foobar2000/Serato/Traktor/Rekordbox/Mixxx for LOCAL playback.
2. **Acquire + embed cover ARTWORK.** Fetch the album front cover from storage-legal
   sources (Cover Art Archive via the MusicBrainz release MBID; TheAudioDB by free text)
   and embed it (front cover, picture type 3, resized JPEG) into the files; acquire artist
   images (fanart.tv / TheAudioDB) for WEBSITE display only.
3. **Expose tags + art to listeners.** Make the station website's now-playing player the
   canonical live surface — labeled BPM/key/camelot/energy fields + rendered cover/artist
   art, plus a recently-played view with sortable columns + art thumbnails — and enrich the
   live ICY StreamTitle so every player's now-playing line reads
   "Artist - Title [96 BPM | 2A | E7]". The `%mp3(320)` audio stream stays UNCHANGED.

### 1.2 The honest capability ceiling (the dossiers are decisive)

[HARD] Three independent research dossiers, adversarially verified, establish a hard
honesty boundary this SPEC MUST respect (research.md, Sections 1-3):

- **Live per-field SORTABLE BPM/KEY/ENERGY COLUMNS over ANY live stream are IMPOSSIBLE**
  (refuted 3/3). ICY metadata is a single periodic TEXT string (`StreamTitle`); MP3/AAC
  have no per-field channel; no off-the-shelf player (foobar2000 included) builds
  user-defined sortable columns from a LIVE source — that is a file-tag / media-library
  feature. Sortable columns are achievable ONLY in our own web player (the history view)
  or for LOCAL tagged files. The SPEC MUST NOT adopt "separate sortable columns over the
  stream" as an acceptance criterion.
- **Artwork bytes CANNOT ride the live MP3/ICY stream as a player-rendered image**
  (refuted 2/2). The website now-playing panel is the only live-art surface the station
  controls; embedded file art only helps local/portable/downstream players. Any cover a
  foobar2000 listener sees on the raw stream is THEIR player's own out-of-band lookup, not
  art the station delivered.
- **The Ogg-FLAC in-band-art mount is a fragile SPIKE, not a deliverable.** foobar2000
  ≥1.6.1 DOES render live in-band album art from an Ogg FLAC stream (a real, narrow
  foobar2000-only win), but per-track updates are fragile (foobar 2.26 turned Ogg chaining
  OFF by default; VLC/mpv regress) and it would mean abandoning the universal `%mp3` mount.
  It is listed as an optional, integration-test-gated spike (REQ-TX-006), never a committed
  AC, and even success does NOT yield sortable columns.

### 1.3 What this layer is, concretely

- A FILE TAG-WRITE path (new module): reads the already-computed features from the library
  storage-agnostically, derives the standard tag values, and writes them in place into the
  205 mp3 + 78 flac files using RAW mutagen classes (`mutagen.id3.ID3` / `mutagen.flac.FLAC`
  — the existing `easy=True` read path cannot write `TKEY`/`TBPM`/`TXXX`/`APIC`), idempotently,
  per-file guarded, with low-key-confidence gating (Group TW).
- An ARTWORK acquisition + embed path (new module): a storage-legality-ranked source chain
  (Cover Art Archive → TheAudioDB → already-embedded), MBID capture in `metadata.py` (the
  release MBID is currently discarded), front-cover-only embedding (picture type 3) with a
  resize/validate ceiling, artist images for website display only, all idempotent + guarded
  (Group TA).
- An EXPOSURE path (additive brain + website changes): the now-playing JSON enriched by a
  by-path lookup of the on-air track, a richer website player rendering the fields + art +
  a sortable recently-played table, an enriched ICY StreamTitle, and the honest non-goal
  (Group TX).
- Coverage: a one-shot BACKFILL of all existing files NOW, AND an auto-hook so newly
  analyzed tracks get tagged + arted automatically going forward (attached at the end of
  analysis in `analyzer.py`); a `has_cover`/tagged marker lets re-runs skip done files.

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] TAGSTREAM-009 owns WRITING features as file tags + acquiring/EMBEDDING artwork +
EXPOSING tags+art to listeners. It MUST NOT restate or fork any CORE-001, VOICE-002,
OPS-004, ORCH-005, ANALYSIS-006, or KNOWLEDGE-008 requirement, and it MUST NOT re-own
feature COMPUTATION, the audio-ingest scan, or the curation loop.

OWNS:
- The feature→tag value mapping + the mp3 (ID3) and flac (Vorbis-comment) WRITE paths +
  idempotency + per-file batch safety + low-key-confidence gating + the one-shot backfill
  + the auto-tag hook + the storage-agnostic feature read (Group TW).
- The artwork SOURCE CHAIN + the embed-safe-vs-display-only legality split + the release
  MBID capture + front-cover-only embedding + the resize/validate ceiling + artist-image
  website-only handling + idempotent skip (Group TA).
- The LISTENER exposure: the website now-playing fields+art, the sortable recently-played
  view, the now-playing-enrichment wiring, the enriched ICY StreamTitle, the honest
  live-columns non-goal, and the optional Ogg-FLAC-art spike (Group TX).

REFERENCES (consumes / extends / feeds; does not restate):
- **ANALYSIS-006 Groups AE/AT/AM + Group AD** — the ENGINE that COMPUTES bpm/musical_key/
  camelot/energy/integrated_lufs and the `Track` feature record they live in. TAGSTREAM-009
  READS those features (storage-agnostically — `library.json` today, a future SQLite store
  later — via the library accessor, NOT coupled to the JSON file) and WRITES them as file
  tags; it never recomputes a feature, never re-runs the DSP, and never re-derives genre.
- **ANALYSIS-006 REQ-AP-007 + the `analyzer.py` Group AP pipeline** — the auto-ingest scan
  + the serialized, bounded, non-blocking analysis worker. TAGSTREAM-009's auto-tag/auto-art
  hook ATTACHES at the END of analysis (after `set_analysis`, in `Analyzer._analyze_one`),
  riding the same off-the-pull-path, throttled, per-file-guarded discipline; it references
  the scan + worker, it does not re-own them.
- **ANALYSIS-006 REQ-AD-005** — the `Track.key` = dedup SLUG (artist-title) vs `musical_key`
  = tonal key distinction. The tag-write maps the MUSICAL key (`musical_key`/`camelot`) to
  `TKEY`/`INITIALKEY`/`CAMELOT`; it MUST NOT touch the dedup `Track.key`.
- **OPS-004 REQ-OA-011** — the external-metadata HTTP CLIENTS (MusicBrainz / TheAudioDB and
  their key/rate-limit/UA plumbing). TAGSTREAM-009 REUSES that client layer for the artwork
  fetches (Cover Art Archive needs the MusicBrainz release MBID; TheAudioDB album/artist
  lookup; fanart.tv); it adds WHAT to fetch (the art endpoints, the MBID capture) + the
  embed logic, NOT a second HTTP client.
- **OPS-004 REQ-OH-006** — the bounded-job / throttle pattern. The artwork fetches adopt it
  so art acquisition + acquisition + analysis do not jointly overload the modest box;
  referenced, not re-owned.
- **KNOWLEDGE-008 Group KS (entities + `entities.mbid`)** — the artist MBID that makes
  fanart.tv artist-image lookup feasible without per-track re-resolution, and the artist
  notes the website now-playing context may show. TAGSTREAM-009 CONSUMES the knowledge
  store as a read source for artist images / notes; KNOWLEDGE-008 owns the store.
- **CORE-001 library + website + the airing path** — `brain/library.py` `Track` (read,
  plus two additive marker fields), `brain/server.py` `/api/nowplaying` + `_annotate_uri` +
  `_handle_airing`, `brain/state.py` `set_on_air`/`now_playing` (which ALREADY carry the
  on-air `path`), `brain/website.py` (the now-playing render), and the
  `%mp3(bitrate=320)` Liquidsoap output (`deploy/config/radio.liq`, left UNCHANGED for the
  primary path). TAGSTREAM-009 ENRICHES these additively; it does not fork the store or the
  pull contract.

### 1.5 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 Section 1.3, OPS-004 Section 1.3, ANALYSIS-006 Section 1.5, and
KNOWLEDGE-008 Section 1.4 in intent and does NOT redefine it. It is almost entirely an
ENGINEERING + PRESENTATION substrate (writing standard tags, embedding a fetched image,
rendering a JSON field is deterministic plumbing, not a creative act). Where it touches a
display decision it follows the same rule: it GRANTS the AI/listener accurate tags + art +
the live surfaces to show them + the safety/legality rails, and MUST NOT prescribe fixed
creative content, the exact website layout's editorial copy, or which art to prefer beyond
the legality + quality ceilings. The thresholds (key-confidence gate, resize ceiling, the
StreamTitle suffix template, the source-chain ordering) are TUNABLE config; the requirement
only guarantees the tags can be WRITTEN, the art ACQUIRED + EMBEDDED, and both EXPOSED.

### 1.6 Fixed engineering/safety rails (the only hard constraints)

- **Write tags + embed art IN PLACE in the 205 mp3 + 78 flac files** — the user-confirmed
  destructive decision. [HARD] idempotent (mp3 `setall`/`delall`+`add`; flac
  `clear_pictures`/key-replace), [HARD] per-file try/except (one corrupt file never aborts
  the batch of 283), embedded art resized (≤600px JPEG q85, target <120KB, hard-reject
  >200KB) and validated as a real image before embed.
- **Raw mutagen write path.** Tag + art writes use `mutagen.id3.ID3` / `mutagen.flac.FLAC`
  (the existing `_read_tags` `easy=True` path cannot write `TKEY`/`TBPM`/`TXXX`/`APIC`); the
  read path is left unchanged. ID3v2.3 (`save(v2_version=3)`) for widest compatibility.
- **Low key-confidence gating.** Below a configurable `key_confidence` threshold, the key
  tag is SKIPPED/flagged rather than written — a wrong key is worse than no key for harmonic
  mixing.
- **Legality is the deciding axis for artwork.** EMBED only from storage-safe sources
  (Cover Art Archive + TheAudioDB). [HARD] NEVER embed iTunes or Deezer art (their ToS forbid
  caching/storage); those may be used for WEBSITE-TRANSIENT display only, if at all. Embed
  only the front cover (picture type 3); artist images are website/sidecar only, never
  embedded. Skip Last.fm covers (placeholder images).
- **Honest capability.** [HARD] The SPEC MUST NOT claim separate sortable BPM/KEY/ENERGY
  COLUMNS over ANY live stream — that is a protocol impossibility. Sortable columns apply to
  the website history view and to LOCAL tagged files only.
- **Never blocks the <1s pull.** Tag writes + art fetches are offline batch / off-hot-path
  (the auto-hook rides the background analysis worker); `/api/next` never waits on a tag
  write, an art fetch, or an embed (inherits ANALYSIS-006 NFR-A-3 / OPS-004 NFR-O-10).
- **Bounded, throttled, rate-limit/ToS-respecting art fetches.** Respect TheAudioDB's
  30/min limit, fanart.tv's free-key + attribution requirement, and Cover Art Archive's
  redirect/404 semantics; a source outage degrades gracefully — the music keeps playing.
- **Brain-only, no store fork, no primary Liquidsoap change.** A new tag-write module + a
  new artwork module + additive now-playing/website fields; the `%mp3(320)` mount is
  untouched (the Ogg-FLAC mount is an optional, separate, integration-tested spike only).

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001, SPEC-RADIO-OPS-004, SPEC-RADIO-ANALYSIS-006, and
(for artist-image MBIDs + artist notes) SPEC-RADIO-KNOWLEDGE-008, and is the
presentation/tagging layer that surfaces their data. It references their subsystems by
CONCEPT (and, where a cited requirement is a deliberately stable invariant or seam, by
number) rather than re-specifying them.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any CORE-001, VOICE-002, OPS-004,
ORCH-005, ANALYSIS-006, or KNOWLEDGE-008 requirement. Where it needs a predecessor behavior
it consumes it. Where a TAGSTREAM decision could conflict with continuous operation, the
inherited continuous-operation behavior WINS.

Consumed ANALYSIS-006 concepts (by number, deliberately):
- **Groups AE/AT/AM + REQ-AD-001** — the COMPUTED feature record (`bpm`, `bpm_confidence`,
  `musical_key`, `camelot`, `key_confidence`, `energy`, `integrated_lufs`) that the tag-write
  reads and maps. TAGSTREAM-009 reads, never recomputes.
- **REQ-AD-005** — the `Track.key` dedup-slug vs `musical_key` tonal-key distinction; the
  tag-write maps `musical_key`/`camelot`, never the dedup `key`.
- **REQ-AP-007 + REQ-AP-001/002/003/004/005 (the `analyzer.py` Group AP worker)** — the
  ingest scan + the bounded, serialized, non-blocking, per-file-guarded analysis pipeline;
  the auto-tag/auto-art hook attaches at the end of analysis on this worker.

Consumed OPS-004 concepts (by number, deliberately):
- **REQ-OA-011** — the external-metadata HTTP CLIENTS (MusicBrainz / TheAudioDB) reused for
  the artwork fetches (CAA needs the release MBID `metadata.py` currently discards; TheAudioDB
  `searchalbum.php` / artist lookup; fanart.tv). The client plumbing is reused, not re-owned.
- **REQ-OH-006** — acquisition accounting + bounded queue + throttle, the pattern the art
  fetches adopt so they do not jointly overload the box.
- **REQ-OA-010** — tag correction/normalization. The tag-write uses the brain's CLEAN
  artist/title (the same the ICY StreamTitle uses) for art lookup keying; it does not re-own
  tag-fixing.

Consumed KNOWLEDGE-008 concepts (by number, deliberately):
- **Group KS (`entities.mbid`)** — the artist MBID for fanart.tv artist-image lookup, and the
  artist notes the website now-playing context may show; consumed read-only.

Consumed CORE-001 concepts:
- `brain/library.py` `Track` (read; plus two additive marker fields `has_cover` + `tagged`),
  `brain/server.py` (`/api/nowplaying`, `_annotate_uri`, `_handle_airing`), `brain/state.py`
  (`set_on_air`/`now_playing`, which already carry the on-air `path`), `brain/website.py`
  (the now-playing render + 5s poll), the config/secrets surface, and the
  `%mp3(bitrate=320)` Liquidsoap output (`deploy/config/radio.liq`), left UNCHANGED for the
  primary path.

### Downstream / sibling note

- A future SPEC could surface the same tags over a standards-based HLS-timed-ID3 web player;
  this SPEC's web now-playing player already delivers the goal with zero stream-format risk,
  so HLS is explicitly out of scope here (Section 15). The Ogg-FLAC spike (REQ-TX-006) is the
  only stream-format exploration in scope, and only as a gated spike.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Feature** | A per-track audio-intelligence value COMPUTED by ANALYSIS-006 and stored on the `Track`: `bpm`, `musical_key`, `camelot`, `energy`, `key_confidence`, etc. TAGSTREAM-009 reads these; it does not compute them. |
| **Tag / tag frame** | A standard metadata field embedded IN a music file: an ID3v2 frame (`TBPM`, `TKEY`, `TXXX:<desc>`, `APIC`) for MP3, or a Vorbis comment (`BPM`, `INITIALKEY`, `ENERGYLEVEL`, `CAMELOT`, picture block) for FLAC. |
| **TBPM** | The ID3v2 tempo frame. Holds an INTEGER numeric string (per spec) — `str(round(bpm))`. |
| **TKEY / INITIALKEY** | The musical-key frame (ID3 `TKEY`, max 3 chars per spec) / FLAC `INITIALKEY` Vorbis comment. Holds MUSICAL NOTATION ("Am", "C", "D#m") — NOT Camelot. |
| **TXXX:EnergyLevel / ENERGYLEVEL** | The energy-level tag (ID3 user-defined `TXXX` with desc `EnergyLevel` / FLAC `ENERGYLEVEL`). Holds the 1-10 integer = `round(energy*9)+1` (Mixed In Key / Serato / Traktor / Rekordbox de-facto convention). |
| **TXXX:CAMELOT / CAMELOT** | The Camelot-notation tag (ID3 `TXXX` desc `CAMELOT` / FLAC `CAMELOT`). Holds the verbatim Camelot code ("8A", "2A") — TKEY cannot legally hold it. |
| **APIC / Picture block** | The embedded-image frame: ID3v2 `APIC` (MP3) / FLAC `Picture` block. TAGSTREAM-009 embeds the album FRONT COVER (picture type 3) only. |
| **Raw mutagen write path** | Writing tags/art via `mutagen.id3.ID3` / `mutagen.flac.FLAC` (the full classes), distinct from the existing read path that opens files with `easy=True` (EasyID3), which cannot write `TKEY`/`TBPM`/`TXXX`/`APIC`. |
| **Idempotent write** | A write that, re-run over an already-tagged/arted file, produces the same result without duplicating frames — `setall` for single-instance frames, `delall`+`add` for `TXXX` by desc, `clear_pictures` before `add_picture` for FLAC, and a `has_cover`/`tagged` marker that lets re-runs skip done files. |
| **Backfill** | The one-shot pass that tags + arts ALL existing files (205 mp3 + 78 flac) NOW, distinct from the auto-hook for newly analyzed tracks going forward. |
| **Auto-hook** | The step attached at the END of analysis (in `analyzer.py`, after `set_analysis`) that tags + arts a newly analyzed track automatically, riding the background, throttled, per-file-guarded analysis worker. |
| **Storage-safe source** | An artwork source whose ToS permit caching/storage/rebroadcast, so its image may be EMBEDDED in files: Cover Art Archive (CC/uploader-released) and TheAudioDB (fan-created). |
| **No-store source** | An artwork source whose ToS forbid caching/storage (iTunes, Deezer). [HARD] NEVER embedded; usable for transient website display only, if at all. |
| **Cover Art Archive (CAA)** | coverartarchive.org — album front covers keyed by a MusicBrainz RELEASE (or release-group) MBID. Storage-safe. The integration cost is capturing the release MBID (currently discarded in `metadata.py`). |
| **Release MBID** | The MusicBrainz release identifier (`rec["release-list"][n]["id"]`) returned by the `search_recordings` call `metadata.py` already makes — currently mined only for the year and DISCARDED. Capturing it feeds CAA at near-zero new network cost. |
| **fanart.tv** | A source of dedicated ARTIST images (artistthumb/background) keyed by artist MBID. Free personal key + attribution required; artist images are website/sidecar only, never embedded. |
| **ICY StreamTitle** | The single periodic TEXT string Icecast injects into the stream (`StreamTitle='...'`). The only per-track metadata channel an MP3/AAC live stream has; it carries one string, split by players into artist/title — NOT separate fields. |
| **Now-playing surface** | The station website's now-playing panel, fed by `/api/nowplaying` JSON (polled ~5s), rendered by `brain/website.py`. The ONLY live display surface the station controls — where labeled fields + rendered art actually appear. |
| **Now-playing enrichment wiring** | The additive change by which the brain looks up the ON-AIR track BY PATH (the airing report already carries `path`) and enriches the now-playing JSON with its bpm/musical_key/camelot/energy + a cover URL, without widening the Liquidsoap report. |
| **Sortable columns** | A client-side-sortable TABLE of recently-played tracks (with art thumbnails) in the WEB player. Achievable for the history view and for LOCAL tagged files — NEVER for the singleton now-playing item over a live stream, and NEVER as off-the-shelf-player columns from a live source. |
| **Ogg-FLAC art spike** | An OPTIONAL second Icecast Ogg FLAC mount carrying in-band cover art (foobar2000 ≥1.6.1 renders it live). A fragile, integration-test-gated SPIKE — not a committed deliverable; the `%mp3` mount stays unchanged. |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group TW — Tag Write.** The storage-agnostic feature READ; the feature→tag value
  mapping (TBPM/TKEY/TXXX:EnergyLevel/TXXX:CAMELOT for mp3; BPM/INITIALKEY/ENERGYLEVEL/
  CAMELOT for flac); the mp3 (raw ID3, v2.3) and flac (raw FLAC, Vorbis-comment) write
  paths; idempotency; per-file batch safety + tagged-marker skip; low-key-confidence
  gating; the one-shot backfill of all existing files; the auto-tag hook for newly analyzed
  tracks.
- **Group TA — Artwork.** The storage-legality-ranked source chain (CAA → TheAudioDB →
  already-embedded) + the embed-safe-vs-display-only split (NEVER embed iTunes/Deezer); the
  release MBID capture in `metadata.py`; front-cover-only embedding (picture type 3) into
  mp3 (APIC) + flac (Picture); the resize/validate ceiling (≤600px JPEG q85, <120KB target,
  >200KB reject, validate real image); artist images for website display only (fanart.tv /
  TheAudioDB; never embedded; skip Last.fm); idempotent skip + per-file guard + backfill +
  auto-art hook.
- **Group TX — Stream/Site Exposure.** PRIMARY: the website now-playing player showing
  labeled BPM/key/camelot/energy fields + rendered cover/artist art; the recently-played
  view with sortable columns + art thumbnails; the now-playing-enrichment wiring (by-path
  on-air lookup). SECONDARY: the enriched ICY StreamTitle ("Artist - Title [96 BPM | 2A |
  E7]"). The honest NON-GOAL (live per-field sortable columns over the stream are
  impossible). The OPTIONAL Ogg-FLAC-art spike (non-committal, integration-test-gated).
- Plus **NFRs** (Section 13) and **Risks** (Section 14).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **Computing the audio features** (bpm/key/energy/genre) — owned by ANALYSIS-006 Groups
  AE/AT/AM; TAGSTREAM-009 reads them, never recomputes.
- **The library auto-ingest SCAN + the analysis worker LOOP** — owned by ANALYSIS-006
  REQ-AP-007 + Group AP; TAGSTREAM-009 attaches its auto-hook at the end of analysis, it
  does not re-own the scan or the worker.
- **The external-metadata HTTP CLIENT layer** — owned by OPS-004 REQ-OA-011; TAGSTREAM-009
  reuses it for the art fetches + adds the art endpoints + the MBID capture, not a second
  client.
- **The curation / picker / rotation loop** — owned by CORE-001/OPS-004; TAGSTREAM-009 reads
  the on-air track to display it, it does not influence selection.
- **Per-field SORTABLE columns over the live stream** — a protocol impossibility (research.md);
  explicitly a NON-GOAL (REQ-TX-005), never a deliverable.
- **Artwork bytes delivered IN-BAND over the live `%mp3`/ICY stream** — impossible (no
  in-band picture channel); the website panel is the controlled live-art surface.
- **The Ogg-FLAC mount as a COMMITTED deliverable** — it is an optional, integration-test-gated
  SPIKE only (REQ-TX-006); the primary path leaves `%mp3(320)` unchanged.
- **An HLS timed-ID3 web player** — a heavier, standards-based alternative the web JSON
  player already beats with zero stream risk; deferred (Section 15).
- **Embedding ARTIST images into files** — most players ignore artist-type pictures and it
  doubles per-file bloat; artist images are website/sidecar only.
- **A new datastore, a new service, or a primary Liquidsoap change** — brain-only; a new
  tag-write module + a new artwork module + additive now-playing/website fields.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain = the existing Python `brain/` package.** TAGSTREAM-009 adds a tag-write
  module + an artwork acquisition/embed module + additive now-playing-JSON + website fields;
  it is not a new service.
- [HARD] **Write tags + embed art IN PLACE in the 205 mp3 + 78 flac files** (the
  user-confirmed destructive decision).
- [HARD] **Idempotent writes.** mp3: `setall` for `TBPM`/`TKEY`, `delall`+`add` for `TXXX` by
  desc, `setall(['APIC'])` for the cover; flac: key-replace for Vorbis comments,
  `clear_pictures` before `add_picture`. A `has_cover`/`tagged` marker lets re-runs skip done
  files.
- [HARD] **Per-file try/except.** One corrupt/unreadable/read-only file logs and is skipped;
  it NEVER aborts the batch of 283.
- [HARD] **Raw mutagen write path.** `mutagen.id3.ID3` / `mutagen.flac.FLAC`; the existing
  `easy=True` read path is unchanged. ID3v2.3 (`save(v2_version=3)`).
- [HARD] **Low key-confidence gating.** Below a configurable threshold, skip/flag the key
  rather than write a misleading one.
- [HARD] **Embedded art resized + validated.** ≤600px JPEG q85, target <120KB, hard-reject
  >200KB; validate it is a real image (e.g. `Image.open(...).verify()`) before embed.
- [HARD] **Embed only storage-safe sources, front cover only.** Cover Art Archive +
  TheAudioDB; NEVER embed iTunes/Deezer (no-store ToS); embed only the front cover (picture
  type 3); artist images are website/sidecar only; skip Last.fm covers.
- [HARD] **Honest capability.** No claim of separate sortable BPM/KEY/ENERGY columns over any
  live stream; sortable columns are the website history view + local files only.
- [HARD] **Never blocks the <1s pull.** Tag writes + art fetches are offline batch /
  off-hot-path; the auto-hook rides the background analysis worker; `/api/next` never waits.
- [HARD] **Bounded/throttled + rate-limit/ToS-respecting art fetches.** TheAudioDB 30/min;
  fanart.tv free key + attribution; CAA redirect/404 semantics; OPS-004 REQ-OH-006 pattern.
- [HARD] **No store fork; no primary Liquidsoap change.** `%mp3(320)` stays unchanged; the
  Ogg-FLAC mount is a separate optional spike.

---

## 6. Requirement Group TW — Tag Write

Priority: High.

### REQ-TW-001 — Storage-agnostic feature read (Ubiquitous) [HARD]

The system shall READ the per-track audio features it writes as tags (`bpm`, `musical_key`,
`camelot`, `energy`, `key_confidence`) from the library's track records THROUGH the library
accessor, NOT by coupling to the concrete JSON-file store. [HARD] The tag-write reads
features storage-agnostically so that a future migration of the feature store (e.g. from
`library.json` to a SQLite store) does NOT require rewriting the tag-write path; it depends
on the `Track` feature fields (ANALYSIS-006 REQ-AD-001), not on the file format they happen
to persist in today. The features are COMPUTED by ANALYSIS-006 (referenced); this requirement
reads them, never recomputes.

**Acceptance criteria:** see acceptance.md AC-TW-001.

### REQ-TW-002 — Feature→tag value mapping (Ubiquitous) [HARD]

The system shall derive the standard tag VALUES from the features once per track, shared by
both formats: (a) BPM → an INTEGER string `str(round(bpm))` (ID3 `TBPM` spec is an integer
numeric string); (b) KEY → MUSICAL NOTATION, max 3 chars (ID3 `TKEY` spec) — convert the
library's `musical_key` ("D# minor" → "D#m"; "A minor" → "Am"; "C major" → "C") via the rule
"<root> minor" → "<root>m", "<root> major" → "<root>", and [HARD] do NOT put Camelot in the
key tag; (c) CAMELOT → the verbatim code ("8A"/"2A") in a SEPARATE field; (d) ENERGY LEVEL →
the 1-10 integer `str(round(energy*9)+1)` (the Mixed In Key / Serato / Traktor / Rekordbox
convention). The exact conversion table + the energy scaling formula are TUNABLE; that the
values follow the standard frame semantics (TBPM integer, TKEY ≤3-char notation, Camelot
separate, EnergyLevel 1-10) is the rail.

**Acceptance criteria:** see acceptance.md AC-TW-002.

### REQ-TW-003 — MP3 ID3 tag write (raw ID3, idempotent) (Event-driven) [HARD]

When a track is an MP3 and is tagged (by backfill or the auto-hook), the system shall write,
via the RAW `mutagen.id3.ID3` class (NOT EasyID3, which lacks `TKEY`/`TBPM`/`TXXX`): `TBPM`
(the integer BPM), `TKEY` (the ≤3-char musical notation), `TXXX:EnergyLevel` (1-10), and
`TXXX:CAMELOT` (verbatim) — creating a fresh ID3 container for an untagged file
(`ID3NoHeaderError`) — and SHALL save as ID3v2.3 (`save(v2_version=3)`) for widest
compatibility. [HARD] The write is IDEMPOTENT: `setall` for the single-instance `TBPM`/`TKEY`
frames and `delall`+`add` (keyed by desc) for the `TXXX` frames, so a re-run NEVER creates
duplicate frames. All text values are unicode `str`. The container "/music/..." path is
resolved to the host path before opening.

**Acceptance criteria:** see acceptance.md AC-TW-003.

### REQ-TW-004 — FLAC Vorbis-comment tag write (raw FLAC, idempotent) (Event-driven) [HARD]

When a track is a FLAC and is tagged (by backfill or the auto-hook), the system shall write,
via the RAW `mutagen.flac.FLAC` class, the Vorbis comments `BPM` (integer), `INITIALKEY` (the
≤3-char musical notation; foobar maps it to "INITIAL KEY"), `ENERGYLEVEL` (1-10), and
`CAMELOT` (verbatim), then save. [HARD] The write is IDEMPOTENT: Vorbis keys are
case-insensitive and assigning a key REPLACES it, so FLAC tag writes are naturally
non-duplicating. Values are `str` lists. The same value derivation (REQ-TW-002) is shared
with the MP3 path.

**Acceptance criteria:** see acceptance.md AC-TW-004.

### REQ-TW-005 — Low key-confidence gating (Unwanted) [HARD]

If a track's `key_confidence` is BELOW a configurable threshold, then the system SHALL NOT
write a key tag (`TKEY` / `INITIALKEY`) — it shall SKIP the key (and may record/flag that it
was skipped) — rather than write a misleading key. [HARD] A wrong key is worse than no key
for harmonic mixing; the BPM and energy tags MAY still be written, but the Camelot tag —
derived from the SAME key estimate — is gated by the SAME threshold and is NOT written below
it (a low-confidence Camelot is as misleading as a low-confidence key). The threshold is
TUNABLE config; that a below-threshold key AND its Camelot are gated out, not written, is the
rail.

**Acceptance criteria:** see acceptance.md AC-TW-005.

### REQ-TW-006 — Per-file batch safety + idempotent skip marker (Ubiquitous) [HARD]

The system shall wrap EACH file's read+derive+write in its own try/except (catching
`mutagen` errors and generic exceptions), log + count failures, and CONTINUE — so one
corrupt, unreadable, partially-written, or read-only file NEVER aborts the batch of 283.
[HARD] The system shall record a per-track `tagged` marker (and, for art, `has_cover`,
REQ-TA-006) so a re-run SKIPS files already done (re-scan resilience), only (re)writing on a
miss or a forced-refresh flag. The batch SHALL verify a write by re-opening the file after
save where feasible; a failed verify logs and does not corrupt the marker.

**Acceptance criteria:** see acceptance.md AC-TW-006.

### REQ-TW-007 — One-shot backfill of all existing files NOW (Event-driven) [HARD]

When the backfill is invoked, the system shall tag ALL existing analyzed files in the music
directory (the 205 mp3 + 78 flac) in one bounded, resumable pass — reading each file's
features (REQ-TW-001), deriving the values (REQ-TW-002), and writing the format-appropriate
tags (REQ-TW-003/004) under the per-file guard (REQ-TW-006) and the confidence gate
(REQ-TW-005). [HARD] The backfill is the one-shot coverage of the EXISTING library; it is
distinct from the going-forward auto-hook (REQ-TW-008) and shares the same write path,
idempotency, and skip marker. A file with no analysis record yet is left untagged (it will be
tagged by the auto-hook once analyzed); the backfill never blocks the pull (NFR-T-1).

**Acceptance criteria:** see acceptance.md AC-TW-007.

### REQ-TW-008 — Auto-tag hook for newly analyzed tracks (Event-driven) [HARD]

When a track finishes analysis (at the END of `Analyzer._analyze_one`, after `set_analysis`
writes the feature record), the system shall tag that track automatically — so newly
ingested/analyzed music gains its file tags without a manual backfill run, keeping the
library's files current going forward. [HARD] The hook ATTACHES to the ANALYSIS-006 Group AP
worker (REQ-AP-001/002/005, referenced) and inherits its rails: it runs off the `/api/next`
pull path (NFR-T-1), under the per-file guard (REQ-TW-006), the confidence gate (REQ-TW-005),
and the idempotent skip marker — so a re-analyzed track re-tags idempotently and a tag
failure never crashes the analysis worker or silences the stream.

**Acceptance criteria:** see acceptance.md AC-TW-008.

---

## 7. Requirement Group TA — Artwork

Priority: High.

### REQ-TA-001 — Storage-legality-ranked source chain; embed-safe vs display-only (Ubiquitous) [HARD]

The system shall acquire album front-cover artwork from a source chain RANKED BY STORAGE
LEGALITY (not image quality), and shall EMBED only from STORAGE-SAFE sources: (1) **Cover
Art Archive** (CC/uploader-released; needs a MusicBrainz release MBID, REQ-TA-002), (2)
**TheAudioDB** album lookup (fan-created; free-text artist+album via `searchalbum.php` —
currently only `searchtrack.php`, which returns no album art, is called), (3) the
ALREADY-EMBEDDED `APIC`/Picture in the file (zero network, last resort). [HARD] The system
SHALL NEVER EMBED art from a NO-STORE source — iTunes and Deezer ToS forbid caching/storage,
so their art is usable for WEBSITE-TRANSIENT display ONLY, if at all, and NEVER written into a
file. Last.fm covers (placeholder images) are skipped. The source-chain ordering is TUNABLE;
the embed-safe-only + no-embed-of-no-store rails are FIXED.

**Acceptance criteria:** see acceptance.md AC-TA-001.

### REQ-TA-002 — Capture the release MBID in metadata.py (Event-driven) [HARD]

When the metadata enrichment runs its existing `search_recordings(... limit=1)` MusicBrainz
call, the system shall CAPTURE the release MBID(s) — `rec["release-list"][n]["id"]` — which
the current `_extract_year` path reads but DISCARDS (it mines only `rel["date"]` for the
year). [HARD] The captured release MBID is persisted with the track so Cover Art Archive
(`/release/{mbid}/front`) can be queried at near-zero new network cost (the
`search_recordings` call already runs); a track with no MBID match falls through to the
TheAudioDB free-text branch (REQ-TA-001). This requirement owns capturing the MBID into the
artwork path; it does not re-own the MusicBrainz client (OPS-004 REQ-OA-011).

[Boundary / coordination] The `metadata.py` edit is an ADDITIVE field-capture only: it reads
a value the existing `search_recordings` response already contains and persists it for the
artwork path, and it MUST NOT alter OPS-004 REQ-OA-011's client behavior — no change to the
request, the rate-limit/User-Agent handling, the existing enrichment fields, or the year
extraction. It is scoped as "what to capture from an already-fetched response," not a second
HTTP client and not a behavioral change to the shared client.

**Acceptance criteria:** see acceptance.md AC-TA-002.

### REQ-TA-003 — Embed front cover only (picture type 3), raw mutagen, idempotent (Event-driven) [HARD]

When a storage-safe front cover is acquired for a track (by backfill or the auto-hook), the
system shall EMBED it as the FRONT COVER (picture type 3 / `COVER_FRONT`) into the file via
the RAW write path: ID3v2 `APIC` (`type=COVER_FRONT`, `mime='image/jpeg'`) for MP3 saved as
v2.3, and a FLAC `Picture` block (`type=COVER_FRONT`) for FLAC. [HARD] The embed is
IDEMPOTENT: `setall('APIC', [apic])` (replaces all existing APIC frames — no accumulation)
for MP3 and `clear_pictures()` before `add_picture(pic)` for FLAC, with the front cover stored
as the first/only picture (the foobar2000 convention). [HARD] ONLY the front cover is
embedded — no second (artist) picture (REQ-TA-005). The write path uses raw mutagen (the
`easy=True` read path cannot write `APIC`).

**Acceptance criteria:** see acceptance.md AC-TA-003.

### REQ-TA-004 — Resize + validate ceiling before embed (Ubiquitous) [HARD]

The system shall, before embedding any image, VALIDATE that the downloaded bytes are a real
image (e.g. `Image.open(...).verify()` — rejecting HTML error pages / truncated downloads)
and RESIZE it to bound per-file bloat: max(width,height) ≤ 600px, re-encoded as JPEG quality
85, EXIF stripped, targeting < ~120KB per image. [HARD] The system shall HARD-REJECT (skip
the embed, log it) an encoded image larger than 200KB and any input that fails image
validation. JPEG (mime `image/jpeg`) is used, not PNG. The 600px ceiling / quality / size
caps are TUNABLE; that art is validated-as-a-real-image and bounded before embed is the rail.

**Acceptance criteria:** see acceptance.md AC-TA-004.

### REQ-TA-005 — Artist images are website/sidecar only, never embedded (Ubiquitous) [HARD]

The system shall acquire ARTIST images (fanart.tv `artistthumb`/background keyed by artist
MBID from KNOWLEDGE-008 `entities.mbid` as PRIMARY; TheAudioDB `strArtistThumb` by free-text
artist as the no-MBID fallback) for WEBSITE / sidecar display ONLY, and SHALL NOT EMBED an
artist image into any music file. [HARD] Only the front cover is embedded (REQ-TA-003); artist
images are served as a website/cached-sidecar asset because most players ignore artist-type
pictures and a second embedded picture doubles per-file bloat. fanart.tv requires a free
personal key and its ToS attribution ("images come from fanart.tv") shall be honored on the
website; Last.fm artist images (placeholder hash) are skipped. The artist-image source set is
TUNABLE; the never-embed-artist-images rail is FIXED.

**Acceptance criteria:** see acceptance.md AC-TA-005.

### REQ-TA-006 — Idempotent skip + per-file guard + backfill + auto-art hook (Ubiquitous) [HARD]

The system shall record a per-track `has_cover` marker (and optional `cover_source`) so the
scan/website know which files carry art and a re-run SKIPS files already arted (only
(re)embedding on a miss, a decode-failure of the existing embedded image, or a forced-refresh
flag). [HARD] Artwork acquisition+embed shall be done as an OFFLINE BATCH enrichment step —
a one-shot BACKFILL of the existing files AND an auto-art hook for newly analyzed tracks (at
the same end-of-analysis point as REQ-TW-008) — NEVER on the live on-air path, with the ENTIRE
download+validate+resize+embed per file wrapped in try/except so one corrupt download,
unreadable tag, or read-only file logs and the batch continues (mirrors REQ-TW-006). The
auto-art hook rides the ANALYSIS-006 Group AP worker (referenced).

**Acceptance criteria:** see acceptance.md AC-TA-006.

---

## 8. Requirement Group TX — Stream/Site Exposure

Priority: High (group default). Per-REQ priorities in the Traceability Index (Section 14)
OVERRIDE this group default where they differ — REQ-TX-004 is Medium (the StreamTitle
enrichment is a secondary nicety atop the primary website surface) and REQ-TX-006 is Low (an
optional, non-committal spike); the rest are High.

### REQ-TX-001 — PRIMARY: website now-playing player shows fields + art (Ubiquitous) [HARD]

The system shall make the station WEBSITE's now-playing player the CANONICAL live surface for
the analyzed data: it shall render the ON-AIR track's BPM, musical key, Camelot, and energy as
LABELED FIELDS and render the cover art (and, where available, the artist image) as images,
driven by the existing `/api/nowplaying` JSON the page already polls (~5s). [HARD] The
`%mp3(bitrate=320)` audio stream stays UNCHANGED; the rich view is delivered entirely through
the website (which the listener should be pointed at, not the raw stream URL). This is the
ONLY surface that reliably shows clean, separate per-field values + rendered art live, to any
listener with a browser, independent of audio player and of the ICY protocol. The exact
visual layout is the AI's/design's (Creative Autonomy); that the fields + art appear, fed by
the now-playing JSON, is the rail.

**Acceptance criteria:** see acceptance.md AC-TX-001.

### REQ-TX-002 — Recently-played view with sortable columns + art thumbnails (Ubiquitous) [HARD]

The system shall render a RECENTLY-PLAYED view in the web player as a client-side-SORTABLE
TABLE with columns (artist/title/BPM/key/Camelot/energy/played-at) and art THUMBNAILS, fed by
the `recent[]` history in `/api/nowplaying` (enriched per REQ-TX-003). [HARD] Sortable columns
apply to the HISTORY view (a finite client-side list) — NOT to the singleton now-playing item,
and NOT as columns synthesized by any off-the-shelf player from a live stream (REQ-TX-005). The
history columns are a property of OUR web player only. The set of columns + the default sort
are TUNABLE; that the history view is sortable with art thumbnails is the rail.

**Acceptance criteria:** see acceptance.md AC-TX-002.

### REQ-TX-003 — Now-playing enrichment wiring: by-path on-air lookup (Event-driven) [HARD]

When the brain assembles the `/api/nowplaying` JSON, the system shall ENRICH the now-playing
(and recent) objects with the on-air track's bpm / musical_key / camelot / energy + a cover
URL by LOOKING UP the on-air track BY PATH — the airing report (`POST /api/airing` →
`state.set_on_air`) already carries `path`, and `now_playing()` already returns it — rather
than widening the Liquidsoap `report_airing` payload. [HARD] The wiring is ADDITIVE and
low-risk: the audio path, the `_annotate_uri` pull contract, and the airing report are
UNCHANGED; only the now-playing JSON gains fields (and a cover route/URL, e.g. `/art?path=...`
or a cached cover, with a static fallback). The by-path lookup resolves the on-air `path` to
the analyzed `Track`; an unanalyzed/unresolved track yields the existing artist/title only
(graceful degradation).

**Acceptance criteria:** see acceptance.md AC-TX-003.

### REQ-TX-004 — SECONDARY: enriched ICY StreamTitle (Event-driven)

When the brain forms the streamed now-playing title, the system shall enrich the live ICY
`StreamTitle` so every player's now-playing LINE reads "Artist - Title [96 BPM | 2A | E7]" —
one decorated string carrying the BPM / Camelot / energy of the on-air track. [HARD honesty]
This lands inside the single `StreamTitle` string (visible to ALL players in the now-playing
line) and is NOT separate sortable columns (players split `StreamTitle` only on the first
hyphen into artist/title); it is well within the ICY block size. The brain should build the
enriched title (so the website display and the ICY agree) while keeping a clean artist/title
available for any downstream parsing; the suffix template + field order are TUNABLE config.
This is the honest best the MP3 path can do for "see it while listening live" in a player UI.

**Acceptance criteria:** see acceptance.md AC-TX-004.

### REQ-TX-005 — NON-GOAL: no live per-field sortable columns over the stream (Ubiquitous prohibition) [HARD]

The system SHALL NOT claim, implement, or adopt as an acceptance criterion the delivery of
SEPARATE SORTABLE BPM/KEY/ENERGY COLUMNS over ANY live stream to an off-the-shelf player.
[HARD] This is a verified protocol impossibility (research.md, refuted 3/3): ICY carries one
`StreamTitle` text string with no per-field channel; MP3/AAC have no in-band metadata; and no
off-the-shelf player (foobar2000 included) builds user-defined sortable columns from a LIVE
source — that is strictly a file-tag / media-library feature. Sortable per-field columns are
delivered ONLY via our own web history view (REQ-TX-002) and via LOCAL playback of the tagged
files (Group TW). The SPEC encodes this as a fixed non-goal so no downstream work or claim
overstates the live stream's capability.

**Acceptance criteria:** see acceptance.md AC-TX-005.

### REQ-TX-006 — OPTIONAL SPIKE: Ogg-FLAC in-band cover-art mount (Optional) [SPIKE, non-committal]

Where the team chooses to explore a foobar2000-specific live-art win, the system MAY add a
SECOND Icecast Ogg FLAC mount carrying in-band cover art (via `METADATA_BLOCK_PICTURE`),
leaving the primary `%mp3(bitrate=320)` mount UNCHANGED. Research CONFIRMS foobar2000 ≥1.6.1
renders live in-band album art from an Ogg FLAC stream (a real, narrow win for foobar2000
desktop listeners), BUT with a per-track-update FRAGILITY caveat that MUST be integration-tested
before any reliance: foobar2000 v2.26 turned Ogg chaining OFF by default (chaining is exactly
the per-track-metadata mechanism), VLC/mpv commonly regress, and native `%opus` has a
metadata-cumulation bug (use `%vorbis` or `%ffmpeg` libopus). [HARD] This is an OPTIONAL,
INTEGRATION-TEST-GATED SPIKE — NOT a committed deliverable and NOT a pass/fail acceptance
criterion for the SPEC; even success does NOT yield sortable columns (REQ-TX-005). Its
acceptance entry verifies the spike is SCOPED and GATED, not that the mount ships.

**Acceptance criteria:** see acceptance.md AC-TX-006.

---

## 9. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following:

- **Computing the audio features** (bpm/key/energy/genre) — owned by ANALYSIS-006 Groups
  AE/AT/AM; TAGSTREAM-009 reads them, never recomputes.
- **The library auto-ingest SCAN + the analysis worker LOOP** — owned by ANALYSIS-006
  REQ-AP-007 + Group AP; the auto-hook attaches at the end of analysis, it does not re-own
  the scan/worker.
- **The external-metadata HTTP CLIENT layer** — owned by OPS-004 REQ-OA-011; reused for the
  art fetches, not re-owned (no second HTTP client).
- **The curation / picker / rotation loop** — owned by CORE-001/OPS-004; TAGSTREAM-009 reads
  the on-air track to display it, never influences selection.
- **Separate sortable BPM/KEY/ENERGY COLUMNS over ANY live stream** — a verified protocol
  impossibility (REQ-TX-005); never claimed, implemented, or accepted.
- **Artwork bytes delivered IN-BAND over the live `%mp3`/ICY stream as a player-rendered
  image** — impossible; the website panel is the controlled live-art surface, embedded file
  art helps only local/downstream players.
- **The Ogg-FLAC mount as a committed deliverable** — it is an optional, integration-test-gated
  SPIKE only (REQ-TX-006); `%mp3(320)` stays unchanged.
- **An HLS timed-ID3 web player** — the web JSON player already delivers the goal with zero
  stream-format risk; deferred (Section 15).
- **EMBEDDING artist images into files** — most players ignore artist-type pictures and it
  doubles per-file bloat; artist images are website/sidecar only (REQ-TA-005).
- **EMBEDDING iTunes or Deezer artwork** — their ToS forbid caching/storage; never embedded
  (display-only-if-at-all) (REQ-TA-001).
- **Skipping the key tag's confidence gate** — a below-threshold key is gated out, not written
  (REQ-TW-005); no "write the key anyway" path.
- **A new datastore, a new service, or a primary Liquidsoap change** — brain-only; a new
  tag-write module + a new artwork module + additive now-playing/website fields.

---

## 10. Tagging-and-exposure note (recommendation, not a hard rail)

The recommended write tool is **mutagen** (already a dependency — `library.py` imports
`from mutagen import File` for the read path), using its RAW classes (`mutagen.id3.ID3`,
`mutagen.flac.FLAC`) for the write path because the existing `easy=True` (EasyID3) read path
cannot write `TKEY`/`TBPM`/`TXXX`/`APIC`. **Pillow** is the recommended resize/validate tool
for the embed ceiling. ID3v2.3 (`save(v2_version=3)`) is recommended for widest device/Serato/
foobar compatibility (v2.4 is also acceptable; confirm no tool in the chain requires it). The
recommended exposure architecture is the JSON-driven WEB now-playing player on the existing
website (the audio stream unchanged), because the three research dossiers establish it as the
ONLY path that reliably delivers structured fields + sortable history columns + rendered art
to a live listener with zero stream-format risk. The SPEC fixes the value mapping + the
idempotency/safety/legality rails + the exposure surfaces; the specific libraries + the visual
layout are implementation choices behind those rails.

---

## 11. Non-Functional Requirements

### NFR-T-1 — Never blocks the playout pull (Ubiquitous) — Priority High
Tag writes, artwork fetches, image resize/validate, and embedding shall be fully decoupled
from the `/api/next` pull; a pull shall never wait on a tag write, an art download, or an
embed (the backfill is an offline batch; the auto-hook rides the background analysis worker;
the now-playing enrichment is a cheap by-path read), inheriting ANALYSIS-006 NFR-A-3 /
OPS-004 NFR-O-10. See acceptance.md AC-NFR-T-1.

### NFR-T-2 — Bounded, throttled, rate-limit/ToS-respecting art fetches (Ubiquitous) — Priority High
External artwork fetches shall be bounded and throttled (OPS-004 REQ-OH-006 pattern) and shall
respect each source's limits + terms: TheAudioDB ≤30 req/min (back off on 429), fanart.tv's
free personal key + its attribution requirement, Cover Art Archive's 307/404/503 semantics; a
quota hit or outage backs off and degrades gracefully — the music keeps playing. See
acceptance.md AC-NFR-T-2.

### NFR-T-3 — Never crash the batch; in-place mutation resilience (Ubiquitous) — Priority High
A failed tag write, a corrupt/unreadable/read-only file, a malformed download, or an embed
error shall log and be SKIPPED without aborting the batch of 283, without crashing the
analysis worker or the daemon, and without silencing the stream; in-place writes are guarded
(per-file try/except, write-then-verify where feasible) so an interrupted write does not
corrupt the file's tagged/has_cover marker (REQ-TW-006, REQ-TA-006). See acceptance.md
AC-NFR-T-3.

### NFR-T-4 — Legality: no no-store art ever embedded (Ubiquitous) — Priority High
No code path shall EMBED artwork from a no-store source (iTunes, Deezer) into any file; embeds
come ONLY from storage-safe sources (Cover Art Archive, TheAudioDB, already-embedded), front
cover only; no-store sources are usable for transient website display only, if at all; Last.fm
covers (placeholders) are skipped (REQ-TA-001, REQ-TA-005). See acceptance.md AC-NFR-T-4.

### NFR-T-5 — Honest capability; no overclaimed stream columns (Ubiquitous) — Priority High
No requirement, acceptance criterion, documentation, or website copy shall claim separate
sortable BPM/KEY/ENERGY columns over a live stream, or claim artwork rides the live `%mp3`/ICY
stream as a player-rendered image; the verified ceilings (web history view + local files for
columns; website panel for live art; enriched StreamTitle as one string) are stated honestly
(REQ-TX-004, REQ-TX-005, REQ-TX-006). See acceptance.md AC-NFR-T-5.

### NFR-T-6 — Idempotent + bloat-bounded (Ubiquitous) — Priority High
Re-running the tag/art write over already-done files shall be non-duplicating (idempotent
frames + `tagged`/`has_cover` skip markers) and embedded art shall be bounded (≤600px JPEG q85,
<120KB target, >200KB reject) so the total embedded overhead across 283 files stays modest
(REQ-TW-003/004, REQ-TW-006, REQ-TA-003/004/006). See acceptance.md AC-NFR-T-6.

### NFR-T-7 — Simplicity / no over-engineering (Ubiquitous) — Priority Medium
This SPEC shall implement the smallest tagging + artwork + exposure substrate that delivers the
file tags, embedded covers, and the website/StreamTitle exposure on the confirmed brain-only
stack; deferred items (Section 9) MUST NOT be partially built — no new service, no second HTTP
client, no primary Liquidsoap change, no HLS player, no artist-image embedding, and the
Ogg-FLAC mount only as a gated spike. See acceptance.md AC-NFR-T-7.

---

## 12. Open Questions / Risks

- **R-T-1 — In-place mutation of 283 source files is destructive (High, decided).** Writing
  tags + embedding art mutates the user's own music files in place. Decided (user, baked in
  Section 1.6/5): write IN PLACE. Mitigated by [HARD] idempotent writes, [HARD] per-file
  try/except so one bad file never aborts the batch, write-then-verify where feasible, the
  `tagged`/`has_cover` skip markers so re-runs are safe, and the bounded resize so embeds do
  not bloat files. Residual: a power loss mid-save could leave one file's tag partially
  written — mitigated by mutagen's in-place save + the per-file verify-after-save + the marker
  only being set on a verified write.
- **R-T-2 — Low key-confidence keys (High driver).** ANALYSIS-006 records `key_confidence`
  and the sample data shows values as low as ~0.25; writing a wrong key is worse than no key.
  Mitigated by the confidence gate (REQ-TW-005): below threshold, the key + Camelot tags are
  skipped, not written. The threshold is the central tuning knob (too high → many tracks
  keyless; too low → misleading keys); TUNABLE config.
- **R-T-3 — Release MBID coverage for Cover Art Archive (Medium).** CAA needs a MusicBrainz
  release MBID; the library has essentially none today (the `search_recordings` MBID is
  discarded). Mitigated by capturing it (REQ-TA-002) at near-zero new cost and falling through
  to TheAudioDB free-text (REQ-TA-001) and to the already-embedded picture; a track with no
  cover from any storage-safe source simply has no embedded art (the website shows the static
  fallback), never a no-store image.
- **R-T-4 — Artwork source rate limits / keys / ToS (Medium).** TheAudioDB free key "123" is
  30/min; fanart.tv needs a free personal key + attribution; CAA has 307/404/503 semantics; the
  no-store sources (iTunes/Deezer) are excluded from embed entirely. Mitigated by the bounded/
  throttled fetches (NFR-T-2), caching the fetched cover with the file/marker, running off the
  pull path (NFR-T-1), config-gating keys, and honoring fanart.tv attribution on the site.
- **R-T-5 — The live-stream capability ceiling is a HARD limit, not a tuning problem (High,
  honesty).** Three adversarial dossiers refuted "live per-field sortable columns" (3/3) and
  "artwork rides the live stream as a rendered image" (2/2). This is encoded as a fixed
  non-goal (REQ-TX-005, NFR-T-5) so no work overstates the stream. Mitigation IS the honesty:
  deliver the real value through the website player (REQ-TX-001/002) + enriched StreamTitle
  (REQ-TX-004) + local file tags (Group TW), and explicitly NOT through fictional stream
  columns. The user has confirmed the website panel as the live per-field surface.
- **R-T-6 — Ogg-FLAC spike fragility (Medium, spike-gated).** foobar2000 ≥1.6.1 renders live
  in-band Ogg FLAC art, but foobar 2.26's Ogg-chaining-off default may break per-track updates,
  and VLC/mpv regress. Mitigated by treating it as an OPTIONAL, integration-test-gated SPIKE
  (REQ-TX-006) that leaves `%mp3(320)` untouched and is never a committed AC; the spike must
  empirically verify per-track updates before any reliance. Open: whether any meaningful number
  of listeners use foobar2000 on the raw stream (if near-zero, the spike's only win may not be
  worth it).
- **R-T-7 — Now-playing by-path lookup reliability (Low/Medium).** The enrichment resolves the
  on-air `path` (already carried by `set_on_air`) to the analyzed `Track`. Mitigated by the
  graceful-degradation rail (REQ-TX-003): an unanalyzed or unresolved path yields the existing
  artist/title only, never a crash or a stale enrichment; talk clips (no `Track`) yield no
  feature fields, as today.
- **R-T-8 — ID3 version + tool compatibility (Low).** v2.3 is recommended for widest device/
  Serato/foobar compatibility; some chains prefer v2.4. Mitigated by `save(v2_version=3)` as
  the recommended default behind a config option; the value semantics (TBPM integer, TKEY
  ≤3-char, TXXX EnergyLevel/CAMELOT) are version-independent.
- **R-T-9 — Embedded-art bloat across 283 files (Low).** Unbounded covers would bloat the
  files. Mitigated by the resize ceiling (REQ-TA-004): ~600px JPEG q85 ≈ 25-35MB total across
  283 files (acceptable), with a hard 200KB-per-image reject; PNG (large for photographic art)
  is avoided in favor of JPEG.
- **R-T-10 — Boundary overlap with ANALYSIS-006 + OPS-004 (Low, reconciled).** ANALYSIS-006
  owns computing the features + the catalog + the analysis worker; OPS-004 owns the external
  HTTP clients + the bounded-job throttle. To avoid duplication, TAGSTREAM-009 OWNS writing the
  features as file tags, acquiring + embedding art, and exposing both to listeners — and READS
  the features storage-agnostically, REUSES the OPS-004 clients, and ATTACHES its auto-hook to
  the ANALYSIS-006 worker, referencing each by number rather than restating it (Sections 1.4,
  2).

---

## 13. Out-of-Scope / Future SPEC Roadmap

- **HLS timed-ID3 web player** — a standards-based path carrying TXXX fields + APIC art inside
  an HLS stream rendered by a custom hls.js web UI; the JSON web player already delivers the
  goal with less complexity and zero stream risk, so HLS is a future exploration, not built
  here.
- **A queryable library/history browser** — a larger sortable table over the whole library
  (powered by the brain's existing bpm/energy/camelot filters) beyond the recent[] history
  view; a future website enhancement layering on the same now-playing JSON shape.
- **A `/cover` extraction route + cover cache strategy** — the exact transport for website art
  (read embedded APIC/Picture via a route, vs cached cover files served statically, vs a remote
  URL) is an implementation choice this SPEC bounds (favor cached/embedded over hotlinked remote
  for robustness); a richer cover-cache CDN/strategy is a future concern.
- **Transient no-store-source website art (iTunes/Deezer)** — using higher-quality but
  no-store covers for DISPLAY ONLY on the website (never embedded); deliberately left out of the
  committed scope to avoid any ToS ambiguity (CAA + TheAudioDB cover the storage-safe need); a
  possible future display-only enhancement if explicitly chosen.

---

## 14. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md;
detailed Given-When-Then scenarios for the load-bearing requirements are in acceptance.md
Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-TW-001 | Tag Write | High | Ubiquitous | AC-TW-001 |
| REQ-TW-002 | Tag Write | High | Ubiquitous | AC-TW-002 |
| REQ-TW-003 | Tag Write | High | Event | AC-TW-003 |
| REQ-TW-004 | Tag Write | High | Event | AC-TW-004 |
| REQ-TW-005 | Tag Write | High | Unwanted | AC-TW-005 |
| REQ-TW-006 | Tag Write | High | Ubiquitous | AC-TW-006 |
| REQ-TW-007 | Tag Write | High | Event | AC-TW-007 |
| REQ-TW-008 | Tag Write | High | Event | AC-TW-008 |
| REQ-TA-001 | Artwork | High | Ubiquitous | AC-TA-001 |
| REQ-TA-002 | Artwork | High | Event | AC-TA-002 |
| REQ-TA-003 | Artwork | High | Event | AC-TA-003 |
| REQ-TA-004 | Artwork | High | Ubiquitous | AC-TA-004 |
| REQ-TA-005 | Artwork | High | Ubiquitous | AC-TA-005 |
| REQ-TA-006 | Artwork | High | Ubiquitous | AC-TA-006 |
| REQ-TX-001 | Stream/Site Exposure | High | Ubiquitous | AC-TX-001 |
| REQ-TX-002 | Stream/Site Exposure | High | Ubiquitous | AC-TX-002 |
| REQ-TX-003 | Stream/Site Exposure | High | Event | AC-TX-003 |
| REQ-TX-004 | Stream/Site Exposure | Medium | Event | AC-TX-004 |
| REQ-TX-005 | Stream/Site Exposure | High | Ubiquitous | AC-TX-005 |
| REQ-TX-006 | Stream/Site Exposure | Low | Optional | AC-TX-006 |
| NFR-T-1 | Non-Functional | High | Ubiquitous | AC-NFR-T-1 |
| NFR-T-2 | Non-Functional | High | Ubiquitous | AC-NFR-T-2 |
| NFR-T-3 | Non-Functional | High | Ubiquitous | AC-NFR-T-3 |
| NFR-T-4 | Non-Functional | High | Ubiquitous | AC-NFR-T-4 |
| NFR-T-5 | Non-Functional | High | Ubiquitous | AC-NFR-T-5 |
| NFR-T-6 | Non-Functional | High | Ubiquitous | AC-NFR-T-6 |
| NFR-T-7 | Non-Functional | Medium | Ubiquitous | AC-NFR-T-7 |

Parity: 20 REQ + 7 NFR = 27 specified items; 27 acceptance entries (20 AC + 7 AC-NFR); 1:1
REQ↔AC preserved.
