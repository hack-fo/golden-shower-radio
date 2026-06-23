---
id: SPEC-RADIO-SHOWS-020
version: 0.4.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: Medium
issue_number: 20
---

# SPEC-RADIO-SHOWS-020 — Last.fm-Powered Per-Persona Editorial Show-Variation Engine

## HISTORY

- 2026-06-23 (v0.4.0): Additive amendment — GENERALIZED the single-source KEXP human-DJ signal (Group SK)
  into a MULTI-SOURCE layer by adding a SIBLING Requirement Group SM — "Multi-Source Human-DJ Signal"
  (REQ-SM-001…005). SM-001 is a THIN PROVIDER INTERFACE (each provider's `poll()` returns ordered clusters
  in the normalized shape, returns EMPTY on ANY failure, NEVER raises) that GENERALIZES the existing
  `brain/kexp.py` into ONE implementation of the interface — the existing `kexp_thread_enabled` flag stays
  valid and back-compatible — with sibling providers each behind a per-source OFF-by-default flag
  (`sr_thread_enabled` + `bbc_thread_enabled` + `asot_thread_enabled` + `nts_thread_enabled`). SM-002
  enumerates the FIVE sources with access tier + sequence-availability: (A clean keyless APIs, primary
  craft fuel) KEXP `/v2/plays` + Sveriges Radio `api.sr.se` `playlists/getplaylistbychannelid` (P3 id=164,
  song array with `starttimeutc`); (B keyless structured feed) BBC Radio 1 + Radio 1 Dance via
  `/programmes/{PID}/segments.json` (explicit order; skip empty tracklists; ignore key-gated Nitro) AND the
  live BBC DASH stream (`a.files.bbci.co.uk` `.mpd`) as a STREAM-FINGERPRINT mode (in-band now-playing
  metadata if present, else fpcalc rolling windows through the SPEC-RADIO-ENRICH-012 AcoustID→MusicBrainz
  identify pipeline to recover the ordered sequence — heavier, bounded, off-by-default); (C scrape) A STATE
  OF TRANCE via cuenation `.cue` files (ordered + transition timecodes = strongest craft fuel) with
  `astateoftrance.com` numbered-list fallback (1001tracklists only as a throttled Playwright cross-check,
  never primary); (D show-level context + low-confidence archive scrape) NTS `/api/v2/live` (show/host/
  genre/locality CONTEXT only, NOT sequence) + episode-page scrape (low-confidence gappy sequence). SM-003
  is the normalized cluster = the existing SK cluster `{artists, titles, albums, airdate, host_name,
  program_name, provenance}` PLUS additive `source` (`kexp|sr|bbc|asot|nts`) + locality tags (+ optional
  cue-point/timecode metadata from cuenation), provenance method ids
  `kexp.plays`/`sr.playlists`/`bbc.segments`/`bbc.stream`/`asot.cue`/`nts.scrape`. SM-004 [HARD,
  load-bearing] fixes the seam: PER-TRACK ORDERED sequences (KEXP/SR/BBC/cuenation) are craft FUEL while
  SHOW-LEVEL signals (NTS-live) are CONTEXT/labeling ONLY and must NEVER inject phantom transitions — each
  cluster is tagged with `source` + an implied SEQUENCE-CONFIDENCE so the consumer (the Group SX angle
  reasoning REQ-SX-001 + the PROGRAMMING-007 REQ-PC-006 transition generator) weights accordingly. SM-005
  [HARD] makes every provider inherit the Group SK rails per-source BY REFERENCE — REQ-LF-002 (rate/timeout/
  isolation; KEXP/SR ≤ 1 req/s jittered, scrape sources a slower per-source cadence, weekly for ASOT/
  cuenation), SK-002 (cache), REQ-LF-005 / OPS-004 REQ-OH-006 (bounded background job, NEVER on `/api/next`,
  the director tick, or the talk loop), EMPTY-on-failure + OFF-by-default, SK-003 (cluster is a thread
  hypothesis never aired raw, KNOWLEDGE-008 sole airable-fact seam, no source track ever enters rotation,
  REQ-PR-009 unaffected), and SK-004 (per-persona refraction, dropped out-of-lane, never a homogenizer).
  The existing REQ-SK-001…004 + `kexp_thread_enabled` stay valid (back-compatible: KEXP becomes the first
  registered provider). SM is a collision-free prefix across the whole RADIO corpus (STATS-013 uses SR not
  SM; MBMIRROR-017 uses MX; no SM anywhere). NEW REFERENCE: SPEC-RADIO-ENRICH-012 (the AcoustID→MusicBrainz
  identify pipeline the BBC stream-fingerprint mode reuses, never re-owns) is added to the Section 1.4
  REFERENCES block + the Section 2 dependencies. Group SM is registered in the Section-4 group roster and
  inserted after the Group SK block (new Section 6M). Recomputed totals: 29→34 REQ (LF/SK/SG/SX/SP/SD/SB
  unchanged; +SM = 5) + 8 NFR (NFR-S-7 scope extended in place to cover the multi-source provider polls —
  no count change) = 42; 1:1 REQ↔AC preserved (5 new acceptance entries: AC-SM-001…005, + a new Section B
  scenario B12). PROGRAMMING-007 / KNOWLEDGE-008 / ENRICH-012 / OPS-004 are referenced only, never edited.
- 2026-06-23 (v0.3.0): Two additive amendments — (1) EXTENDED REQ-SD-005 (the per-persona forward
  "planned shows" queue) so a queue ENTRY MAY OPTIONALLY carry an `episode_id` + `part_number` + `series_arc_id`
  (a pure additive field extension on the queue entry — the per-session `Show` model REQ-SG-001 is UNTOUCHED,
  the novelty check REQ-SX-002 is UNCHANGED, and the fields are INERT in SHOWS-020 single-session operation).
  These optional fields are the FORWARD-REFERENCE seam a future multi-session SPEC consumes: SPEC-RADIO-LONGFORM-025
  Group LB (not yet authored; the seam is recorded so the queue is not later forked) reads the REQ-SX-002 novelty
  ledger + the REQ-SG-005 show history and the episode/part/arc fields to thread multi-part series across sessions.
  (2) ADDED a NEW Requirement Group SK — "KEXP Human-DJ Thread Signal" (REQ-SK-001…004), a SIBLING to the Group LF
  Last.fm research client: a keyless, fully-graceful, OFF-by-default `brain/kexp.py` that polls the public no-auth
  KEXP API v2 `/v2/plays/?ordering=-airdate`, walks the show FK to assemble short back-to-back human-DJ track
  CLUSTERS keyed on one show/host session, and hands each cluster to the LLM as a THREAD HYPOTHESIS — colour to
  reason about, NEVER voiced raw — that seeds a REQ-SX-001 angle or a PROGRAMMING-007 REQ-PC-006 transition idea,
  then passes the SAME taste/novelty/anti-convergence gates as any angle (one shared signal refracted divergently
  per persona, never a homogenizer). SK reuses REQ-LF-002 (rate/timeout/isolation), REQ-LF-004 (provenance shape,
  `method=kexp.plays`), REQ-LF-005 (bounded background job), and REQ-LF-006 (research-lead-never-aired-raw) BY
  REFERENCE and rides the existing NFRs (NFR-S-1/S-4/S-5/S-7; KEXP is keyless so NFR-S-8's Last.fm-ToS clauses do
  not apply to it, only the polite-rate / identifiable-User-Agent posture is shared). The SK prefix is collision-free
  across the whole RADIO corpus (STATS-013 = SA/SE/SI/SR/SV/SW; SHOWS-020 = SG/SX/SP/SD/SB; KNOWLEDGE-008 =
  KS/KF/KR/KG/KI — no SK anywhere). Group SK is registered in the Section-4 group roster and inserted after the
  Group LF block (new Section 6K). Recomputed totals: 25→29 REQ (LF/SG/SX/SP/SD/SB unchanged; +SK = 4) + 8 NFR
  (unchanged) = 37; 1:1 REQ↔AC preserved (4 new acceptance entries: AC-SK-001…004; AC-SD-005 extended in place with
  the episode/part/arc additive rows). PROGRAMMING-007 is referenced only (REQ-PC-006 / REQ-PR-004 / REQ-PR-009 /
  REQ-PL-004), never edited.
- 2026-06-23 (v0.2.0): Amendment incorporating the verified Last.fm API research artifact (`research.md`,
  fetched + checked against the official Last.fm docs 2026-06-23) and resolving the five open decisions as
  DECIDED orchestrator rulings. Changes: (1) cited `research.md` as the SPEC's research artifact in the
  Overview + the Group LF discussion; aligned the Group LF method surface with the no-auth read methods
  research verified (the existing `artist.getInfo`/`getSimilar`/`getTopTags` / `tag.getTopArtists` /
  `track.getInfo` are all confirmed no-auth, broadened to the verified no-auth research set —
  `track.getSimilar`, `tag.getInfo`, `tag.getSimilar`, `tag.getTopTracks`, `chart.*`, `geo.*` — and
  explicitly excluded the `user.*` / `auth.*` / write surface that needs a signed session); folded the
  research's rate-limit + ToS caveats into the Constraints + a new NFR-S-8 (Last.fm ToS compliance:
  caching-is-required, 100 MB Reasonable-Usage cap, non-commercial / research-input-only, attribution if
  ever surfaced, polite ≤1 req/s under the community 5/s ceiling, error-29/16 backoff). (2) Resolved
  D-S-1…D-S-5 as DECIDED in a new Section 14 "Decisions (resolved 2026-06-23)" and sharpened the affected
  REQs: D-S-1 = ship now in single-default-persona mode (variation engine is roster-independent;
  per-persona distinctness activates with the PROGRAMMING-007 roster, no SHOWS-020 change); D-S-2 = thread
  the active show's `selection_lens` into curation as a NON-BINDING bias (like `seed_reference`), not a
  director rewrite; D-S-3 = a SEPARATE `brain/lastfm.py` research module sharing the key + rate-limit /
  exception discipline, not an extension of `brain/metadata.py`'s consensus; D-S-4 = a deterministic
  text-similarity novelty check for v1 (LLM-judged escalation optional later); D-S-5 = KNOWLEDGE-008 is
  the single home for AIRABLE Last.fm-derived facts (Last.fm research is show-DESIGN material until
  grounded). (3) Made the broadened use cases EXPLICIT: ARTIST FACTS (Last.fm `artist.getInfo` /
  `track.getInfo` as research LEADS, never aired raw, grounded through KNOWLEDGE-008 per D-S-5 →
  REQ-LF-006), "LAST SHOWS" (the durable per-persona show-HISTORY ledger we persist; Last.fm has no
  events API — it was retired 2016 — so show history is OUR data → REQ-SG-005), and "PLANNED SHOWS" (the
  per-persona FORWARD schedule of planned show CONTENT we persist; also OUR data, distinct from the
  OPS-004/ORCH-005 time-grid → REQ-SD-005). Recomputed totals: 22→25 REQ (LF 5→6, SG 4→5, SD 4→5; SX/SP/SB
  unchanged) + 7→8 NFR = 33; 1:1 REQ↔AC preserved (4 new acceptance entries: AC-LF-006, AC-SG-005,
  AC-SD-005, AC-NFR-S-8).
- 2026-06-23 (v0.1.0): Initial draft, occupying the new global-incrementing SHOWS-020 id. The
  twentieth authored SPEC in the golden-shower-radio RADIO series and the EDITORIAL SHOW-VARIATION
  subsystem of the autonomous AI radio station. It answers the verbatim user directive (feature
  backlog 2026-06-23): "Wire and make use of Last.fm API to research music, bands and producers. This
  is particularly useful for the creation of new shows for each host, so that you do not run the same
  kind of show week after week but have variations, come up with new editorial angles/themes/ideas
  continuously. Remember we have different radio hosts, with different personas, playing different kinds
  of music - just like real world radio stations we do not play the same things week after week."
  RADIO SPEC-IDs are GLOBAL-INCREMENTING (CORE-001, VOICE-002, CALLIN-003, OPS-004, ORCH-005,
  ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009, IMAGING-010, REQUEST-011, STATS-013,
  DEDUP-014, LIKE-015, HOSTCTX-016, MBMIRROR-017, WEBUI-018, ACQQUEUE-019, SHOWS-020 = this).
  Where SPEC-RADIO-CORE-001 owns the music engine + library store + the LLM program-director loop
  (`brain/director.py`, REQ-D-006/007) + the self-controlled website; SPEC-RADIO-ANALYSIS-006 owns the
  per-track genre/feature substrate + the Group AM metadata enrichment (`brain/metadata.py`, which
  ALREADY carries a key-gated Last.fm provider path for `track.getTopTags`); SPEC-RADIO-PROGRAMMING-007
  owns the persona ROSTER + per-persona taste charters + the anti-convergence firewall (Group PR), the
  show FORMATS / recurring-segment skeletons (Group PT), the per-persona evolving TASTE PROFILE +
  acquisition diary + grab-reason (Group PL), and the grounded-voice fact contract + quality gate
  (Group PG); SPEC-RADIO-KNOWLEDGE-008 owns the dated, sourced, freshness-gated artist/music KNOWLEDGE
  GRAPH; SPEC-RADIO-HOSTCTX-016 owns the PER-SONG host facts (year/album/curiosa); and
  SPEC-RADIO-OPS-004 / SPEC-RADIO-ORCH-005 own the SCHEDULER / dayparting / world-model director —
  SHOWS-020 owns the SHOW-VARIATION ENGINE that sits ABOVE HOSTCTX-016 (per-song facts) and BELOW the
  director: (LF) a richer, key-gated, rate-limited, exception-isolated Last.fm RESEARCH client
  (`artist.getInfo` / `artist.getSimilar` / `artist.getTopTags` / `tag.getTopArtists` /
  `track.getInfo`) that COMPLEMENTS — never duplicates — the existing ANALYSIS-006 enrichment provider
  and the MBMIRROR-017 / KNOWLEDGE-008 fact ownership; (SG) a per-persona SHOW / PROGRAM data model (an
  editorial angle/theme + a track-selection lens + talking points the host runs for one session/slot);
  (SX) the CORE ask — continuous EDITORIAL VARIATION: generate FRESH show angles grounded in Last.fm
  research + the persona's taste, and AVOID repeating the same kind of show over a configurable recent
  window; (SP) PER-PERSONA distinctness so each host's shows stay in its own voice and the roster never
  converges; (SD) SCHEDULING/DIRECTION wiring so an active show drives the curation + talk layers (feeds
  `brain/director.py`'s wishlist + the talk themes) WITHOUT ever blocking playout, and so the director
  decides when no host is scheduled; (SB) the BRAIN-ONLY additive wiring into the existing
  `brain/director.py` curation tick + the `brain/talk.py` talk-context assembly + `brain/config.py`
  knobs. It uses a DISTINCT REQ namespace — LF (Last.fm research), SG (show/program model), SX (show
  variation / anti-repetition), SP (per-persona distinctness), SD (scheduling/direction), SB (show
  wiring) — chosen to avoid collision with CORE (A-E + D), VOICE (V-A…V-F), CALLIN
  (CT/CL/CD/CM/CC/CF/CS/CG), OPS (OA/OB/OC/OD/OE/OF/OG/OH/OX/OY), ORCH (RL/RW/RE/RC/RD/RA/RN/RI),
  ANALYSIS (AE/AT/AM/AD/AP), PROGRAMMING (PR/PC/PS/PT/PL/PG/PV/PI), KNOWLEDGE (KS/KF/KR/KG/KI), TAGSTREAM
  (TW/TA/TX), IMAGING (IG/IB/IP/IL/IS/IH/IX), REQUEST (RQ/RM/RA/RWL/RS/RV/RD), STATS
  (SA/SE/SI/SR/SV/SW + AD/AT/OA/PL refs), DEDUP, LIKE (LH/LD/LS/LA/LP/LX), HOSTCTX (HY/HC/HD/HW),
  MBMIRROR (MX), WEBUI (WV/WP/WA/WS), and ACQQUEUE (Q*). NOTE: STATS-013 already uses SV + SW; SHOWS-020
  therefore uses SX (not SV) for variation and SB (not SW) for wiring — the two no longer share a
  prefix. NOTE: the v0.4.0 multi-source group uses SM, collision-free across the whole corpus (STATS-013
  uses SR -- Sveriges Radio appears here only as the `sr_thread_enabled` CONFIG flag, NOT a REQ prefix;
  MBMIRROR-017 uses MX; no SM anywhere). Grounded in the existing code: `brain/config.py` already declares `lastfm_api_key` (optional,
  empty default) and `brain/metadata.py` already has a key-gated/log-once/exception-isolated Last.fm
  provider; the persona roster is GREENFIELD (PROGRAMMING-007 Group PR specifies it but the talk layer
  in `brain/llm.py` still uses a single generic HOST_PERSONA) — see Section 2. The Last.fm capability surface is grounded in the
  companion `research.md` (verified against the official Last.fm API docs 2026-06-23). Total (as of
  v0.4.0): 34 REQ + 8 NFR = 42, 1:1 REQ-AC (LF=6, SK=4, SM=5, SG=5, SX=4, SP=3, SD=5, SB=2).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "research the music, and stop running the same show every week"

The station can play continuously (CORE-001), talk in personas (VOICE-002, PROGRAMMING-007), program
itself (OPS-004), perceive its music (ANALYSIS-006), know facts about artists (KNOWLEDGE-008), say
something nice per song (HOSTCTX-016), and grow its library (REQUEST-011, ACQQUEUE-019). What it does
NOT yet do is the thing a real radio station does every week: have each host run a DIFFERENT show —
a fresh editorial angle, a new theme, a different lens on the music — instead of an endless, undifferentiated
shuffle. Today `brain/director.py` calls a single flat `llm.curate_batch` with a generic curator persona
and a "recently played, avoid these" list; there is NO show structure, NO per-host program, and NO
mechanism that varies the editorial angle from one session to the next.

This SPEC adds exactly that, and the research substrate that fuels it. The user named the engine: wire
Last.fm to research music/bands/producers so the AI can keep inventing new shows for each host. The two
asks are one feature: Last.fm research is the FUEL, and per-persona editorial show-variation is the
ENGINE that burns it.

[HARD] The Last.fm capability surface this SPEC relies on is grounded in the companion **`research.md`**
(this SPEC's research artifact — a factual study of the Last.fm Web API verified against the official
Last.fm documentation, fetched 2026-06-23). `research.md` establishes the load-bearing facts this SPEC
builds on: (a) the read methods SHOWS-020 needs require ONLY an `api_key` — no OAuth, no session, no
signature (read-only auth, `research.md` §2–§3.1); (b) Last.fm is the TASTE / TAG / SIMILARITY /
POPULARITY layer, NOT a canonical-fact source — facts/credits/identity stay with MusicBrainz
(MBMIRROR-017) / Discogs / KNOWLEDGE-008, and Last.fm bios/wikis are crowd-sourced and unsourced
(`research.md` §5b, §6); (c) the events/gigs API was RETIRED in Last.fm's March-2016 relaunch, so
"last shows" and "planned shows" CANNOT come from Last.fm and are OUR OWN persisted data
(`research.md` §4, §5c–d); and (d) the ToS imposes real constraints — caching is required, a 100 MB
Reasonable-Usage cap, a non-commercial / research-input-only restriction, attribution if Last.fm data is
ever surfaced, and a polite rate ceiling (`research.md` §3). These facts are reflected directly in the
requirements (Group LF), the Constraints (Section 5), and NFR-S-8.

### 1.2 The anti-repetition / per-persona-distinctness spine (the load-bearing idea)

[HARD] The single design decision that makes this SPEC deliver on the user's intent is this: **a show is
a per-persona editorial PLAN (theme + selection lens + talking points) whose ANGLE must be NOVEL against
that persona's own recent shows over a configurable window — and the engine REFUSES to re-run a recent
kind of show.** Two properties fall out of this one rule:

- It defeats **show-sameness** ("the same kind of show week after week"): each new show angle is checked
  against a per-persona recent-shows ledger; an angle too similar to a recent one is rejected and the
  LLM is asked again, grounded in fresh Last.fm research, so variation is structural, not hoped-for.
- It preserves **per-persona distinctness** ("different hosts, different personas, different music"): a
  show is generated IN the persona's own taste/voice and stays inside its territory; the engine never
  homogenizes the roster, and one host's show angle is never reused for another (it inherits
  PROGRAMMING-007's anti-convergence firewall, REQ-PR-004, rather than re-owning it).

This SPEC inherits the station philosophy verbatim (no pandering / no appeal-maximization; the host
decides with full creative autonomy; grounded, never confidently-wrong). Show angles are EDITORIAL
INVENTION grounded in real research, never engagement-optimized themes; the engine guarantees variation
and groundedness, never a target audience-reaction.

### 1.3 What this layer is, concretely

- A LAST.FM RESEARCH CLIENT (Group LF): a richer, key-gated, rate-limited, exception-isolated Last.fm
  client exposing `artist.getInfo` (bio/listeners/tags), `artist.getSimilar` (neighbours),
  `artist.getTopTags`, `tag.getTopArtists` (theme → artist discovery), and `track.getInfo` — with
  per-field provenance. It COMPLEMENTS the existing ANALYSIS-006 `brain/metadata.py` Last.fm provider
  (which does only `track.getTopTags` for genre consensus) and the MBMIRROR-017 / KNOWLEDGE-008 fact
  ownership; it never re-derives genre consensus or re-owns artist facts. With no `lastfm_api_key` it
  degrades cleanly: the research client returns empty, the show engine falls back to taste-only angles,
  and the station is completely unaffected.
- A KEXP HUMAN-DJ THREAD SIGNAL (Group SK): a SECOND, optional, keyless, OFF-by-default research client
  (`brain/kexp.py`, sibling to `brain/lastfm.py`) that polls the public no-auth KEXP API v2 plays feed and
  assembles short back-to-back human-DJ track CLUSTERS (one show/host session) as THREAD HYPOTHESES — colour the
  LLM reasons about to seed a fresh show angle (Group SX) or a PROGRAMMING-007 REQ-PC-006 transition idea. It is
  treated exactly like a Last.fm artist-fact research lead (REQ-LF-006): never voiced raw, the station plays only
  its OWN catalog, KEXP track ids never enter rotation (REQ-PR-009 unaffected), and a KEXP-seeded angle passes the
  same per-persona taste / novelty / anti-convergence gates as any other (one shared signal refracted divergently,
  never a homogenizer). Disabled or failing, it is simply absent and Group SX falls back to Last.fm + taste-only
  angles.
- A MULTI-SOURCE HUMAN-DJ SIGNAL LAYER (Group SM): a THIN PROVIDER INTERFACE that GENERALIZES the
  single-source KEXP client (Group SK / `brain/kexp.py`) into a registry of human-DJ signal providers. Each
  provider's `poll()` returns ordered clusters in one normalized shape, returns EMPTY on ANY failure, and
  NEVER raises; each sibling provider is behind a per-source OFF-by-default flag (`kexp_thread_enabled`
  [existing, back-compatible] + `sr_thread_enabled` + `bbc_thread_enabled` + `asot_thread_enabled` +
  `nts_thread_enabled`). FIVE sources are wired by access tier + sequence-availability: KEXP `/v2/plays` and
  Sveriges Radio `api.sr.se` (clean keyless APIs, per-track ordered, primary craft fuel); BBC Radio 1 + Radio
  1 Dance `/programmes/{PID}/segments.json` and the live BBC DASH `.mpd` stream-fingerprint mode (keyless
  structured feed / heavier identify pass via SPEC-RADIO-ENRICH-012); A STATE OF TRANCE via cuenation `.cue`
  files with transition timecodes (scrape; strongest craft fuel) + an `astateoftrance.com` numbered-list
  fallback and a throttled 1001tracklists cross-check; and NTS `/api/v2/live` (show/host/genre/locality
  CONTEXT only, NOT sequence) + a low-confidence episode-page scrape. [HARD] PER-TRACK ORDERED sequences are
  craft FUEL; SHOW-LEVEL signals (NTS-live) are CONTEXT/labeling ONLY and never inject phantom transitions —
  each cluster carries a `source` + a sequence-confidence the consumer weights by. Every provider inherits the
  Group SK rails per-source by reference (rate/timeout/isolation, cache, bounded background job off the pull
  path, EMPTY-on-failure + OFF-by-default, never-aired-raw, per-persona refraction). KEXP is simply the first
  registered provider; the existing Group SK requirements stay valid.
- A SHOW / PROGRAM MODEL (Group SG): a typed `Show` record — `persona_id`, an editorial `theme` /
  `angle`, a `selection_lens` (the catalog filter/biasing rule that picks tracks for the show — genre /
  era / mood / similarity-neighbourhood / tag), `talking_points` (grounded research notes the host MAY
  voice), provenance (which research backed it), a `created_at`, and a `status` lifecycle. It persists
  in the existing store seam alongside the other JSON/SQLite stores; it does NOT fork the library.
- THE EDITORIAL VARIATION ENGINE (Group SX): the core ask. The LLM PROPOSES a fresh show angle for a
  persona, GROUNDED in Last.fm research + the persona's taste profile, the proposal is checked for
  NOVELTY against a per-persona recent-shows ledger over a configurable window, and a too-similar angle
  is rejected/regenerated so the station does not run the same kind of show repeatedly. Angles are
  invented continuously, never templated.
- PER-PERSONA DISTINCTNESS (Group SP): each persona generates shows in its OWN taste/voice/territory;
  the engine consumes the PROGRAMMING-007 persona roster + taste charter + anti-convergence firewall
  rather than re-owning them, and never converges two personas onto the same angle/territory.
- SCHEDULING / DIRECTION (Group SD): an active show DRIVES the curation + talk layers — its selection
  lens biases `brain/director.py`'s curation/wishlist (as a non-blocking input, exactly like the
  existing seed_reference) and its theme + talking points flow into `brain/talk.py`'s talk context — and
  when no host is scheduled the LLM director decides the show itself (consistent with HOSTCTX-016
  director discretion). It NEVER blocks or stalls playout.
- BRAIN-ONLY WIRING (Group SB): the engine attaches to the EXISTING `brain/director.py` tick + the
  EXISTING `brain/talk.py` `_build_context` assembly + new `brain/config.py` knobs; no new service, no
  store fork, never on the sub-1s `/api/next` pull path.

### 1.3a The broadened use cases, made explicit (research-driven)

Beyond show-variation, the user named three concrete uses of the Last.fm research substrate. Each is made
explicit here and bound to a requirement; per `research.md` two of them are NOT Last.fm features at all but
OUR OWN persisted data.

- **ARTIST FACTS (research LEADS, never aired raw).** `artist.getInfo` / `track.getInfo` supply bio
  context, tags, and relative popularity as colour for host talk. [HARD] Per `research.md` §5b these are
  crowd-sourced and unsourced, so they are RESEARCH LEADS — a Last.fm fact is something to LOOK UP, not to
  broadcast. An artist fact becomes AIRABLE only after it lands as a KNOWLEDGE-008 dated/sourced fact and
  passes the PROGRAMMING-007 grounding gate UNCHANGED (D-S-5). This is owned by REQ-LF-006 (the research
  lead) feeding REQ-SG-004 / REQ-SD-003 (the airing gate); KNOWLEDGE-008 is the single home for airable
  Last.fm-derived facts.
- **"LAST SHOWS" (our per-persona show HISTORY).** Last.fm cannot tell us what shows a persona has run —
  its events API was retired in 2016 (`research.md` §4, §5c) and it has no concept of our personas. The
  record of which shows ran is OUR durable per-persona show-history (the same store that feeds the
  novelty ledger, framed as history). Owned by REQ-SG-005 (built on the typed Show record REQ-SG-001 + the
  status lifecycle REQ-SG-002 + the recent-shows ledger REQ-SX-002).
- **"PLANNED SHOWS" (our per-persona FORWARD schedule).** The forward queue of upcoming planned show
  CONTENT for a persona is likewise OUR data (`research.md` §5d); Last.fm contributes only the research
  that shapes each planned show. This is a per-persona forward schedule the engine persists and the
  director consumes — DISTINCT from the OPS-004/ORCH-005 time-grid (which owns WHEN a slot occurs +
  WHICH persona is on-air). Owned by REQ-SD-005.

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] SHOWS-020 OWNS the show-variation engine: the Last.fm RESEARCH client, the show/program data
model, the editorial-variation (novelty) engine, the per-persona-distinctness application, the
show-drives-curation/talk wiring, and the brain-only integration. It MUST NOT restate, fork, or weaken
any CORE-001, VOICE-002, ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, HOSTCTX-016, MBMIRROR-017, or
OPS-004/ORCH-005 requirement, and it MUST NOT re-own the persona roster, the taste profile, the
anti-convergence firewall, the genre consensus, the artist/music fact graph, the per-song host facts,
the scheduler, or the picker/playout chain — it CONSUMES them.

OWNS:
- The LAST.FM RESEARCH CLIENT: a key-gated, rate-limited, exception-isolated client (the SEPARATE
  `brain/lastfm.py` module, D-S-3) over the verified no-auth read surface — `artist.getInfo` /
  `artist.getSimilar` / `artist.getTopTags` / `artist.getTopTracks`, `track.getInfo` / `track.getSimilar`,
  `tag.getInfo` / `tag.getSimilar` / `tag.getTopArtists` / `tag.getTopTracks`, and `chart.*` / `geo.*`
  (all confirmed key-only, no signed session, in `research.md` §2) — with per-field provenance, supplying
  SHOW-DESIGN research material (bio context, similar artists, theme→artist discovery, tags, time-varying
  + region trends). It is a NEW research surface DISTINCT from the ANALYSIS-006 Last.fm GENRE-CONSENSUS
  provider (Group LF). It also supplies ARTIST-FACT research LEADS (`artist.getInfo`/`track.getInfo`) that
  are aired only via KNOWLEDGE-008 (REQ-LF-006).
- The KEXP HUMAN-DJ THREAD SIGNAL (Group SK): the SEPARATE, keyless, OFF-by-default `brain/kexp.py` client
  (sibling to `brain/lastfm.py`) over the public no-auth KEXP API v2 plays feed, the back-to-back human-DJ
  CLUSTER assembly (one show/host session), and the cluster-as-thread-hypothesis seam that seeds a Group SX angle
  or a PROGRAMMING-007 REQ-PC-006 transition idea — treated exactly like a Last.fm research lead (REQ-LF-006,
  never voiced raw; KNOWLEDGE-008 stays the sole airable-fact seam), with KEXP picks NEVER copied into rotation
  (the station plays only its own catalog; REQ-PR-009 unaffected) and KEXP-seeded angles passing the same
  taste/novelty/anti-convergence gates (Group SK). SHOWS-020 reuses REQ-LF-002/004/005/006 by reference, never
  re-owning them.
- The MULTI-SOURCE HUMAN-DJ SIGNAL LAYER (Group SM): the THIN PROVIDER INTERFACE that generalizes Group SK
  (`brain/kexp.py` becomes the first registered provider, back-compatible) into a registry of human-DJ signal
  providers (`poll()` returns ordered clusters in the normalized shape, EMPTY on any failure, never raises);
  the FIVE enumerated sources with their access tier + sequence-availability (KEXP, Sveriges Radio, BBC
  segments + DASH stream-fingerprint, A State of Trance / cuenation, NTS); the normalized cluster shape (the
  SK cluster + additive `source` + locality tags + optional cue-point/timecode); the per-track-ordered =
  FUEL vs show-level = CONTEXT-ONLY classification with a per-cluster sequence-confidence; and the per-source
  inheritance of the Group SK rails. SHOWS-020 reuses REQ-LF-002/004/005 + REQ-SK-002/003/004 by reference
  and REFERENCES SPEC-RADIO-ENRICH-012's identify pipeline for the BBC stream-fingerprint mode; it re-owns
  none of them (Group SM).
- The SHOW / PROGRAM data model: the typed `Show` record, its selection-lens semantics, talking-points,
  provenance, and status lifecycle; the durable per-persona show-HISTORY ("last shows", REQ-SG-005); and
  where it all persists (Group SG).
- The EDITORIAL VARIATION engine: the LLM-proposes-grounded-angle flow, the per-persona recent-shows
  ledger, the novelty check over a configurable window, and the reject-and-regenerate-a-too-similar-angle
  discipline — the anti-show-sameness invariant (Group SX).
- The PER-PERSONA distinctness APPLICATION: that each show is generated in its persona's taste/voice and
  the engine never converges the roster (it consumes, not re-owns, the PROGRAMMING-007 firewall)
  (Group SP).
- The SHOW-DRIVES-CURATION/TALK wiring: how an active show biases the director's curation/wishlist (a
  non-blocking input) and feeds the talk theme + talking points, the director-decides-when-unhosted
  fallback, and the per-persona FORWARD "planned shows" schedule the engine persists + the director
  consumes (REQ-SD-005), including the OPTIONAL `episode_id` / `part_number` / `series_arc_id` queue-entry
  fields that are inert here and consumed by the future SPEC-RADIO-LONGFORM-025 Group LB (Group SD).
- The BRAIN-ONLY integration: the additive attachment to `brain/director.py` + `brain/talk.py` +
  `brain/config.py`; no new service/store fork; never on the pull path (Group SB).

REFERENCES (consumes / feeds; does not restate):
- **CORE-001 REQ-D-006/007 (the LLM director loop + self-initiated cadence) + `brain/director.py`** —
  the show engine attaches to the existing director tick; an active show's selection lens biases the
  curation batch as a NON-BINDING input (exactly as `seed_reference` already is). SHOWS-020 does not
  re-own the director loop or the picker.
- **ANALYSIS-006 Group AM (`brain/metadata.py`) + REQ-AM-003 (genre consensus) + the existing Last.fm
  `track.getTopTags` provider** — the show engine's Last.fm RESEARCH client is SEPARATE from the
  genre-consensus provider; it does not re-derive genre consensus and does not change `enrich()`.
  Show track-selection reads the ANALYSIS-006 per-track genre/feature data; it does not re-own it.
- **PROGRAMMING-007 Group PR (persona roster + taste charter + REQ-PR-004 anti-convergence firewall) +
  REQ-PR-009 (per-track cross-show rotation EXCLUSIVITY) + REQ-PL-004 (per-persona evolving taste profile) +
  REQ-PC-006 (theme/thread generators) + Group PT (show FORMATS / recurring skeletons) + Group PG
  (grounded-voice fact contract + quality gate)** — a show is generated FOR a roster persona, IN its taste
  profile, INSIDE the firewall, and any spoken talking point is grounded + gate-validated by Group PG unchanged.
  A KEXP-thread hypothesis (Group SK) may seed a fresh show angle OR feed PROGRAMMING-007's REQ-PC-006
  theme/thread generator as a transition idea; KEXP picks never enter rotation, so the REQ-PR-009 per-track
  exclusivity rule is UNAFFECTED (the station plays only its own catalog). SHOWS-020 references all of these by
  id; it does not re-own the roster, the taste profile, the firewall, the per-track exclusivity rule, the
  theme/thread generator, the show-format skeletons, or the grounding/gate. [HARD][GREENFIELD] The persona roster
  (Group PR) is specified but not yet built (the talk layer still uses one generic HOST_PERSONA) — see Section 2 +
  the degraded mode (REQ-SP-001, AC Section B).
- **KNOWLEDGE-008 (artist/music KNOWLEDGE GRAPH, dated/sourced/freshness-gated facts) + the grounding
  feed (REQ-KI-001)** — researched ARTIST FACTS that become airable talking points are OWNED by
  KNOWLEDGE-008. SHOWS-020's Last.fm research material that is to be SPOKEN flows into a talking point
  only as a grounded fact; the engine does NOT open a parallel unvalidated trivia channel (it mirrors
  HOSTCTX-016 REQ-HW-003: one fact-supply seam). Last.fm research used purely for SHOW DESIGN (selecting
  tracks, choosing a theme) is internal planning material, not an airable fact.
- **HOSTCTX-016 (per-song year/album/curiosa) + the talk-context assembly (`brain/talk.py`
  `_build_context` / `_attach_grounding`)** — SHOWS-020 sits ABOVE HOSTCTX-016: HOSTCTX adds PER-SONG
  facts; SHOWS adds the PER-SESSION show theme + talking points to the SAME context dict. SHOWS-020 adds
  show-level keys to the existing bundle; it does not fork the per-song fact wiring.
- **MBMIRROR-017 (self-hosted MusicBrainz + Discogs/Last.fm cross-check)** — the heavier research /
  cross-check infrastructure. SHOWS-020's Last.fm client is the LIGHT, direct research path for show
  design; where richer cross-checked facts are needed they come via KNOWLEDGE-008 over MBMIRROR-017.
  SHOWS-020 does not re-own the mirror or its clients.
- **SPEC-RADIO-ENRICH-012 (AcoustID -> MusicBrainz identify pipeline; referenced code-seam)** — the
  Group SM BBC DASH stream-fingerprint mode (REQ-SM-002) recovers an ordered now-playing sequence by running
  fpcalc rolling windows through the ENRICH-012 AcoustID -> MusicBrainz identify pipeline WHEN no in-band
  now-playing metadata is present. SHOWS-020 CONSUMES that pipeline by reference (heavier, bounded,
  off-by-default behind `bbc_thread_enabled`) and does NOT re-own or fork the identify logic; it stays
  ENRICH-012's. This is a heavier, last-resort path within the BBC provider, not the default.
- **OPS-004 Group OA (dayparting / scheduler) + ORCH-005 (world-model director)** — WHEN a show runs and
  WHICH persona is on-air is the scheduler's/director's call; SHOWS-020 supplies the show CONTENT and
  states that show selection is in scope for that discretion, and that the director decides when no host
  is scheduled. It does not fork the schedule store.
- **OPS-004 REQ-OH-006 (bounded-job throttle)** — the Last.fm research + show-planning work, the Group SK
  KEXP poll, AND every Group SM multi-source provider poll, adopt the bounded/throttled background pattern;
  referenced, not re-owned.
- **SPEC-RADIO-LONGFORM-025 Group LB (FORWARD reference; not yet authored)** — the future multi-session
  long-form / series subsystem CONSUMES the SHOWS-020 seams: the REQ-SX-002 per-persona novelty ledger, the
  REQ-SG-005 show history, and the OPTIONAL `episode_id` / `part_number` / `series_arc_id` fields on the
  REQ-SD-005 planned-shows queue entry. SHOWS-020 records this seam (the optional fields are inert here) so the
  queue is not later forked; LONGFORM-025 owns the multi-session threading, SHOWS-020 stays single-session.

### 1.5 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 Section 1.3 and the sibling SPECs' autonomy principle in intent and does NOT
redefine it. The AI decides, with full creative freedom, WHAT show each host runs, WHICH editorial angle,
WHICH tracks the lens selects, and WHAT to say — exactly as a smart human programmer + DJ would, inventing
fresh shows continuously. What is NOT the AI's call, and what this SPEC fixes as hard rails, is: research
is key-gated and never blocks; a show angle MUST be novel against the persona's recent shows; a show is
per-persona and the roster never converges; a spoken talking point is grounded or unsaid; and nothing ever
stalls or silences playout. The windows, cadence, and novelty thresholds are TUNABLE config; the
requirement guarantees only that shows vary, stay per-persona, and stay grounded.

### 1.6 Fixed engineering rails (the only hard constraints)

- **Last.fm is key-gated + fully graceful without a key.** [HARD] The research client runs ONLY when
  `lastfm_api_key` is set; with no key it logs once and returns empty, the show engine falls back to
  taste-only angles, and the station is unaffected (mirrors the existing `brain/metadata.py` behaviour)
  (REQ-LF-001, NFR-S-1).
- **Research is rate-limited + exception-isolated + never blocks.** [HARD] Every Last.fm call has an
  explicit timeout, is rate-limited, and is exception-isolated (returns empty on ANY error); research +
  show-planning run as a bounded background job, never on the `/api/next` pull path (REQ-LF-002,
  REQ-SB-002, NFR-S-1/S-5).
- **Complement, don't duplicate, ANALYSIS-006 + MBMIRROR-017 + KNOWLEDGE-008.** [HARD] The Last.fm
  research client is SEPARATE from the ANALYSIS-006 genre-consensus provider, does not re-derive genre
  consensus, and does not re-own artist facts (those are KNOWLEDGE-008's over MBMIRROR-017); each is
  referenced (REQ-LF-003, NFR-S-4).
- **A show angle must be NOVEL against the persona's recent shows.** [HARD] The variation engine rejects
  a proposed angle too similar to one this persona ran within the configurable window and regenerates,
  so the station does not run the same kind of show repeatedly (REQ-SX-001/002, NFR-S-2).
- **A show is grounded.** [HARD] A show angle and its talking points are grounded in supplied research +
  the persona's taste; a SPOKEN talking point is a grounded fact validated by the PROGRAMMING-007 gate
  exactly like any other host fact — never invented (REQ-SX-003, REQ-SD-003, NFR-S-3).
- **Per-persona distinct; the roster never converges.** [HARD] Shows are generated per-persona in their
  own taste/voice and obey the PROGRAMMING-007 anti-convergence firewall (REQ-PR-004) unchanged; one
  persona's angle is never reused for another (REQ-SP-001/002, NFR-S-6).
- **A show biases, never forces; never a jukebox of the picker.** [HARD] An active show's selection lens
  is a NON-BINDING bias on the curation/wishlist input (like `seed_reference`); it never force-inserts
  tracks, never overrides rotation/clock/no-repeat, and the picker keeps full autonomy (REQ-SD-001,
  NFR-S-5).
- **Director decides when unhosted.** [HARD] When no host is scheduled the LLM director chooses the show
  itself, under the same rails (grounded, novel, never-blocks) — consistent with HOSTCTX-016 director
  discretion (REQ-SD-004).
- **Never blocks / silences playout.** [HARD] Missing research, an absent show, a novelty-reject loop, or
  any engine error logs and degrades gracefully (taste-only angle, or no show / plain curation); it never
  stalls a curation tick, a talk break, or the audio path (NFR-S-1/S-5).
- **Brain-only; additive.** [HARD] SHOWS-020 adds a research client + a show model + a variation engine +
  wiring to the existing `brain/` package, the existing director + talk loops, and the existing store
  seam. No new service, no store fork, no Liquidsoap change (NFR-S-4).

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001, SPEC-RADIO-ANALYSIS-006, SPEC-RADIO-PROGRAMMING-007,
SPEC-RADIO-KNOWLEDGE-008, and SPEC-RADIO-HOSTCTX-016, and references SPEC-RADIO-MBMIRROR-017,
SPEC-RADIO-ENRICH-012, SPEC-RADIO-OPS-004, and SPEC-RADIO-ORCH-005. It is the editorial show-variation
subsystem layered on top
of them; it references their subsystems by CONCEPT (and, where a cited requirement is a deliberately
stable invariant or seam, by number) rather than re-specifying them.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any sibling SPEC requirement. Where it needs a
predecessor behavior it consumes it. Where a SHOW decision could conflict with continuous operation, the
grounding discipline, or the anti-convergence firewall, the inherited behavior WINS — the music keeps
playing, talking points stay grounded, and the roster stays distinct.

Consumed concepts (by number where the requirement is a stable invariant or seam):
- **CORE-001 REQ-D-006/007 + `brain/director.py`** — the LLM director loop + self-initiated cadence the
  show engine attaches to; an active show's lens biases the curation batch as a non-binding input.
- **ANALYSIS-006 Group AM + REQ-AM-003 + `brain/metadata.py` Last.fm `track.getTopTags` provider** — the
  EXISTING key-gated, log-once, exception-isolated Last.fm provider used for GENRE CONSENSUS. SHOWS-020's
  Group LF is a SEPARATE research client; it does not change `enrich()` or re-derive consensus.
  Per-track genre/feature data is read for the selection lens, not re-owned.
- **PROGRAMMING-007 Group PR (roster + taste charter + REQ-PR-004 firewall), REQ-PL-004 (evolving taste
  profile), Group PT (show formats), Group PG (fact contract REQ-PG-001 + grounding REQ-PG-002 +
  quality gate REQ-PG-005)** — a show is generated for a roster persona, in its taste profile, inside
  the firewall, with show-format skeletons available, and any spoken talking point grounded +
  gate-validated. [HARD][GREENFIELD] The persona ROSTER (Group PR) is specified in PROGRAMMING-007 but
  NOT yet built — the talk layer (`brain/llm.py`) still uses a single generic `HOST_PERSONA`. SHOWS-020
  DEPENDS ON the roster: a show is per-persona. Until the roster ships, SHOWS-020 degrades to a SINGLE
  default persona (the existing generic host) — shows still vary (the novelty engine works against the
  single persona's own recent shows) and stay grounded; per-persona DISTINCTNESS becomes active when the
  roster lands, with no SHOWS-020 change (REQ-SP-001, AC Section B). The dependency is recorded so the
  engine is not built assuming a roster surface that does not yet exist.
- **KNOWLEDGE-008 (artist/music graph + grounding feed REQ-KI-001 + freshness gate)** — researched
  ARTIST FACTS that become airable talking points are owned here; a Last.fm research item to be SPOKEN
  enters a talking point only as a grounded fact, never a parallel unvalidated trivia feed (mirrors
  HOSTCTX-016 REQ-HW-003).
- **HOSTCTX-016 + `brain/talk.py` `_build_context` / `_attach_grounding`** — the talk-context assembly
  SHOWS-020 extends with show-level keys (theme + talking points), sitting above HOSTCTX's per-song
  facts.
- **MBMIRROR-017** — the heavier research/cross-check substrate; SHOWS-020's Last.fm client is the light
  direct path; richer cross-checked facts come via KNOWLEDGE-008.
- **ENRICH-012 (AcoustID -> MusicBrainz identify pipeline)** — the Group SM BBC DASH stream-fingerprint
  mode (REQ-SM-002) reuses this identify pipeline (fpcalc rolling windows) to recover an ordered now-playing
  sequence when no in-band metadata is present; consumed by reference, never re-owned. Heavier, bounded,
  off-by-default behind `bbc_thread_enabled`.
- **OPS-004 Group OA + ORCH-005** — the scheduler / world-model director own WHEN a show runs + WHICH
  persona is on-air; SHOWS-020 supplies the show content and rides their discretion.
- **OPS-004 REQ-OH-006** — the bounded-job throttle the research + planning work + every Group SM provider
  poll adopt.

### bhive memory seam

bhive memory (AGENTS.md protocol) has no proven pattern for the Last.fm-research-driven per-persona
show-variation + novelty-ledger pattern on this Go/Python+Liquidsoap stack (recorded gap). Re-run a bhive
query on the Last.fm `artist.getSimilar` / `tag.getTopArtists` research client + the LLM-proposes-grounded-
angle + recent-shows-novelty-window pattern during implementation, and contribute the verified approach
back per the AGENTS.md memory protocol.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Last.fm research client** | The Group LF key-gated, rate-limited, exception-isolated client (the SEPARATE `brain/lastfm.py` module, D-S-3) over the verified no-auth read surface — `artist.getInfo` / `artist.getSimilar` / `artist.getTopTags` / `artist.getTopTracks`, `track.getInfo` / `track.getSimilar`, `tag.getInfo` / `tag.getSimilar` / `tag.getTopArtists` / `tag.getTopTracks`, `chart.*`, `geo.*` (all key-only, no signed session, `research.md` §2) — supplying SHOW-DESIGN research material (bio context, similar artists, theme→artist discovery, tags, time/region trends). DISTINCT from the ANALYSIS-006 `brain/metadata.py` Last.fm GENRE-CONSENSUS provider (REQ-LF-001/003). |
| **Artist-fact research lead** | A Last.fm `artist.getInfo` / `track.getInfo` item (bio, tags, relative popularity) used as a LEAD to look up — crowd-sourced + unsourced (`research.md` §5b), so NEVER aired raw. It becomes airable only after landing as a KNOWLEDGE-008 dated/sourced fact and passing the PROGRAMMING-007 grounding gate (REQ-LF-006, D-S-5). |
| **KEXP thread signal client** | The Group SK keyless, OFF-by-default (`kexp_thread_enabled=false`) `brain/kexp.py` client (sibling to `brain/lastfm.py`) that polls the public no-auth KEXP API v2 `/v2/plays/?ordering=-airdate` feed, walks the show FK, and assembles short back-to-back human-DJ track CLUSTERS keyed on one show/host session. Rate-limited / timed-out / exception-isolated by reuse of REQ-LF-002; provenance `method=kexp.plays` by reuse of REQ-LF-004 (REQ-SK-001/002). |
| **KEXP human-DJ cluster (thread hypothesis)** | A short ordered run of tracks `{artists, titles, albums, airdate, host_name, program_name, provenance}` from ONE KEXP show/host session, handed to the LLM as a THREAD HYPOTHESIS — colour to reason about, NEVER voiced raw — that may seed a Group SX angle (REQ-SX-001) or a PROGRAMMING-007 REQ-PC-006 transition idea. Treated exactly like a Last.fm artist-fact research lead (REQ-LF-006): KEXP picks are NOT a playlist to copy, the station plays only its OWN catalog, KEXP track ids never enter rotation (REQ-PR-009 unaffected). KNOWLEDGE-008 stays the sole airable-fact seam (REQ-SK-003). |
| **Multi-source human-DJ signal layer (Group SM)** | The THIN PROVIDER INTERFACE that GENERALIZES the single-source Group SK KEXP client into a registry of human-DJ signal providers. Each provider exposes a `poll()` returning ordered clusters in the normalized shape (REQ-SM-003), returns EMPTY on ANY failure, and NEVER raises; each is behind a per-source OFF-by-default flag. `brain/kexp.py` becomes the first registered provider (back-compatible). The FIVE sources (REQ-SM-002): KEXP, Sveriges Radio, BBC (segments + DASH stream-fingerprint), A State of Trance (cuenation), NTS. |
| **Human-DJ signal provider** | One implementation of the Group SM interface for a single source, behind its own enable flag (`kexp_thread_enabled` / `sr_thread_enabled` / `bbc_thread_enabled` / `asot_thread_enabled` / `nts_thread_enabled`), inheriting the Group SK rails per-source by reference (REQ-SM-005): rate/timeout/isolation (REQ-LF-002), cache (REQ-SK-002), bounded background job off the pull path (REQ-LF-005), EMPTY-on-failure + OFF-by-default, never-aired-raw (REQ-SK-003), per-persona refraction (REQ-SK-004). |
| **Sequence-confidence** | A per-cluster tag (REQ-SM-004) the consumer (the Group SX angle reasoning REQ-SX-001 + the PROGRAMMING-007 REQ-PC-006 transition generator) weights by: PER-TRACK ORDERED sources (KEXP/SR/BBC-segments+stream/cuenation, the last with transition timecodes) are craft FUEL (medium→high confidence); SHOW-LEVEL signals (NTS-live: show/host/genre/locality) are CONTEXT/labeling ONLY (confidence none) and NEVER inject phantom transitions; a gappy archive scrape is low confidence. |
| **Episode / part / series-arc fields** | OPTIONAL fields (`episode_id`, `part_number`, `series_arc_id`) a REQ-SD-005 planned-shows queue ENTRY MAY carry; a pure additive extension that is INERT in SHOWS-020 (the per-session `Show` model REQ-SG-001 + the novelty check REQ-SX-002 are unchanged). The forward-reference seam consumed by the future SPEC-RADIO-LONGFORM-025 Group LB to thread multi-part series across sessions (REQ-SD-005). |
| **Last shows (show history)** | The durable per-persona record of which shows ran (the `retired` Show records that also feed the novelty ledger). Last.fm has NO events API (retired 2016, `research.md` §4) — show history is OUR data (REQ-SG-005). |
| **Planned shows (forward schedule)** | The per-persona forward queue of upcoming planned show CONTENT the engine persists + the director consumes; OUR data, DISTINCT from the OPS-004/ORCH-005 time-grid (which owns WHEN a slot occurs + WHICH persona is on-air) (REQ-SD-005). |
| **Show / program** | A per-persona themed PROGRAM the host runs for one session/slot: an editorial `theme`/`angle`, a `selection_lens`, `talking_points`, provenance, and a status. The unit of editorial variation (Group SG). |
| **Editorial angle / theme** | The idea behind a show — e.g. "the producers behind the sound", "1979 in one hour", "artists adjacent to X you have not heard", a mood arc, a label retrospective. Invented by the LLM, grounded in research + taste; must be NOVEL against the persona's recent angles (REQ-SX-001). |
| **Selection lens** | The catalog filter/biasing rule a show uses to pick its tracks — by genre / era / mood / similarity-neighbourhood (Last.fm similar artists) / tag. It BIASES the curation/wishlist input; it never force-inserts or overrides the picker (REQ-SD-001). |
| **Talking points** | Grounded research notes attached to a show that the host MAY voice. A spoken talking point is a grounded fact validated by the PROGRAMMING-007 gate; show-design-only research (used to pick tracks) is internal planning material, not an airable fact (REQ-SX-003, REQ-SD-003). |
| **Recent-shows ledger** | The per-persona record of recently-run show angles/themes (with timestamps) the novelty check compares a new proposal against, over a configurable window. The structural defeat of "same show every week" (REQ-SX-002). |
| **Novelty check** | The rejection of a proposed show angle that is too similar to one the persona ran within the recent-shows window, triggering a regenerate (grounded in fresh research). Threshold + window are config; that an angle must be novel is the rail (REQ-SX-001/002). |
| **Per-persona distinctness** | Each persona generates shows in its OWN taste/voice/territory; the engine never converges two personas onto the same angle/territory, inheriting the PROGRAMMING-007 REQ-PR-004 firewall (REQ-SP-001/002). |
| **Director discretion (unhosted)** | When no scheduled-host persona is presenting, the LLM director (CORE-001 REQ-D-006/007) decides the show itself under the same rails — consistent with HOSTCTX-016 director discretion (REQ-SD-004). |
| **Provenance (research)** | Per-research-item source attribution (which Last.fm method / which artist/tag query produced it), so a talking point can be traced and a show's grounding audited (REQ-LF-004). |
| **Graceful degradation** | With no Last.fm key, missing research, an absent roster, or a novelty-reject loop, the engine falls back (taste-only angle / single default persona / no show + plain curation) and the station is unaffected; absence is never a defect (NFR-S-1). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group LF — Last.fm Research Client.** The key-gated, rate-limited, exception-isolated SEPARATE
  `brain/lastfm.py` client over the verified no-auth read surface (`artist.getInfo` / `getSimilar` /
  `getTopTags` / `getTopTracks`, `track.getInfo` / `getSimilar`, `tag.getInfo` / `getSimilar` /
  `getTopArtists` / `getTopTracks`, `chart.*`, `geo.*` — `research.md` §2), with per-field provenance and
  ToS compliance (NFR-S-8); complements (does not duplicate) the ANALYSIS-006 genre-consensus provider
  and the MBMIRROR-017 / KNOWLEDGE-008 fact ownership; supplies artist-fact research leads (REQ-LF-006);
  fully graceful with no key. The `user.*` / `auth.*` / write surface (signed session) is OUT of scope
  (`research.md` §2.7).
- **Group SK — KEXP Human-DJ Thread Signal.** A SECOND, optional, keyless, OFF-by-default (`kexp_thread_enabled
  =false`) research client (`brain/kexp.py`, sibling to `brain/lastfm.py`) that polls the public no-auth KEXP API
  v2 `/v2/plays/?ordering=-airdate` feed, walks the show FK, and assembles short back-to-back human-DJ track
  CLUSTERS (one show/host session) as THREAD HYPOTHESES that seed a Group SX angle or a PROGRAMMING-007 REQ-PC-006
  transition idea. Rate-limited / timed-out / exception-isolated and provenance-shaped by reuse of REQ-LF-002 /
  REQ-LF-004 / REQ-LF-005; treated as a research lead never aired raw (REQ-LF-006); KEXP picks never enter rotation
  (the station plays only its own catalog; REQ-PR-009 unaffected); KEXP-seeded angles pass the same
  taste/novelty/anti-convergence gates as any angle.
- **Group SM — Multi-Source Human-DJ Signal.** The THIN PROVIDER INTERFACE that generalizes Group SK into a
  registry of human-DJ signal providers (`poll()` returns ordered clusters in the normalized shape, EMPTY on
  any failure, never raises; each provider behind a per-source OFF-by-default flag); the FIVE enumerated
  sources with access tier + sequence-availability (KEXP `/v2/plays`; Sveriges Radio `api.sr.se`; BBC Radio 1
  + Radio 1 Dance `/programmes/{PID}/segments.json` + the live BBC DASH `.mpd` stream-fingerprint mode via
  ENRICH-012; A State of Trance via cuenation `.cue` + `astateoftrance.com` fallback + throttled
  1001tracklists cross-check; NTS `/api/v2/live` context + episode-page scrape); the normalized cluster shape
  (the SK cluster + additive `source` + locality tags + optional cue-point/timecode); the per-track-ordered =
  FUEL vs show-level = CONTEXT-ONLY classification with a per-cluster sequence-confidence; and the per-source
  inheritance of the Group SK rails (rate/timeout/isolation, cache, bounded background job off the pull path,
  EMPTY-on-failure + OFF-by-default, never-aired-raw, per-persona refraction). `brain/kexp.py` is the first
  registered provider (back-compatible); the existing Group SK requirements stay valid.
- **Group SG — Show / Program Model.** The typed `Show` record (persona, theme/angle, selection lens,
  talking points, provenance, status lifecycle), the durable per-persona show-HISTORY ("last shows"), and
  where it persists; brain-only, no store fork.
- **Group SX — Editorial Variation Engine.** The LLM-proposes-grounded-angle flow; the per-persona
  recent-shows ledger; the novelty check over a configurable window; the reject-and-regenerate-a-too-
  similar-angle discipline; the grounded-angle rule.
- **Group SP — Per-Persona Distinctness.** Each show generated in its persona's taste/voice/territory;
  the engine consumes the PROGRAMMING-007 roster + firewall and never converges the roster; the
  greenfield-roster degraded mode (single default persona).
- **Group SD — Scheduling / Direction.** An active show biases the director's curation/wishlist (non-
  blocking) and feeds the talk theme + talking points; the director decides when no host is scheduled; the
  per-persona FORWARD "planned shows" schedule the engine persists + the director consumes (OUR data,
  distinct from the OPS-004/ORCH-005 time-grid); never blocks playout.
- **Group SB — Show Wiring (brain-only integration).** The additive attachment to `brain/director.py` +
  `brain/talk.py` `_build_context` + `brain/config.py`; never on the pull path.
- Plus **NFRs** (Section 8) and **Risks** (Section 9).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **The persona ROSTER + taste charter + anti-convergence firewall + evolving taste profile** — owned by
  PROGRAMMING-007 Group PR / REQ-PL-004; a show is generated FOR a persona IN its taste INSIDE the
  firewall; never re-owned.
- **The show FORMATS / recurring-segment skeletons (incl. Solstice Hour)** — owned by PROGRAMMING-007
  Group PT; SHOWS-020 generates VARIATION over the available formats, it does not re-own the skeletons.
- **The genre/feature substrate + the genre consensus** — owned by ANALYSIS-006 (Group AM, REQ-AM-003,
  `brain/metadata.py`); the show selection lens reads the per-track genre/feature data and the Last.fm
  research client is separate from the consensus provider; never re-owned.
- **The artist/music KNOWLEDGE GRAPH + dated/sourced/freshness-gated facts + the grounding feed** — owned
  by KNOWLEDGE-008; airable talking points are grounded facts from this feed; SHOWS-020 opens no parallel
  trivia channel.
- **The grounded-voice fact contract + the two-tier quality gate + the forbidden-fact scan** — owned by
  PROGRAMMING-007 Group PG; talking points route through them unchanged; SHOWS-020 adds no new gate.
- **The per-song year/album/curiosa host facts** — owned by HOSTCTX-016; SHOWS-020 adds PER-SESSION show
  content above them, on the same context bundle.
- **The self-hosted MusicBrainz mirror + Discogs/Last.fm cross-check infrastructure** — owned by
  MBMIRROR-017; SHOWS-020's Last.fm client is the light direct research path; never re-owns the mirror.
- **The SCHEDULER / dayparting / WHEN-a-show-runs / WHICH-persona-is-on-air** — owned by OPS-004 Group OA
  / ORCH-005; SHOWS-020 supplies show content and rides their discretion; never forks the schedule store.
- **The next-track PICKER + the playout chain** — owned by CORE-001 / OPS-004; a show lens is a
  non-binding bias INPUT, never a re-owned picker, force-insert, or synchronous playout insertion.
- **TTS synthesis + ear-writing the spoken line** — owned by VOICE-002 + PROGRAMMING-007 Group PS;
  SHOWS-020 owns show CONTENT (theme + talking-point eligibility), not phrasing or synthesis.
- **Acquisition pipeline + provenance + grab-reason + acquisition diary** — owned by OPS-004 Group OH /
  PROGRAMMING-007 Group PL; a show lens biases WHAT the director wishlists, but acquisition, provenance,
  and the diary are not re-owned.
- **A public-facing show schedule / programme guide UI** — out of scope for v1; the website surface is
  owned by CORE-001 Group E / WEBUI-018 and a show-guide is a future enhancement (Section 10).
- **A new datastore or a new web service** — brain-only + additive; the show records + recent-shows
  ledger live in the existing store seam (NFR-S-4).

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain-only + additive.** SHOWS-020 adds a Last.fm research client + a show model + a variation
  engine + wiring to the existing `brain/` package, the existing director + talk loops, and the existing
  store seam. No new service, no store fork, no Liquidsoap change.
- [HARD] **Last.fm key-gated + fully graceful.** The research client runs ONLY with `lastfm_api_key`;
  with no key it logs once and returns empty, the engine falls back to taste-only angles, and the station
  is unaffected.
- [HARD] **Research rate-limited + exception-isolated + never blocks.** Explicit timeout, rate-limit,
  exception-isolation (empty on any error); research + planning run as a bounded background job, never on
  the `/api/next` pull path. [HARD] Per `research.md` §3.2 the polite default is **≤ 1 request/second**
  with jittered spacing + a small bounded burst (staying well under the community-cited 5 req/s ceiling
  that the current ToS clause 4.4 no longer states numerically), with exponential backoff on Last.fm
  error 29 (rate-limit) and error 16 (temporary error); responses arrive HTTP 200 even on error, so the
  client branches on the `error` key (`research.md` §1.2).
- [HARD] **Last.fm ToS compliance** (`research.md` §3, NFR-S-8). The research client/store MUST: cache
  responses per the HTTP cache headers (ToS 4.3.4 makes caching a REQUIREMENT, not an optimization); keep
  any stored Last.fm-derived data under the 100 MB Reasonable-Usage cap (4.3.4) and prune accordingly; use
  Last.fm strictly as PRIVATE, NON-COMMERCIAL research INPUT (ToS 3.1) and not re-publish raw Last.fm data
  as station content or build a public mirror of it; set an identifiable User-Agent on every request; and
  attach Last.fm attribution + the returned `url` back-link IF any Last.fm-derived text/link is ever shown
  to listeners (4.2.2). If the station is ever monetized or Last.fm data surfaces verbatim to listeners, a
  `partners@last.fm` contact is a prerequisite (flagged in Section 13).
- [HARD] **Last.fm is NOT a fact authority and has NO events API.** Last.fm is the taste/tag/similarity/
  popularity layer; canonical facts/credits/identity stay with MusicBrainz (MBMIRROR-017) / Discogs /
  KNOWLEDGE-008 (`research.md` §6), and Last.fm bios/wikis are crowd-sourced + unsourced research LEADS
  (§5b). The events/gigs + radio/streaming APIs were RETIRED in 2016 (§4), so "last shows" + "planned
  shows" are OUR persisted data, never Last.fm events (REQ-SG-005, REQ-SD-005).
- [HARD] **Complement, don't duplicate.** The Last.fm research client is separate from the ANALYSIS-006
  genre-consensus provider; it does not re-derive consensus or re-own artist facts (KNOWLEDGE-008 over
  MBMIRROR-017).
- [HARD] **KEXP is a keyless, OFF-by-default research lead, never a playlist or fact channel.** The Group SK
  KEXP thread signal (`brain/kexp.py`) is OFF by default (`kexp_thread_enabled=false`), keyless, rate-limited,
  timed-out, exception-isolated, and cached (REQ-SK-001/002, reusing REQ-LF-002/004/005). A KEXP human-DJ
  cluster is a THREAD HYPOTHESIS treated exactly like a Last.fm research lead (REQ-LF-006) — never voiced raw,
  KNOWLEDGE-008 stays the sole airable-fact seam — and KEXP picks NEVER enter rotation: the station plays only
  its OWN catalog, so the PROGRAMMING-007 REQ-PR-009 per-track exclusivity rule is UNAFFECTED (REQ-SK-003). A
  KEXP-seeded angle passes the SAME taste (REQ-PL-004) / novelty (REQ-SX-002) / anti-convergence
  (REQ-PR-004 + REQ-PR-009) gates and is DROPPED if outside a persona's lane — one shared signal refracted
  divergently, never a homogenizer (REQ-SK-004).
- [HARD] **The multi-source human-DJ signal is a thin provider interface; per-track ordered = fuel,
  show-level = context-only.** The Group SM provider interface (REQ-SM-001) generalizes Group SK; each
  provider's `poll()` returns ordered clusters in the normalized shape (REQ-SM-003), returns EMPTY on ANY
  failure, never raises, and is OFF by default behind its own flag (`kexp_thread_enabled` [existing] /
  `sr_thread_enabled` / `bbc_thread_enabled` / `asot_thread_enabled` / `nts_thread_enabled`). [HARD] FIVE
  sources are enumerated by access tier + sequence-availability (REQ-SM-002). [HARD] PER-TRACK ORDERED
  sequences (KEXP / Sveriges Radio / BBC segments + DASH stream-fingerprint / cuenation `.cue`) are craft
  FUEL; SHOW-LEVEL signals (NTS-live) are CONTEXT/labeling ONLY and SHALL NEVER inject phantom transitions —
  each cluster is tagged with `source` + a sequence-confidence (REQ-SM-004). [HARD] Every provider inherits
  the Group SK rails per-source BY REFERENCE — rate/timeout/isolation (REQ-LF-002; KEXP/SR ≤ 1 req/s
  jittered, scrape sources a slower per-source cadence, weekly for ASOT/cuenation), cache (REQ-SK-002),
  bounded background job off the pull path (REQ-LF-005 / OPS-004 REQ-OH-006), EMPTY-on-failure +
  OFF-by-default, never-aired-raw + KNOWLEDGE-008 sole fact seam + no source track into rotation
  (REQ-SK-003, REQ-PR-009 unaffected), and per-persona refraction (REQ-SK-004) (REQ-SM-005). The BBC DASH
  stream-fingerprint mode reuses the ENRICH-012 AcoustID->MusicBrainz identify pipeline by reference, never
  re-owning it.
- [HARD] **A show angle must be novel against the persona's recent shows** over a configurable window;
  a too-similar angle is rejected + regenerated.
- [HARD] **A show is grounded.** Angle + talking points grounded in supplied research + taste; a spoken
  talking point is a grounded fact validated by the PROGRAMMING-007 gate; never invented.
- [HARD] **Per-persona distinct; roster never converges** (PROGRAMMING-007 REQ-PR-004 unchanged); one
  persona's angle is never reused for another.
- [HARD] **A show biases, never forces.** The selection lens is a non-binding curation/wishlist input;
  it never force-inserts, overrides rotation/clock/no-repeat, or removes picker autonomy.
- [HARD] **Director decides when unhosted**, under the same rails.
- [HARD] **Continuous operation is the prime rail.** Missing research, an absent show, a novelty-reject
  loop, an absent roster, or any engine error logs + degrades gracefully; never stalls a tick, a break,
  or the audio path.
- [HARD] **No pandering.** Show angles are editorial invention grounded in research, never an
  engagement/popularity optimization target (inherited CORE-001 REQ-OF-004 / the curation ethos).
- [HARD][GREENFIELD] **Roster dependency.** Per-persona distinctness (Group SP) depends on the
  PROGRAMMING-007 persona roster (Group PR), which is GREENFIELD; until it ships, SHOWS-020 degrades to a
  single default persona (variation + grounding still hold).

---

## 6. Requirement Group LF — Last.fm Research Client

Priority: High.

### REQ-LF-001 — Key-gated Last.fm research client; fully graceful with no key (Ubiquitous) [HARD]

The system SHALL provide a Last.fm RESEARCH client that runs ONLY when `lastfm_api_key` (already declared
in `brain/config.py`, optional/empty-default) is set. [HARD] With NO key the client SHALL log once at INFO
and return EMPTY results without constructing any client or raising — exactly as the existing
`brain/metadata.py` Last.fm provider does — and the show engine SHALL fall back to taste-only show angles
with the station completely unaffected. The key being absent is a normal, supported, quiet state, not an
error. That the research client is key-gated and fully graceful without a key is the rail.

**Acceptance criteria:** see acceptance.md AC-LF-001.

### REQ-LF-002 — Rate-limited, explicitly-timed-out, exception-isolated research calls (Ubiquitous) [HARD]

Every Last.fm research call SHALL have an EXPLICIT short timeout, SHALL be RATE-LIMITED (a self-throttle
so the client cannot exceed a polite request rate — a default of ≤ 1 request/second with jittered spacing
and a small bounded burst, well under the community-cited 5 req/s ceiling, `research.md` §3.2), and SHALL
be EXCEPTION-ISOLATED — returning EMPTY on ANY error (network down, dependency missing, malformed response,
timeout, OR a Last.fm error envelope) and NEVER raising into the caller. [HARD] Because Last.fm returns
HTTP 200 even on failure, the client SHALL branch on the response `error` key (not the HTTP status,
`research.md` §1.2), and SHALL apply exponential backoff on error 29 (rate-limit) and error 16 (temporary
error). [HARD] A research flake can never propagate toward the director tick, the talk loop, or the
`/api/next` pull. The timeout / rate / retry policy are config; that every call is timed-out, rate-limited,
and exception-isolated is the rail.

**Acceptance criteria:** see acceptance.md AC-LF-002.

### REQ-LF-003 — Research methods complement, never duplicate, ANALYSIS-006 / MBMIRROR-017 / KNOWLEDGE-008 (Ubiquitous) [HARD]

The research client SHALL expose SHOW-DESIGN research methods drawn from the Last.fm read surface that
`research.md` §2 VERIFIED requires no user authentication (key-only, no signed session): the core set
`artist.getInfo` (bio/listeners/tags), `artist.getSimilar` (neighbours for similarity-lens discovery, with
the 0–1 `match` score), `artist.getTopTags`, `tag.getTopArtists` (theme→artist discovery), and
`track.getInfo`; and MAY additionally use the verified no-auth methods `artist.getTopTracks`,
`track.getSimilar`, `tag.getInfo` (reach/taggings/wiki), `tag.getSimilar` (best-effort theme-graph walk),
`tag.getTopTracks`, and the trend surfaces `chart.*` (`getTopArtists`/`getTopTags`/`getTopTracks`) and
`geo.*` (`getTopArtists`/`getTopTracks`, a last-week country window — a built-in source of week-to-week
novelty). [HARD] It SHALL NOT use the `user.*` / `library.*` / `auth.*` / write methods that require a
signed session (`research.md` §2.7), SHALL be DISTINCT from the ANALYSIS-006 `brain/metadata.py` Last.fm
GENRE-CONSENSUS provider, SHALL NOT re-derive genre consensus (REQ-AM-003 stays sole owner), SHALL NOT
modify `enrich()`, and SHALL NOT re-own artist FACTS (owned by KNOWLEDGE-008 over MBMIRROR-017). Where
richer cross-checked facts are needed, they come via KNOWLEDGE-008; the Last.fm research client supplies
LIGHT, direct show-design material only. The client SHALL also tolerate the JSON quirks `research.md` §1.2
documents (`"#text"` nodes, stringified numbers/booleans, single-vs-list collapse). That the research
client uses only the verified no-auth surface and complements (does not duplicate) the existing providers
is the rail.

**Acceptance criteria:** see acceptance.md AC-LF-003.

### REQ-LF-004 — Per-field research provenance (Ubiquitous)

Each research item the client returns SHALL carry PROVENANCE — which Last.fm method and which artist/tag
query produced it — so a downstream talking point can be traced to its source and a show's grounding can
be audited. The provenance shape is implementation detail; that every research item is source-attributed
is the rail.

**Acceptance criteria:** see acceptance.md AC-LF-004.

### REQ-LF-005 — Research + planning run as a bounded background job, never on the pull path (State-driven) [HARD]

While the station is running, the Last.fm research + show-planning work SHALL run as a BOUNDED, THROTTLED
BACKGROUND job adopting the OPS-004 REQ-OH-006 bounded-job pattern (and the existing director/talk
best-effort background discipline), and SHALL NEVER execute on the sub-1s `/api/next` playout pull path.
[HARD] When at its bound (e.g. downloads in flight, or the throttle engaged), research/planning is
deferred, not piled on; SHOWS-020 ADOPTS the throttle pattern by reference and does not re-own it. That
research + planning is bounded background work off the pull path is the rail.

**Acceptance criteria:** see acceptance.md AC-LF-005.

### REQ-LF-006 — Artist-fact research leads are aired only via KNOWLEDGE-008, never raw (Ubiquitous) [HARD]

The research client SHALL treat `artist.getInfo` / `track.getInfo` bio/tag/popularity material as ARTIST-FACT
RESEARCH LEADS — colour to LOOK UP, not to broadcast. [HARD] Per `research.md` §5b these Last.fm bios/wikis
are crowd-sourced and UNSOURCED; the system SHALL NOT voice a Last.fm fact lead directly. An artist fact
becomes AIRABLE only after it lands as a KNOWLEDGE-008 dated/sourced fact and passes the PROGRAMMING-007
grounding gate UNCHANGED (the single airable-fact seam, REQ-SG-004 / REQ-SD-003, D-S-5). Relative popularity
(`listeners`/`playcount`) MAY frame a show loosely ("a cult act vs a household name") but SHALL NOT be quoted
as precise live figures (they are cached, stringified snapshots, `research.md` §5b). KNOWLEDGE-008 is the
single home for airable Last.fm-derived facts; SHOWS-020 opens no parallel trivia channel. That artist-fact
research is a grounded-via-KNOWLEDGE-008 lead, never aired raw, is the rail.

**Acceptance criteria:** see acceptance.md AC-LF-006.

---

## 6K. Requirement Group SK — KEXP Human-DJ Thread Signal

Priority: Medium. [A SIBLING to Group LF — a SECOND, optional, keyless research client. OFF by default;
when enabled, its [HARD] rails (SK-002/003/004) are must-pass. It reuses REQ-LF-002 (rate/timeout/
isolation), REQ-LF-004 (provenance shape), REQ-LF-005 (bounded background job), and REQ-LF-006
(research-lead-never-aired-raw) BY REFERENCE.]

### REQ-SK-001 — Keyless, fully-graceful, OFF-by-default KEXP thread-signal client (Ubiquitous)

The system SHALL provide a KEXP THREAD-SIGNAL client (a SEPARATE `brain/kexp.py` module, sibling to
`brain/lastfm.py`) that polls the PUBLIC, NO-AUTH KEXP API v2 plays endpoint
(`/v2/plays/?ordering=-airdate` — live, no key/OAuth/signature), WALKS the show foreign-key to assemble
short BACK-TO-BACK human-DJ track CLUSTERS — a configurable N songs (default 3–4, tunable) from ONE
KEXP show/host session — each carrying `{artists, titles, albums, airdate, host_name, program_name,
provenance}`. [HARD] The client SHALL be OFF BY DEFAULT behind a `kexp_thread_enabled` config flag
(`false` default); when disabled it constructs no client, polls nothing, and returns EMPTY. [HARD] On ANY
failure (network down, endpoint change, malformed/partial response, missing show FK) it SHALL return
EMPTY and NEVER raise — exactly the graceful posture of the Group LF Last.fm client (REQ-LF-001). With the
signal disabled or empty, the show engine (Group SX) falls back to Last.fm + taste-only angles and the
station is completely unaffected. KEXP needs no key (no Last.fm-style ToS clauses apply, NFR-S-8), so the
gate is purely the enable flag. That the KEXP client is keyless, OFF by default, and fully graceful (empty,
never raising) is the rail.

**Acceptance criteria:** see acceptance.md AC-SK-001.

### REQ-SK-002 — Rate-limited, explicitly-timed-out, exception-isolated, cached KEXP polls (Ubiquitous) [HARD]

Every KEXP poll SHALL have an EXPLICIT short timeout, SHALL SELF-THROTTLE to a polite rate
(default ≤ 1 request/second with jittered spacing), SHALL CACHE the last poll (so repeated planning ticks
reuse a recent result rather than re-hitting KEXP), and SHALL be EXCEPTION-ISOLATED — returning EMPTY on
ANY error and never raising into the caller. [HARD] A KEXP flake can NEVER propagate toward the
`brain/director.py` tick, the `brain/talk.py` talk loop, or the `/api/next` playout pull. [HARD] The KEXP
poll SHALL run under the SAME bounded, throttled background-job pattern as the Last.fm research
(REQ-LF-005 / OPS-004 REQ-OH-006, referenced not re-owned) and SHALL adopt the rate/timeout/isolation
discipline of REQ-LF-002 by reference; it is never re-owned and never on the sub-1s pull path. The
timeout / rate / cache TTL are config; that every poll is timed-out, throttled, cached, and
exception-isolated off the pull path is the rail.

**Acceptance criteria:** see acceptance.md AC-SK-002.

### REQ-SK-003 — A KEXP cluster is a thread HYPOTHESIS (research lead), never an airable-fact channel (Ubiquitous) [HARD]

The system SHALL hand a KEXP human-DJ cluster (`{artists, titles, albums, airdate, host_name,
program_name, provenance}`, with `provenance` shaped by REQ-LF-004, `method=kexp.plays`) to the LLM to
produce a THREAD HYPOTHESIS that may SEED a REQ-SX-001 angle proposal OR a PROGRAMMING-007 REQ-PC-006
transition idea. [HARD] The cluster SHALL be treated EXACTLY like a Last.fm artist-fact research lead
under REQ-LF-006 — colour to REASON ABOUT, NEVER voiced raw: "KEXP played X then Y" is NOT an
airable-fact channel, and KNOWLEDGE-008 stays the SOLE airable-fact seam (D-S-5 unchanged); a fact about
a KEXP cluster becomes airable only after it lands as a KNOWLEDGE-008 dated/sourced fact and passes the
PROGRAMMING-007 grounding gate UNCHANGED. [HARD] KEXP picks are NOT a playlist to copy: the station plays
ONLY its own catalog, the cluster's tracks bias only the ANGLE/THREAD reasoning, and KEXP track ids NEVER
enter rotation (the PROGRAMMING-007 REQ-PR-009 per-track exclusivity rule is UNAFFECTED — SHOWS-020 adds
no track to any rotation pool). That a KEXP cluster is a never-aired-raw research lead, and never a
playlist or an airable-fact channel, is the rail.

**Acceptance criteria:** see acceptance.md AC-SK-003.

### REQ-SK-004 — A KEXP-seeded angle passes the same per-persona taste/novelty/anti-convergence gates; one signal refracted divergently (Event-driven) [HARD]

When a KEXP-thread hypothesis seeds a proposed show angle for a persona, the system SHALL subject that
angle to the SAME gates as ANY other angle: the per-persona taste profile (PROGRAMMING-007 REQ-PL-004),
the novelty check against the persona's recent-shows ledger (REQ-SX-002), and the anti-convergence
firewall — BOTH layers, REQ-PR-004 (primary-genre territory) and REQ-PR-009 (per-track rotation
exclusivity) — UNCHANGED. [HARD] If a KEXP thread falls OUTSIDE a persona's lane (territory / taste),
then it SHALL be DROPPED for that persona (the firewall WINS) — the single KEXP signal is REFRACTED
DIVERGENTLY across the roster (each persona keeps only the thread that fits its own taste), and it is
NEVER a homogenizer that pushes two personas toward the same angle. [HARD] With the KEXP signal disabled
or failing, REQ-SX-001 SHALL fall back to Last.fm + taste-only angles with no change in behaviour. That a
KEXP-seeded angle is gate-equal to any angle, dropped when outside a persona's lane, and never a
convergence force is the rail.

**Acceptance criteria:** see acceptance.md AC-SK-004.

---

## 6M. Requirement Group SM — Multi-Source Human-DJ Signal

Priority: Medium. [A SIBLING to Group SK that GENERALIZES the single-source KEXP signal into a MULTI-SOURCE
provider layer. Every provider is OFF by default; when enabled, its [HARD] rails (SM-004/005) are must-pass.
It reuses REQ-LF-002 (rate/timeout/isolation), REQ-LF-004 (provenance shape), REQ-LF-005 (bounded background
job), REQ-LF-006 (research-lead-never-aired-raw), and REQ-SK-002/003/004 (cache / thread-hypothesis /
per-persona refraction) BY REFERENCE. The existing Group SK requirements + `kexp_thread_enabled` stay valid:
KEXP becomes the FIRST registered provider, back-compatible.]

### REQ-SM-001 — Thin multi-source human-DJ signal provider interface; generalizes brain/kexp.py (Ubiquitous) [HARD]

The system SHALL provide a THIN HUMAN-DJ SIGNAL PROVIDER INTERFACE that GENERALIZES the existing single-source
`brain/kexp.py` (Group SK) into a REGISTRY of providers. [HARD] Each provider SHALL expose a `poll()` that
returns ORDERED CLUSTERS in the normalized shape (REQ-SM-003), SHALL return EMPTY on ANY failure, and SHALL
NEVER raise into the caller — exactly the graceful posture of the Group SK client (REQ-SK-001). [HARD] Each
sibling provider SHALL be behind its OWN per-source OFF-by-default config flag: `kexp_thread_enabled`
(EXISTING, back-compatible — KEXP becomes the first registered provider), `sr_thread_enabled`,
`bbc_thread_enabled`, `asot_thread_enabled`, and `nts_thread_enabled` (all `false` default). When a
provider's flag is off it constructs no client, polls nothing, and returns EMPTY; with ALL providers off or
empty the show engine (Group SX) falls back to Last.fm + taste-only angles and the station is completely
unaffected. The consumer (the Group SX angle reasoning REQ-SX-001 + the PROGRAMMING-007 REQ-PC-006 transition
generator) sees a UNIFORM stream of normalized clusters regardless of source. The provider registry shape,
the cluster cap, and which providers are registered are config; that the interface is a thin per-provider
`poll()` returning ordered clusters, EMPTY-on-failure / never-raising, each behind a per-source OFF-by-default
flag, generalizing `brain/kexp.py`, is the rail.

**Acceptance criteria:** see acceptance.md AC-SM-001.

### REQ-SM-002 — The five sources, by access tier + sequence-availability (Ubiquitous)

The system SHALL source the multi-source human-DJ signal from FIVE sources, each classified by ACCESS TIER +
SEQUENCE-AVAILABILITY (which determines its sequence-confidence, REQ-SM-004), and each behind its own flag
(REQ-SM-001):

- **(A) Clean keyless APIs — primary craft fuel, per-track ORDERED sequence.**
  - **KEXP** `/v2/plays/?ordering=-airdate` (the EXISTING `brain/kexp.py`; `method=kexp.plays`;
    `kexp_thread_enabled`).
  - **Sveriges Radio** `api.sr.se` `playlists/getplaylistbychannelid` (P3, channel `id=164`; the response
    `song` array carries `starttimeutc`, giving an ordered per-track sequence; `method=sr.playlists`;
    `sr_thread_enabled`).
- **(B) Keyless structured feed — per-track ORDERED (BBC).** Behind `bbc_thread_enabled`.
  - **BBC Radio 1 + Radio 1 Dance** via `/programmes/{PID}/segments.json` (the segment list carries explicit
    ORDER; the client SHALL SKIP programmes with empty tracklists and SHALL ignore the key-gated Nitro feed;
    `method=bbc.segments`).
  - **The live BBC DASH stream** (`a.files.bbci.co.uk` `.mpd`) as a STREAM-FINGERPRINT mode: parse in-band
    now-playing metadata IF present, ELSE run fpcalc ROLLING WINDOWS through the SPEC-RADIO-ENRICH-012
    AcoustID->MusicBrainz identify pipeline (consumed by reference, REQ-SM-005) to recover the ordered
    sequence. [HARD] This is the HEAVIER, BOUNDED, off-by-default last-resort path within the BBC provider,
    not the default (`method=bbc.stream`).
- **(C) Scrape — A STATE OF TRANCE; per-track ORDERED + transition timecodes = strongest craft fuel.** Behind
  `asot_thread_enabled`.
  - **cuenation `.cue` files** (ordered tracklist + transition TIMECODES; `method=asot.cue`) — the primary,
    strongest fuel.
  - **`astateoftrance.com` numbered-list** fallback when no `.cue` is available.
  - **1001tracklists** ONLY as a THROTTLED Playwright cross-check, NEVER primary.
- **(D) Show-level CONTEXT + low-confidence archive scrape — NTS.** Behind `nts_thread_enabled`.
  - **NTS** `/api/v2/live` — show / host / genre / LOCALITY CONTEXT only, NOT a sequence (`method=nts.scrape`).
  - **NTS episode-page scrape** — a low-confidence, gappy sequence.

[HARD] The per-track-ordered sources (A, B, and cuenation in C) are craft FUEL; the show-level NTS-live signal
is CONTEXT/labeling ONLY (REQ-SM-004). That the five sources are enumerated by access tier +
sequence-availability, each behind its own OFF-by-default flag, is the rail; exact endpoints / channel ids /
scrape cadences are config.

**Acceptance criteria:** see acceptance.md AC-SM-002.

### REQ-SM-003 — Normalized cluster shape across all providers; additive over the Group SK cluster (Ubiquitous) [HARD]

Every provider's `poll()` SHALL return clusters in ONE NORMALIZED SHAPE: the EXISTING Group SK cluster
`{artists, titles, albums, airdate, host_name, program_name, provenance}` (REQ-SK-001) PLUS additive fields —
a `source` (`kexp` | `sr` | `bbc` | `asot` | `nts`), `locality` tags, and (OPTIONAL, cuenation only)
cue-point / transition-timecode metadata. [HARD] The `provenance` is shaped by REQ-LF-004 with one of the
method ids `kexp.plays` / `sr.playlists` / `bbc.segments` / `bbc.stream` / `asot.cue` / `nts.scrape`. [HARD]
This is an ADDITIVE extension of the SK cluster — the existing SK cluster shape stays valid (back-compatible:
the KEXP provider continues to emit `source=kexp`, `method=kexp.plays`). The exact field types are
implementation detail; that all providers emit one normalized cluster shape, additive over the SK cluster
with `source` + locality (+ optional cue timecodes), is the rail.

**Acceptance criteria:** see acceptance.md AC-SM-003.

### REQ-SM-004 — Per-track ordered = craft FUEL; show-level = CONTEXT only; per-cluster sequence-confidence (Ubiquitous) [HARD]

[HARD] PER-TRACK ORDERED sequences (KEXP / Sveriges Radio / BBC `segments` + DASH stream-fingerprint /
cuenation `.cue`) are craft FUEL — they may seed a REQ-SX-001 angle or a PROGRAMMING-007 REQ-PC-006 TRANSITION
idea (a real human-DJ segue order to reason about). [HARD] SHOW-LEVEL signals (NTS `/api/v2/live`:
show / host / genre / locality) are CONTEXT / LABELING ONLY and SHALL NEVER be treated as an ordered track
sequence — they SHALL NEVER inject PHANTOM TRANSITIONS (the engine SHALL NOT infer a segue from a show-level
signal). [HARD] Each cluster SHALL be tagged with its `source` + an implied SEQUENCE-CONFIDENCE so the
consumer (the Group SX angle reasoning REQ-SX-001 + the PROGRAMMING-007 REQ-PC-006 transition generator)
WEIGHTS it accordingly: HIGH for cuenation `.cue` transition timecodes, MEDIUM for an ordered playlist /
segment list (KEXP / SR / BBC), LOW for a gappy archive scrape (NTS episode page), and NONE / CONTEXT-ONLY
for the NTS-live show-level signal. The confidence scale + exact weights are config; that ordered sequences
are fuel, show-level signals are context-only and never phantom transitions, and every cluster carries a
sequence-confidence the consumer weights by is the rail.

**Acceptance criteria:** see acceptance.md AC-SM-004.

### REQ-SM-005 — Every provider inherits the Group SK rails per-source, by reference (Ubiquitous) [HARD]

[HARD] EVERY Group SM provider SHALL inherit the Group SK rails PER-SOURCE, BY REFERENCE — re-owning or
weakening none:

- **Rate / timeout / isolation (REQ-LF-002):** each poll has an explicit short timeout, self-throttles, and is
  exception-isolated (EMPTY on any error, never raises). [HARD] The polite rate is PER-SOURCE: KEXP / Sveriges
  Radio ≤ 1 req/s jittered; the SCRAPE sources (ASOT / NTS / 1001tracklists cross-check) a SLOWER per-source
  cadence; ASOT / cuenation a WEEKLY cadence (a tracklist publishes once per episode).
- **Cache (REQ-SK-002):** each provider caches its last poll so repeated planning ticks reuse a recent result
  rather than re-hitting the source.
- **Bounded background job off the pull path (REQ-LF-005 / OPS-004 REQ-OH-006):** every provider poll runs
  under the SAME bounded, throttled background-job pattern as the Last.fm research + the KEXP poll, and SHALL
  NEVER execute on `/api/next`, the `brain/director.py` tick, or the `brain/talk.py` talk loop.
- **EMPTY-on-failure + OFF-by-default (REQ-SM-001):** any failure returns EMPTY; every provider is off until
  its flag is set.
- **Never aired raw; KNOWLEDGE-008 the sole airable-fact seam; no source track into rotation (REQ-SK-003,
  REQ-LF-006):** a cluster from ANY source is a thread HYPOTHESIS / research lead — never voiced raw; an
  airable fact first lands as a KNOWLEDGE-008 dated/sourced fact through the unchanged grounding gate; no
  source's tracks are copied into rotation (the station plays only its OWN catalog; the PROGRAMMING-007
  REQ-PR-009 per-track exclusivity rule is UNAFFECTED).
- **Per-persona refraction (REQ-SK-004):** a cluster-seeded angle from ANY source passes the SAME per-persona
  taste (REQ-PL-004) / novelty (REQ-SX-002) / anti-convergence (REQ-PR-004 + REQ-PR-009) gates and is DROPPED
  outside a persona's lane — one shared signal refracted divergently, never a homogenizer.

That every provider inherits the Group SK rails per-source by reference (rate/timeout/isolation, cache,
bounded background job off the pull path, EMPTY-on-failure + OFF-by-default, never-aired-raw, per-persona
refraction) is the rail.

**Acceptance criteria:** see acceptance.md AC-SM-005.

---

## 7. Requirement Group SG — Show / Program Model

Priority: High.

### REQ-SG-001 — Typed Show record (Ubiquitous) [HARD]

The system SHALL model a SHOW as a TYPED record with the fields: `persona_id` (the roster persona the
show belongs to, or the single default persona in the greenfield-roster mode), an editorial `theme` /
`angle`, a `selection_lens` (the catalog filter/biasing rule — genre / era / mood / similarity-
neighbourhood / tag), `talking_points` (grounded research notes the host MAY voice), `provenance` (which
research backed the show, REQ-LF-004), `created_at`, and a `status`. [HARD] The record lives in the
existing store seam (no new datastore, no library fork). The exact storage layout + which lens types are
supported are config; that a typed show record with this field set exists is the rail.

**Acceptance criteria:** see acceptance.md AC-SG-001.

### REQ-SG-002 — Show status lifecycle (Ubiquitous) [HARD]

The system SHALL advance a show through a STATUS lifecycle: `proposed` (the LLM generated an angle) →
`rejected` (failed the novelty check, REQ-SX-002) | `active` (currently driving curation + talk) →
`retired` (the slot ended; recorded in the recent-shows ledger for future novelty checks). [HARD] A
`rejected` show never drives curation or talk; a `retired` show's angle/theme is what the per-persona
recent-shows ledger remembers (REQ-SX-002). That a show has this status lifecycle is the rail; the exact
transition triggers are config.

**Acceptance criteria:** see acceptance.md AC-SG-002.

### REQ-SG-003 — Selection lens is a declarative, catalog-resolvable filter/bias (Ubiquitous) [HARD]

The `selection_lens` (REQ-SG-001) SHALL be a DECLARATIVE rule resolvable against the LOCAL catalog +
the ANALYSIS-006 per-track genre/feature data + the Last.fm similar-artist research — e.g. "tracks in
genre/era/mood X", "tracks by artists similar to Y" (via `artist.getSimilar` neighbours intersected with
the catalog), "tracks tagged Z". [HARD] The lens RESOLVES to a bias over EXISTING catalog tracks (and a
wishlist hint for gaps); it NEVER fabricates a track, never force-inserts, and a lens that resolves to
nothing degrades to ordinary curation (NFR-S-5). That the lens is a declarative catalog-resolvable
filter/bias (never a fabricated track list) is the rail.

**Acceptance criteria:** see acceptance.md AC-SG-003.

### REQ-SG-004 — Show talking points are show-design research vs airable grounded facts, kept separate (Ubiquitous) [HARD]

The system SHALL distinguish a show's INTERNAL show-design research (material used purely to choose the
theme + the selection lens) from its AIRABLE TALKING POINTS (notes the host MAY voice). [HARD] A talking
point that will be SPOKEN SHALL be a GROUNDED fact (a KNOWLEDGE-008 sourced fact in the supplied context),
validated by the PROGRAMMING-007 Group PG grounding rule + quality gate UNCHANGED — never an unvalidated
Last.fm research string voiced directly. Internal show-design research is planning material only and is
never aired. That spoken talking points are grounded facts (not raw research) while design research stays
internal is the rail.

**Acceptance criteria:** see acceptance.md AC-SG-004.

### REQ-SG-005 — Durable per-persona show HISTORY ("last shows"); our data, not Last.fm events (Ubiquitous) [HARD]

The system SHALL persist a DURABLE PER-PERSONA SHOW HISTORY — the record of which shows a persona has run
(its `retired` Show records, REQ-SG-002, with `theme`/`angle`, `selection_lens`, `provenance`, and
timestamps) — as the "last shows" surface. [HARD] This history is OUR OWN data: Last.fm has NO events API
(it was retired in Last.fm's March-2016 relaunch, `research.md` §4/§5c) and no concept of our personas, so
the record of which shows ran is ours, merely INFORMED by Last.fm research. It lives in the existing store
seam (no new datastore) and is the SAME store that feeds the per-persona recent-shows novelty ledger
(REQ-SX-002), framed as history rather than only as a novelty input. That a durable per-persona show
history exists as our own data (never sourced from a Last.fm events API) is the rail.

**Acceptance criteria:** see acceptance.md AC-SG-005.

---

## 8X. Requirement Group SX — Editorial Variation Engine

Priority: High.

### REQ-SX-001 — LLM proposes a fresh show angle grounded in research + the persona's taste (Event-driven) [HARD]

When the engine plans a show for a persona (a slot becoming due, or the director self-initiating), the
system SHALL have the LLM PROPOSE an editorial angle/theme + a selection lens + candidate talking points,
GROUNDED in the supplied Last.fm research (Group LF) + the persona's taste profile (PROGRAMMING-007
REQ-PL-004 / the charter seed) + the available catalog. [HARD] The angle SHALL be editorial INVENTION
grounded in real research, NOT an engagement/popularity-optimized theme (inherited anti-pandering); and
the LLM call SHALL be best-effort — on an LLM/research error the engine falls back to a taste-only angle
or no show (plain curation), never stalling (NFR-S-1/S-5). That a show angle is an LLM-proposed,
research-grounded, taste-grounded editorial invention is the rail.

**Acceptance criteria:** see acceptance.md AC-SX-001.

### REQ-SX-002 — Per-persona recent-shows ledger + novelty check over a configurable window (Ubiquitous) [HARD] [consistency]

The system SHALL maintain a PER-PERSONA RECENT-SHOWS LEDGER (recently-run angles/themes with timestamps,
sourced from `retired` shows, REQ-SG-002) and SHALL run a NOVELTY CHECK that REJECTS a proposed angle too
similar to one this persona ran within a CONFIGURABLE WINDOW, triggering a regenerate (grounded in fresh
research). [HARD] [consistency] This is the load-bearing invariant of the SPEC and the direct encoding of
the user's "do not run the same kind of show week after week": no slot's show may repeat a recent kind of
show for that persona within the window; an angle that passes novelty becomes `active`, one that fails is
`rejected` and the engine regenerates (bounded retries, then falls back to a taste-only angle rather than
loop forever, NFR-S-5). [DECIDED D-S-4] The v1 novelty check is a LIGHTWEIGHT DETERMINISTIC text-similarity
comparison over the ledger's recent angle/theme text (keyed on persona + primary-genre-territory), with no
extra LLM call; an LLM-judged escalation is an optional future enhancement. The novelty threshold + window
length + max regenerate attempts are TUNABLE config; that a show angle must be novel against the persona's
recent shows is the rail.

**Acceptance criteria:** see acceptance.md AC-SX-002.

### REQ-SX-003 — Continuous fresh angles; never a fixed template (State-driven) [HARD]

While generating successive shows, the system SHALL vary the editorial angle CONTINUOUSLY — across
themes, lenses, and eras/genres/moods within the persona's territory — so the programme is a stream of
DIFFERENT shows, not one repeating skeleton. [HARD] The system SHALL NOT mechanically reuse a single show
template; reusing an angle/lens repeatedly is the exact failure REQ-SX-002 forbids. The variety cadence is
a tunable default the AI owns; that successive shows are genuinely different (not a fixed template) is the
rail. This composes with PROGRAMMING-007 Group PT show FORMATS: SHOWS-020 supplies the VARYING editorial
content over the available format skeletons, it does not re-own the skeletons.

**Acceptance criteria:** see acceptance.md AC-SX-003.

### REQ-SX-004 — Novelty-reject loop never blocks; bounded retries then graceful fallback (Unwanted) [HARD]

If the novelty check (REQ-SX-002) rejects proposed angles repeatedly, then the system SHALL NOT loop
indefinitely or stall the curation/talk path: after a BOUNDED number of regenerate attempts it SHALL fall
back to a taste-only angle (or no show + ordinary curation) and proceed. [HARD] A novelty-reject storm
(e.g. a persona with a thin catalog and many recent shows) degrades gracefully to plain operation; it
never blocks a director tick, a talk break, or playout. The retry bound is config; that the reject loop is
bounded and degrades gracefully is the rail.

**Acceptance criteria:** see acceptance.md AC-SX-004.

---

## 8Y. Requirement Group SP — Per-Persona Distinctness

Priority: High. [Depends on PROGRAMMING-007 Group PR — GREENFIELD; see Section 2.]

### REQ-SP-001 — Shows are generated per-persona in their own taste/voice (Ubiquitous) [HARD]

The system SHALL generate each show FOR a specific roster persona, IN that persona's taste/voice/territory
— consuming the PROGRAMMING-007 persona roster (Group PR), taste charter (REQ-PR-006), persistent POV
(REQ-PR-005), and evolving taste profile (REQ-PL-004) — so a show reads as THAT host's show. [HARD] The
engine consumes the persona model by reference; it does NOT re-own the roster or the taste profile.
[HARD][GREENFIELD] Until the roster ships (it is specified in PROGRAMMING-007 but not yet built — the talk
layer uses one generic HOST_PERSONA), the engine degrades to a SINGLE DEFAULT persona: shows still vary
(the novelty engine runs against that persona's own recent shows) and stay grounded; per-persona
distinctness activates when the roster lands, with NO SHOWS-020 change. [DECIDED D-S-1] SHOWS-020 ships NOW
in this single-default-persona mode (the variation engine is roster-independent); it is not sequenced
behind the roster. That shows are per-persona (degrading to a single default persona pre-roster) is the
rail.

**Acceptance criteria:** see acceptance.md AC-SP-001.

### REQ-SP-002 — The roster never converges; one persona's angle is never reused for another (Ubiquitous) [HARD]

The system SHALL keep the roster's shows DISTINCT — a show angle/lens generated for one persona SHALL NOT
be reused for another, and the engine SHALL obey the PROGRAMMING-007 anti-convergence firewall
(REQ-PR-004: no two personas share a primary genre territory + rotation pool) UNCHANGED. [HARD] No
homogenizing behavior — no shared global "show of the week", no copying a successful angle across personas
— is permitted; each persona's programme stays its own. SHOWS-020 references the firewall, it does not
re-own or weaken it. That the roster never converges and angles are not shared across personas is the rail.

**Acceptance criteria:** see acceptance.md AC-SP-002.

### REQ-SP-003 — Per-persona distinctness is preserved against the shared engine (Ubiquitous) [HARD]

The shared show-variation ENGINE SHALL NOT homogenize the roster: the recent-shows ledger, the novelty
window, and the taste grounding are all PER-PERSONA, and the anti-convergence + disjoint-territory
discipline (PROGRAMMING-007 REQ-PR-004 / the persona voice-card distinctness) applies unchanged. [HARD] A
single uniform show behaviour across hosts is forbidden; the engine being shared is an implementation
detail, not a convergence force. That the shared engine preserves per-persona distinctness is the rail.

**Acceptance criteria:** see acceptance.md AC-SP-003.

---

## 9. Requirement Group SD — Scheduling / Direction

Priority: High.

### REQ-SD-001 — An active show biases the director's curation/wishlist as a non-binding input (Event-driven) [HARD]

When a show is `active`, the system SHALL apply its `selection_lens` as a NON-BINDING BIAS on
`brain/director.py`'s curation/wishlist input — exactly the way the existing `seed_reference` is a
non-binding reference to the curation batch ([DECIDED D-S-2]: this lens-hint seam, NOT a director rewrite) —
so the show shapes WHAT the director researches/wishlists + biases the picker toward. [HARD] The lens SHALL NOT force-insert tracks, override rotation/clock/no-repeat,
or remove the picker's autonomy; the picker MAY still decline a lens-favoured track. An active show shapes
direction; it does not command the playout. That the active show biases (never forces) curation is the
rail.

**Acceptance criteria:** see acceptance.md AC-SD-001.

### REQ-SD-002 — An active show feeds the talk theme + talking points into the talk context (Event-driven) [HARD]

When a talk break is generated during an `active` show, the system SHALL ADD the show's `theme` + its
grounded `talking_points` into the EXISTING `brain/talk.py` `_build_context` bundle (alongside the
HOSTCTX-016 per-song facts and the KNOWLEDGE-008 grounding feed), so the host's spoken breaks reflect the
show the listener is hearing. [HARD] This EXTENDS the existing context dict in place (a show-level key
beside the per-song keys); it does NOT fork the talk-context wiring or add a second talk loop. A break
without an active show simply omits the show keys (the existing behaviour). That an active show feeds its
theme + grounded talking points into the existing talk context is the rail.

**Acceptance criteria:** see acceptance.md AC-SD-002.

### REQ-SD-003 — Spoken show content is grounded + gate-validated like any host fact (Ubiquitous) [HARD]

The system SHALL treat any spoken show talking point as a FACT TOKEN subject to the PROGRAMMING-007
grounding rule (REQ-PG-002) + two-tier quality gate (REQ-PG-005) UNCHANGED: a talking point not traceable
to a supplied grounded fact FAILS the forbidden-fact scan, regenerates once, and is skipped on a second
FAIL. [HARD] SHOWS-020 adds NO new gate and weakens none; a show theme is editorial framing, but any
factual claim within a spoken break must pass the same closed-world validation the host's other facts
pass. A show angle being interesting never licenses an ungrounded claim. That spoken show content is
grounded + gate-validated like any host fact is the rail.

**Acceptance criteria:** see acceptance.md AC-SD-003.

### REQ-SD-004 — Director decides the show when no host is scheduled (Event-driven) [HARD]

When no scheduled-host persona is presenting, the system SHALL let the LLM DIRECTOR (CORE-001 REQ-D-006/007)
decide the show itself — its angle, lens, and talking points — under the SAME rails as a persona's
(grounded, novel against the recent-shows ledger, never-blocks). [HARD] The director has DISCRETION over
which show to run when unhosted (consistent with HOSTCTX-016 director discretion), NOT over the
grounding/novelty/non-blocking discipline, which is invariant. WHEN a show runs + WHICH persona is on-air
remains the OPS-004 Group OA / ORCH-005 scheduler's call (referenced, not re-owned). That the director
decides the unhosted show under the same rails is the rail.

**Acceptance criteria:** see acceptance.md AC-SD-004.

### REQ-SD-005 — Per-persona forward "planned shows" schedule; our data, distinct from the time-grid (Ubiquitous) [HARD]

The system SHALL maintain a PER-PERSONA FORWARD "PLANNED SHOWS" SCHEDULE — a bounded queue of upcoming
planned show CONTENT (novelty-passed `proposed` shows queued ahead, REQ-SG-002/SX-002) that the engine
persists and the director consumes when a slot for that persona comes due. [HARD] This forward schedule is
OUR OWN data (`research.md` §5d); Last.fm contributes only the research that shapes each planned show, not
the schedule itself. [HARD] It is DISTINCT from the OPS-004 Group OA / ORCH-005 TIME-GRID, which remains
the sole owner of WHEN a slot occurs + WHICH persona is on-air — SHOWS-020 supplies the queued show CONTENT
and rides that discretion; it never forks the schedule store or becomes a daypart scheduler. [HARD] The
planned-shows queue is bounded, never-blocks, and degrades gracefully: an empty queue falls back to
just-in-time angle proposal (REQ-SX-001), and a queued show still passes the novelty check against the
persona's recent shows at activation time (REQ-SX-002). That a per-persona forward planned-shows schedule
exists as our data, distinct from the time-grid, is the rail.

[ADDITIVE — multi-session series seam] A planned-shows queue ENTRY MAY OPTIONALLY carry an `episode_id`, a
`part_number`, and a `series_arc_id`. [HARD] This is a PURE ADDITIVE FIELD extension on the QUEUE ENTRY: the
per-session `Show` record (REQ-SG-001) is UNTOUCHED, the novelty check (REQ-SX-002) and the show-history
ledger (REQ-SG-005) are UNCHANGED, and the fields are INERT in SHOWS-020 — a single-session show ignores
them and behaves exactly as before. They exist solely as the FORWARD-REFERENCE seam consumed by the future
SPEC-RADIO-LONGFORM-025 Group LB (not yet authored), which reads the REQ-SX-002 novelty ledger + the
REQ-SG-005 history + these optional fields to thread multi-part series across sessions. SHOWS-020 records
the seam so the queue is not later forked; it does NOT itself implement multi-session threading (that is
LONGFORM-025's, referenced not re-owned). That the episode/part/arc fields are an optional, inert, additive
queue-entry extension reserving the LONGFORM-025 seam is the rail.

**Acceptance criteria:** see acceptance.md AC-SD-005.

---

## 10X. Requirement Group SB — Show Wiring (brain-only integration)

Priority: High.

### REQ-SB-001 — Additive wiring into the existing director + talk loops + config; no fork (Event-driven) [HARD]

When the show engine is integrated, the system SHALL ADD it to the EXISTING brain seams — the
`brain/director.py` curation tick (the show lens biases the curation batch like `seed_reference`), the
`brain/talk.py` `_build_context` assembly (the show theme + talking points join the existing bundle), and
new `brain/config.py` knobs (enable toggle, anti-repetition window, cadence, Last.fm rate/timeout) —
WITHOUT a new service, a store fork, a second director/talk loop, or a Liquidsoap change. [HARD] The show
records + recent-shows ledger live in the existing store seam (no new datastore). Fields are populated
best-effort: with the engine disabled or empty, the director + talk loops behave exactly as before this
SPEC. That the wiring is additive into the existing seams (no fork) is the rail.

**Acceptance criteria:** see acceptance.md AC-SB-001.

### REQ-SB-002 — Strictly off the playout pull path (Unwanted) [HARD]

If the show planning, the Last.fm research, or the show-context assembly is slow, errors, or finds
nothing, then the `/api/next` playout pull SHALL NOT wait on it or be affected: all SHOWS-020 work runs on
the director tick + the talk-context-assembly path (the same best-effort, exception-swallowing background
paths those loops already use), NEVER on the sub-1s pull. [HARD] An error in SHOWS-020 wiring SHALL log
and be skipped (the show simply does not apply this tick / the show keys are not added), preserving the
existing curation + break and never crashing the director loop, the talk loop, or the daemon. That all
SHOWS-020 work is strictly off the pull path is the rail.

**Acceptance criteria:** see acceptance.md AC-SB-002.

---

## 11. Non-Functional Requirements

### NFR-S-1 — Never blocks / silences playout; fully graceful (Ubiquitous) — Priority High
The show subsystem shall NEVER block or silence playout: research is key-gated + exception-isolated, show
planning is best-effort background work off the pull path (REQ-LF-005, REQ-SB-002), and missing research /
an absent show / an absent key / a novelty-reject loop degrades gracefully (taste-only angle / single
default persona / no show + plain curation). Inherits CORE-001's continuous-operation identity. See
acceptance.md AC-NFR-S-1.

### NFR-S-2 — Anti-repetition is load-bearing: shows vary, never the same kind week after week (Ubiquitous) — Priority High
No slot's show shall repeat a recent KIND of show for that persona within the configurable window: the
per-persona recent-shows ledger + the novelty check (REQ-SX-002) structurally defeat show-sameness, the
direct encoding of the user's intent. This is the load-bearing NFR. See acceptance.md AC-NFR-S-2.

### NFR-S-3 — Grounded integrity: never a confident-wrong show fact (Ubiquitous) — Priority High
Every spoken show talking point shall trace to a supplied grounded fact and pass the PROGRAMMING-007
REQ-PG-005 forbidden-fact scan + adversarial self-check unchanged; a show angle being compelling never
licenses an ungrounded claim; a FAIL never airs (REQ-SD-003, REQ-SG-004). See acceptance.md AC-NFR-S-3.

### NFR-S-4 — Single-source-of-truth: reference siblings, never re-own; brain-only + additive (Ubiquitous) — Priority High
No code path shall re-own or fork the PROGRAMMING-007 roster / taste profile / firewall / show formats /
grounding gate, the ANALYSIS-006 genre consensus, the KNOWLEDGE-008 fact graph, the HOSTCTX-016 per-song
facts, the MBMIRROR-017 mirror, the OPS-004/ORCH-005 scheduler, or the CORE-001 picker; each is referenced
by id and consumed. SHOWS-020 is brain-only + additive (a research client + show model + variation engine
+ wiring on the existing brain package, loops, and store; no new service, no new datastore). See
acceptance.md AC-NFR-S-4.

### NFR-S-5 — A show biases, never forces; picker autonomy preserved (Ubiquitous) — Priority High
No code path shall let a show's selection lens force-insert tracks, override rotation/clock/no-repeat, or
remove the picker's autonomy: the lens is a non-binding curation/wishlist bias (REQ-SD-001, like
`seed_reference`), and a lens resolving to nothing degrades to ordinary curation. See acceptance.md
AC-NFR-S-5.

### NFR-S-6 — Per-persona distinctness preserved; the roster never converges (Ubiquitous) — Priority High
The shared engine shall not homogenize the roster: the ledger, novelty window, and taste grounding are
per-persona and the PROGRAMMING-007 REQ-PR-004 anti-convergence firewall applies unchanged; no angle is
shared across personas, no uniform every-host show is imposed (REQ-SP-001/002/003). See acceptance.md
AC-NFR-S-6.

### NFR-S-7 — Bounded, throttled processing (Ubiquitous) — Priority Medium
The Last.fm research + show-planning jobs, AND every Group SM multi-source human-DJ provider poll
(REQ-SM-005), shall be BOUNDED and THROTTLED (OPS-004 REQ-OH-006 pattern, REQ-LF-005) — each provider on its
own per-source cadence (KEXP/SR ≤ 1 req/s, scrape sources slower, ASOT/cuenation weekly) — so the provider
fan-out does not jointly overload the modest box alongside playout, acquisition, analysis, and knowledge
research. See acceptance.md AC-NFR-S-7.

### NFR-S-8 — Last.fm ToS compliance (Ubiquitous) — Priority High
The Last.fm research client + any store it builds shall comply with the Last.fm Terms of Service as
verified in `research.md` §3: (a) [HARD] CACHE responses per the HTTP cache headers / a sane TTL (ToS
4.3.4 makes caching a REQUIREMENT, not an optimization); (b) [HARD] keep stored Last.fm-derived data under
the 100 MB Reasonable-Usage cap (4.3.4) and prune accordingly — SHOWS-020 persists only small derived
notes (tags, similar-artist names, match scores, bio snippets used as input), so this is easily met but
must be bounded; (c) [HARD] use Last.fm strictly as PRIVATE, NON-COMMERCIAL research INPUT (ToS 3.1) — do
NOT re-publish raw Last.fm data as station content or build a public mirror; (d) set an identifiable
User-Agent on every request; (e) attach Last.fm attribution + the returned `url` back-link IF any
Last.fm-derived text/link is ever surfaced to listeners (4.2.2); and (f) observe the polite ≤ 1 req/s
default with error-29/16 backoff (REQ-LF-002). A `partners@last.fm` contact is a prerequisite IF the
station is ever monetized or Last.fm data surfaces verbatim to listeners (Section 13). See acceptance.md
AC-NFR-S-8.

---

## 12. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 + the
Section 13 roadmap, as the mandatory exclusions list):

- **The persona ROSTER + taste charter + anti-convergence firewall + evolving taste profile** — owned by
  PROGRAMMING-007 Group PR / REQ-PL-004; consumed, never re-owned (REQ-SP-001/002).
- **The show FORMATS / recurring-segment skeletons (incl. Solstice Hour)** — owned by PROGRAMMING-007
  Group PT; SHOWS-020 generates VARIATION over them, never re-owns the skeletons (REQ-SX-003).
- **A second Last.fm GENRE-CONSENSUS provider** — the ANALYSIS-006 `brain/metadata.py` provider stays the
  sole genre-consensus path; the Group LF research client is separate and does not re-derive consensus
  (REQ-LF-003).
- **The artist/music KNOWLEDGE GRAPH + dated/sourced facts + the grounding feed** — owned by KNOWLEDGE-008;
  airable talking points are grounded facts from it; no parallel trivia channel (REQ-SG-004, REQ-SD-003).
- **The grounded-voice fact contract + two-tier quality gate + forbidden-fact scan** — owned by
  PROGRAMMING-007 Group PG; talking points route through them unchanged; no new gate (REQ-SD-003).
- **The per-song year/album/curiosa host facts** — owned by HOSTCTX-016; SHOWS-020 adds per-SESSION show
  content above them (REQ-SD-002).
- **The self-hosted MusicBrainz mirror + Discogs/Last.fm cross-check infra** — owned by MBMIRROR-017;
  SHOWS-020's Last.fm client is the light direct path (REQ-LF-003).
- **The SCHEDULER / dayparting / WHEN a show runs / WHICH persona is on-air (the TIME-GRID)** — owned by
  OPS-004 Group OA / ORCH-005; SHOWS-020 supplies show content + a per-persona forward "planned shows"
  CONTENT queue (REQ-SD-005) and rides their discretion; it never forks the time-grid scheduler
  (REQ-SD-004).
- **The next-track PICKER + the playout chain** — owned by CORE-001 / OPS-004; a show lens is a
  non-binding bias INPUT, never a re-owned picker, force-insert, or synchronous playout insertion
  (REQ-SD-001, NFR-S-5).
- **TTS synthesis + ear-writing the spoken line** — owned by VOICE-002 + PROGRAMMING-007 Group PS;
  SHOWS-020 owns show CONTENT, not phrasing/synthesis.
- **The acquisition pipeline + provenance + grab-reason + diary** — owned by OPS-004 Group OH /
  PROGRAMMING-007 Group PL; a show lens biases what is wishlisted, never re-owning acquisition.
- **A public-facing show schedule / programme guide UI** — deferred; owned by CORE-001 Group E /
  WEBUI-018; a show-guide is a future enhancement (Section 13).
- **Engagement/popularity-optimized show themes** — barred; angles are editorial invention grounded in
  research, never an appeal target (inherited CORE-001 REQ-OF-004).
- **A new datastore or a new web service** — brain-only + additive; show records + ledger live in the
  existing store seam (NFR-S-4).
- **Copying any human-DJ source's playlist / putting source picks into rotation** — barred; a human-DJ
  cluster from ANY Group SK / Group SM source (KEXP, Sveriges Radio, BBC, A State of Trance, NTS) is a THREAD
  HYPOTHESIS / research lead only (REQ-SK-003, REQ-SM-005), never voiced raw (REQ-LF-006) and never a track
  source: the station plays ONLY its own catalog, source track ids never enter any rotation pool, and the
  PROGRAMMING-007 REQ-PR-009 per-track exclusivity rule is UNAFFECTED.
- **Treating a show-level signal as a track sequence / inferring phantom transitions** — barred; the NTS
  `/api/v2/live` show-level signal (and any non-ordered source) is CONTEXT / labeling ONLY (show / host /
  genre / locality), never an ordered sequence — the engine SHALL NOT infer a segue or transition from it
  (REQ-SM-004). Only per-track-ordered sources are craft fuel.
- **Re-owning the AcoustID / MusicBrainz identify pipeline** — barred; the Group SM BBC DASH
  stream-fingerprint mode (REQ-SM-002) REUSES the SPEC-RADIO-ENRICH-012 AcoustID->MusicBrainz identify
  pipeline by reference; SHOWS-020 does not fork or re-own identification logic.
- **Multi-session / multi-part series threading** — NOT built here; the OPTIONAL `episode_id` / `part_number` /
  `series_arc_id` queue-entry fields (REQ-SD-005) are an INERT reserved seam consumed by the future
  SPEC-RADIO-LONGFORM-025 Group LB. SHOWS-020 stays single-session; the per-session `Show` model + the novelty
  check are unchanged.

---

## 13. User-Provisioned Prerequisites + Out-of-Scope / Future Roadmap

[HARD] SHOWS-020 does NOT provision any external account. The following are flagged so the user knows
what is required, plus the deferred roadmap.

- **The Last.fm API key.** The Last.fm research client (Group LF) runs only with `BRAIN_LASTFM_API_KEY`
  set (already a config field). The user must obtain a free Last.fm API key to enable richer research;
  read-only methods need ONLY this key — no OAuth/session/signature (`research.md` §2–§3.1); with no key
  the engine runs in taste-only mode and the station is unaffected (REQ-LF-001).
- **Last.fm ToS posture (non-commercial + partners@last.fm).** Last.fm Data is licensed for NON-COMMERCIAL
  use only (ToS 3.1), with caching required and a 100 MB Reasonable-Usage cap (4.3.4, `research.md` §3).
  SHOWS-020 uses Last.fm strictly as private research INPUT and airs nothing raw (NFR-S-8). [HARD] If the
  station is ever MONETIZED, or if any Last.fm-derived text/link is ever surfaced verbatim to listeners,
  the user MUST contact `partners@last.fm` for a commercial/usage agreement and add Last.fm attribution
  before doing so. This is a user-provisioned legal prerequisite, not something SHOWS-020 can satisfy in
  code.
- **The KEXP thread signal (no key required).** The Group SK KEXP client uses the PUBLIC, NO-AUTH KEXP API v2
  plays feed — no key/account is provisioned. It is OFF by default (`kexp_thread_enabled=false`); the user/AI
  enables it to let real-world human-DJ thread hypotheses seed show angles. With it off or failing the engine
  falls back to Last.fm + taste-only angles and the station is unaffected (REQ-SK-001/004).
- **The multi-source human-DJ signal providers (no key required).** The Group SM providers (REQ-SM-001/002)
  use PUBLIC / keyless endpoints + scrapes — no account is provisioned. Each is OFF by default behind its own
  flag: `sr_thread_enabled` (Sveriges Radio `api.sr.se`), `bbc_thread_enabled` (BBC Radio 1 segments + the
  heavier DASH stream-fingerprint mode), `asot_thread_enabled` (A State of Trance via cuenation `.cue` +
  `astateoftrance.com` + a throttled 1001tracklists cross-check), and `nts_thread_enabled` (NTS `/api/v2/live`
  context + episode-page scrape). The user/AI enables individual sources; all off, the engine behaves exactly
  as with only Group SK (or taste-only). [HARD] The BBC DASH stream-fingerprint mode REUSES the
  SPEC-RADIO-ENRICH-012 AcoustID->MusicBrainz identify pipeline (which must exist for that heavier sub-path);
  if ENRICH-012 is absent the BBC stream-fingerprint sub-path simply yields no sequence and degrades to the
  BBC `segments.json` path (REQ-SM-002/005).
- **The persona roster.** Per-persona distinctness (Group SP) depends on the PROGRAMMING-007 roster, which
  is greenfield; until it ships SHOWS-020 runs against a single default persona (REQ-SP-001).
- **The anti-repetition window + novelty threshold + cadence.** The recent-shows window, the novelty
  similarity threshold, the max regenerate attempts, and the show cadence are config with sane defaults;
  the user/AI may tune them (REQ-SX-002, REQ-SB-001).

Future roadmap (out of scope for v1):
- **A public programme guide / show schedule on the website** — a CORE-001 Group E / WEBUI-018 surface
  showing "what's on / what's coming"; bounded by the honest-numbers + no-vanity rails of those SPECs.
- **Cross-show story arcs / multi-session series** — a persona running a multi-week themed series; a
  richer variation model on top of the single-session show. Owned by the future SPEC-RADIO-LONGFORM-025
  Group LB, which CONSUMES the SHOWS-020 seams reserved at v0.3.0 (the REQ-SX-002 novelty ledger, the
  REQ-SG-005 history, and the optional `episode_id` / `part_number` / `series_arc_id` REQ-SD-005 queue-entry
  fields); SHOWS-020 stays single-session.
- **Listener-signal-aware show angles** — letting REQUEST-011 want-counts / LIKE-015 signals softly
  inform show theme selection as ONE non-binding curatorial input, bounded by the anti-pandering rail
  (counts never bind, never an appeal target).
- **Last.fm scrobble-derived discovery** — using a station Last.fm account's scrobbles as additional
  research; deferred.

---

## 14. Decisions (resolved 2026-06-23)

The five judgment calls the v0.1.0 draft surfaced have been RULED by the orchestrator and are now DECIDED.
Each ruling is folded into the affected requirements (cited inline); the rulings are recorded here as the
authoritative resolution.

- **D-S-1 — Greenfield persona roster → DECIDED: SHIP NOW in single-default-persona mode.** The
  variation engine is ROSTER-INDEPENDENT: the novelty engine + grounding work immediately against a single
  default persona's own recent shows. Per-persona DISTINCTNESS (Group SP) activates automatically when the
  PROGRAMMING-007 roster (Group PR) lands, with NO SHOWS-020 change. Variation is the user's headline ask
  and works pre-roster, so SHOWS-020 ships now rather than being sequenced after the roster. Reflected in
  REQ-SP-001 and the Section 5 [GREENFIELD] constraint.
- **D-S-2 — How a show drives the director loop → DECIDED: NON-BINDING bias, like `seed_reference`.** An
  active show's `selection_lens` is threaded into the existing `brain/director.py` curation batch as a
  NON-BINDING bias exactly the way `seed_reference` already is (a lens hint added to the existing batch
  prompt), and the show theme rides the existing talk-context bundle. This is the integration seam — NOT a
  director rewrite into a show-aware scheduler. It is additive, preserves picker autonomy, and is the
  lowest-regression seam. Reflected in REQ-SD-001 / REQ-SB-001 and NFR-S-5.
- **D-S-3 — Last.fm research client placement → DECIDED: SEPARATE `brain/lastfm.py` module.** The
  SHOWS-020 research client is a SEPARATE module (`brain/lastfm.py`) that SHARES the key
  (`lastfm_api_key`) + the rate-limit / timeout / exception-isolation discipline with `brain/metadata.py`,
  but does NOT extend `metadata.py`'s genre-consensus logic. The research methods
  (`getSimilar` / `getTopArtists` / `getInfo` / `tag.*` / `chart.*` / `geo.*`) serve show DESIGN, not
  genre consensus; keeping them apart preserves the single-purpose `enrich()` rail. Reflected in
  REQ-LF-003 (and the OWNS list + glossary, which now name `brain/lastfm.py`).
- **D-S-4 — Novelty check mechanism → DECIDED: deterministic text-similarity check for v1.** The novelty
  check (REQ-SX-002) is a LIGHTWEIGHT DETERMINISTIC text-similarity comparison over recent angle/theme
  text in the per-persona ledger, with a tunable threshold + the persona + primary-genre-territory keys —
  cheap, no extra LLM call. An LLM-judged novelty escalation is an OPTIONAL future enhancement, not v1.
  Reflected in REQ-SX-002 and R-S-2.
- **D-S-5 — Airable-fact boundary for Last.fm research → DECIDED: KNOWLEDGE-008 is the single home.**
  KNOWLEDGE-008 is the SINGLE home for AIRABLE Last.fm-derived facts (it owns provenance + freshness);
  Last.fm research is show-DESIGN material until it lands as a KNOWLEDGE-008 sourced fact and passes the
  PROGRAMMING-007 grounding gate. A Last.fm bio line is NEVER directly airable — it must first enter
  KNOWLEDGE-008, never bypassing the grounding gate (the single grounded-fact seam, mirrors HOSTCTX-016
  REQ-HW-003). Reflected in REQ-LF-006, REQ-SG-004, and REQ-SD-003.

---

## 15. Risks

- **R-S-1 — Greenfield persona roster (Medium, dependency).** Per-persona distinctness (Group SP) biases on
  a roster that does not yet exist. Mitigated: REQ-SP-001 degrades to a single default persona; variation +
  grounding hold; distinctness activates when the roster ships. Resolved: D-S-1 = ship now in
  single-default-persona mode.
- **R-S-2 — Novelty false-negatives / false-positives (Medium, build-time).** A weak novelty check could
  let near-duplicate shows through, or reject genuinely-fresh angles. Mitigated: tunable threshold + window
  + bounded regenerate + graceful fallback (REQ-SX-002/004); D-S-4 RULED the mechanism (deterministic
  text-similarity for v1, optional LLM-judged escalation later). Open: tune against observed angles.
- **R-S-3 — Thin catalog starves the lens (Medium, honesty).** A selection lens (e.g. "artists similar to
  Y") may resolve to few/no catalog tracks. Mitigated: the lens degrades to a wishlist hint + ordinary
  curation (REQ-SG-003, NFR-S-5); it never fabricates or force-inserts. Open: lens-fit feedback could
  inform future acquisition (roadmap).
- **R-S-4 — Last.fm rate/availability (Low/Medium).** Last.fm could rate-limit or be down. Mitigated:
  rate-limit + timeout + exception-isolation + key-gating (REQ-LF-001/002); the engine falls back to
  taste-only angles. Open: tune the polite rate.
- **R-S-5 — Show-fact honesty drift (Low, honesty).** A compelling show angle could tempt an ungrounded
  spoken claim. Mitigated: REQ-SD-003 routes every spoken talking point through the unchanged PG gate +
  forbidden-fact scan; the show theme is editorial framing, but factual claims must be grounded. Open: keep
  the gate assertion in CI.
- **R-S-6 — Over-engineering the show model (Low).** A show model could balloon into a full scheduler —
  especially with the new forward "planned shows" queue (REQ-SD-005). Mitigated: NFR-S-4 + the
  additive-wiring rail (REQ-SB-001) keep it brain-only; D-S-2 RULED the non-binding bias seam; the
  time-grid stays OPS-004/ORCH-005's (REQ-SD-005 supplies CONTENT only, never WHEN/WHICH). Open: hold the
  line on the bias seam + the content/time-grid split.
- **R-S-7 — bhive had no proven pattern for this stack (Low, recorded gap).** No bhive instruction exists
  for the Last.fm-research-driven per-persona show-variation pattern. Mitigated: grounded in the existing
  code (the metadata.py Last.fm provider, the director seed_reference seam, the talk-context bundle).
  Action: re-run a bhive query during implementation and contribute back per AGENTS.md.
- **R-S-8 — KEXP API drift / availability (Low/Medium).** The KEXP API v2 plays endpoint
  (`/v2/plays/?ordering=-airdate`) or its show FK could change shape or be unavailable. Mitigated: the Group SK
  client is keyless + OFF by default + cached + timed-out + exception-isolated and returns EMPTY on ANY error
  (REQ-SK-001/002); a KEXP outage simply falls the engine back to Last.fm + taste-only angles (REQ-SK-004),
  never blocking. Open: re-confirm the endpoint shape at build time.
- **R-S-9 — KEXP as a homogenizer (Low, distinctness).** A single shared KEXP signal could tempt the engine to
  push two personas toward the same thread. Mitigated: REQ-SK-004 routes every KEXP-seeded angle through the
  same per-persona taste / novelty / anti-convergence (REQ-PR-004 + REQ-PR-009) gates and DROPS a thread outside
  a persona's lane — one signal refracted divergently, the firewall wins. Open: keep the refraction assertion
  (B11) in CI.
- **R-S-10 — Multi-source provider fan-out / source drift (Low/Medium, availability + load).** Five providers
  polling distinct keyless APIs + scrapes could overload the box or break when an endpoint changes shape (SR
  channel id, BBC `segments.json`, NTS `/api/v2/live`, cuenation page layout). Mitigated: the thin provider
  interface returns EMPTY on ANY failure and never raises (REQ-SM-001); each provider is OFF by default + on
  its own per-source throttle/cadence (REQ-SM-005, NFR-S-7); one source's drift falls the engine back to the
  remaining enabled sources + Last.fm + taste-only angles, never blocking. Open: re-confirm each endpoint shape
  at build time; the scrape sources (ASOT/NTS/1001tracklists) are the most drift-prone.
- **R-S-11 — Phantom transitions from show-level / fingerprint heaviness (Low/Medium, honesty + cost).** A
  show-level NTS-live signal could be mistaken for an ordered sequence (a phantom segue), and the BBC DASH
  stream-fingerprint mode is a heavy fpcalc + ENRICH-012 identify pass. Mitigated: REQ-SM-004 makes show-level
  signals CONTEXT-ONLY (never phantom transitions) and tags every cluster with a sequence-confidence the
  consumer weights by; the stream-fingerprint mode is the bounded, off-by-default last-resort sub-path within
  the BBC provider (prefer in-band metadata, then `segments.json`) and reuses ENRICH-012 by reference
  (REQ-SM-002/005). Open: keep the sequence-confidence + no-phantom-transition assertion (B12) in CI; tune the
  fpcalc window bound.

---

## 16. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements are in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-LF-001 | Last.fm Research Client | High | Ubiquitous | AC-LF-001 |
| REQ-LF-002 | Last.fm Research Client | High | Ubiquitous | AC-LF-002 |
| REQ-LF-003 | Last.fm Research Client | High | Ubiquitous | AC-LF-003 |
| REQ-LF-004 | Last.fm Research Client | Medium | Ubiquitous | AC-LF-004 |
| REQ-LF-005 | Last.fm Research Client | High | State | AC-LF-005 |
| REQ-LF-006 | Last.fm Research Client | High | Ubiquitous | AC-LF-006 |
| REQ-SG-001 | Show / Program Model | High | Ubiquitous | AC-SG-001 |
| REQ-SG-002 | Show / Program Model | High | Ubiquitous | AC-SG-002 |
| REQ-SG-003 | Show / Program Model | High | Ubiquitous | AC-SG-003 |
| REQ-SG-004 | Show / Program Model | High | Ubiquitous | AC-SG-004 |
| REQ-SG-005 | Show / Program Model | High | Ubiquitous | AC-SG-005 |
| REQ-SX-001 | Editorial Variation Engine | High | Event | AC-SX-001 |
| REQ-SX-002 | Editorial Variation Engine | High | Ubiquitous | AC-SX-002 |
| REQ-SX-003 | Editorial Variation Engine | High | State | AC-SX-003 |
| REQ-SX-004 | Editorial Variation Engine | High | Unwanted | AC-SX-004 |
| REQ-SP-001 | Per-Persona Distinctness | High | Ubiquitous | AC-SP-001 |
| REQ-SP-002 | Per-Persona Distinctness | High | Ubiquitous | AC-SP-002 |
| REQ-SP-003 | Per-Persona Distinctness | High | Ubiquitous | AC-SP-003 |
| REQ-SD-001 | Scheduling / Direction | High | Event | AC-SD-001 |
| REQ-SD-002 | Scheduling / Direction | High | Event | AC-SD-002 |
| REQ-SD-003 | Scheduling / Direction | High | Ubiquitous | AC-SD-003 |
| REQ-SD-004 | Scheduling / Direction | High | Event | AC-SD-004 |
| REQ-SD-005 | Scheduling / Direction | High | Ubiquitous | AC-SD-005 |
| REQ-SB-001 | Show Wiring | High | Event | AC-SB-001 |
| REQ-SB-002 | Show Wiring | High | Unwanted | AC-SB-002 |
| REQ-SK-001 | KEXP Human-DJ Thread Signal | Medium | Ubiquitous | AC-SK-001 |
| REQ-SK-002 | KEXP Human-DJ Thread Signal | High | Ubiquitous | AC-SK-002 |
| REQ-SK-003 | KEXP Human-DJ Thread Signal | High | Ubiquitous | AC-SK-003 |
| REQ-SK-004 | KEXP Human-DJ Thread Signal | High | Event | AC-SK-004 |
| REQ-SM-001 | Multi-Source Human-DJ Signal | Medium | Ubiquitous | AC-SM-001 |
| REQ-SM-002 | Multi-Source Human-DJ Signal | Medium | Ubiquitous | AC-SM-002 |
| REQ-SM-003 | Multi-Source Human-DJ Signal | High | Ubiquitous | AC-SM-003 |
| REQ-SM-004 | Multi-Source Human-DJ Signal | High | Ubiquitous | AC-SM-004 |
| REQ-SM-005 | Multi-Source Human-DJ Signal | High | Ubiquitous | AC-SM-005 |
| NFR-S-1 | Non-Functional | High | Ubiquitous | AC-NFR-S-1 |
| NFR-S-2 | Non-Functional | High | Ubiquitous | AC-NFR-S-2 |
| NFR-S-3 | Non-Functional | High | Ubiquitous | AC-NFR-S-3 |
| NFR-S-4 | Non-Functional | High | Ubiquitous | AC-NFR-S-4 |
| NFR-S-5 | Non-Functional | High | Ubiquitous | AC-NFR-S-5 |
| NFR-S-6 | Non-Functional | High | Ubiquitous | AC-NFR-S-6 |
| NFR-S-7 | Non-Functional | Medium | Ubiquitous | AC-NFR-S-7 |
| NFR-S-8 | Non-Functional | High | Ubiquitous | AC-NFR-S-8 |

Parity: 34 REQ + 8 NFR = 42 specified items; 42 acceptance entries (34 AC + 8 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: LF (Last.fm Research Client) = 6, SK (KEXP Human-DJ Thread Signal) = 4, SM
(Multi-Source Human-DJ Signal) = 5, SG (Show / Program Model) = 5, SX (Editorial Variation Engine) = 4, SP
(Per-Persona Distinctness) = 3, SD (Scheduling / Direction) = 5, SB (Show Wiring) = 2 →
6+4+5+5+4+3+5+2 = 34 REQ across 8 groups. NFR-S-1…8 = 8 NFR. Total = 34 + 8 = 42 specified items, 42
acceptance entries, 1:1 REQ↔AC.
