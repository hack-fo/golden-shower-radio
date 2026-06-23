---
id: SPEC-RADIO-KNOWLEDGE-008
version: 0.3.2
status: draft
created: 2026-06-22
updated: 2026-06-23
author: charlie
priority: High
issue_number: 8
---

# SPEC-RADIO-KNOWLEDGE-008 — Artist & Music Knowledge Base

## HISTORY

- 2026-06-22 (v0.1.0): Initial draft. The sixth authored SPEC in the
  golden-shower-radio RADIO series and the EDITORIAL-KNOWLEDGE layer of the autonomous
  AI radio station. Where SPEC-RADIO-CORE-001 owns the music engine + library store +
  program-director loop + website; SPEC-RADIO-VOICE-002 owns TTS; SPEC-RADIO-OPS-004
  owns the autonomous program director, imaging, the self-learning playbook STORE
  (append-only ledger + diary), newscasting, and library/acquisition policy;
  SPEC-RADIO-ORCH-005 owns the director-loop / world-model / event-reaction nervous
  system; SPEC-RADIO-ANALYSIS-006 owns the per-TRACK audio-feature DATA MODEL
  (genre/key/bpm/energy/tags), the Last.fm SIMILAR-ARTIST edges, the library auto-ingest
  scan (REQ-AP-007), and the queryable track catalog (Group AD); and
  SPEC-RADIO-PROGRAMMING-007 owns the persona roster, taste charters, and radio-craft +
  ear-writing rules — KNOWLEDGE-008 owns the RESEARCHED EDITORIAL KNOWLEDGE *about the
  music*: artist/band bios, members, discography, labels, scene/era, recent AND UPCOMING
  releases, and anecdotes, each carried WITH dates and freshness, in a persisted
  relational store; the continuous RESEARCH JOBS that fill it; the enriched relational
  KNOWLEDGE GRAPH that lets the brain make conscious, sane transitions and play genuinely
  related music; and the GROUNDING FEED that makes this dated, sourced knowledge the
  verified-facts source the host speaks from. It answers a direct user concern
  (2026-06-22): "researched info about an artist/band should be stored in a database with
  DATES, so we don't announce old/outdated/irrelevant info" — and the worked scenario "the
  host can say 'speaking of %ARTIST%, he's got a new solo project releasing an album in two
  weeks on %LABEL%, here's a sneak peek of his latest single.'" RADIO SPEC-IDs are
  GLOBAL-INCREMENTING (CORE-001, VOICE-002, CALLIN-003 reserved, OPS-004, ORCH-005,
  ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008 = next free 008; KNOWLEDGE-001 was rejected
  to preserve the proven global pattern). It uses a DISTINCT REQ namespace — KS (store &
  schema), KF (freshness & currency), KR (continuous research jobs), KG (relational
  graph), KI (grounding feed & integration) — to avoid collision with CORE (A-E + D),
  VOICE (V-A…V-F), OPS (OA/OB/OC/OD/OE/OF/OG/OH), ORCH (RL/RW/RE/RC/RD/RA), ANALYSIS
  (AE/AT/AM/AD/AP), and PROGRAMMING (PR/PC/PS/PT/PL). Built on the BRAIN-ONLY seam: it
  extends the existing Python `brain/` package WITHOUT forking a store and WITHOUT any
  Liquidsoap change. RECOMMENDED storage engine (research.md): **SQLite** — a relational,
  file-based, serverless, zero-config engine that ships in the brain container, lives in
  `/db` alongside the existing JSON stores, and natively supports the dated + relational
  queries this SPEC needs (the current JSON-file stores cannot express the relational
  joins; an embedded graph DB is heavier than the modest box warrants). Total: 24 REQ +
  7 NFR = 31, 1:1 REQ↔AC.
- 2026-06-22 (v0.2.0): Added REQ-KS-006 [HARD] — MULTI-SOURCE CONSENSUS for researched
  editorial facts (relayed during authoring; the user's "legitimate / verified / reach
  consensus" requirement applied to editorial facts). A fact is treated as RELIABLE / AIRABLE
  only when corroborated across MULTIPLE VERIFIED sources from an allowlist (MusicBrainz,
  Wikidata, Wikipedia, Last.fm, official/label pages, reputable music press) above a
  consensus threshold; the fact carries a per-fact CONFIDENCE derived from how many verified
  sources agree; a SINGLE-SOURCE or CONFLICTING fact is FLAGGED/qualified ("reportedly…",
  "according to …") and NEVER stated to the host as certain. It slots into Group KS (it is the
  property by which a stored fact reaches airable status), is consumed by the freshness gate
  (REQ-KF-003 now also gates on consensus, not just recency) and the grounding feed
  (REQ-KI-001 feeds consensus-passed facts as CERTAIN, qualified facts as hedged). [Boundary]
  ANALYSIS-006 REQ-AM-003 owns multi-source reconciliation/consensus for AUDIO / GENRE /
  per-track FEATURES; KNOWLEDGE-008 REQ-KS-006 owns consensus for researched EDITORIAL FACTS
  (bio / members / discography / labels / releases / news) — same discipline, distinct domains,
  no fork. Net: +1 REQ (KS-006). Total: 25 REQ + 7 NFR = 32, 1:1 REQ↔AC preserved.
- 2026-06-23 (v0.3.0): CONVERGENCE of three plans into one coherent additive pass — deepening the
  knowledge layer from artist/release editorial knowledge to PER-TRACK editorial DEPTH, broadening the
  research SOURCES into a RELIABILITY-RANKED set (incl. Discogs + reputable press + open archives), and
  adding release-scoped grounding. **(A) Per-track editorial depth.** Group KS gains per-TRACK editorial
  fields — `recording_session`, `writing_story`, `lyrical_meaning(s)` (plural, each with its own
  source + confidence), `production_notes`, `era_context` (REQ-KS-007) — plus a `subjectivity_class`
  {FACTUAL | INTERPRETED | EDITORIAL-OPINION} with a CONFIDENCE-GRADE for subjective editorial claims
  (HIGH = 3+ authoritative concur / MODERATE = 2 with disagreement noted / LOW = 1 or strong
  disagreement) and a per-fact DISAGREEMENT field (REQ-KS-008): FACTUAL claims keep the existing
  REQ-KS-006 consensus engine UNCHANGED (the SOLE airable-FACT seam); INTERPRETED / EDITORIAL-OPINION
  claims are aired as MEANING-AS-ATTRIBUTED-SPEECH ("%CRITIC% reads it as…", "the band has said…") with
  CONTESTED-MEANING a FIRST-CLASS airable outcome ("some hear X, others Y"), MODERATE / LOW always
  hedged, never stated as the fixed meaning. Group KF gains a per-track currency classification — a
  THIRD currency class CONTEXTUAL (lyrical-meaning / cultural-context, which accrues + shifts rather
  than expires by a date) alongside TIMELESS (writing / recording) and TIME-SENSITIVE (REQ-KF-005).
  Group KR gains per-TRACK + per-ALBUM deep-research job types (REQ-KR-006) and a PRE-SHOW RESEARCH PASS
  trigger (bounded-timeout deep research that completes before grounding-feed assembly, never blocks,
  REQ-KR-007). Group KG gains richer track-to-track edges — cover lineage, sample / interpolation,
  writing / production connections, thematic / musical influence (REQ-KG-006). **(B) Discogs + release
  grounding.** Group KR gains a Discogs ARTIST-scoped editorial provider (`SRC_DISCOGS`, CROWD-tier
  weight ~0.25, NOT authoritative): its STRUCTURED fields (credits / companies / labels / styles) CAN
  reach consensus, but its free-text NOTES are permanently single-source -> ALWAYS hedged ("according to
  Discogs") (REQ-KR-008). Group KG's `credited_to` / `recorded_at` / `signed_to` edges + ENTITY_PERSON /
  ENTITY_PLACE nodes are now populated by Discogs (annotated on REQ-KG-002, surfaced in REQ-KG-006);
  per-release-credit cross-check is DEFERRED to MBMIRROR-017 (referenced, not forked). Group KI gains a
  release-scoped grounding accessor `grounding_for_release(artist_key, album_title)` (REQ-KI-006) beside
  the existing artist/track-scoped feed — in-depth shows are release-scoped. **(C) Reliability-ranked
  sourcing.** The flat REQ-KS-006 verified-source allowlist becomes a RELIABILITY-RANKED tier list
  (AUTHORITATIVE-STRUCTURED > REPUTABLE-PRESS > EDITORIAL-BLOG > CROWD), declared TUNABLE config, where
  the tier drives the consensus WEIGHT (REQ-KS-009); and the provider set expands (REQ-KR-009) — The
  Guardian (Open Platform API, full text), Internet Archive (discovery + public-domain text + Wayback),
  LoC Chronicling America (public-domain full-text), CritiqueBrainz (open criticism), plus Nardwuar,
  WhoSampled, Bandcamp Daily, Aquarium Drunkard, The Fader, Stereogum, The Quietus, BBC, and the deep
  sources Genius / AllMusic / Pitchfork / Songfacts — all reachable by SCRAPING (trafilatura /
  newspaper4k) where there is no API; AOTY is skip-on-feasibility (Cloudflare bot-block, noted not
  reachable). [PIVOT — private personal PoC, never public] Sources are ranked by RELIABILITY, NOT by
  license; no copyright / ToS / CC-vs-NC source-tiering, no scraping ban, no attribution-for-law, no
  no-store-time rule is added; lyrics may be quoted verbatim for ANALYSIS. The existing multi-source
  CONSENSUS + confidence + freshness + provenance + grounding engine is REUSED UNCHANGED on the new
  per-track + interpretation + expanded-source scope — REQ-KS-006 stays the SOLE airable-FACT seam;
  single / crowd sources stay hedged; the host is never confidently wrong; the per-persona
  anti-convergence firewall (PROGRAMMING-007 REQ-PR-004 / REQ-PR-009) is untouched. One NFR added
  (NFR-K-8: subjective / interpreted claims attributed + hedged, never stated as fact; contested-meaning
  a first-class outcome). Net: +10 REQ (KS-007/008/009, KF-005, KR-006/007/008/009, KG-006, KI-006) + 1
  NFR (NFR-K-8). Total: 35 REQ + 8 NFR = 43; 1:1 REQ<->AC preserved (group counts KS=9, KF=5, KR=9,
  KG=6, KI=6).
- 2026-06-23 (v0.3.2): BOUNDARY NOTE ONLY — no schema change, no new airable-fact path, no new
  REQ/NFR, no count change (35 REQ + 8 NFR = 43, group counts unchanged). Documented the
  one-directional boundary with the new SPEC-RADIO-REFLECT-026 (the station's internal
  beliefs/hypotheses layer; forward-ref, authored in the same wave). REFLECT-026 REUSES the
  KNOWLEDGE-008 fact-discipline PATTERN (provenance + as-of dating + confidence-grading +
  hedging + never-confidently-wrong) for its OWN internal hypotheses store, but those hypotheses
  are NEVER promoted into the KNOWLEDGE-008 AIRABLE-FACT contract: REQ-KS-006 (multi-source
  consensus across the verified / reliability-ranked source set) remains the SOLE seam by which a
  claim becomes airable-as-certain, and a REFLECT-026 internal belief — however high its internal
  confidence — does not by that confidence become an airable editorial fact. The boundary is
  clean and one-directional (KNOWLEDGE-008 facts MAY ground REFLECT-026 reasoning; REFLECT-026
  hypotheses MAY NOT enter the grounding feed as facts). Recorded as a prose REFERENCES /
  Exclusions boundary; REFLECT-026 is referenced by id (it OWNS its internal-belief store;
  KNOWLEDGE-008 MUST NOT restate or fork it, and REFLECT-026 MUST NOT restate, fork, or weaken
  REQ-KS-006).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "know the music well enough to talk about it, and never say stale things"

The station can play continuously (CORE-001), talk (VOICE-002), program itself
(OPS-004), orchestrate as one operator (ORCH-005), understand the SOUND of its music
(ANALYSIS-006), and present it with distinct personas and craft (PROGRAMMING-007). What
it still lacks is DEEP, CURRENT, RELATIONAL KNOWLEDGE about the artists, bands, and songs
it plays — the editorial substance a real DJ carries in their head and reads up on before
a show.

Two concrete user concerns drive this SPEC:

1. **Dated knowledge, no stale announcements.** Researched info about an artist/band must
   be stored WITH DATES so the host never announces something old, outdated, or no longer
   true. An "upcoming album in two weeks" fact has a shelf life; once the date passes it
   must be dropped or re-cast, never read as if still upcoming.
2. **Relational knowledge, sane transitions + related music.** The store must be
   RELATIONAL so the brain makes conscious, sane transitions ("speaking of X, here's their
   side-project Y") and plays music that is genuinely related — same genre/era/style/
   network/label — instead of free-associating.

The worked scenario the user gave captures both: *"speaking of %ARTIST%, he's got a new
solo project releasing an album in two weeks on %LABEL%, here's a sneak peek of his latest
single."* That single sentence requires: a researched, dated, time-validated fact (a new
album, releasing in two weeks, on a named label); a relational link (this artist → their
solo side-project → the latest single in the library); and a curation action (queue the
single). KNOWLEDGE-008 makes all three expressible from one dated, sourced, relational
store.

### 1.2 What this layer is, concretely

- A persisted, queryable RELATIONAL STORE (SQLite, recommended) of entities — artist/band,
  person (member), release/album, song/recording, label, genre/scene/era, place — with
  FACTS attached to them, every fact carrying PROVENANCE (source + URL) and a RETRIEVAL /
  AS-OF date, classified TIMELESS vs TIME-SENSITIVE, and reaching airable-as-certain status
  only on MULTI-SOURCE CONSENSUS across a verified-source allowlist (single-source/conflicting
  facts are flagged and only voiced qualified) (Group KS).
- A FRESHNESS / currency model: time-sensitive facts carry a validity window/expiry; the
  brain knows the current Faroe-local date (ORCH-005 world model); a generation/airtime
  GATE filters or re-casts stale facts so the host never states an expired one; periodic
  re-research refreshes time-sensitive facts more often than timeless ones (Group KF).
- Continuous RESEARCH JOBS triggered by library ingest (ANALYSIS-006's scan), by periodic
  refresh, and by pre-show prep, pulling from MusicBrainz, Wikidata/Wikipedia, Last.fm, and
  web search — de-duplicated, idempotent, cached, rate-limit-respecting, bounded/throttled,
  and run as background jobs ORCH-005 schedules (Group KR).
- A relational KNOWLEDGE GRAPH modelling artist↔artist (member-of, side-project/solo,
  collaborator, similar/influenced-by), artist↔label, artist↔genre/scene/era/place,
  song↔song (cover/sample/remix lineage), release↔artist — seeded from ANALYSIS-006's
  similar-artist edges + genre/era dimensions and enriched with researched MusicBrainz
  relationships — queryable so the brain selects related music and grounds comparisons in
  REAL edges only (Group KG).
- A GROUNDING FEED: the knowledge base is THE verified-facts source fed to the talk-script
  LLM (the host speaks ONLY from dated, sourced facts here), to the picker/curation
  (relational + related-music selection + sane transitions), to the website, and to the
  newscaster (Group KI).

### 1.2a Per-track editorial depth + reliability-ranked sourcing (v0.3.0 convergence)

v0.3.0 deepens the same engine from artist/release knowledge to per-TRACK editorial DEPTH, and
broadens its SOURCES, WITHOUT forking the store or adding a second consensus path:

- **Per-track editorial fields (Group KS).** A song/recording entity now carries the deeper
  editorial fields a real DJ reads up on before featuring a track: `recording_session` (where /
  how / with whom it was cut), `writing_story` (how the song came to be), one or more
  `lyrical_meaning` readings (each with its OWN source + confidence — a song can carry several
  competing readings), `production_notes` (who produced / engineered / what gear or technique),
  and `era_context` (what the track meant in its moment) (REQ-KS-007).
- **Subjectivity is first-class (Group KS).** Not every editorial claim is a fact. Each carries a
  `subjectivity_class` — FACTUAL (a verifiable claim: recorded at Studio X, written by Y),
  INTERPRETED (what the lyrics MEAN / how critics read it), or EDITORIAL-OPINION (a critic's
  evaluative judgment). FACTUAL claims pass through the UNCHANGED REQ-KS-006 consensus engine (the
  SOLE airable-fact seam). INTERPRETED / EDITORIAL-OPINION claims are aired only as
  MEANING-AS-ATTRIBUTED-SPEECH ("%CRITIC% reads it as a breakup song", "the band has said it's
  about…"), carry a confidence-grade (HIGH / MODERATE / LOW) and a DISAGREEMENT record, and a
  CONTESTED meaning is a FIRST-CLASS airable outcome the host can voice as disagreement itself
  ("some hear it as X, others as Y") — never collapsed into one false certainty (REQ-KS-008,
  NFR-K-8). KNOWLEDGE-008 owns the attributed claim + its source + grade; PROGRAMMING-007 owns the
  host-voice PHRASING (the attributed-speech wording + the bounded personal-musing aside).
- **A third currency class, CONTEXTUAL (Group KF).** Writing / recording facts are TIMELESS;
  upcoming releases / tours are TIME-SENSITIVE; lyrical-meaning + cultural-context are CONTEXTUAL —
  they do not expire on a date but ACCRUE and SHIFT as readings evolve, so they are refreshed on a
  cadence and may gain disagreement over time, but are never gated stale by a release date
  (REQ-KF-005).
- **Deeper + wider research (Group KR).** Per-TRACK + per-ALBUM deep-research jobs (REQ-KR-006) fill
  the new fields; a PRE-SHOW RESEARCH PASS (REQ-KR-007) runs a bounded-timeout deep pass before a
  featured artist/release's grounding feed is assembled (and proceeds with whatever is ready on
  timeout — it never blocks). A Discogs ARTIST-scoped provider (REQ-KR-008) adds credits / labels /
  styles (structured fields can reach consensus; free-text NOTES are permanently single-source and
  always hedged). The verified-source allowlist becomes a RELIABILITY-RANKED tier list (REQ-KS-009)
  and the provider set expands to reputable press, open archives, and editorial deep sources, all
  reachable by SCRAPING where there is no API (REQ-KR-009).
- **Release-scoped grounding (Group KI).** Beside the artist/track-scoped feed, a
  `grounding_for_release(artist_key, album_title)` accessor (REQ-KI-006) serves the release-scoped
  facts an in-depth album show needs.

[PIVOT — this is a private personal PoC, never public] Sources are ranked by RELIABILITY, NOT by
license. No copyright / ToS / CC-vs-NC source-tiering, no scraping ban, no attribution-for-law, and
no no-store-time rule is added in v0.3.0; lyrics may be quoted verbatim for analysis. The
multi-source CONSENSUS + confidence + freshness + provenance + grounding engine is REUSED as-is on
the wider scope; reliability simply drives the consensus weight.

### 1.3 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] KNOWLEDGE-008 owns the RESEARCHED EDITORIAL KNOWLEDGE + the dated relational store +
the research jobs + the grounding feed. It MUST NOT restate or fork any CORE-001,
VOICE-002, OPS-004, ORCH-005, ANALYSIS-006, or PROGRAMMING-007 requirement.

OWNS:
- The dated, relational knowledge STORE + entity/fact SCHEMA + provenance + as-of dating +
  TIMELESS/TIME-SENSITIVE classification (Group KS).
- The FRESHNESS / currency model: validity windows, the don't-announce-stale gate, the
  re-research refresh cadence (Group KF).
- The continuous RESEARCH JOBS: triggers, sources, de-dup/idempotency/caching, bounding/
  throttling, graceful degradation (Group KR).
- The relational KNOWLEDGE GRAPH: the relationship model, the seed-from-ANALYSIS-006 +
  enrich-with-research, the related-music + sane-transition + grounded-comparison queries
  (Group KG).
- The GROUNDING FEED + integration: the verified-facts source for talk, curation, website,
  news; the worked %ARTIST%/%LABEL% scenario end-to-end (Group KI).

REFERENCES (consumes / extends / feeds; does not restate):
- **ANALYSIS-006 Group AD** (REQ-AD-001/002/003/004) — the per-TRACK audio-feature data
  model + queryable catalog + the per-persona taste dimensions. KNOWLEDGE-008's graph
  SEEDS from ANALYSIS-006's genre/era dimensions and Last.fm SIMILAR-ARTIST edges
  (referenced at REQ-AD-003's discovery-boundary note + Group AM) and EXTENDS them with
  researched relationships; it does NOT recompute per-track audio features.
- **ANALYSIS-006 REQ-AP-007** — the library auto-ingest scan (periodic stat-only manifest
  diff). It is the TRIGGER that enqueues an artist-research job when a new artist enters the
  library; KNOWLEDGE-008 references the trigger, does not re-own the scan.
- **ANALYSIS-006 REQ-AM-001/002/003** — genre/mood/tag DERIVATION + Last.fm folksonomy +
  multi-source reconciliation for a TRACK. KNOWLEDGE-008's facts about an ARTIST/RELEASE are
  a distinct, editorial layer; where the two touch a shared external source (Last.fm,
  MusicBrainz), each owns its own consumption and KNOWLEDGE-008 does not re-own track-level
  genre derivation. [Consensus boundary] ANALYSIS-006 REQ-AM-003 owns the multi-source
  reconciliation / consensus for AUDIO / GENRE / per-track FEATURES; KNOWLEDGE-008 REQ-KS-006
  owns multi-source consensus for researched EDITORIAL FACTS (bio / members / discography /
  labels / releases / news). Same discipline (corroborate across verified sources, record
  confidence + provenance), distinct domains — neither forks the other.
- **ORCH-005 Group RL / Group RW** — the director loop that SCHEDULES background jobs and
  the world model that knows the current Faroe-local date. KNOWLEDGE-008 DEFINES the research
  jobs + store; ORCH-005 orchestrates WHEN they run and supplies the current date to the
  freshness gate. ORCH-005's world model may read library-knowledge state as a sensor; this
  SPEC owns the store, not the loop.
- **OPS-004 REQ-OH-006** — acquisition accounting + bounded-job pattern + the throttle
  thresholds. KNOWLEDGE-008's research jobs adopt the same bounded/throttled discipline so
  research and acquisition do not jointly overload the box; referenced, not re-owned.
- **OPS-004 REQ-OA-011 / REQ-OA-012** — track enrichment + the queryable catalog. The
  ARTIST/RELEASE knowledge here is editorial, distinct from per-track enrichment; the
  external-source CLIENTS (MusicBrainz / Last.fm HTTP) the enrichment names are reused, not
  re-owned.
- **OPS-004 Group OG** — newscasting (news cadence/sourcing/grounding/Faroese angle).
  KNOWLEDGE-008 FEEDS the newscaster MUSIC news (new releases, artist news) as one consumer
  of the grounding feed; OPS-004 owns the news production + the general (non-music) source
  list.
- **OPS-004 REQ-OF-004 / REQ-OC-005 / REQ-OG-005 + NFR-O-7** — the apolitical +
  grounded-not-fabricated constraints. KNOWLEDGE-008 inherits them: facts are sourced + dated,
  never invented, and the music's cultural significance is never partisan framing.
- **PROGRAMMING-007 Group PC / Group PS + r-organic grounding architecture** — the
  radio-craft + ear-writing rules and the host's grounded-banter discipline. The talk-script
  LLM CONSUMES KNOWLEDGE-008 as its verified-facts source; PROGRAMMING-007 owns HOW the host
  speaks, KNOWLEDGE-008 owns WHAT (dated, sourced facts) it speaks from. Neither redefines the
  other.
- **PROGRAMMING-007 Group PG / Group PV + the bounded personal-musing allowance + the
  anti-convergence firewall (REQ-PR-004 / REQ-PR-009)** — KNOWLEDGE-008 v0.3.0 supplies the
  ATTRIBUTED editorial claim + its source + its confidence-grade + its disagreement record
  (REQ-KS-008); PROGRAMMING-007 owns the host-voice PHRASING of that attributed speech ("critics
  read it as…"), the bounded self-aware first-person MUSING aside (a light curiosity-framed
  question, the host opinion never authoritative), and the inviolable per-persona anti-convergence
  firewall. KNOWLEDGE-008 NEVER re-owns or weakens the firewall and NEVER mints a host opinion as a
  fact — it records WHOSE reading a meaning is, and hands the host an attributed claim to voice.
- **MBMIRROR-017 (self-hosted MusicBrainz mirror + Discogs/Last.fm cross-check)** — KNOWLEDGE-008's
  Discogs provider (REQ-KR-008) is the LIGHT, direct artist-scoped editorial path used to fill
  credits / labels / styles + the credited_to / recorded_at / signed_to graph edges. The heavier
  PER-RELEASE-CREDIT cross-check (reconciling Discogs credits against the MusicBrainz mirror at
  release granularity) is DEFERRED to MBMIRROR-017 and referenced by number; KNOWLEDGE-008 does not
  fork the mirror or re-own its cross-check.
- **REFLECT-026 (the station's internal beliefs / hypotheses layer)** — REFLECT-026 REUSES the
  KNOWLEDGE-008 fact-discipline PATTERN (provenance + as-of dating + confidence-grading + hedging +
  never-confidently-wrong, the discipline established by REQ-KS-003/006/008 and the freshness +
  consensus gates) to manage its OWN internal beliefs/hypotheses about the station and its world.
  [HARD, one-directional boundary] This is a PATTERN reuse, NOT a fact-path extension: a REFLECT-026
  internal hypothesis — no matter how high its internal confidence — is NEVER promoted into the
  KNOWLEDGE-008 airable-fact contract. REQ-KS-006 (multi-source consensus across the verified /
  reliability-ranked source set, REQ-KS-009) remains the SOLE seam by which a claim becomes
  airable-as-certain, and the grounding feed (Group KI) serves ONLY KNOWLEDGE-008's dated, sourced,
  consensus-gated editorial facts — never a REFLECT-026 belief restyled as a fact. The flow is
  one-way: KNOWLEDGE-008's facts MAY GROUND REFLECT-026's reasoning, but REFLECT-026's hypotheses
  MAY NOT enter the grounding feed as airable facts. REFLECT-026 OWNS its internal-belief store;
  KNOWLEDGE-008 does not restate or fork it, and REFLECT-026 does not restate, fork, or weaken
  REQ-KS-006 / the airable-fact seam. (No schema change here; the seam is unchanged and remains
  the sole airable-fact contract.)
- **OPS-004 REQ-OD-007 / OD-008 + PROGRAMMING-007 REQ-PL-003** — the append-only ledger +
  diary + acquisition diary memory substrate. The research jobs coordinate with that
  substrate for continuity/audit; KNOWLEDGE-008 does not fork the ledger.
- **CORE-001 library** (`brain/library.py` `Track`) — the knowledge store ATTACHES to
  tracks by the existing artist/title keying; it does not fork the library store and adds no
  new playout seam.

### 1.4 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 Section 1.3, OPS-004 Section 1.3, ANALYSIS-006 Section 1.5, and
PROGRAMMING-007 Section 1.3 in intent and does NOT redefine it. It is largely an
ENGINEERING + KNOWLEDGE substrate (researching and dating facts is information retrieval,
not a creative act), but where it touches editorial decisions it follows the same rule: it
GRANTS the AI accurate, dated, relational knowledge + the queries to use it + the safety
rails, and MUST NOT prescribe fixed creative content, what the host says about an artist,
which transitions to make, or which related track to pick. The research SOURCES, the
freshness thresholds, the refresh cadences, the relationship WEIGHTING, and the per-fact
significance are TUNABLE config or the AI's call; the store only guarantees the knowledge
can be REPRESENTED, DATED, related, and QUERIED. The human stays out of the run loop;
research is fully autonomous and continuous.

### 1.5 Fixed engineering/safety rails (the only hard constraints)

- **Dated facts only; never announce stale.** Every TIME-SENSITIVE fact carries an as-of
  date + a validity window; at generation/airtime an expired time-sensitive fact is dropped
  or re-cast against the current Faroe-local date (ORCH-005). This is the core user rail.
- **Grounded, sourced, never fabricated.** Every fact carries provenance (source name + URL)
  and a retrieval date; the host speaks only from stored facts, never free-recall; an
  un-sourced claim is not a fact (inherits OPS-004 REQ-OC-005 / NFR-O-7).
- **Multi-source consensus before a fact is aired as certain.** A researched editorial fact
  is treated as RELIABLE / AIRABLE-AS-CERTAIN only when corroborated across MULTIPLE VERIFIED
  sources (an allowlist) above a consensus threshold; a single-source or conflicting fact is
  flagged and may only be voiced QUALIFIED ("reportedly…"), never stated as certain
  (REQ-KS-006). ANALYSIS-006 owns consensus for audio/genre features; this owns it for
  editorial facts.
- **Relational comparisons use real edges only.** A "speaking of X → related Y" segue or a
  related-music pick is grounded in an actual stored graph edge, never a free-associated
  similarity the LLM invented.
- **Never blocks the <1s pull.** Research is strictly background (ORCH-005 schedules it);
  the freshness gate at generation time reads ready knowledge; the playout pull never waits
  on a research job (inherits ORCH-005 / OPS-004 non-blocking rails).
- **Bounded, throttled, rate-limit-respecting.** Research jobs are bounded and throttled
  (OPS-004 REQ-OH-006 pattern) and respect each external source's rate limits + key/ToS;
  a source outage or quota hit degrades gracefully — the music keeps playing.
- **Apolitical.** The cultural/societal significance of music is the editorial lens, never
  partisan commentary (inherits OPS-004 REQ-OF-004).
- **Brain-only, no store fork, no Liquidsoap change.** The knowledge store is a new SQLite
  file in `/db`; it attaches to the existing library by artist/title keying and adds no
  playout seam.

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001, SPEC-RADIO-OPS-004, SPEC-RADIO-ORCH-005,
SPEC-RADIO-ANALYSIS-006, and SPEC-RADIO-PROGRAMMING-007, and is the researched-knowledge
layer that feeds their engines. It references their subsystems by CONCEPT (and, where a
cited requirement is a deliberately stable invariant or seam, by number) rather than
re-specifying them.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any CORE-001, VOICE-002, OPS-004,
ORCH-005, ANALYSIS-006, or PROGRAMMING-007 requirement. Where it needs a predecessor
behavior it consumes it. Where a KNOWLEDGE decision could conflict with continuous
operation, the inherited continuous-operation behavior WINS.

Consumed ANALYSIS-006 concepts (by number, deliberately):
- **REQ-AP-007** (library auto-ingest stat-only scan) — the TRIGGER that enqueues
  artist-research when a new artist enters the library.
- **REQ-AD-001/002/003/004** (track feature data model + queryable catalog + per-persona
  taste dimensions + DJ-set/energy queries) — the SEED for the relational graph
  (genre/era dimensions) and the per-track features a knowledge query joins against.
- **REQ-AM-001/002/003 + REQ-AD-003 discovery-boundary note** — Last.fm folksonomy +
  similar-artist edges, the seed for artist↔artist similarity. KNOWLEDGE-008 extends, does
  not recompute.

Consumed ORCH-005 concepts (by number, deliberately):
- **Group RL (REQ-RL-001/002/003)** — the director loop + cheap/planning ticks + serialized
  generator dispatch. Research jobs are dispatched as background generators on this loop.
- **Group RW (REQ-RW-002)** — the world model + the local-clock/daypart sensor (current
  Faroe date), the input to the freshness gate; library-knowledge state MAY be a sensor.
- **REQ-RC-001/002 + REQ-RD-001** — background-off-the-pull + serialized + graceful
  degradation, which the research jobs obey.

Consumed OPS-004 concepts (by number, deliberately):
- **REQ-OH-006** (acquisition accounting + bounded queue + throttle) — the bounded-job
  pattern the research jobs adopt.
- **REQ-OA-011 / REQ-OA-012** (track enrichment + queryable catalog) + the external-source
  CLIENTS (MusicBrainz / Last.fm HTTP) reused, not re-owned.
- **Group OG (REQ-OG-001…009)** — newscasting; KNOWLEDGE-008 feeds it music news.
- **REQ-OF-004 / REQ-OC-005 / REQ-OG-005 / NFR-O-7** (apolitical + grounded-not-fabricated).
- **REQ-OD-007 / OD-008** (append-only ledger + diary memory substrate).

Consumed PROGRAMMING-007 concepts (by number, deliberately):
- **Group PC / Group PS** (radio-craft + ear-writing) + the r-organic grounded-banter
  architecture — the talk-script generator consumes KNOWLEDGE-008 as its verified-facts
  source. **REQ-PL-003** (acquisition diary) coordinates with the research memory substrate.

Consumed CORE-001 concepts:
- The library store (`brain/library.py` `Track`, artist/title keying), the self-served
  website (CORE Group E) for artist/show notes, and the config/secrets/health surface.

### Downstream / sibling note

- ORCH-005's world model reads situational state; a future SPEC may surface a richer
  "knowledge coverage" sensor (how much of the library is researched). KNOWLEDGE-008 owns the
  store + jobs; ORCH owns the loop. Neither redefines the other.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Knowledge base** | The persisted, relational store (recommended: SQLite in `/db`) of entities + dated, sourced facts + relationships about the music the station plays. Distinct from the per-track audio-feature catalog (ANALYSIS-006). |
| **Entity** | A node in the knowledge base: artist/band, person (member), release/album, song/recording, label, genre/scene/era, or place. |
| **Fact** | A dated, sourced statement attached to an entity (e.g. "founded 1994", "new album due 2026-07-06 on Label X"). Carries provenance + an as-of date + a TIMELESS/TIME-SENSITIVE class. |
| **Provenance** | The source(s) of a fact: the source name (MusicBrainz / Wikidata / Last.fm / web) + the URL, recorded with the fact so it is auditable and the host can ground a claim. A fact may carry MULTIPLE corroborating source+URL entries (multi-source provenance, REQ-KS-006). |
| **Verified-source allowlist** | The set of sources that COUNT toward consensus: MusicBrainz, Wikidata, Wikipedia, Last.fm, official artist/label pages, and reputable music press. A source outside the allowlist may seed a research lead but does not corroborate a fact (REQ-KS-006). |
| **Multi-source consensus** | The property that a researched editorial fact is corroborated across multiple VERIFIED (allowlisted) sources above a threshold, making it airable AS CERTAIN. Single-source or conflicting facts are flagged and may only be voiced QUALIFIED. The editorial-fact counterpart to ANALYSIS-006 REQ-AM-003's audio/genre reconciliation (REQ-KS-006). |
| **Per-fact confidence** | A reliability score derived from how many verified sources agree on a fact (more agreeing verified sources, and more authoritative ones, → higher confidence), used to decide certain vs. qualified (REQ-KS-006). |
| **Qualified claim** | A fact that has NOT reached consensus, voiced with a hedge ("reportedly…", "according to %SOURCE%…") rather than as established fact; never stated to the host as certain (REQ-KS-006, REQ-KI-001). |
| **As-of / retrieval date** | The date a fact was retrieved/last verified. Every fact has one; it is how the freshness model reasons about staleness. |
| **Timeless fact** | A fact that does not expire (birth/founding year, members, discography, label of a past release). Refreshed rarely. |
| **Time-sensitive fact** | A fact whose truth depends on the current date (upcoming release, current tour, "new single", "recently signed"). Carries a validity window/expiry and is refreshed often. |
| **Validity window / expiry** | For a time-sensitive fact, the date range during which it is announceable (e.g. "upcoming until the release date"). After expiry the fact is stale and gated out or re-cast. |
| **Freshness gate** | The generation/airtime check that, against the current Faroe-local date (ORCH-005), drops or re-casts expired time-sensitive facts so the host never announces a stale one. |
| **Re-research / refresh** | A periodic research pass that re-verifies facts; time-sensitive facts are refreshed on a tighter cadence than timeless ones, and stale entries are flagged for refresh. |
| **Research job** | A bounded, background unit of work that researches one artist/band/release/song from the external sources, de-duplicated and idempotent, dispatched by ORCH-005. |
| **Knowledge graph** | The relational structure of edges between entities (artist↔artist, artist↔label, artist↔genre/scene/era/place, song↔song lineage, release↔artist) that powers related-music selection + sane transitions + grounded comparisons. |
| **Seed edge** | A relationship edge imported from ANALYSIS-006 (a Last.fm similar-artist link or a shared genre/era dimension) used to bootstrap the graph before research enriches it. |
| **Researched edge** | A relationship edge added by a research job from an authoritative source (chiefly MusicBrainz relationships: member-of, side-project, collaborator, label). |
| **Grounding feed** | The interface that exposes the dated, sourced, fresh facts + graph edges as the verified-facts source the talk-script LLM, curation, website, and newscaster read from. |
| **Sane transition** | A segue grounded in a real graph edge ("speaking of X, here's their side-project Y"), as opposed to a free-associated or arbitrary jump. |
| **Related music** | Tracks selected because a real graph edge or shared dimension connects them to the current track's artist (same genre/era/style/network/label), not by free LLM association. |
| **Per-track editorial fields** | The deeper editorial attachments on a song/recording entity (v0.3.0): `recording_session`, `writing_story`, one or more `lyrical_meaning` readings (each source+confidence), `production_notes`, `era_context` (REQ-KS-007). |
| **Subjectivity class** | A per-fact label on every editorial claim: FACTUAL (a verifiable claim — routes through the REQ-KS-006 consensus engine unchanged), INTERPRETED (what lyrics mean / how critics read a track), or EDITORIAL-OPINION (a critic's evaluative judgment) (REQ-KS-008). |
| **Meaning-as-attributed-speech** | The discipline that an INTERPRETED / EDITORIAL-OPINION claim is aired only as ATTRIBUTED speech ("%CRITIC% reads it as…", "the band has said…"), never as the station's own asserted fact; the host states whose reading it is, not a settled truth (REQ-KS-008, NFR-K-8). |
| **Confidence-grade (editorial)** | For a subjective editorial claim, a grade HIGH (3+ authoritative sources concur on a reading) / MODERATE (2, with disagreement noted) / LOW (1 source, or strong disagreement). MODERATE/LOW claims are always hedged. Distinct from the FACTUAL per-fact consensus confidence (REQ-KS-006), which still governs FACTUAL claims (REQ-KS-008). |
| **Disagreement field** | A per-fact record of competing readings/values across sources, so a CONTESTED meaning is preserved as a FIRST-CLASS airable outcome the host can voice as disagreement ("some hear X, others Y") rather than collapsed into one false certainty (REQ-KS-008). |
| **Contextual fact** | A THIRD currency class (beside TIMELESS + TIME-SENSITIVE): lyrical-meaning + cultural-context facts that do not expire on a date but ACCRUE and SHIFT as readings evolve; refreshed on a cadence, may gain disagreement over time, never gated stale by a release date (REQ-KF-005). |
| **Per-track / per-album deep-research job** | A research job type that fills the per-track / per-release editorial fields (recording session, writing story, lyrical readings, production credits, era context) for a specific track/album, distinct from the per-ARTIST job (REQ-KR-006). |
| **Pre-show research pass** | A bounded-timeout deep-research pass for a featured artist/release/track that runs BEFORE the grounding feed is assembled, so the show is well-researched in time; on timeout it proceeds with whatever is ready, never blocking (REQ-KR-007). |
| **Reliability tier** | The rank a source sits in — AUTHORITATIVE-STRUCTURED (MusicBrainz, Wikidata, LoC/IA public-domain) > REPUTABLE-PRESS (The Guardian, BBC, Pitchfork, The Quietus…) > EDITORIAL-BLOG (Stereogum, Aquarium Drunkard, Bandcamp Daily…) > CROWD (Discogs notes, Last.fm, Genius community) — which drives the consensus WEIGHT in REQ-KS-006 (REQ-KS-009). Ranked by reliability, NOT license. |
| **Discogs provider** | An ARTIST-scoped editorial research source (`SRC_DISCOGS`, CROWD-tier ~0.25 weight, not authoritative): STRUCTURED fields (credits/companies/labels/styles) CAN reach consensus; free-text NOTES are permanently single-source and ALWAYS hedged ("according to Discogs"). Populates the credited_to/recorded_at/signed_to edges + ENTITY_PERSON/ENTITY_PLACE nodes (REQ-KR-008, REQ-KG-006). |
| **Release-scoped grounding** | The `grounding_for_release(artist_key, album_title)` accessor that serves the release-scoped facts an in-depth album show needs, beside the existing artist/track-scoped feed (REQ-KI-006). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group KS — Knowledge Store & Schema.** The persisted relational store (SQLite
  recommended), in `/db` alongside the JSON stores; the entity set (artist/band, person,
  release/album, song/recording, label, genre/scene/era, place); facts attached to entities;
  per-fact PROVENANCE + as-of date; the TIMELESS vs TIME-SENSITIVE classification; the
  MULTI-SOURCE CONSENSUS rule (the RELIABILITY-RANKED source tier list + threshold + per-fact
  confidence; single-source/conflicting flagged + qualified); the PER-TRACK editorial fields
  (recording session / writing story / lyrical meaning(s) / production notes / era context),
  the `subjectivity_class` {FACTUAL | INTERPRETED | EDITORIAL-OPINION} + editorial
  confidence-grade + disagreement record (meaning-as-attributed-speech, contested-meaning a
  first-class outcome); the brain-only / no-fork / engine-choice rails.
- **Group KF — Freshness & Currency.** Validity windows/expiry on time-sensitive facts; the
  current-date awareness from ORCH-005; the don't-announce-stale GATE at generation/airtime;
  the periodic re-research refresh cadence (tighter for time-sensitive); stale-entry flagging;
  the per-track currency classification (writing/recording = TIMELESS; lyrical-meaning/
  cultural-context = CONTEXTUAL, a third class that accrues/shifts rather than expires).
- **Group KR — Continuous Research Jobs.** Triggers (ingest of a new artist; periodic
  refresh; pre-show prep + the PRE-SHOW RESEARCH PASS; per-TRACK + per-ALBUM deep research);
  sources — a RELIABILITY-RANKED set: MusicBrainz, Wikidata/Wikipedia, Last.fm, the Discogs
  artist-scoped editorial provider, reputable press (The Guardian, BBC, Pitchfork, The Quietus…),
  open archives (Internet Archive, LoC Chronicling America, CritiqueBrainz), editorial deep
  sources (Genius, AllMusic, Songfacts, WhoSampled, Nardwuar, Bandcamp Daily, Aquarium Drunkard,
  The Fader, Stereogum), web search for currency, official/label pages — reachable by SCRAPING
  (trafilatura/newspaper4k) where no API; de-dup/idempotency/caching; bounded/throttled (OPS-004
  REQ-OH-006); graceful degradation; non-blocking background.
- **Group KG — Relational Graph.** The relationship model (artist↔artist member-of/
  side-project/collaborator/similar, artist↔label, artist↔genre/scene/era/place, song↔song
  cover/sample/interpolation/remix lineage + writing/production/thematic-influence connections,
  release↔artist, credited_to/recorded_at/signed_to + ENTITY_PERSON/ENTITY_PLACE populated by
  Discogs); seed from ANALYSIS-006 + enrich with research; the related-music + sane-transition +
  grounded-comparison QUERIES.
- **Group KI — Grounding Feed & Integration.** The verified-facts source for the talk-script
  LLM (host speaks only from dated, sourced facts; attributed-speech for interpreted/opinion);
  the artist/track-scoped feed AND the release-scoped `grounding_for_release(...)` accessor;
  feeds to curation (related-music + sane transitions), the website (artist/show notes), and the
  newscaster (music news); the worked %ARTIST%/new-album/%LABEL%/sneak-peek scenario end-to-end.
- Plus **NFRs** (Section 13) and **Risks** (Section 14).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **Per-TRACK audio-feature analysis** (BPM/key/energy/genre/cue points) — owned by
  ANALYSIS-006; KNOWLEDGE-008 joins against it and seeds the graph from it, never recomputes.
- **The library auto-ingest SCAN mechanism** — owned by ANALYSIS-006 REQ-AP-007; KNOWLEDGE-008
  references it as the artist-research trigger only.
- **The director LOOP + job SCHEDULING** — owned by ORCH-005 Group RL; KNOWLEDGE-008 defines
  the jobs, ORCH schedules when they run.
- **External-source HTTP CLIENTS** (the MusicBrainz / Last.fm / Wikidata / web HTTP request
  layer, rate-limit queueing, key handling) — the client plumbing is shared with OPS-004
  REQ-OA-011 enrichment; KNOWLEDGE-008 owns WHAT to research + the dated relational schema +
  the de-dup/cache logic, not a second copy of the HTTP client.
- **The news PRODUCTION pipeline + general (non-music) news sources** — owned by OPS-004
  Group OG; KNOWLEDGE-008 feeds it music news as one consumer.
- **HOW the host speaks** (radio-craft, ear-writing, persona POV) — owned by PROGRAMMING-007;
  KNOWLEDGE-008 supplies the facts, not the delivery.
- **Similar-artist DISCOVERY for targeted ACQUISITION** (driving the acquisition wishlist) —
  a CORE-001/OPS-004 curation/acquisition concern (ANALYSIS-006 REQ-AD-003 discovery note);
  KNOWLEDGE-008's graph may surface candidates but does not own the acquisition wishlist.
- **The append-only ledger/diary STORE** — owned by OPS-004 REQ-OD-007/008; KNOWLEDGE-008
  coordinates with it, does not fork it.
- **A vector/embedding semantic-search store** — the relational graph + dated facts are the
  scope; semantic embeddings over bios are a possible future enhancement, not built here.
- **Full Wikipedia article ingestion / a general encyclopedia** — only music-relevant
  artist/band/release/song/label facts are stored; this is not a general knowledge base.
- **A new playout seam, a new service, or a Liquidsoap change** — brain-only; the store is a
  new SQLite file, not a new daemon.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain = the existing Python `brain/` package.** KNOWLEDGE-008 adds a knowledge
  store module + research-job module + grounding-feed accessor; it is not a new service.
- [HARD] **Dated facts.** Every fact has an as-of/retrieval date; every time-sensitive fact
  additionally has a validity window/expiry. No fact is stored undated.
- [HARD] **Provenance on every fact.** Source name + URL recorded with each fact; an
  un-sourced claim is not stored as a fact.
- [HARD] **Multi-source consensus before airing as certain.** A researched editorial fact is
  airable-as-certain only when corroborated across multiple VERIFIED sources (an allowlist)
  above a consensus threshold; single-source/conflicting facts are flagged and voiced only
  qualified ("reportedly…"), never as certain (REQ-KS-006).
- [HARD] **Grounded, never fabricated.** The host speaks only from stored facts; the
  knowledge base never invents facts (inherits OPS-004 REQ-OC-005 / NFR-O-7).
- [HARD] **Don't announce stale.** At generation/airtime, expired time-sensitive facts are
  dropped or re-cast against the current Faroe-local date (ORCH-005 world model).
- [HARD] **Relational comparisons use real edges only.** Related-music + "speaking of"
  segues are grounded in actual stored edges, never free-associated.
- [HARD] **Never blocks the <1s pull.** Research is background (ORCH-005 schedules); the
  freshness gate reads ready knowledge; the pull never waits on research.
- [HARD] **Bounded/throttled + rate-limit/ToS-respecting.** Research jobs follow the OPS-004
  REQ-OH-006 bounded-job pattern and respect each source's rate limit, API key, and terms.
- [HARD] **Apolitical.** Cultural/societal significance is the lens, never partisan content
  (inherits OPS-004 REQ-OF-004).
- [HARD] **No store fork; SQLite recommended in `/db`.** A new relational file alongside the
  JSON stores; it attaches to the library by artist/title keying. The engine is a strong
  recommendation (research.md), not the requirement itself — the requirement is a persisted,
  relational, dated, queryable store.

---

## 6. Requirement Group KS — Knowledge Store & Schema

Priority: High.

### REQ-KS-001 — Persisted, queryable, relational knowledge store (Ubiquitous) [HARD]

The system shall maintain a PERSISTED, QUERYABLE, RELATIONAL store of researched editorial
knowledge about the music it plays, separate from the per-track audio-feature catalog
(ANALYSIS-006), living in `/db` alongside the existing JSON stores and surviving daemon
restarts. The store SHALL support relational queries (joins across entities and their
relationships) and dated facts; the recommended engine is SQLite (research.md — relational,
file-based, serverless, zero-config, ships in the brain container), but the requirement is
the persisted/relational/dated/queryable CAPABILITY, with the specific engine an
implementation choice behind a stable schema. [HARD] No existing store is forked; the
knowledge store attaches to the library by the existing artist/title keying.

**Acceptance criteria:** see acceptance.md AC-KS-001.

### REQ-KS-002 — Entity model: artist, person, release, song, label, genre/scene/era, place (Ubiquitous) [HARD]

The store shall represent at least these ENTITY types as first-class records:
artist/band, person (a member or associated individual), release/album, song/recording,
label, genre/scene/era, and place. Each entity carries a stable identifier (and, where
available, its MusicBrainz MBID and Wikidata QID for cross-linking and de-dup) and is keyed
so the library's tracks resolve to their artist/release/song entities. The entity SET is the
rail (these types must be representable); the attributes within each are extensible.

**Acceptance criteria:** see acceptance.md AC-KS-002.

### REQ-KS-003 — Facts attached to entities with provenance + as-of date (Ubiquitous) [HARD]

The store shall attach FACTS to entities, and every fact SHALL carry: the fact content, its
PROVENANCE (source name + source URL), and a RETRIEVAL / AS-OF DATE (when it was fetched or
last verified). [HARD] A fact without provenance and an as-of date SHALL NOT be stored as a
trusted fact (an un-sourced or undated claim is not a fact). This makes every fact auditable
and lets the host ground a claim and the freshness model reason about staleness.

**Acceptance criteria:** see acceptance.md AC-KS-003.

### REQ-KS-004 — Timeless vs time-sensitive fact classification (Ubiquitous) [HARD]

The store shall classify every fact as TIMELESS (does not expire — birth/founding year,
members, discography, the label of a past release) or TIME-SENSITIVE (truth depends on the
current date — upcoming release, current tour, "new single", "recently signed"). [HARD] The
classification is recorded on the fact and drives the freshness model (Group KF): timeless
facts are refreshed rarely; time-sensitive facts carry a validity window (REQ-KF-001) and
are refreshed often and gated at airtime. The classification heuristic is TUNABLE; that
every fact is classified is the rail.

**Acceptance criteria:** see acceptance.md AC-KS-004.

### REQ-KS-005 — Knowledge attaches to the library by artist/title keying; no fork (Ubiquitous) [HARD]

The system shall link knowledge entities to the existing `brain/library.py` library by the
same artist/title keying the library already uses (consistent with the dedup slug
semantics ANALYSIS-006 preserves at REQ-AD-005), so that a track in the library resolves to
its artist/release/song knowledge entities for grounding and curation. [HARD] The knowledge
store is a NEW relational store; it does NOT fork or modify the library JSON index or the
ANALYSIS-006 feature record — it references them.

**Acceptance criteria:** see acceptance.md AC-KS-005.

### REQ-KS-006 — Multi-source consensus before a fact is reliable / airable as certain (Ubiquitous) [HARD]

The system shall treat a researched editorial fact (bio, members, discography, label,
release, news) as RELIABLE / AIRABLE-AS-CERTAIN only when it is CORROBORATED across MULTIPLE
VERIFIED SOURCES above a consensus threshold. [HARD] The system shall maintain a
VERIFIED-SOURCE ALLOWLIST — MusicBrainz, Wikidata, Wikipedia, Last.fm, official artist/label
pages, and reputable music press — and shall:
- record, per fact, WHICH allowlisted sources assert it (multi-source provenance, extending
  REQ-KS-003's single source+URL to a set of corroborating source+URL entries);
- compute a per-fact CONFIDENCE from how many verified sources agree (more agreeing verified
  sources → higher confidence; authoritative structured sources — MusicBrainz, Wikidata —
  weigh more than crowd/press), against a TUNABLE consensus threshold;
- mark a fact CONSENSUS-PASSED when it meets the threshold, and FLAG a SINGLE-SOURCE or
  CONFLICTING fact (verified sources disagree) as unconfirmed.

[HARD] A fact that has NOT reached consensus SHALL NEVER be presented to the host as CERTAIN:
it is either omitted, or — only where editorially worthwhile — voiced QUALIFIED ("reportedly…",
"according to %SOURCE%…", "some sources say…"), never as established fact. A fact from a
source NOT on the verified allowlist does not count toward consensus (it may seed a research
lead but is not corroboration). The allowlist + the consensus threshold + the source weights
are TUNABLE config; that a fact is airable-as-certain only on multi-source consensus, and that
single-source/conflicting facts are flagged and qualified, are the FIXED rails.

[Boundary] This is the EDITORIAL-FACT counterpart to ANALYSIS-006 REQ-AM-003's multi-source
reconciliation for AUDIO / GENRE / per-track FEATURES — same discipline, distinct domain; it
does not fork or re-own AM-003. The consensus state feeds the freshness gate (REQ-KF-003:
a fact must be BOTH non-stale AND consensus-passed to air as certain) and the grounding feed
(REQ-KI-001: certain facts vs. hedged qualified facts).

**Acceptance criteria:** see acceptance.md AC-KS-006.

### REQ-KS-007 — Per-TRACK editorial fields on the song/recording entity (Ubiquitous) [HARD]

The store shall attach, to a song/recording entity, the deeper PER-TRACK EDITORIAL FIELDS a real DJ
researches before featuring a track: `recording_session` (where / how / with whom it was cut),
`writing_story` (how the song came to be), one or more `lyrical_meaning` readings (a track may carry
SEVERAL — each a separate entry with its OWN provenance + as-of date + confidence), `production_notes`
(who produced / engineered / technique / gear), and `era_context` (what the track meant in its moment).
[HARD] Each per-track editorial field is a FACT (or a set of facts) and carries the same provenance +
as-of date as any other fact (REQ-KS-003), is classified for currency (REQ-KF-005), and carries a
`subjectivity_class` (REQ-KS-008). [HARD] The `lyrical_meaning` field is INHERENTLY plural-capable so
COMPETING readings are stored side by side, never overwritten into one (the substrate for
contested-meaning, REQ-KS-008). The field SET is the rail (these fields must be representable); the
attributes within each are extensible. Lyrical text MAY be quoted verbatim where it supports an
interpretation (private-PoC posture — no licensing constraint).

**Acceptance criteria:** see acceptance.md AC-KS-007.

### REQ-KS-008 — Subjectivity class + editorial confidence-grade + disagreement; meaning-as-attributed-speech (Ubiquitous) [HARD]

The store shall tag every editorial claim with a `subjectivity_class` — FACTUAL (a verifiable claim:
recorded at Studio X, written by Y, produced by Z), INTERPRETED (what the lyrics MEAN / how critics read
the track), or EDITORIAL-OPINION (a critic's evaluative judgment) — and shall handle each class by its
nature:
- [HARD] **FACTUAL** claims route through the EXISTING REQ-KS-006 multi-source consensus engine
  UNCHANGED — it remains the SOLE airable-FACT seam: a FACTUAL claim is airable AS CERTAIN only on
  multi-source consensus, else flagged + qualified. No second fact-consensus path is created.
- [HARD] **INTERPRETED** and **EDITORIAL-OPINION** claims are NEVER stated as the station's own settled
  truth. They are aired only as MEANING-AS-ATTRIBUTED-SPEECH — attributed to whose reading it is
  ("%CRITIC% reads it as a breakup song", "the band has said it's about…", "critics at the time heard
  it as…"). Each carries an editorial CONFIDENCE-GRADE: HIGH (3+ authoritative sources concur on a
  reading) / MODERATE (2 sources, with the disagreement noted) / LOW (a single source, or strong
  disagreement); MODERATE and LOW are ALWAYS hedged.
- [HARD] Each subjective claim carries a DISAGREEMENT record of the competing readings/values across
  sources, so a CONTESTED meaning is a FIRST-CLASS airable outcome: the host MAY voice the disagreement
  itself ("some hear it as X, others as Y"), and a contested meaning is NEVER collapsed into one false
  certainty.

[HARD] KNOWLEDGE-008 OWNS the attributed claim + its source + its grade + its disagreement record;
PROGRAMMING-007 owns the host-voice PHRASING of attributed speech and the bounded self-aware first-person
MUSING aside (a light curiosity-framed question; the host opinion is never authoritative) — KNOWLEDGE-008
NEVER mints a host opinion as a fact and NEVER weakens the per-persona anti-convergence firewall
(PROGRAMMING-007 REQ-PR-004 / REQ-PR-009). The subjectivity heuristic + the grade thresholds are TUNABLE
config; that every editorial claim is classed, that FACTUAL routes through REQ-KS-006 unchanged, and that
INTERPRETED/EDITORIAL-OPINION are attributed + graded + hedged with contested-meaning preserved, are the
FIXED rails.

**Acceptance criteria:** see acceptance.md AC-KS-008.

### REQ-KS-009 — Reliability-ranked source tiers drive consensus weight (Ubiquitous) [HARD]

The system shall declare the REQ-KS-006 verified-source set as a RELIABILITY-RANKED TIER LIST (TUNABLE
config), not a flat allowlist, with at least the tiers: AUTHORITATIVE-STRUCTURED (MusicBrainz, Wikidata,
LoC Chronicling America / Internet Archive public-domain text) > REPUTABLE-PRESS (The Guardian, BBC,
Pitchfork, The Quietus, The Fader, AllMusic) > EDITORIAL-BLOG (Stereogum, Aquarium Drunkard, Bandcamp
Daily) > CROWD (Discogs notes, Last.fm, Genius community annotations, Songfacts). [HARD] A source's tier
drives its WEIGHT in the REQ-KS-006 consensus computation (a higher-reliability source contributes more to
a fact's confidence; a CROWD source corroborates weakly and never alone makes a fact airable-as-certain).
[PIVOT — private personal PoC] Sources are ranked by RELIABILITY, NOT by license; no copyright / ToS /
CC-vs-NC tiering, no scraping ban, and no attribution-for-law is applied — the ranking is purely about how
trustworthy the source is. [HARD] The tier membership + the per-tier weights are TUNABLE config; that the
source set is reliability-ranked and the rank drives consensus weight is the rail. The existing REQ-KS-006
consensus engine is REUSED unchanged; KS-009 only supplies it a richer, ranked weighting input.

**Acceptance criteria:** see acceptance.md AC-KS-009.

---

## 7. Requirement Group KF — Freshness & Currency

Priority: High. (The core user concern: dated knowledge, never announce stale.)

### REQ-KF-001 — Time-sensitive facts carry a validity window / expiry (Ubiquitous) [HARD]

The system shall give every TIME-SENSITIVE fact (REQ-KS-004) a VALIDITY WINDOW or EXPIRY —
the date range during which the fact is announceable (e.g. an "upcoming album" fact is valid
until its release date; a "current tour" until the tour's end) — derived from the fact's own
content where the source provides a date, or from a configured default window for its fact
type where it does not. [HARD] After its validity window passes, a time-sensitive fact is
STALE. The default windows per fact type are TUNABLE config; that every time-sensitive fact
has a window is the rail.

**Acceptance criteria:** see acceptance.md AC-KF-001.

### REQ-KF-002 — Brain knows the current Faroe-local date for freshness reasoning (Ubiquitous) [HARD]

The system's freshness reasoning shall use the CURRENT local date in the Faroe/Atlantic
timezone, obtained from the ORCH-005 world model's local-clock sensor (REQ-RW-002, anchored
to `Atlantic/Faroe`, DST-correct per OPS-004 REQ-OA-009 / NFR-O-9), as the reference against
which validity windows are evaluated. [HARD] Freshness is evaluated against the real current
Faroe date, never server-local time or a cached/stale clock; KNOWLEDGE-008 consumes the date
from ORCH-005, it does not re-own timezone handling.

**Acceptance criteria:** see acceptance.md AC-KF-002.

### REQ-KF-003 — Don't-announce-stale gate at generation / airtime (Unwanted) [HARD]

If a time-sensitive fact's validity window has passed relative to the current Faroe-local
date, then at fact-selection / generation / airtime the system SHALL NOT present that fact
as current: it shall DROP the stale fact, or RE-CAST it against the current date (e.g. an
"upcoming in two weeks" release whose date has passed is removed, or re-expressed as a past
release "out now / released last month" only if a fresh fact supports the re-cast).
[HARD] The host SHALL NOT state an expired time-sensitive fact as if still true. This is the
core user rail: dated knowledge, no stale announcements. The gate runs wherever facts are
selected for talk, curation, website, or news (Group KI).

[HARD] The same gate ALSO enforces the consensus state (REQ-KS-006): to be presented AS
CERTAIN a fact must be BOTH non-stale AND consensus-passed; a non-stale but
single-source/conflicting fact is passed through only QUALIFIED ("reportedly…"), never as
certain. A fact failing EITHER recency OR consensus is dropped or hedged accordingly. Recency
and consensus are independent conditions; both must hold for a certain claim.

**Acceptance criteria:** see acceptance.md AC-KF-003.

### REQ-KF-004 — Periodic re-research refresh; time-sensitive refreshed more often; stale flagged (State-driven) [HARD]

While running, the system shall periodically RE-RESEARCH facts to keep them current, on a
cadence that refreshes TIME-SENSITIVE facts MORE OFTEN than TIMELESS ones, and shall FLAG
entries whose as-of date is older than a configured freshness threshold (per fact class) as
due for refresh so a refresh job (Group KR) re-verifies them. [HARD] Time-sensitive facts get
a tighter refresh threshold than timeless facts; the concrete thresholds and cadences are
TUNABLE config, but that time-sensitive facts are refreshed more aggressively and that stale
entries are flagged is the rail. Refresh runs as a background research job (Group KR), never
on the pull path.

**Acceptance criteria:** see acceptance.md AC-KF-004.

### REQ-KF-005 — Per-track editorial fact currency classification incl. a third CONTEXTUAL class (Ubiquitous) [HARD]

The system shall classify the per-track editorial facts (REQ-KS-007) for currency: WRITING and RECORDING
facts (when/where/with-whom a track was written or cut, its production credits) are TIMELESS (REQ-KS-004 —
they do not expire); LYRICAL-MEANING and CULTURAL-CONTEXT facts (`lyrical_meaning`, `era_context`) are a
THIRD currency class, CONTEXTUAL. [HARD] A CONTEXTUAL fact does NOT expire on a date the way a TIME-SENSITIVE
fact does — there is no release-date past which it goes stale — but it ACCRUES and SHIFTS as readings evolve:
it is refreshed on a cadence (REQ-KF-004), MAY gain additional `lyrical_meaning` readings or DISAGREEMENT
over time (REQ-KS-008), and is NEVER gated out by the don't-announce-stale release-date gate (REQ-KF-003,
which targets TIME-SENSITIVE facts only). [HARD] The CONTEXTUAL class is therefore exempt from the
expired-release-date drop, but still subject to refresh + the consensus/attribution discipline. That every
per-track editorial fact is classified, and that lyrical-meaning/cultural-context is the accruing CONTEXTUAL
class rather than a date-expiring one, is the rail.

**Acceptance criteria:** see acceptance.md AC-KF-005.

---

## 8. Requirement Group KR — Continuous Research Jobs

Priority: High.

### REQ-KR-001 — Research triggered by new-artist ingest, periodic refresh, and pre-show prep (Event-driven) [HARD]

When (a) a new artist enters the library via the ANALYSIS-006 auto-ingest scan (REQ-AP-007),
or (b) a fact/entity is flagged for refresh by its freshness threshold (REQ-KF-004), or (c) a
show/persona is about to feature a particular artist (pre-show prep), the system shall ENQUEUE
a research job for the relevant artist/band/release/song so the knowledge base is filled and
kept current. [HARD] New-artist ingest is the primary fill trigger; the periodic refresh keeps
time-sensitive facts current; the pre-show prep makes a featured artist well-researched before
air. The trigger that detects a new artist is ANALYSIS-006's scan (referenced); this
requirement owns enqueuing the research from it.

**Acceptance criteria:** see acceptance.md AC-KR-001.

### REQ-KR-002 — Research from MusicBrainz, Wikidata/Wikipedia, Last.fm, web, official/label pages (Event-driven) [HARD] [documented compound]

[Documented compound requirement: research draws on several alternative sources feeding the
same dated relational store; the sources are alternatives, not separable requirements, and
share one AC. Verified intentionally compound.]

When a research job runs, the system shall gather facts and relationships from these SOURCES,
preferring authoritative + structured over crowd/free-text: (a) **MusicBrainz** for
discography, relationships, members, and labels (the relational gold — member-of /
side-project / collaborator / label edges, one-call-per-second, User-Agent required, no key);
(b) **Wikidata / Wikipedia** for biography and dated facts (founding/birth dates, career
milestones — via the entity-data endpoint / SPARQL, no key, respect 429/Retry-After);
(c) **Last.fm** for bio, tags, and similar artists (`artist.getInfo` / `artist.getTopTags` /
`artist.getSimilar` — requires an API key); (d) **web search** for RECENT NEWS and UPCOMING
releases (the "new album in two weeks" facts — the hardest to keep accurate, hence heavily
dated); and (e) **official / label pages** where findable. Each fetched fact is stored with
its source + URL + as-of date (REQ-KS-003) and classified (REQ-KS-004). The external HTTP
CLIENT layer is shared with OPS-004 REQ-OA-011 (referenced, not re-owned); this requirement
owns WHICH sources and WHAT to extract into the dated relational store.

**Acceptance criteria:** see acceptance.md AC-KR-002.

### REQ-KR-003 — De-duplicated, idempotent, cached research (Ubiquitous) [HARD]

The system shall make research DE-DUPLICATED, IDEMPOTENT, and CACHED: an entity is keyed
(by MBID/QID where available, else normalized name) so the same artist is not researched as
two entities; a research job that re-runs over unchanged source data does not duplicate facts
or edges (it updates as-of dates and adds only new facts); and fetched source responses are
cached with the facts so a restart, retry, or re-scan does not re-fetch unnecessarily.
[HARD] Re-running a research job is safe and non-duplicating (mirrors ANALYSIS-006 REQ-AE-002
idempotency in spirit).

**Acceptance criteria:** see acceptance.md AC-KR-003.

### REQ-KR-004 — Bounded, throttled, rate-limit-respecting research (State-driven) [HARD]

While researching, the system shall run research jobs as a BOUNDED, THROTTLED queue that
adopts the OPS-004 REQ-OH-006 acquisition-accounting / bounded-job pattern — it shall not
enqueue an unbounded flood, it shall throttle research throughput in concert with acquisition
and analysis load so the modest box is not jointly overloaded, and it shall RESPECT each
external source's RATE LIMIT, API key, and terms of service (MusicBrainz ≤1 req/s with a
proper User-Agent; Last.fm key + limits; Wikidata 429/Retry-After; web-search/official-page
politeness). [HARD] The queue bound + throttle thresholds + per-source rate limits are TUNABLE
config; that research is bounded, throttled, and rate-limit-respecting is the rail.

**Acceptance criteria:** see acceptance.md AC-KR-004.

### REQ-KR-005 — Research is background, non-blocking, and degrades gracefully (Unwanted) [HARD]

If a research job is slow, queued, a source is down, or an API quota/rate limit is hit, then
the system SHALL NOT block, stall, or silence the stream: research runs strictly as a
background job dispatched by the ORCH-005 director loop (Group RL, REQ-RC-001), never on the
`/api/next` pull path, and a source outage or quota hit degrades gracefully — the affected
facts simply stay at their last-known state (flagged stale if applicable) and the job
re-attempts on a later cadence (ORCH-005 REQ-RD-002 self-recovery). [HARD] Missing or lagging
research degrades knowledge richness, never continuity; the music keeps playing.

**Acceptance criteria:** see acceptance.md AC-KR-005.

### REQ-KR-006 — Per-TRACK and per-ALBUM deep-research job types (Event-driven) [HARD]

When a track/album needs deeper editorial coverage (it is freshly ingested, flagged for refresh, or about
to be featured), the system shall run PER-TRACK and per-ALBUM DEEP-RESEARCH jobs — distinct from the
per-ARTIST job (REQ-KR-001/002) — that research the recording session, writing story, lyrical reading(s),
production credits, and era context for that specific track/release and fill the per-track editorial fields
(REQ-KS-007). [HARD] The per-track/per-album jobs reuse the same de-dup/idempotency/cache (REQ-KR-003),
bounded/throttled queue (REQ-KR-004), and non-blocking background discipline (REQ-KR-005) as the artist
job; they add WHAT to research at track/album granularity, not a second job runner. Each fetched item is
stored with provenance + as-of date (REQ-KS-003), a subjectivity class (REQ-KS-008), and a currency class
(REQ-KF-005). That per-track + per-album deep-research jobs exist and feed the per-track editorial fields
is the rail.

**Acceptance criteria:** see acceptance.md AC-KR-006.

### REQ-KR-007 — Pre-show research pass with a bounded timeout, before grounding-feed assembly (Event-driven) [HARD]

When a show/persona is about to feature a particular artist/release/track (pre-show prep, REQ-KR-001 case
(c)), the system shall run a PRE-SHOW RESEARCH PASS — a bounded deep-research pass (REQ-KR-006) that aims to
COMPLETE within a configured TIMEOUT BEFORE the grounding feed (Group KI) is assembled for that show, so the
host goes on air well-researched. [HARD] The pre-show pass has a BOUNDED TIMEOUT; on timeout it SHALL NOT
block — the grounding feed is assembled with whatever facts are READY (and unresearched fields simply yield
no claim, REQ-KI-001), and the remaining research continues in the background and is available for a later
break. [HARD] The pre-show pass NEVER runs on the `/api/next` pull path and NEVER stalls a curation tick, a
talk break, or playout (inherits REQ-KR-005). [Boundary] SHOWS-020's pre-show prep TRIGGERS this pass;
KNOWLEDGE-008 owns the bounded deep-research-before-grounding behavior, SHOWS-020 owns when a show is
scheduled (referenced, not re-owned). That the pre-show pass is bounded-timeout and never blocks is the rail.

**Acceptance criteria:** see acceptance.md AC-KR-007.

### REQ-KR-008 — Discogs artist-scoped editorial provider; structured can reach consensus, NOTES always hedged (Event-driven) [HARD]

When a research job runs, the system MAY consult a DISCOGS ARTIST-SCOPED editorial provider (`SRC_DISCOGS`)
for credits, companies, labels, and styles. [HARD] Discogs is a CROWD-tier source (REQ-KS-009, weight
~0.25 — NOT authoritative): its STRUCTURED fields (release credits, company roles, label, genre/style tags)
CAN contribute toward multi-source consensus (REQ-KS-006) like any other corroborating source, but its
FREE-TEXT NOTES are PERMANENTLY SINGLE-SOURCE — they originate with one Discogs contributor, cannot be
corroborated by their nature, and SHALL therefore ALWAYS be hedged + attributed ("according to Discogs…"),
NEVER stated as a consensus-passed certain fact. [HARD] Discogs structured credits populate the
`credited_to` / `recorded_at` / `signed_to` graph edges and the ENTITY_PERSON / ENTITY_PLACE nodes
(REQ-KG-006); the heavier per-release-credit cross-check against the MusicBrainz mirror is DEFERRED to
MBMIRROR-017 (referenced, not forked here). The Discogs key/availability is config-gated; with no Discogs
access the provider is simply skipped (graceful, REQ-KR-005). That Discogs structured fields can reach
consensus while its free-text notes are permanently single-source/hedged is the rail.

**Acceptance criteria:** see acceptance.md AC-KR-008.

### REQ-KR-009 — Expanded reliability-ranked provider set, reachable by scraping where no API (Event-driven) [HARD] [documented compound]

[Documented compound requirement: research draws on many alternative editorial sources feeding the SAME
reliability-ranked consensus engine (REQ-KS-006/009); the sources are alternatives, not separable
requirements, and share one AC. Verified intentionally compound.]

When a research job runs, the system shall draw on an EXPANDED, RELIABILITY-RANKED provider set beyond the
core MusicBrainz/Wikidata/Last.fm/web sources, each tagged its reliability tier (REQ-KS-009): **The
Guardian** (free Open Platform API, full article text — REPUTABLE-PRESS, dual-use for OPS-004 news leads +
music-journalism); **Internet Archive** (discovery + public-domain text + Wayback recovery of dead
sources); **LoC Chronicling America** (public-domain full-text historical press); **CritiqueBrainz** (open
music criticism); plus the editorial sources **Nardwuar**, **WhoSampled** (sample/interpolation lineage,
REQ-KG-006), **Bandcamp Daily**, **Aquarium Drunkard**, **The Fader**, **Stereogum**, **The Quietus**,
**BBC**, and the deep sources **Genius** / **AllMusic** / **Pitchfork** / **Songfacts**. [HARD] Where a
source has NO API, the system MAY reach it by SCRAPING (e.g. `trafilatura` / `newspaper4k` for article
extraction); scraping is a permitted acquisition method for this private PoC. [PIVOT — private personal
PoC] Sources are ranked by RELIABILITY, NOT by license — no copyright/ToS/CC-vs-NC filtering, no scraping
ban, no attribution-for-law, no no-store-time rule; lyrics may be quoted verbatim for analysis (Genius /
Songfacts lyrical readings). [HARD] **AOTY (AlbumOfTheYear)** is SKIP-ON-FEASIBILITY — it Cloudflare
bot-blocks and is recorded as NOT reliably reachable (a feasibility skip, not a policy exclusion). Every
fetched item is stored with provenance + as-of date (REQ-KS-003), a subjectivity class (REQ-KS-008), and
its source tier (REQ-KS-009), and flows through the UNCHANGED consensus engine (REQ-KS-006). That the
provider set is reliability-ranked and scraping-reachable where no API exists, feeding the same consensus
engine, is the rail.

**Acceptance criteria:** see acceptance.md AC-KR-009.

---

## 9. Requirement Group KG — Relational Graph

Priority: High. (Enables sane transitions + genuinely related music.)

### REQ-KG-001 — Relationship model across entities (Ubiquitous) [HARD]

The store shall model RELATIONSHIPS as first-class edges between entities, including at
least: artist↔artist (member-of, side-project / solo project, collaborator, similar /
influenced-by), artist↔label (signed-to / released-on), artist↔genre/scene/era/place,
song↔song (cover / sample / remix lineage), and release↔artist (credited-to). [HARD] Each
edge carries its type, provenance (REQ-KS-003), and an as-of date so relationships are
auditable and dateable like facts. The edge type SET is the rail (these relations must be
representable); additional edge types are extensible.

**Acceptance criteria:** see acceptance.md AC-KG-001.

### REQ-KG-002 — Seed the graph from ANALYSIS-006, enrich with researched relationships (Event-driven) [HARD]

The system shall SEED the relational graph from ANALYSIS-006 — importing its Last.fm
SIMILAR-ARTIST edges (REQ-AD-003 discovery-boundary note / Group AM) as artist↔artist
similar edges and its genre/era feature dimensions (REQ-AD-002/003) as artist↔genre/era edges
— and shall ENRICH the seeded graph with RESEARCHED relationships from research jobs (chiefly
MusicBrainz member-of / side-project / collaborator / label edges, REQ-KR-002). [HARD] The
seed edges are marked as seed-provenance and the researched edges as research-provenance so
the two are distinguishable; KNOWLEDGE-008 EXTENDS ANALYSIS-006's edges, it does not
recompute the similar-artist analysis or the audio features.

[Annotation, v0.3.0] The researched-edge sources now include the DISCOGS provider (REQ-KR-008): Discogs
STRUCTURED credits populate the `credited_to` / `recorded_at` / `signed_to` edges and the ENTITY_PERSON /
ENTITY_PLACE nodes, marked Discogs research-provenance (CROWD-tier). The richer TRACK-TO-TRACK edges are
specified in REQ-KG-006. Per-release-credit cross-check against the MusicBrainz mirror remains DEFERRED to
MBMIRROR-017 (referenced, not forked).

**Acceptance criteria:** see acceptance.md AC-KG-002.

### REQ-KG-003 — Related-music selection query (Event-driven) [HARD]

When curation needs music RELATED to the current track's artist, the system shall provide a
query over the graph that returns genuinely related tracks — artists connected by a real edge
(member-of / side-project / collaborator / same-label / similar) and/or sharing a
genre/era/scene dimension, intersected with what is actually in the library and airable.
[HARD] The related-music selection is grounded in REAL graph edges + shared dimensions, NEVER
a free-associated similarity; the curation POLICY (which related track to pick, the persona
taste charter) is PROGRAMMING-007/OPS-004's call, this requirement provides the grounded
candidate query.

**Acceptance criteria:** see acceptance.md AC-KG-003.

### REQ-KG-004 — Sane-transition / grounded-comparison query (Event-driven) [HARD]

When the host makes a transition or comparison ("speaking of X, here's their side-project Y";
"this label also put out Z"; "like X, but from the same scene"), the system shall provide a
query that returns the REAL graph edges connecting the current artist to the candidate
material, so the segue and any comparison the host voices are grounded in an actual stored
relationship. [HARD] A "speaking of … related …" segue or comparison the host speaks SHALL be
backed by a real edge from this query; the host SHALL NOT free-associate a relationship that
does not exist in the graph (ties to the grounded-banter discipline, Group KI / PROGRAMMING-007).

**Acceptance criteria:** see acceptance.md AC-KG-004.

### REQ-KG-005 — Graph supports era/scene/network/label cohesion for curation (Event-driven)

When curation builds a cohesive set (a scene night, a label showcase, an era block, a
network of collaborators), the system shall support queries that group artists/tracks by a
shared dimension or network — same genre/scene/era, same label, or a connected
collaborator/member cluster — so the program director can build cohesive, related programming
rather than a disconnected shuffle. This provides the cohesion query primitives; the editorial
decision to build such a set is OPS-004/PROGRAMMING-007's (consistent with the per-persona
distinct-taste separability, ANALYSIS-006 REQ-AD-003).

**Acceptance criteria:** see acceptance.md AC-KG-005.

### REQ-KG-006 — Richer track-to-track edges; Discogs-populated credit/person/place edges (Ubiquitous) [HARD]

The store shall model richer TRACK-TO-TRACK (song↔song) edges beyond the cover/sample/remix lineage of
REQ-KG-001: COVER LINEAGE (this recording is a cover of / was covered by that song), SAMPLE / INTERPOLATION
(this track samples or interpolates that one — sourced chiefly from WhoSampled, REQ-KR-009), WRITING /
PRODUCTION CONNECTIONS (two tracks sharing a writer or producer), and THEMATIC / MUSICAL INFLUENCE (one
track is an acknowledged influence on / response to another). [HARD] Each edge carries its type, provenance,
and an as-of date (REQ-KG-001), and supports the sane-transition / grounded-comparison query (REQ-KG-004) so
the host can ground a track-to-track segue ("this samples that", "these two share a producer") in a REAL
edge, never a free-associated one. [HARD] In addition, the `credited_to` / `recorded_at` / `signed_to` edges
and the ENTITY_PERSON (a producer / session player / writer) and ENTITY_PLACE (a studio / scene location)
nodes are now POPULATED BY DISCOGS structured credits (REQ-KR-008), marked Discogs research-provenance
(CROWD-tier). The edge-type SET is the rail (these track-to-track + credit/person/place relations must be
representable); additional edge types are extensible.

**Acceptance criteria:** see acceptance.md AC-KG-006.

---

## 10. Requirement Group KI — Grounding Feed & Integration

Priority: High.

### REQ-KI-001 — Knowledge base is the verified-facts source for the talk-script LLM (Ubiquitous) [HARD]

The system shall expose the dated, sourced, FRESH facts + graph edges as a GROUNDING FEED
that is THE verified-facts source supplied to the talk-script LLM, so the host speaks ONLY
from facts in the knowledge base (passed the freshness gate, REQ-KF-003) and NOT from
free-recall. [HARD] Factual claims the host makes about an artist/track/release SHALL be
grounded in a stored, dated, sourced, non-stale fact; an artist with no researched facts yet
yields no factual claims (the host falls back to genre/feel-level talk, PROGRAMMING-007),
never invented biography. [HARD] The feed shall mark each fact's CONSENSUS state (REQ-KS-006):
a CONSENSUS-PASSED fact is offered to the host as CERTAIN, while a single-source/conflicting
fact is offered ONLY as a QUALIFIED claim (carrying its "reportedly…" / "according to %SOURCE%"
hedge + its source) so the host never voices an unconfirmed fact as established. This ties to
OPS-004 REQ-OC-005 (grounded, not fabricated) and the r-organic grounding architecture
(PROGRAMMING-007); KNOWLEDGE-008 owns the verified-facts SOURCE + its certainty marking,
PROGRAMMING-007 owns HOW the host speaks it (certain vs. hedged).

**Acceptance criteria:** see acceptance.md AC-KI-001.

### REQ-KI-002 — Feed curation: related-music selection + sane transitions (Event-driven) [HARD]

The system shall feed the relational graph queries (Group KG) to the picker / curation so the
program director selects genuinely RELATED music and makes SANE, conscious transitions
grounded in real edges. [HARD] Related-music and sane-transition decisions consume the
grounded queries (REQ-KG-003/004); the picker SHALL NOT base a "related" selection on a
similarity that has no graph edge or shared dimension. The selection POLICY is OPS-004/
PROGRAMMING-007's; this requirement provides the grounded feed it consumes.

**Acceptance criteria:** see acceptance.md AC-KI-002.

### REQ-KI-003 — Feed the website (artist / show notes) and the newscaster (music news) (Event-driven)

The system shall feed the dated, sourced facts to (a) the self-controlled website (CORE-001
Group E) for artist notes / show notes / "now playing" context, and (b) the newscaster
(OPS-004 Group OG) for MUSIC NEWS (new releases, artist news), each passed through the
freshness gate (REQ-KF-003) so neither the website nor a newscast presents a stale fact. The
website rendering and the news production are owned by CORE-001 / OPS-004 (referenced); this
requirement owns supplying them the fresh, sourced facts.

**Acceptance criteria:** see acceptance.md AC-KI-003.

### REQ-KI-004 — The worked %ARTIST% / new-album / %LABEL% / sneak-peek scenario is expressible end-to-end (Event-driven) [HARD]

The system shall make the user's worked scenario expressible end-to-end from the knowledge
base: GIVEN a time-validated fact ("%ARTIST% has a new solo-project album releasing on
%DATE% on %LABEL%", time-sensitive, valid until %DATE%, sourced + dated) AND a relational
link (the artist → the solo project → the latest single present in the library) AND a curation
action (queue that single), the host can say "speaking of %ARTIST%, he's got a new solo
project releasing an album in two weeks on %LABEL%, here's a sneak peek of his latest single"
— and the curation queues the single. [HARD] If the release-date fact has expired relative to
the current Faroe date (REQ-KF-003), the "in two weeks" framing is dropped or re-cast (e.g.
"out now"); the relational link and the comparison are grounded in real edges (REQ-KG-004).
This requirement is the integration test that the dated fact + the relational link + the
curation action compose.

**Acceptance criteria:** see acceptance.md AC-KI-004.

### REQ-KI-005 — Grounding feed coordinates with the ledger/diary memory substrate (Ubiquitous)

The system shall coordinate research outcomes and knowledge updates with the existing
memory substrate — OPS-004's append-only event ledger + director diary (REQ-OD-007/008) and
PROGRAMMING-007's acquisition diary (REQ-PL-003) — recording research events (artist
researched, facts added/refreshed, a fact aired) for continuity and audit, so the director
picks up its editorial through-line and a research/fact decision is auditable after the fact.
KNOWLEDGE-008 owns recording the knowledge events; OPS-004 owns the ledger/diary store
(no fork).

**Acceptance criteria:** see acceptance.md AC-KI-005.

### REQ-KI-006 — Release-scoped grounding accessor for in-depth album shows (Event-driven) [HARD]

The system shall expose a RELEASE-SCOPED grounding accessor `grounding_for_release(artist_key, album_title)`
— beside the existing artist/track-scoped grounding feed (REQ-KI-001) — that returns the dated, sourced,
fresh, consensus-marked facts + graph edges scoped to a SPECIFIC RELEASE: the album's release facts, its
per-TRACK editorial fields (REQ-KS-007), its production credits + credited-to/recorded-at edges (REQ-KG-006),
and its era context, so an IN-DEPTH ALBUM SHOW (which is release-scoped, not artist-scoped) is grounded at
the right granularity. [HARD] Every fact the release accessor returns passes the SAME freshness + consensus
gate (REQ-KF-003) and carries the SAME certain-vs-qualified + attributed-speech marking (REQ-KS-006/008,
REQ-KI-001) as the artist-scoped feed — the release accessor is a SCOPE over the same engine, not a second
grounding path. An album with no researched facts yields no claims (the host falls back, REQ-KI-001). That a
release-scoped grounding accessor exists over the same gated engine is the rail.

**Acceptance criteria:** see acceptance.md AC-KI-006.

---

## 11. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following:

- **Per-TRACK audio-feature analysis** (BPM/key/energy/genre/cue points) — owned by
  ANALYSIS-006; KNOWLEDGE-008 joins against it + seeds the graph from it, never recomputes.
- **The library auto-ingest SCAN mechanism** — owned by ANALYSIS-006 REQ-AP-007; referenced
  only as the artist-research trigger.
- **The director LOOP + background-job SCHEDULING** — owned by ORCH-005 Group RL; KNOWLEDGE-008
  defines the jobs, ORCH schedules them.
- **The external-source HTTP CLIENT layer** (MusicBrainz / Last.fm / Wikidata / web request
  plumbing, rate-limit queueing, key handling) — shared with OPS-004 REQ-OA-011; KNOWLEDGE-008
  owns WHAT to research + the dated relational schema + de-dup/cache, not a second HTTP client.
- **The news PRODUCTION pipeline + general (non-music) news sourcing** — owned by OPS-004
  Group OG; KNOWLEDGE-008 feeds it music news only.
- **Multi-source consensus for AUDIO / GENRE / per-track FEATURES** — owned by ANALYSIS-006
  REQ-AM-003; KNOWLEDGE-008's REQ-KS-006 consensus covers researched EDITORIAL FACTS only
  (bio/members/discography/labels/releases/news), not track-feature reconciliation.
- **HOW the host speaks** (radio-craft, ear-writing, persona POV, banter delivery, the exact
  qualified-claim phrasing) — owned by PROGRAMMING-007; KNOWLEDGE-008 supplies the facts +
  their certain/hedged marking, not the delivery wording.
- **The attributed-speech PHRASING + the bounded personal-musing host aside** — owned by
  PROGRAMMING-007 (Group PG / Group PV + the host-voice musing allowance); KNOWLEDGE-008 supplies
  the ATTRIBUTED claim + its source + grade + disagreement record (REQ-KS-008), never the host's
  spoken wording and never a host opinion minted as a fact; the per-persona anti-convergence
  firewall (REQ-PR-004 / REQ-PR-009) is referenced, never re-owned or weakened.
- **A copyright / ToS / license source-tiering axis** — explicitly NOT built (PIVOT, private PoC):
  sources are ranked by RELIABILITY only (REQ-KS-009); no CC0-vs-NC filtering, no ToS exclusions,
  no scraping bans, no attribution-for-law, and no no-store-time rules are added. Scraping is a
  permitted acquisition method; lyrics may be quoted verbatim for analysis.
- **AOTY (AlbumOfTheYear) scraping** — SKIP-ON-FEASIBILITY (Cloudflare bot-block, not reliably
  reachable); recorded as a feasibility skip, not built (REQ-KR-009).
- **The PER-RELEASE-CREDIT cross-check against the MusicBrainz mirror** — DEFERRED to MBMIRROR-017;
  KNOWLEDGE-008 populates Discogs structured credits onto the graph (REQ-KR-008/KG-006) but does not
  reconcile them release-by-release against the mirror, and does not fork the mirror or its clients.
- **A path that promotes REFLECT-026 internal beliefs/hypotheses into the airable-fact contract** —
  explicitly NOT built. REFLECT-026 (the station's internal beliefs/hypotheses layer) REUSES the
  KNOWLEDGE-008 fact-discipline PATTERN for its OWN store, but a REFLECT-026 hypothesis — however
  internally confident — is NEVER admitted to the grounding feed (Group KI) as an airable editorial
  fact. REQ-KS-006 multi-source consensus stays the SOLE airable-fact seam; the boundary is
  one-directional (KNOWLEDGE-008 facts may ground REFLECT-026 reasoning, REFLECT-026 hypotheses may
  not become airable facts). REFLECT-026 owns its internal-belief store; this SPEC neither forks it
  nor opens a second airable-fact path for it.
- **The curation / taste POLICY** (which related track to pick, the persona taste charter,
  the anti-convergence firewall) — owned by OPS-004 / PROGRAMMING-007; KNOWLEDGE-008 supplies
  the grounded related-music + transition queries.
- **Similar-artist DISCOVERY for targeted ACQUISITION / the acquisition wishlist** — a
  CORE-001/OPS-004 curation/acquisition concern (ANALYSIS-006 REQ-AD-003 note); the graph may
  surface candidates but does not own the wishlist or acquisition.
- **The append-only ledger / diary STORE / schema** — owned by OPS-004 REQ-OD-007/008;
  coordinated with, not forked.
- **A vector / embedding semantic-search store over bios** — out of scope; relational graph
  + dated facts only. A possible future enhancement.
- **Full Wikipedia / general-encyclopedia ingestion** — only music-relevant artist/band/
  release/song/label facts; not a general knowledge base.
- **A new playout seam, a new service, or a Liquidsoap change** — brain-only; the store is a
  new SQLite file in `/db`.

---

## 12. Storage-engine note (recommendation, not a hard rail)

The recommended engine is **SQLite** (research.md): relational (the joins this SPEC needs are
native SQL), file-based + serverless + zero-config (no server process to run on the modest
cloud box), already shippable in the brain container (Python's stdlib `sqlite3`), and living
in `/db` alongside the existing JSON stores. The current JSON-file stores cannot express the
relational joins (artist→side-project→release→song, label showcases, collaborator clusters)
without loading and scanning everything in memory; an embedded graph database (e.g. a
property-graph engine) is heavier than the modest single box and the moderate graph size
warrant, and SQLite with recursive CTEs comfortably handles the relationship traversals at
this scale. The SPEC fixes the persisted/relational/dated/queryable CAPABILITY + the schema
shape + the rails; the specific engine is an implementation choice behind that stable schema,
and a future move to a graph DB or the addition of a vector index (Section 11) would not
change the requirements.

---

## 13. Non-Functional Requirements

### NFR-K-1 — Dated, sourced facts; never undated/un-sourced (Ubiquitous) — Priority High
Every fact and every relationship edge shall carry provenance (source + URL) and an as-of
date; every time-sensitive fact shall additionally carry a validity window (REQ-KS-003,
REQ-KS-004, REQ-KF-001). An undated or un-sourced claim shall not be stored as a trusted
fact. See acceptance.md AC-NFR-K-1.

### NFR-K-2 — Never announce stale or unconfirmed-as-certain; grounded never fabricated (Ubiquitous) — Priority High
No code path shall present an expired time-sensitive fact as current (REQ-KF-003), present a
non-consensus (single-source/conflicting) fact AS CERTAIN (REQ-KS-006 — such facts may only be
voiced qualified), or assert (in a host claim, website note, or newscast item) a fact absent
from the knowledge base (REQ-KI-001, inherits OPS-004 REQ-OC-005 / REQ-OG-005 / NFR-O-7); aired
facts are logged with their consensus + freshness state so a stale, unconfirmed-as-certain, or
ungrounded statement is detectable after the fact. See acceptance.md AC-NFR-K-2.

### NFR-K-3 — Non-blocking to the playout pull (Ubiquitous) — Priority High
Research and knowledge refresh shall be fully decoupled from the `/api/next` pull; a pull
shall never wait on a research job, a source fetch, or a knowledge query render, and the
freshness gate at generation time reads ready knowledge (REQ-KR-005, inherits ORCH-005
NFR-R-2/3, OPS-004 NFR-O-10). See acceptance.md AC-NFR-K-3.

### NFR-K-4 — Bounded, throttled, rate-limit/ToS-respecting research (Ubiquitous) — Priority High
Research jobs shall be bounded and throttled (OPS-004 REQ-OH-006 pattern) and shall respect
each external source's rate limit, API key, and terms of service (REQ-KR-004); a quota hit or
rate-limit breach shall back off, never hammer a source. See acceptance.md AC-NFR-K-4.

### NFR-K-5 — Resilience / never-crash, never-silence (Ubiquitous) — Priority High
A failed research job, a source outage, a malformed response, or a knowledge-store error
shall log and be skipped without crashing the research worker, the director loop, or the
daemon, and without silencing the stream; facts stay at last-known state and re-attempt later
(REQ-KR-005, inherits ORCH-005 REQ-RD-001/002). See acceptance.md AC-NFR-K-5.

### NFR-K-6 — Relational comparisons grounded in real edges (Ubiquitous) — Priority High
Every related-music selection and every "speaking of … related …" transition/comparison the
host voices shall be grounded in a real stored graph edge or shared dimension (REQ-KG-003/004,
REQ-KI-002), never a free-associated relationship; a comparison without a backing edge shall
not be made. See acceptance.md AC-NFR-K-6.

### NFR-K-7 — Simplicity / no over-engineering (Ubiquitous) — Priority Medium
This SPEC shall implement the smallest knowledge substrate that delivers the dated relational
store, the freshness gate, the continuous research jobs, the relational graph, and the
grounding feed on the confirmed brain-only stack; deferred items (Section 11) MUST NOT be
partially built — no new service, no second HTTP client, no vector store, no graph-DB engine,
no Liquidsoap change. See acceptance.md AC-NFR-K-7.

### NFR-K-8 — Subjective/interpreted editorial claims are attributed + hedged, never stated as fact (Ubiquitous) — Priority High
No code path shall present an INTERPRETED or EDITORIAL-OPINION claim (a lyrical meaning, a critical
reading, a critic's evaluative judgment) AS the station's own settled fact: such claims are aired only as
MEANING-AS-ATTRIBUTED-SPEECH (attributed to whose reading it is) with their editorial confidence-grade, and
MODERATE/LOW-grade claims are hedged (REQ-KS-008). A CONTESTED meaning is preserved as a first-class airable
outcome (the host may voice the disagreement) and is NEVER collapsed into one false certainty. FACTUAL
claims remain governed by the REQ-KS-006 consensus engine UNCHANGED (the sole airable-FACT seam); aired
editorial claims are logged with their subjectivity class + grade + attribution so an unattributed-as-fact
statement is detectable after the fact. The host opinion is never authoritative, and the per-persona
anti-convergence firewall (PROGRAMMING-007 REQ-PR-004 / REQ-PR-009) is untouched. See acceptance.md
AC-NFR-K-8.

---

## 14. Open Questions / Risks

- **R-K-1 — Web-sourced "upcoming release" facts are the hardest to keep accurate (High).**
  Recent-news / upcoming-release facts from web search are the least structured and most
  perishable source — a scraped "new album in two weeks" can be wrong, delayed, or already
  out. This is the central editorial risk and the direct driver of the dating model. Mitigated
  by: classifying them TIME-SENSITIVE with a tight validity window keyed to the release date
  (REQ-KF-001), the don't-announce-stale gate (REQ-KF-003) that drops/re-casts them once the
  date passes, aggressive re-research of time-sensitive facts (REQ-KF-004), provenance + as-of
  dating so a wrong source is auditable (REQ-KS-003), and the grounded-not-fabricated rail
  (REQ-KI-001). A wrong-but-dated fact that the gate catches is acceptable; a stale fact aired
  as current is the defect the whole freshness model prevents.
- **R-K-2 — External-source rate limits / keys / ToS (Medium).** MusicBrainz is ≤1 req/s with
  a required User-Agent (no key); Last.fm needs a free API key and has limits + commercial-use
  contact terms; Wikidata is key-free but expects User-Agent compliance + 429/Retry-After
  backoff; web search and official-page fetches need politeness. Mitigated by the bounded/
  throttled queue respecting per-source limits (REQ-KR-004), caching responses with the facts
  (REQ-KR-003), running off the playout path (REQ-KR-005), and config-gating keys like the
  other OA-011 sources. The shared HTTP client (OPS-004 REQ-OA-011) is not re-owned here.
- **R-K-3 — Entity de-dup / disambiguation (Medium).** Two artists with the same name, a
  band vs. a solo artist sharing a name, or a garbled tag can split or merge entities wrongly.
  Mitigated by keying on MusicBrainz MBID / Wikidata QID where available (REQ-KS-002), the
  de-dup/idempotency rule (REQ-KR-003), and consuming OPS-004 REQ-OA-010 tag correction +
  ANALYSIS-006 keying. Residual: an artist with no MBID match relies on normalized-name keying
  and may need a manual merge later — flagged.
- **R-K-4 — Relational-graph quality depends on MusicBrainz coverage (Medium).** Sane
  transitions + grounded comparisons are only as good as the researched edges; an obscure
  artist may have sparse MusicBrainz relationships. Mitigated by seeding from ANALYSIS-006's
  similar-artist edges + genre/era dimensions (REQ-KG-002) so the graph is non-empty even
  before deep research, by enriching over time (REQ-KF-004 refresh), and by the grounded-only
  rail (REQ-KG-004) so a missing edge means "no claim", never a fabricated one.
- **R-K-5 — Storage-engine choice + SQLite concurrency (Low/Medium, build-time).** SQLite is
  recommended (research.md) but a single writer + concurrent readers needs care under the
  brain's async loop (WAL mode, short transactions). Mitigated by the engine being an
  implementation choice behind a stable schema (Section 12), the store living off the pull
  path (NFR-K-3), and writes happening in the serialized research worker (REQ-KR-004 /
  ORCH-005 REQ-RC-002). Reads for the freshness gate are non-blocking snapshots.
- **R-K-6 — Boundary overlap with ANALYSIS-006 + OPS-004 (Low, reconciled).** ANALYSIS-006
  already owns per-track genre/tags + Last.fm similar-artist edges + the ingest scan; OPS-004
  owns track enrichment + the queryable catalog + the external clients. To avoid duplication,
  KNOWLEDGE-008 OWNS the researched ARTIST/RELEASE editorial knowledge WITH dates, the dated
  relational store, the research jobs, and the grounding feed — and SEEDS from / EXTENDS
  ANALYSIS-006's edges + dimensions, REFERENCES the shared HTTP client (OPS-004 REQ-OA-011)
  and the ingest trigger (REQ-AP-007) by number rather than restating them (Sections 1.3, 2).
- **R-K-7 — Knowledge-coverage vs. library size (Low/Medium).** A large library means many
  artists to research; full coverage takes time. Mitigated by the bounded/throttled queue
  (REQ-KR-004), prioritizing newly-ingested + about-to-be-featured artists (REQ-KR-001), the
  seed graph giving immediate (if shallow) relations (REQ-KG-002), and the grounded-only feed
  (REQ-KI-001) so an unresearched artist simply yields genre/feel-level talk, never invented
  facts. Coverage is a throughput/tuning concern, not a correctness one.
- **R-K-8 — Apolitical cultural commentary (Low).** Music's cultural/societal significance is
  the editorial lens; an artist's facts could touch politically charged context. Mitigated by
  the inherited apolitical rail (OPS-004 REQ-OF-004): the host conveys factual significance,
  never partisan framing; a fact that cannot be presented apolitically is omitted.
- **R-K-9 — Consensus threshold tuning vs. coverage (Medium, relayed).** REQ-KS-006: requiring
  multi-source consensus before a fact airs as certain trades RICHNESS for RELIABILITY — too
  strict a threshold and many true facts about obscure artists (thin source coverage) are
  demoted to qualified/omitted; too loose and a wrong single-source fact slips through as
  certain. Mitigated by: the threshold + source weights being TUNABLE config (REQ-KS-006);
  authoritative structured sources (MusicBrainz, Wikidata) weighing more so a strong single
  authority can still earn a reasonable confidence while remaining qualified until corroborated;
  the QUALIFIED ("reportedly…") path preserving an editorially-useful fact without asserting it
  as certain (so coverage is not simply lost); and the per-fact confidence making the demotion
  visible/auditable. The consensus discipline mirrors ANALYSIS-006 REQ-AM-003 for editorial
  facts (distinct domain, no fork). Relayed during authoring; confirm with the user (the
  allowlist membership + the threshold). The reputable-music-press half of the allowlist is the
  fuzziest to define and is the part most likely to need tuning.
- **R-K-10 — Subjectivity/attribution drift on interpreted claims (Medium, v0.3.0).** The new
  per-track interpretation surface (REQ-KS-008) is where a "confidently wrong" failure could creep
  in: a lyrical reading is INTERPRETED, not FACTUAL, and the temptation is to state "this song is
  about X" as settled truth. Mitigated by: the `subjectivity_class` forcing every editorial claim to
  declare FACTUAL vs INTERPRETED vs EDITORIAL-OPINION; FACTUAL routing through the unchanged REQ-KS-006
  consensus engine; INTERPRETED/EDITORIAL-OPINION aired only as attributed speech with a grade and a
  preserved DISAGREEMENT record so a contested meaning is voiced AS contested (NFR-K-8); and the
  host-voice phrasing + bounded personal-musing aside owned by PROGRAMMING-007 (a host musing is a
  light curiosity question, never an authoritative verdict). The residual risk is the FACTUAL-vs-
  INTERPRETED classification heuristic itself mislabeling a claim — tunable, and a mislabel toward
  INTERPRETED is the SAFE direction (it gets attributed/hedged, never over-asserted).
- **R-K-11 — Scraper brittleness + AOTY bot-block (Medium, v0.3.0, build-time).** Many of the new
  REPUTABLE-PRESS / EDITORIAL-BLOG / deep sources (REQ-KR-009) have no API and are reached by scraping
  (trafilatura/newspaper4k); page-structure changes break extractors, and AOTY Cloudflare-blocks
  outright. Mitigated by: the bounded/throttled non-blocking research discipline (REQ-KR-004/005 — a
  failed scrape degrades richness, never continuity); per-source exception isolation (NFR-K-5); the
  Internet Archive / Wayback fallback for dead or moved pages (REQ-KR-009); AOTY recorded as
  skip-on-feasibility rather than retried into the ground; and the reliability-ranked weighting
  (REQ-KS-009) so a flaky low-tier source contributes little and its absence barely moves a fact's
  confidence. [PIVOT] No license/ToS concern is in scope — only reliability/availability.
- **R-K-12 — Discogs notes single-source + crowd-tier noise (Low/Medium, v0.3.0).** Discogs free-text
  NOTES are one contributor's words and Discogs credits/styles are crowd-curated (sometimes wrong).
  Mitigated by: Discogs being CROWD-tier (~0.25 weight, REQ-KS-009/KR-008) so it corroborates weakly
  and never alone makes a fact airable-as-certain; its STRUCTURED fields contributing to consensus
  only alongside higher-tier sources; its free-text NOTES permanently single-source and ALWAYS hedged
  ("according to Discogs"); and the per-release-credit cross-check against the MusicBrainz mirror
  deferred to MBMIRROR-017 for the heavier reconciliation. Residual: an isolated wrong Discogs credit
  with no corroboration stays hedged, never asserted.

---

## 15. Out-of-Scope / Future SPEC Roadmap

- **Semantic / embedding search over bios** — a vector index (e.g. a SQLite vector extension)
  over artist bios + anecdotes for "find me an artist whose story is like…" queries; a future
  enhancement that would layer onto the same store without changing these requirements.
- **Targeted similar-artist ACQUISITION wishlist** — driving the acquisition queue from the
  graph's similar/network edges; a CORE-001/OPS-004 curation/acquisition concern (the graph
  surfaces candidates here, the wishlist + acquisition is theirs).
- **A richer cultural-context knowledge dimension** — deeper scene/movement/era essays beyond
  per-artist facts, feeding the OPS-004 playbook's music-history dimension (REQ-OD-005); the
  per-artist facts here are the substrate a future dimension would build on.
- **Knowledge-coverage sensor in the world model** — surfacing "how much of the library is
  researched / how fresh" to ORCH-005's world model as a sensor to prioritize research;
  ORCH-005 owns the sensor, KNOWLEDGE-008 owns the underlying store state.

---

## 16. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md;
detailed Given-When-Then scenarios for the load-bearing requirements are in acceptance.md
Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-KS-001 | Knowledge Store & Schema | High | Ubiquitous | AC-KS-001 |
| REQ-KS-002 | Knowledge Store & Schema | High | Ubiquitous | AC-KS-002 |
| REQ-KS-003 | Knowledge Store & Schema | High | Ubiquitous | AC-KS-003 |
| REQ-KS-004 | Knowledge Store & Schema | High | Ubiquitous | AC-KS-004 |
| REQ-KS-005 | Knowledge Store & Schema | High | Ubiquitous | AC-KS-005 |
| REQ-KS-006 | Knowledge Store & Schema | High | Ubiquitous | AC-KS-006 |
| REQ-KS-007 | Knowledge Store & Schema | High | Ubiquitous | AC-KS-007 |
| REQ-KS-008 | Knowledge Store & Schema | High | Ubiquitous | AC-KS-008 |
| REQ-KS-009 | Knowledge Store & Schema | High | Ubiquitous | AC-KS-009 |
| REQ-KF-001 | Freshness & Currency | High | Ubiquitous | AC-KF-001 |
| REQ-KF-002 | Freshness & Currency | High | Ubiquitous | AC-KF-002 |
| REQ-KF-003 | Freshness & Currency | High | Unwanted | AC-KF-003 |
| REQ-KF-004 | Freshness & Currency | High | State | AC-KF-004 |
| REQ-KF-005 | Freshness & Currency | High | Ubiquitous | AC-KF-005 |
| REQ-KR-001 | Continuous Research Jobs | High | Event | AC-KR-001 |
| REQ-KR-002 | Continuous Research Jobs | High | Event | AC-KR-002 |
| REQ-KR-003 | Continuous Research Jobs | High | Ubiquitous | AC-KR-003 |
| REQ-KR-004 | Continuous Research Jobs | High | State | AC-KR-004 |
| REQ-KR-005 | Continuous Research Jobs | High | Unwanted | AC-KR-005 |
| REQ-KR-006 | Continuous Research Jobs | High | Event | AC-KR-006 |
| REQ-KR-007 | Continuous Research Jobs | High | Event | AC-KR-007 |
| REQ-KR-008 | Continuous Research Jobs | High | Event | AC-KR-008 |
| REQ-KR-009 | Continuous Research Jobs | High | Event | AC-KR-009 |
| REQ-KG-001 | Relational Graph | High | Ubiquitous | AC-KG-001 |
| REQ-KG-002 | Relational Graph | High | Event | AC-KG-002 |
| REQ-KG-003 | Relational Graph | High | Event | AC-KG-003 |
| REQ-KG-004 | Relational Graph | High | Event | AC-KG-004 |
| REQ-KG-005 | Relational Graph | Medium | Event | AC-KG-005 |
| REQ-KG-006 | Relational Graph | High | Ubiquitous | AC-KG-006 |
| REQ-KI-001 | Grounding Feed & Integration | High | Ubiquitous | AC-KI-001 |
| REQ-KI-002 | Grounding Feed & Integration | High | Event | AC-KI-002 |
| REQ-KI-003 | Grounding Feed & Integration | Medium | Event | AC-KI-003 |
| REQ-KI-004 | Grounding Feed & Integration | High | Event | AC-KI-004 |
| REQ-KI-005 | Grounding Feed & Integration | Medium | Ubiquitous | AC-KI-005 |
| REQ-KI-006 | Grounding Feed & Integration | High | Event | AC-KI-006 |
| NFR-K-1 | Non-Functional | High | Ubiquitous | AC-NFR-K-1 |
| NFR-K-2 | Non-Functional | High | Ubiquitous | AC-NFR-K-2 |
| NFR-K-3 | Non-Functional | High | Ubiquitous | AC-NFR-K-3 |
| NFR-K-4 | Non-Functional | High | Ubiquitous | AC-NFR-K-4 |
| NFR-K-5 | Non-Functional | High | Ubiquitous | AC-NFR-K-5 |
| NFR-K-6 | Non-Functional | High | Ubiquitous | AC-NFR-K-6 |
| NFR-K-7 | Non-Functional | Medium | Ubiquitous | AC-NFR-K-7 |
| NFR-K-8 | Non-Functional | High | Ubiquitous | AC-NFR-K-8 |

Parity: 35 REQ + 8 NFR = 43 specified items; 43 acceptance entries (35 AC + 8 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: KS (Knowledge Store & Schema) = 9, KF (Freshness & Currency) = 5, KR
(Continuous Research Jobs) = 9, KG (Relational Graph) = 6, KI (Grounding Feed & Integration) = 6 →
9+5+9+6+6 = 35 REQ across 5 groups. NFR-K-1…8 = 8 NFR. Total = 35 + 8 = 43 specified items, 43 acceptance
entries, 1:1 REQ↔AC.
