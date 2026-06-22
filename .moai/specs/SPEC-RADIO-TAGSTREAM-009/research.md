# SPEC-RADIO-TAGSTREAM-009 — Research

Codebase + external research grounding the track-tagging, artwork, and listener-exposure
SPEC. This is a short pointer document: the three primary dossiers are large verified JSON
research outputs (each adversarially reviewed by 6-8 agents) — they are the authoritative
source for the capability findings and the concrete implementation plans, and the SPEC's
HARD honesty rails are derived directly from them.

---

## 1. Primary research dossiers (verified, adversarial)

These are the decisive inputs. Read them in full for the concrete plans and the refutation
evidence.

### Dossier A — Tag-writing + live-stream metadata feasibility
Path: `/tmp/claude-1000/-mnt-f-golden-shower-radio/e8ab03c7-aff2-4575-9056-567ac559e45c/tasks/wjkobm6co.output`
- 8 agents, 3 skeptic refutations, 3 verdicts.
- Concrete TAG-WRITING plan (mp3 ID3 + flac Vorbis) with exact mutagen code, value
  derivation (TBPM `round`, TKEY ≤3-char notation, TXXX:EnergyLevel `round(energy*9)+1`,
  TXXX:CAMELOT verbatim), idempotency (`setall`/`delall`+`add`; flac key-replace), ID3v2.3
  recommendation, and per-file batch safety. Confirms `library.json` field names
  (`bpm`/`bpm_confidence`/`musical_key`/`camelot`/`key_confidence`/`energy`/`integrated_lufs`)
  and the 205 mp3 + 78 flac counts, and that `mutagen` is already a read-only dependency.
- VERDICT (decisive): separate sortable BPM/KEY/ENERGY columns over the live MP3/ICY stream
  are IMPOSSIBLE (ICY = one StreamTitle string; MP3 has no per-field channel; foobar2000 does
  not build user columns from a live source). Honest ceiling: file tags (real columns for
  LOCAL playback) + enriched StreamTitle (one string, all players) + website now-playing
  panel (rich per-field display, all listeners). → SPEC REQ-TW-*, REQ-TX-004/005, NFR-T-5.

### Dossier B — Cover-art / artist-image acquisition, embedding, exposure
Path: `/tmp/claude-1000/-mnt-f-golden-shower-radio/e8ab03c7-aff2-4575-9056-567ac559e45c/tasks/wx4zsoxoi.output`
- 6 agents, 2 refutations, 2 verdicts.
- RANKED source chains by STORAGE LEGALITY: embed only from Cover Art Archive (needs a
  MusicBrainz release MBID — currently DISCARDED in `metadata.py` `_extract_year`, lines
  ~501-509, where `rec["release-list"][n]["id"]` should be captured) and TheAudioDB
  (`searchalbum.php`, free-text; only `searchtrack.php` is wired today and returns no art).
  NEVER embed iTunes/Deezer (no-store ToS). Artist images via fanart.tv (artist MBID key +
  attribution) / TheAudioDB → website/sidecar only, never embedded. Skip Last.fm
  (placeholders).
- EMBEDDING plan: raw mutagen `ID3.APIC` / `FLAC.Picture`, front cover (type 3) only,
  idempotent (`setall('APIC')` / `clear_pictures()`), resize ≤600px JPEG q85 (<120KB target,
  >200KB reject), validate real image before embed, per-file try/except, offline batch (not
  on-air). The `easy=True` read path cannot write APIC → separate raw write function; add a
  `has_cover` Track marker.
- VERDICT: artwork cannot ride the live MP3/ICY stream as a rendered image (refuted 2/2). The
  website now-playing `<img>` fed by an `artwork_url` in the now-playing JSON is the reliable
  live-art surface. → SPEC REQ-TA-*, REQ-TX-001/003.

### Dossier C — Can ANY format/protocol/player deliver live fields + art?
Path: `/tmp/claude-1000/-mnt-f-golden-shower-radio/e8ab03c7-aff2-4575-9056-567ac559e45c/tasks/w9dsin9el.output`
- 8 agents, 3 verdicts.
- Full landscape (MP3+ICY / Ogg+Vorbis-comments / HLS-timed-ID3 / custom web player). The
  ONLY path delivering the full goal (structured fields + sortable history columns + rendered
  art) reliably is a JSON-driven WEB now-playing player with the audio stream left at
  `%mp3(320)`. The wiring gap: `set_on_air`/`report_airing` carry only artist/title/kind/path
  — close it by having the brain look up the on-air track BY PATH (the airing POST already
  carries `path`) rather than widening the Liquidsoap report.
- foobar2000-specific: Ogg FLAC gives foobar2000 ≥1.6.1 live cover art (a real, narrow win)
  but NO sortable columns by any means, and per-track updates are fragile (foobar 2.26 turned
  Ogg chaining OFF by default → integration-test required). HLS-timed-ID3 is standards-based
  but web-player-only and buys little over the JSON player. → SPEC REQ-TX-001/002/005/006,
  NFR-T-5; Ogg-FLAC = the gated spike, HLS = future roadmap.

---

## 2. Codebase grounding (read during authoring)

- `brain/library.py` — `Track` dataclass already carries the ANALYSIS-006 features
  (`bpm`/`bpm_confidence`/`musical_key`/`camelot`/`key_confidence`/`energy`/`integrated_lufs`,
  etc.); `Track.key` is the dedup SLUG (NOT a musical key — REQ-AD-005); the read path
  (`_read_tags`) opens files with `MutagenFile(path, easy=True)` (EasyID3) which CANNOT write
  `TKEY`/`TBPM`/`TXXX`/`APIC` → the SPEC's write path uses RAW `mutagen.id3.ID3` /
  `mutagen.flac.FLAC`. The tolerant `_load` / corrupt-tag-swallowing pattern is the model for
  per-file batch safety. The SPEC adds two additive markers (`tagged`, `has_cover`).
- `brain/analyzer.py` — the bounded, serialized, NON-BLOCKING analysis worker (Group AP).
  `Analyzer._analyze_one` ends with `self.library.set_analysis(track.key, record)` — the
  exact attach point for the auto-tag / auto-art hook (REQ-TW-008, REQ-TA-006), inheriting the
  off-pull-path, throttled, per-file-guarded rails.
- `brain/metadata.py` — `_provider_musicbrainz` runs `search_recordings(... limit=1)` and
  `_extract_year` reads `rec.get("release-list")` but mines only `rel["date"]`, DISCARDING
  `rel["id"]` (the release MBID Cover Art Archive needs — REQ-TA-002). `_provider_theaudiodb`
  calls only `searchtrack.php` (no album/artist art) → add `searchalbum.php` /artist lookup.
  These are the OPS-004 REQ-OA-011 shared HTTP clients (reused, not re-owned).
- `brain/server.py` — `_annotate_uri` builds the Liquidsoap annotate URI (carries
  bpm/camelot/energy to the transition function but NEVER promotes them to ICY StreamTitle);
  `_handle_airing` sets ground-truth now-playing from the airing POST (artist/title/kind/path);
  `_handle_nowplaying` returns `{now_playing, recent, library, downloading}`. The enrichment
  (REQ-TX-003) is an additive by-path lookup folded into this handler — no pull-contract change.
- `brain/state.py` — `set_on_air(artist, title, kind, path)` already STORES `path` (line ~90)
  and `now_playing()` returns it → the by-path on-air lookup needs no Liquidsoap change.
- `brain/website.py` — renders `#np-title`/`#np-artist` only (no `<img>`, no fields); `poll()`
  fetches `/api/nowplaying` every 5s. REQ-TX-001/002 add labeled fields + an `<img>` + a
  sortable recent[] table.
- `deploy/config/radio.liq` — `output.icecast(%mp3(bitrate=320), ...)` (line 121-131);
  `report_airing` POSTs only artist/title/kind. PRIMARY path leaves this UNCHANGED; the
  Ogg-FLAC mount (REQ-TX-006) would be a separate, optional, gated mount.

---

## 3. Key decisions (baked into the SPEC as fixed constraints)

1. Write tags + embed art IN PLACE in the 205 mp3 + 78 flac files (destructive, user-confirmed):
   idempotent, per-file try/except, art resized ≤600px JPEG q85 (<120KB target, >200KB reject)
   + validated.
2. Coverage = one-shot BACKFILL now + an auto-hook at end-of-analysis going forward; `tagged`/
   `has_cover` markers skip done files.
3. Tag values: mp3 TBPM (int) / TKEY (≤3-char notation, e.g. "Am") / TXXX:EnergyLevel
   (`round(energy*9)+1`) / TXXX:CAMELOT (verbatim); flac BPM / INITIALKEY / ENERGYLEVEL /
   CAMELOT; ID3v2.3; raw mutagen write path; low-key-confidence gating.
4. Artwork legality is the deciding axis: embed only CAA (release MBID) + TheAudioDB; NEVER
   embed iTunes/Deezer; artist images website-only; front cover only; skip Last.fm.
5. Exposure: PRIMARY = rich JSON-driven website now-playing player (fields + art + sortable
   history), `%mp3(320)` unchanged, wired by by-path on-air lookup. SECONDARY = enriched ICY
   StreamTitle (one string). OPTIONAL/SPIKE = Ogg-FLAC in-band art (foobar2000 live-art win,
   fragility-gated). NON-GOAL = live per-field sortable columns over any stream (impossible).

---

## 4. Boundary vs ANALYSIS-006 (and the others)

ANALYSIS-006 COMPUTES the features (Groups AE/AT/AM) and owns the catalog + the analysis
worker + the ingest scan. TAGSTREAM-009 owns (A) WRITING those features as file tags,
(B) acquiring + EMBEDDING artwork, (C) EXPOSING tags+art to listeners — reading features
storage-agnostically, reusing the OPS-004 HTTP clients, attaching its auto-hook to the
ANALYSIS-006 worker, and consuming KNOWLEDGE-008 `entities.mbid` for artist images — all
referenced by number, never re-owned. RADIO SPEC-IDs are global-incrementing: CORE-001,
VOICE-002, CALLIN-003 (reserved), OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007,
KNOWLEDGE-008, TAGSTREAM-009.

---

## 5. Source URLs (from the dossiers, for implementation reference)

- Foobar2000 ID3 Tag Mapping + Title Formatting + Properties (Hydrogenaudio wiki)
- mutagen docs (quodlibet/mutagen)
- Liquidsoap ICY metadata + encoding formats + HLS output docs; savonet discussions #3990/#4154/#4633
- foobar2000 changelog (1.6.1 internet-radio album art; 2.26 Ogg-chaining-off)
- MusicBrainz Cover Art Archive API; TheAudioDB free API; fanart.tv API; Deezer/Apple Search API ToS
- Mixed In Key energy-level sorting; mp3tag INITIALKEY conversion
- icecast-metadata-js / icecast-metadata-player; foo_artwork; FFmpeg metadata; Mozilla chained-Ogg bug 1417300
(Full lists are in each dossier's `source_urls`.)
