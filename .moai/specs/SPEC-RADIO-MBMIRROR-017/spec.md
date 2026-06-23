---
id: SPEC-RADIO-MBMIRROR-017
version: 0.2.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: High
issue_number: null
---

# SPEC-RADIO-MBMIRROR-017 — MusicBrainz Metadata Access (Public API + Persistent Local Cache; Self-Hosted Mirror as Optional Future Upgrade) + Discogs/Last.fm Cross-Check

## HISTORY

- 2026-06-23 (v0.2.0): **Inverted the implementation default (user-approved).** The
  RECOMMENDED / DEFAULT path is now the **public MusicBrainz web-service API (1 req/sec, no
  token) backed by a PERSISTENT LOCAL RESULT CACHE in the brain's DB** (new Group MC). The
  self-hosted Hetzner mirror (full `musicbrainz-docker`) is DEMOTED to an OPTIONAL,
  "promote-when-needed" FUTURE variant — the mirror provisioning/replication requirements
  (Group MM) and the volume/sizing requirements (Group MV) are rephrased as EARS **Optional**
  ("Where the self-hosted mirror is enabled, the system shall …") rather than ubiquitous
  mandates, and the replication-token requirement is now conditional on that optional variant.
  **Rationale (grounded numbers):** at ~500 tracks growing at Soulseek download speed, with
  CACHE-ONCE / reuse-forever, MusicBrainz call volume is ~500–1000 calls ONE-TIME for the
  backfill (~10–20 min at 1/sec) plus a trickle for new downloads — well under the 86,400
  calls/day that the 1/sec limit allows (we use <1% of it). The 1/sec public limit is
  massively over-provisioned for our scale; a self-hosted mirror is justified ONLY by
  (a) independence from MusicBrainz uptime, (b) huge relationship queries at scale, or
  (c) repeated bulk re-processing — none of which apply today. The user's live-feed
  replication token therefore stays UNUSED until/unless the mirror variant is adopted. The
  brain-client repoint (Group MB) is reframed so the DEFAULT endpoint is the public API, with
  the optional mirror reachable behind the same `musicbrainzngs` client + the same cache via a
  config flag. Discogs/Last.fm cross-check (Group MX) and the never-block / resilience NFRs are
  unchanged in intent. Group MC added (6 REQ); the old REQ-MB-007 (cache-with-track-record) is
  SUPERSEDED by and absorbed into Group MC; NFR-M-5 (throughput) reframed around cache-makes-
  1req/s-sufficient; NFR-M-9 (cache durability/persistence) added. New total: 27 REQ + 9 NFR
  = 36, 1:1 REQ↔AC.
- 2026-06-23 (v0.1.0): Initial draft (the v0.2.0 amendment above inverts the default; this
  paragraph is retained for history). The metadata-INFRASTRUCTURE SPEC of the
  golden-shower-radio autonomous AI radio station: it stands up a SELF-HOSTED MusicBrainz
  mirror on the user's **Hetzner Cloud instance** (NOT local WSL disk — the cross-cutting
  infra decision locked 2026-06-23 in `.moai/planning/feature-backlog-2026-06-23.md`,
  which removes the earlier ~39 GB local-disk constraint), keeps it synced via the
  MetaBrainz live-feed REPLICATION TOKEN (a gitignored secret), and repoints the brain's
  EXISTING `musicbrainzngs` access at the remote endpoint (a config-gated host) with the
  public MusicBrainz API as automatic fallback. It is the throughput substrate that lets
  ENRICH-012 (the id3-sanitization / canonical-recording engine — `brain/enrich.py`)
  identify and correct tags AT VOLUME without the public API's 1 req/s ceiling, and lets
  SPEC-RADIO-HOSTCTX-016 pull RICH host facts (release date, album, producer, credited
  personnel, record labels, release-group relationships) the public-API politeness budget
  would otherwise starve. It adds Discogs + Last.fm cross-check ONLY for the coverage
  MusicBrainz lacks (producer/engineer credits, pressing/label detail, crowd corroboration)
  — rate-limited, with PER-FIELD provenance — and it inherits the project's CONSENSUS
  discipline (multi-source corroboration before a fact is stated as certain). The defining
  rail is **the brain NEVER blocks on the mirror**: a mirror that is down, lagging, mid-sync,
  or unreachable degrades to the public API or to graceful no-enrichment, never to a stall or
  to dead air. RADIO SPEC-IDs are GLOBAL-INCREMENTING (CORE-001, VOICE-002, CALLIN-003
  reserved, OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009,
  IMAGING-010, REQUEST-011, and the ENRICH-012…WEBUI-018 planning batch) — so MBMIRROR is
  017, the planned ID from the backlog, NOT a re-numbered 001. DISTINCT REQ namespaces — MM
  (mirror provisioning + sync), MB (brain client repoint + fallback), MX (cross-check:
  Discogs/Last.fm + provenance), MV (volume/sizing + ops), MN (NFRs). Built on the
  BRAIN-ONLY seam: it changes config + a thin client-host setter in `brain/metadata.py` /
  `brain/enrich.py`; it adds NO schema coupling (the recommended variant is the FULL
  musicbrainz-docker web service, so the brain calls the SAME `musicbrainzngs` HTTP API it
  calls today — it just talks to a different hostname via the documented
  `musicbrainzngs.set_hostname(host, use_https)`). (Note: v0.2.0 above inverts the default to
public-API-plus-cache; the mirror is the optional upgrade.) Total: 27 REQ + 9 NFR = 36, 1:1 REQ↔AC.

---

## 1. Overview & Background

### 1.1 Why this SPEC — "we need accurate MusicBrainz metadata, cached so 1 req/s is plenty"

The brain already talks to MusicBrainz. `brain/metadata.py` has a `_provider_musicbrainz`
that lazy-imports `musicbrainzngs`, sets a User-Agent, and self-throttles to <= 1 request
per second (the published public-API policy). `brain/enrich.py` (ENRICH-012, in progress)
uses the same access for AcoustID-then-MusicBrainz canonical-recording identification to
correct garbled id3 tags. Two new demands need a richer, more reliable MusicBrainz path:

1. **ENRICH-012 across the library.** Sanitizing the id3 tags of the WHOLE existing library
   plus every new download means a MusicBrainz lookup per recording. We have ~500 tracks
   today, growing at Soulseek download speed.
2. **HOSTCTX-016 rich facts.** The host wants to say the year, the album, who PRODUCED it,
   who is CREDITED, and which LABEL released it — release-relationship data that lives in
   MusicBrainz's relationship (`l_*`) tables and needs `includes=` expansions (artist-rels,
   release-rels, labels, recording-rels). Those are multi-include calls.

The earlier framing assumed those demands "break the 1 req/s ceiling" and therefore required a
self-hosted mirror at volume. **The user-approved v0.2.0 decision inverts that conclusion**, on
grounded numbers: with a CACHE-ONCE / reuse-forever local result cache, the backfill is a ONE-
TIME ~500–1000 calls (~10–20 min at 1/sec); thereafter only NEW downloads trickle in. That is
well under the 86,400 calls/day the 1/sec limit allows — we use **<1%** of it. The 1/sec public
limit is massively over-provisioned for our scale. So the DEFAULT path is the public
`musicbrainz.org` web-service API (1 req/sec, NO token) backed by a PERSISTENT local result cache
in the brain's DB (Group MC). A self-hosted mirror buys nothing for our scale today; it is kept
as an OPTIONAL future upgrade (Groups MM / MV), justified only when one of these becomes true:
(a) independence from MusicBrainz uptime is required, (b) huge relationship queries at scale, or
(c) repeated bulk re-processing. The user's MetaBrainz live-feed replication token stays UNUSED
until/unless that upgrade is adopted. This SPEC owns the default API+cache path, the brain-side
client (default = public API; config-gated to point at the optional mirror; both go through the
same `musicbrainzngs` client + the same cache), the OPTIONAL mirror provisioning/sizing, and the
Discogs/Last.fm cross-check for credits MusicBrainz alone does not cover.

### 1.2 The default path (recommended), and the optional mirror upgrade (the "how much" answer)

**DEFAULT (recommended, build FIRST): public API + persistent local result cache.** The brain
queries `musicbrainz.org` through the existing 1 req/sec self-throttle and writes every enriched
result into a durable cache in its own DB. A cached track is never re-fetched (REQ-MC-003); the
cache serves ENRICH-012 id3 sanitization, HOSTCTX-016 host facts, and DEDUP-014's MBID lookup
from one store (REQ-MC-005). At ~500 tracks the whole backfill is a ~10–20 minute one-time crawl;
steady state is a trickle. NO token, NO extra infra, NO Hetzner cost. This is Group MC.

**OPTIONAL FUTURE UPGRADE (deferred): self-hosted MusicBrainz mirror on Hetzner.** The backlog
posed the mirror sizing question; the answer is kept here so the upgrade is ready when/if one of
the (a)/(b)/(c) triggers above fires, but it is NOT built by default. The sizing table below is
the FUTURE provisioning reference, not a current requirement:

| Variant (FUTURE, optional) | What runs | Approx. Hetzner volume | Brain change | Trade-off |
|---------|-----------|------------------------|--------------|-----------|
| **A — Full `musicbrainz-docker`** (the upgrade we'd pick) | Postgres + Solr search + the MB **web service** (mbslave/replication included) | ~100–150 GB (provision **~150 GB** for headroom + replication growth) | DROP-IN: repoint the hostname only (`musicbrainzngs.set_hostname`) — same HTTP API + same cache, no schema coupling | Largest disk; standard, well-trodden, easiest to keep in sync; matches the public API surface 1:1 |
| B — Postgres-only (no Solr, no web service) | Postgres + replication; brain queries by SQL joins / MBID | ~50–80 GB | INVASIVE: brain must learn the MB schema + write SQL; loses `search_recordings` text-match unless we add Solr or a text index | Smaller disk; couples the brain to the MB schema (a maintenance burden we explicitly avoid) |
| C — Selective import (subset of tables) | Postgres with only artist, recording, release, release_group, label, artist_credit, medium, track, and the `l_*` relationship tables | ~15–25 GB | MOST invasive: brain writes SQL against a partial schema; replication of a subset is fragile | Smallest disk; brittle sync; partial schema means missing-data surprises |

[HARD] The default path (Group MC) is what we build. **The mirror is DEFERRED.** If/when it IS
adopted, Variant A is the recommended upgrade because the brain change is the SMALLEST possible —
repoint a hostname and the existing `musicbrainzngs` calls work UNCHANGED against the local web
service, and the SAME local cache sits in front of it. Variants B and C trade disk for schema
coupling and replication fragility, which is exactly the maintenance cost this SPEC avoids. The
brain-facing contract (the `musicbrainzngs` HTTP API + the local cache + the public-API path) is
IDENTICAL whether the brain points at the public API or at any mirror variant, so the whole
mirror question is a reversible OPS decision behind a stable client seam.

### 1.3 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] MBMIRROR-017 owns the DEFAULT METADATA ACCESS PATH (public API + persistent local
cache), the BRAIN CLIENT (default = public API; config-gated optional mirror), the OPTIONAL
FUTURE mirror infrastructure, and the cross-check clients. It MUST NOT re-own, restate, or fork
the id3-sanitization logic, the host-talk logic, the consensus algorithm, or the artist-fact
knowledge store.

OWNS:
- The DEFAULT path: querying the public MusicBrainz API through the existing 1 req/sec throttle
  + a PERSISTENT local result cache (cache-once, reuse-forever) in the brain's DB that serves
  ENRICH-012, HOSTCTX-016, and DEDUP-014 from one store (Group MC). **This is what we build first.**
- The brain-side client: default endpoint = the public API; a config-gated host that, when set,
  repoints the SAME `musicbrainzngs` client at the optional mirror via `set_hostname`; both paths
  go through the same cache (Group MB).
- The Discogs + Last.fm cross-check CLIENTS for credits/label/corroboration coverage that
  MusicBrainz alone lacks, rate-limited, with per-field provenance (Group MX).
- The OPTIONAL FUTURE self-hosted mirror on Hetzner — its variant choice + sizing + replication-
  token sync + operational posture — rephrased as Optional ("where the mirror is enabled")
  requirements that are NOT built by default (Group MM / MV).

REFERENCES (consumes / feeds; does not restate):
- **ENRICH-012** (`brain/enrich.py`, config `enrich_*`) — the canonical-recording
  identification + id3 write-back ENGINE. It is the PRIMARY CONSUMER: MBMIRROR-017 gives it
  a cached MusicBrainz endpoint (default = public API + cache; optionally the mirror) so it can
  sanitize the whole library with a one-time cached backfill. The identification /
  correction / write-back logic, the confidence threshold, and the write-back-to-file
  decision stay in ENRICH-012; MBMIRROR-017 only changes WHERE the MusicBrainz bytes come
  from (and caches them) and adds cross-check coverage. ENRICH-012 is the metadata SPINE; this
  SPEC is its cached-access + coverage substrate.
- **SPEC-RADIO-HOSTCTX-016** (richer host talk: year/album/curiosa) — the OTHER primary
  consumer. It asks the mirror for producer/credits/labels/release relationships and turns
  them into grounded host talk. The talk generation, persona style, and grounding gate stay
  in HOSTCTX-016 / PROGRAMMING-007 PG; MBMIRROR-017 only SUPPLIES the rich facts.
- **SPEC-RADIO-ANALYSIS-006 REQ-AM-003** (multi-source CONSENSUS for audio/genre/feature
  claims) + `brain/metadata.py`'s `consensus()` — MBMIRROR-017 ADDS Discogs as a new
  allowlisted source and feeds its fields into the SAME consensus discipline; it does NOT
  fork or restate the consensus algorithm. ANALYSIS-006 owns audio/genre/feature consensus.
- **SPEC-RADIO-KNOWLEDGE-008** (dated, sourced ARTIST FACTS + their provenance/consensus) —
  where the cross-check surfaces ARTIST-level facts (label history, scene, lineage), those
  are KNOWLEDGE-008's domain. MBMIRROR-017 supplies RELEASE/RECORDING-level credits
  (producer, engineer, personnel, label-on-this-release) and references KNOWLEDGE-008 for
  artist-fact ownership; neither re-owns the other.
- **OPS-004 REQ-OA-011** (the external-metadata source list + the enrichment obligation) —
  MusicBrainz/TheAudioDB/Last.fm/Discogs are NAMED there; MBMIRROR-017 is the SPEC that makes
  the MusicBrainz source self-hosted-and-fast and adds the Discogs client OA-011 anticipated.
- **OPS-004 REQ-OH-006** (acquisition accounting + bounded queue) — the cross-check + backfill
  enrichment throttle ties to it (enrichment is downstream of acquisition); referenced.
- **CORE-001 continuous operation / never-dead-air** — the never-block rail (Group MB)
  inherits it: a mirror problem must never reach the playout path.
- **`brain/metadata.py` / `brain/config.py`** — the existing MusicBrainz client seam
  (`_mb_set_useragent`, `_mb_throttle`, `_provider_musicbrainz`, the `musicbrainz_user_agent`
  / `enrichment_*` config) is EXTENDED in place (a host setting + a host setter), not forked.

### 1.4 Fixed engineering/safety rails (the only hard constraints)

- **The brain NEVER blocks on metadata access.** Every external metadata interaction (public
  API or the optional mirror) is bounded by a timeout and degrades gracefully (cache →
  public API → graceful no-enrichment) on any failure. A slow/down public API, or — when the
  optional mirror is enabled — a down/lagging/mid-sync/unreachable mirror, is an expected
  operating state, never a defect and never dead air.
- **Cache-once, reuse-forever.** A successfully enriched track is written to the persistent
  local cache and never re-fetched; the cache is the default-path substrate that makes the
  1 req/sec public limit more than sufficient at our scale.
- **Secrets stay gitignored + orchestrator-perm-denied.** Any Discogs/Last.fm key — and the
  MetaBrainz replication token IF the optional mirror is ever enabled — live in the gitignored
  `secrets/` tree (or env), never in the repo, never in a SPEC, never logged. (The orchestrator
  is permission-denied in `secrets/`.) The default path needs NO token.
- **Drop-in client, no schema coupling.** The brain talks the same `musicbrainzngs` HTTP API
  to the public API by default; the ONLY change to reach the optional mirror is the host it
  points at — no schema coupling either way.
- **Per-field provenance + consensus before certainty.** A cross-checked field records WHICH
  source supplied it; a fact is stated as certain only under the inherited consensus discipline
  (REQ-AM-003), single-source values are flagged, never asserted as confirmed.
- **Rate-limit every external source.** MusicBrainz public-API fallback keeps the 1 req/s
  self-throttle; Discogs + Last.fm keep their own published rate limits. The local mirror is
  the ONLY high-throughput path.
- **Mirror is additive infra, not a brain-internal service.** The mirror is a separate
  deployment on Hetzner; the brain is a CLIENT. MBMIRROR-017 adds no new service to the brain
  container.

### 1.5 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 / OPS-004 Section 1.3 in intent. It is an ENGINEERING substrate:
it grants the AI ACCURATE, FAST, RICH metadata + safety rails, and MUST NOT prescribe what the
host says, which facts are interesting, or how curation uses the data. The facts are evidence;
their editorial use lives in HOSTCTX-016 / PROGRAMMING-007. The human stays out of the run loop.

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001, SPEC-RADIO-OPS-004, SPEC-RADIO-ANALYSIS-006, and
the in-progress ENRICH-012; it is CONSUMED BY ENRICH-012 (cached access), SPEC-RADIO-HOSTCTX-016
(cached rich facts), and SPEC-RADIO-DEDUP-014 (cached canonical MBID). It references their subsystems by CONCEPT and, where a cited requirement is a
deliberately stable invariant, by number.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any CORE-001, OPS-004, ANALYSIS-006,
ENRICH-012, HOSTCTX-016, or KNOWLEDGE-008 requirement. Where it needs a predecessor behavior it
consumes it. Where a mirror decision could conflict with continuous operation, the inherited
continuous-operation behavior WINS.

Consumed concepts:
- **`brain/metadata.py` MusicBrainz client** — `_provider_musicbrainz`, `_mb_set_useragent`
  (calls `musicbrainzngs.set_useragent`), the process-wide `_mb_throttle` (1 req/s), and the
  `consensus()` reconciliation. MBMIRROR-017 adds a host setter + a Discogs provider here.
- **`brain/enrich.py` (ENRICH-012)** — AcoustID + MusicBrainz text-match canonical-recording
  identification + id3 write-back. The PRIMARY consumer; MBMIRROR-017 changes its MB endpoint.
- **`brain/config.py`** — the `musicbrainz_user_agent`, `enrichment_*`, `enrich_*`,
  `lastfm_api_key`, `acoustid_*` config. MBMIRROR-017 adds mirror-host + Discogs config here.
- **ANALYSIS-006 REQ-AM-003 + REQ-AD-001** — the consensus discipline + the `Track` provenance
  fields the cross-checked values are recorded against (no fork).
- **OPS-004 REQ-OA-011 / REQ-OH-006** — the source list + the acquisition-accounting throttle.
- **CORE-001 Group C** — continuous operation / never-dead-air, which the never-block rail
  inherits.

### Downstream SPECs that depend on MBMIRROR-017 (forward reference)

- **ENRICH-012** consumes the cached MusicBrainz endpoint (default = public API + cache; optional
  mirror) to sanitize id3 across the library with a one-time cached backfill.
- **SPEC-RADIO-HOSTCTX-016** consumes the cached rich release/recording relationships (producer,
  credits, labels) for grounded host talk.
- **SPEC-RADIO-DEDUP-014** consumes the canonical MusicBrainz **recording MBID** (surfaced via the
  cached endpoint through ENRICH-012, REQ-MC-005) as its dedup key; referenced, not owned here.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **MusicBrainz mirror** | A self-hosted copy of the MusicBrainz database + (Variant A) the MB web service, running on the user's Hetzner Cloud instance, kept current via replication. |
| **`musicbrainz-docker`** | The official MetaBrainz Docker Compose stack (Postgres + Solr search + MB web service + replication/mbslave). The RECOMMENDED Variant A deployment. |
| **Replication token** | The MetaBrainz live-data-feed token that authorizes downloading the hourly/periodic replication packets that keep the mirror in sync. A gitignored SECRET. Value lives only in `secrets/`. |
| **Mirror host** | The config-gated hostname[:port] the brain points `musicbrainzngs` at (e.g. the Hetzner instance's address). Empty → use the public MusicBrainz API. |
| **Public-API fallback** | The brain's automatic fall-back to `musicbrainz.org` (at the 1 req/s self-throttle) when the mirror is unset, down, slow, or errored — so enrichment degrades, never blocks. |
| **`set_hostname`** | The documented `musicbrainzngs.set_hostname(new_hostname, use_https=False)` call (accepts `host:port`) that repoints the EXISTING client at the mirror — the drop-in seam for Variant A. |
| **Rich facts** | Release/recording-relationship data: first-release year, album/release, producer, engineer + credited personnel, record label(s), release-group relationships — fetched via `includes=` expansions. Consumed by HOSTCTX-016. |
| **Cross-check** | Querying Discogs and/or Last.fm for fields MusicBrainz lacks or to corroborate a MusicBrainz value, rate-limited, with per-field provenance, folded into the inherited consensus. |
| **Per-field provenance** | A record, per supplied field, of WHICH source (mirror MusicBrainz / public MusicBrainz / Discogs / Last.fm / embedded) supplied it + the consensus level, so the catalog has auditable origins. |
| **Consensus discipline** | ANALYSIS-006 REQ-AM-003's rule: a value is "confirmed" only when corroborated by >= N allowlisted sources (or one authoritative source); single-source values are "candidate", flagged, never stated as certain. MBMIRROR-017 feeds new sources INTO it, does not restate it. |
| **Never-block rail** | The HARD invariant that no mirror interaction (or any external metadata call) is ever on the sub-1s `/api/next` pull path or able to stall the director/daemon/stream. |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group MC — Default Path: Public API + Persistent Result Cache (HIGH, build FIRST).** The
  default metadata access path: query the public MusicBrainz API through the existing 1 req/sec
  throttle, write every enriched result into a PERSISTENT local cache in the brain's DB
  (cache-once, reuse-forever), never re-fetch a cached track, refresh/invalidate on schema or
  file change, serve ENRICH-012 + HOSTCTX-016 + DEDUP-014 from the one cache, with per-field
  cache provenance. This group needs NO token and NO extra infra.
- **Group MB — Brain Client (default public API; optional mirror) & Graceful Degradation.** The
  brain's `musicbrainzngs` client defaults to the public API; a config-gated mirror host that,
  WHEN SET, repoints the SAME client via `musicbrainzngs.set_hostname`; graceful degradation
  (cache → public API → no-enrichment); the never-block rail; the 1 req/s throttle on the
  public-API path (the optional mirror is unthrottled-but-bounded); ENRICH-012 + HOSTCTX-016
  query routing through this seam (and the cache).
- **Group MX — Discogs / Last.fm Cross-Check & Provenance.** A Discogs client (new) +
  reuse of the existing Last.fm provider for the credits/label/corroboration coverage
  MusicBrainz lacks; rate-limited; per-field provenance; folded into the inherited
  ANALYSIS-006 consensus; the artist-fact boundary to KNOWLEDGE-008.
- **Group MM — OPTIONAL FUTURE Mirror Provisioning & Replication Sync (deferred).** Phrased as
  EARS Optional ("where the self-hosted mirror is enabled, …"): standing up the mirror on
  Hetzner (Variant A `musicbrainz-docker`); the replication-token-driven keep-in-sync; the
  documented slimmer Variants B/C; the secret-handling discipline for the token; the mirror's
  own health/observability surface. NOT built by default.
- **Group MV — OPTIONAL FUTURE Volume, Sizing & Operations (deferred).** Phrased as EARS
  Optional: the ~150 GB Hetzner volume provision for Variant A (with B/C documented);
  replication lag monitoring; the resync/rebuild posture; cost/disk headroom. Applies only when
  the mirror upgrade is adopted.
- Plus **NFRs** (Section 11) and **Risks** (Section 12).

### 4.2 Out of scope (explicitly deferred)

- **The id3-sanitization / canonical-recording identification + write-back LOGIC** — owned by
  ENRICH-012; MBMIRROR-017 only supplies the fast endpoint + cross-check coverage.
- **The host-talk generation, persona style, and grounding gate** — owned by HOSTCTX-016 /
  PROGRAMMING-007 PG; MBMIRROR-017 only supplies the rich facts.
- **The consensus ALGORITHM** — owned by ANALYSIS-006 REQ-AM-003 (`brain/metadata.py`
  `consensus()`); MBMIRROR-017 only ADDS sources into it.
- **Artist-FACT research + the dated/sourced fact store** — owned by KNOWLEDGE-008;
  MBMIRROR-017 supplies release/recording credits, not the artist-fact store.
- **The download-duplication-control dedup POLICY** — owned by SPEC-RADIO-DEDUP-014; MBMIRROR
  only makes the canonical recording MBID available (via ENRICH-012).
- **AcoustID fingerprinting** — owned by ENRICH-012 (`identify_acoustid`); the AcoustID API
  is a separate hosted service, NOT mirrored here (only the MusicBrainz database is mirrored).
- **A general-purpose MusicBrainz schema ORM / SQL layer in the brain** — explicitly avoided
  by recommending Variant A (HTTP web service, no schema coupling). If Variant B/C is chosen,
  the SQL layer is an OPS implementation detail behind the same client contract, still not a
  brain-owned schema product.
- **Hosting AcoustID, Wikidata, Discogs, or Last.fm mirrors** — only MusicBrainz is mirrored;
  Discogs/Last.fm are queried via their public rate-limited APIs.
- **Provisioning automation / IaC for the Hetzner box** — the mirror deployment is operated by
  the user/operator following the documented runbook; MBMIRROR-017 specifies the REQUIREMENTS
  and posture, not a Terraform/Ansible product.
- **A new datastore in the brain** — cross-check provenance is recorded on the EXISTING
  `Track` record (ANALYSIS-006 REQ-AD-001), no fork.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Default path = public API + persistent cache; mirror is the OPTIONAL future upgrade.**
  User-approved v0.2.0 inversion: build Group MC first; the mirror (Hetzner) is deferred.
- [HARD] **If/when the optional mirror is adopted, it lives on Hetzner Cloud, not local WSL disk.**
  Locked 2026-06-23 (`feature-backlog-2026-06-23.md`). The brain (local WSL2/Docker) is a remote
  CLIENT; the default path needs no such deployment.
- [HARD] **Brain = the existing Python `brain/` package.** MBMIRROR-017 extends
  `config.py`, `metadata.py`, `enrich.py`; it adds a persistent result cache + a Discogs provider
  (+ an optional host setter for the mirror), not a new service.
- [HARD] **Never block on metadata access.** Every external call (public API, the optional mirror,
  or a cross-check) is timeout-bounded and degrades gracefully; never on the sub-1s `/api/next`
  pull; never stalls the director/daemon/stream.
- [HARD] **Cache-once, reuse-forever.** A successfully enriched track is persisted and never
  re-fetched; this is what makes the 1 req/sec default sufficient at our scale.
- [HARD] **Drop-in client.** The default endpoint is the public API; adopting the optional mirror
  repoints the hostname via `musicbrainzngs.set_hostname(host, use_https)`, and the existing
  `search_recordings` / `get_recording_by_id(includes=...)` calls work unchanged. No schema
  coupling either way.
- [HARD] **Secrets gitignored + never logged.** Any API keys — and the replication token IF the
  optional mirror is enabled — live in `secrets/` / env, never the repo, never a SPEC, never a log
  line. The default path needs no token.
- [HARD] **Public-API politeness on the default path.** The 1 req/s MusicBrainz self-throttle
  (`_mb_throttle`) applies whenever the brain talks to `musicbrainz.org` (the default); the
  optional mirror path is exempt from the 1 req/s limit but still bounded by timeout + a local cap.
- [HARD] **Per-field provenance + consensus.** Cross-checked values record their source and
  are folded into the inherited ANALYSIS-006 consensus; single-source values are flagged, not
  asserted as certain.
- [HARD] **No fork of the library store or the consensus algorithm.** Extend in place.
- **License/ToS awareness.** MusicBrainz data is CC0 (core) / CC-BY-NC-SA (some supplementary
  tables); self-hosting + replication is explicitly supported by MetaBrainz under the token.
  Discogs + Last.fm API use is bound by their ToS + rate limits (R-M-7). Flagged, not blocking.

---

## 6. Requirement Group MC — Default Path: Public API + Persistent Result Cache

Priority: High. **This is the DEFAULT, recommended path and what we build FIRST.**

### REQ-MC-001 — Default metadata access is the public MusicBrainz API at 1 req/s, no token (Ubiquitous) [HARD]

The system shall, by default, access MusicBrainz via the PUBLIC `musicbrainz.org` web-service
API through the existing `_provider_musicbrainz` client at the existing <= 1 req/sec self-throttle
(`_mb_throttle`), requiring NO replication token and NO self-hosted infrastructure. [HARD] At the
station's scale (~500 tracks growing at download speed) this is sufficient: backed by the
persistent cache (REQ-MC-002), MusicBrainz call volume is a ONE-TIME ~500–1000-call backfill plus
a trickle for new downloads — well under the 86,400 calls/day the 1/sec limit allows. The
self-hosted mirror (Group MM) is an OPTIONAL future upgrade, not a prerequisite for this path.

**Acceptance criteria:** see acceptance.md AC-MC-001.

### REQ-MC-002 — Persistent local result cache, cache-once / reuse-forever (Ubiquitous) [HARD]

The system shall persist every successful MusicBrainz (and cross-check) enrichment result in a
DURABLE local cache in the brain's existing DB (on the `Track` record / its idempotent-cache
pattern, ANALYSIS-006 REQ-AD-001 / REQ-AE-002), so a result fetched once is reused forever across
re-scans, restarts, and retries without a fresh network call. [HARD] The cache is the substrate
that makes the 1 req/sec default path viable at volume; it survives brain and Icecast restarts.

**Acceptance criteria:** see acceptance.md AC-MC-002.

### REQ-MC-003 — Never re-fetch a cached track (Unwanted) [HARD]

If a track's MusicBrainz result is already in the persistent cache and is still valid (not
invalidated per REQ-MC-004), then the system shall NOT issue a new MusicBrainz network call for
it; it shall serve the cached result. Re-querying an unchanged, already-cached track is the waste
this requirement prevents — it is also what keeps the 1 req/sec default well within budget.

**Acceptance criteria:** see acceptance.md AC-MC-003.

### REQ-MC-004 — Cache refresh / invalidation policy (State-driven)

While the cache holds a result, the system shall invalidate (and allow re-fetch of) that entry
only on a well-defined trigger: an enrichment schema/version bump, a changed underlying file, or
an explicit operator-requested refresh — mirroring ANALYSIS-006's cache-invalidation discipline.
Absent such a trigger the entry is treated as durably valid (cache-once, reuse-forever); the
policy SHALL NOT silently expire entries on a timer at our scale (which would re-introduce
needless call volume).

**Acceptance criteria:** see acceptance.md AC-MC-004.

### REQ-MC-005 — One cache serves ENRICH-012, HOSTCTX-016, and DEDUP-014 (Event-driven) [HARD wiring]

When ENRICH-012 needs canonical-recording data, HOSTCTX-016 needs rich facts, or DEDUP-014 needs
the canonical recording MBID, the system shall serve them from the ONE persistent cache (filling
it from the public API or the optional mirror on a miss) — so the metadata is fetched once and
reused by all consumers, never re-fetched per consumer. [HARD] MBMIRROR-017 supplies the cached
access; the consumers' own logic (ENRICH-012 identification/write-back, HOSTCTX-016 talk, DEDUP-014
policy) stays in those SPECs (referenced, not re-owned).

**Acceptance criteria:** see acceptance.md AC-MC-005.

### REQ-MC-006 — Per-field cache provenance + fetched-at (Ubiquitous) [HARD]

The system shall record, with each cached value, WHICH source supplied it (public-MusicBrainz /
mirror-MusicBrainz / Discogs / Last.fm / TheAudioDB / embedded / audio-hint) and WHEN it was
fetched, alongside the consensus level (Group MX), so every cached value has an auditable origin
and the cache is diagnosable. A cached value with no recorded source/fetched-at is the defect this
requirement prevents. (This is the cache-side face of the Group MX per-field provenance,
REQ-MX-003; it is not a second store.)

**Acceptance criteria:** see acceptance.md AC-MC-006.

---

## 7. Requirement Group MM — OPTIONAL FUTURE Mirror Provisioning & Replication Sync

Priority: Low (OPTIONAL future upgrade — NOT built by default; applies only where the operator
elects to enable the self-hosted mirror).

### REQ-MM-001 — Self-hosted MusicBrainz mirror on Hetzner (Optional) [HARD when enabled]

Where the self-hosted mirror upgrade is enabled, the system shall run a self-hosted MusicBrainz
mirror on the user's Hetzner Cloud instance (NOT on the local WSL2/Docker host), exposing — for
Variant A — the MusicBrainz WEB SERVICE over HTTP so the brain can query it with the same client
protocol it uses for the public API. The mirror is a SEPARATE deployment from the brain; the brain
is a network client. [HARD when enabled] When the mirror is NOT enabled (the default), this
requirement is dormant and the brain uses the public-API + cache path (Group MC).

**Acceptance criteria:** see acceptance.md AC-MM-001.

### REQ-MM-002 — Full `musicbrainz-docker` variant; slimmer variants documented (Optional)

Where the mirror upgrade is enabled, the system shall deploy it as the FULL `musicbrainz-docker`
stack (Postgres + Solr search + MB web service + replication) by default among the mirror variants,
because it gives the brain a DROP-IN local web-service endpoint with NO schema coupling (Section 1.2
Variant A). The Postgres-only (Variant B) and selective-import (Variant C) alternatives — with their
disk savings and their schema-coupling / replication-fragility trade-offs — shall be DOCUMENTED so
the operator can choose; whichever variant is chosen, the brain-facing contract (the
`musicbrainzngs` HTTP API + the local cache + the public-API path) shall remain identical
(REQ-MB-001, REQ-MC-002).

**Acceptance criteria:** see acceptance.md AC-MM-002.

### REQ-MM-003 — Replication-token keep-in-sync (Optional; Event-driven when enabled) [HARD when enabled]

Where the mirror is enabled: when the mirror is initialized and on the replication cadence
thereafter, the system shall keep the mirror current by applying the MetaBrainz live-data-feed
REPLICATION PACKETS authorized by the replication token, so the mirror's data tracks upstream
MusicBrainz over time without a manual full re-import. The replication mechanism is the standard
`musicbrainz-docker` replication (mbslave). [HARD when enabled] The MetaBrainz replication token is
used ONLY by this optional path; the default public-API + cache path (Group MC) needs no token, so
the token stays UNUSED until the mirror is adopted.

**Acceptance criteria:** see acceptance.md AC-MM-003.

### REQ-MM-004 — Replication token (when used) is a gitignored secret, never in the repo (Unwanted) [HARD]

The system shall store the MetaBrainz replication token — IF the optional mirror is enabled — and
any Discogs/Last.fm API keys ONLY in the gitignored `secrets/` tree or process environment on the
deployment host; it SHALL NOT commit them to version control, SHALL NOT write them into any SPEC,
config-template, or documentation file, and SHALL NOT emit them in any log line or error message. A
secret leak is the defect this requirement prevents. (This applies whenever such a secret exists;
the default path simply has no replication token to leak.)

**Acceptance criteria:** see acceptance.md AC-MM-004.

### REQ-MM-005 — Mirror health + replication-lag observability (Optional) — Priority Low

Where the mirror is enabled, the system shall surface the mirror's health and replication freshness
— at least: reachable yes/no, last successful replication timestamp / lag, and web-service
responsiveness — so an operator can tell whether the mirror is current and serving, and so the
brain's degradation decisions (Group MB) are diagnosable after the fact. Mirror-side metrics live
with the mirror deployment; the brain-side reachability/degradation status surfaces through the
CORE-001 health/status surface (OPS-004 NFR-O-6). When the mirror is not enabled, this is dormant.

**Acceptance criteria:** see acceptance.md AC-MM-005.

### REQ-MM-006 — Initial import + rebuild/resync posture (Optional; State-driven when enabled) — Priority Low

Where the mirror is enabled: while provisioning or recovering it, the system shall support a bounded
INITIAL IMPORT (the upstream database dump) and a documented REBUILD/RESYNC path (re-import + resume
replication) for the case where replication falls too far behind to catch up incrementally or the
data volume is lost. During an initial import or rebuild — when the mirror is not yet serving — the
brain SHALL operate on the default public-API + cache path (Group MC / REQ-MB-002), so a mirror that
is being (re)built never blocks enrichment or the stream.

**Acceptance criteria:** see acceptance.md AC-MM-006.

---

## 8. Requirement Group MB — Brain Client (default public API; optional mirror) & Graceful Degradation

Priority: High.

### REQ-MB-001 — Default endpoint = public API; config-gated optional mirror host (Ubiquitous) [HARD]

The system shall use the PUBLIC MusicBrainz API as the brain's DEFAULT `musicbrainzngs` endpoint,
and shall add a config-gated MIRROR HOST setting (e.g. `BRAIN_MB_MIRROR_HOST` →
`config.musicbrainz_mirror_host`, with an optional `use_https` flag) that, WHEN SET, repoints the
brain's EXISTING `musicbrainzngs` client at the optional mirror via the documented
`musicbrainzngs.set_hostname(host, use_https)` call (which accepts a `host:port` form) — so the
SAME `_provider_musicbrainz` / ENRICH-012 calls (`search_recordings`,
`get_recording_by_id(includes=...)`) execute against whichever endpoint is configured, unchanged,
and behind the SAME local cache (Group MC). WHEN UNSET (empty) — the default — the brain uses the
public MusicBrainz API. [HARD] Pointing at a mirror is the only brain change required to adopt the
optional mirror; there shall be NO MusicBrainz-schema coupling in the brain on either path.

**Acceptance criteria:** see acceptance.md AC-MB-001.

### REQ-MB-002 — Graceful degradation: cache → public API → empty (Unwanted) [HARD]

If a lookup misses the cache and the configured endpoint (the public API by default, or the
optional mirror if set) is unreachable, times out, returns an error, or (mirror only) is
mid-(re)build, then the brain shall degrade gracefully — serving the cache when present, falling
back to the public API when the optional mirror is the one failing, and returning gracefully empty
(no enrichment for that track) when no source answers — so any metadata-access problem degrades to
slower-or-absent enrichment, NEVER to an error that propagates, a stall, or dead air. The decision
is per-call and bounded by the configured timeout (`enrichment_http_timeout_seconds`).

**Acceptance criteria:** see acceptance.md AC-MB-002.

### REQ-MB-003 — The brain NEVER blocks on metadata access (Unwanted) [HARD]

If any metadata interaction (a cache miss going to the public API, the optional mirror, or a
cross-check) is slow, queued, or hung, then it SHALL NOT be on the sub-1s `/api/next` pull path
and SHALL NOT stall the director loop, the analysis worker, or the daemon: all enrichment runs OFF
the playout path, bounded by timeout, and a track always plays whether or not its enrichment has
completed (graceful degradation, inherited from ANALYSIS-006 REQ-AP-003 / REQ-AT-006 + CORE-001
continuous operation). [HARD] This is the defining rail of this SPEC, and it holds identically for
the default public-API path and for the optional mirror.

**Acceptance criteria:** see acceptance.md AC-MB-003.

### REQ-MB-004 — Throttle policy: public API at 1 req/s; optional mirror unthrottled-but-bounded (State-driven) [HARD]

While querying MusicBrainz, the system shall apply the 1 req/s self-throttle (`_mb_throttle`)
whenever the call targets the PUBLIC API (the default path, and the politeness policy MetaBrainz
requires); when the call targets the OPTIONAL local MIRROR, the system shall NOT apply the 1 req/s
public limit (the point of the mirror is volume) but SHALL still bound each call by the configured
timeout and a sane local concurrency/rate cap. [HARD] On the default path, the 1 req/s throttle is
NOT a problem because the persistent cache (Group MC) means the call volume is a one-time backfill
plus a trickle — well within budget. The mirror cap + the public-API throttle are TUNABLE config.

**Acceptance criteria:** see acceptance.md AC-MB-004.

### REQ-MB-005 — ENRICH-012 enrichment routes through this seam + the cache (Event-driven) [HARD wiring]

When ENRICH-012 (`brain/enrich.py`) identifies/corrects a track's canonical recording, the
MusicBrainz calls it makes shall route through the Group MB client seam and the Group MC cache —
serving the cache on a hit, and on a miss using the public API by default (or the optional mirror
if configured), then caching the result — so the id3 sanitization of the WHOLE library is a
one-time cached backfill and every new download is a single cached lookup, within the 1 req/s
budget. [HARD] MBMIRROR-017 changes only WHERE the MusicBrainz bytes come from and that they are
cached; the ENRICH-012 identification, confidence-threshold, and write-back logic are unchanged
(referenced, not re-owned).

**Acceptance criteria:** see acceptance.md AC-MB-005.

### REQ-MB-006 — HOSTCTX-016 rich-fact lookups route through this seam with includes (Event-driven)

When SPEC-RADIO-HOSTCTX-016 requests rich facts for a track (first-release year, album/release,
producer, engineer + credited personnel, record label(s), release-group relationships), the
system shall fetch them via the Group MB client seam and the Group MC cache using the appropriate
`musicbrainzngs` `includes=` expansions (e.g. artist-rels, recording-rels, release-rels, labels)
against the public API by default (or the optional mirror if configured), and shall return the
relationship data in a form HOSTCTX-016 consumes. [HARD] These multi-include calls run OFF the
playout path (REQ-MB-003) and their results are CACHED (REQ-MC-002), so each track's rich facts are
fetched once and the per-talk-break path reads the cache — keeping the default 1 req/s path well
within budget. The host-talk generation itself stays in HOSTCTX-016 (referenced).

**Acceptance criteria:** see acceptance.md AC-MB-006.

*(REQ-MB-007 from v0.1.0 — "mirror/fallback result is cached + idempotent with the track record" —
is SUPERSEDED by and absorbed into Group MC, which makes the persistent cache the load-bearing
default-path substrate, REQ-MC-002 / REQ-MC-006.)*

---

## 9. Requirement Group MX — Discogs / Last.fm Cross-Check & Provenance

Priority: Medium (MC / MB are the High-priority spine; cross-check is coverage enrichment).

### REQ-MX-001 — Discogs cross-check for credits/label coverage MusicBrainz lacks (Event-driven)

When MusicBrainz (public API by default, or the optional mirror) lacks producer/engineer/personnel
credits or pressing/label detail for a release, the system shall OPTIONALLY query the Discogs API for that
coverage — adding a new Discogs provider alongside the existing MusicBrainz/TheAudioDB/Last.fm
providers in `brain/metadata.py` — config-gated by a Discogs token (gitignored secret, absent →
provider disabled, log-once, return empty, exactly like the existing Last.fm provider). Discogs
is a COVERAGE source for fields MusicBrainz does not have, not a replacement for the mirror.

**Acceptance criteria:** see acceptance.md AC-MX-001.

### REQ-MX-002 — Last.fm cross-check reuses the existing provider for corroboration (Event-driven)

When corroborating genre/mood/tag or surfacing crowd context, the system shall REUSE the
existing `_provider_lastfm` (`brain/metadata.py`) — already optional/config-gated/log-once — as
a CROSS-CHECK / corroboration source, NOT add a second Last.fm client. MBMIRROR-017 does not
re-own Last.fm; it ensures Last.fm's corroboration feeds the same consensus as the new Discogs
coverage.

**Acceptance criteria:** see acceptance.md AC-MX-002.

### REQ-MX-003 — Per-field provenance on every cross-checked value (Ubiquitous) [HARD]

The system shall record, per supplied field, WHICH source provided it — mirror-MusicBrainz /
public-MusicBrainz / Discogs / Last.fm / TheAudioDB / embedded / audio-hint — and the resulting
consensus level, persisted on the `Track` record (ANALYSIS-006 REQ-AD-001), so every enriched
or cross-checked value has an auditable origin. A value with no recorded provenance is the
defect this requirement prevents.

**Acceptance criteria:** see acceptance.md AC-MX-003.

### REQ-MX-004 — Cross-check folds into the inherited consensus, never asserts single-source as certain (Event-driven) [HARD]

When more than one source (now including Discogs) supplies a value for the same field, the
system shall reconcile it through the EXISTING ANALYSIS-006 REQ-AM-003 consensus discipline
(`brain/metadata.py` `consensus()`): authoritative MusicBrainz outranks crowd folksonomy
(Discogs/Last.fm/TheAudioDB) which outranks embedded/audio-hints; a value is recorded as
"confirmed" only on multi-source consensus (or one authoritative source); single-source /
low-consensus values are FLAGGED as "candidate", NEVER stated as certain. [HARD] MBMIRROR-017
ADDS Discogs into the existing precedence + threshold; it does NOT fork or restate the
algorithm. Discogs's base confidence + its precedence rank are TUNABLE config.

**Acceptance criteria:** see acceptance.md AC-MX-004.

### REQ-MX-005 — Cross-check is rate-limited and off the playout path (State-driven) [HARD]

While cross-checking, the system shall respect each external source's published RATE LIMITS
(Discogs and Last.fm have their own; the local mirror does not throttle, the public-API fallback
keeps 1 req/s), shall bound each call by the configured timeout, and shall run all cross-check
strictly OFF the playout path and downstream of acquisition (coordinating with OPS-004
REQ-OH-006 so a download burst + cross-check do not jointly overload the box). A cross-check
that is slow, rate-limited, or failing degrades to no-coverage for that field, never to a block.

**Acceptance criteria:** see acceptance.md AC-MX-005.

### REQ-MX-006 — Artist-fact boundary to KNOWLEDGE-008 (Ubiquitous)

The system shall scope the cross-check to RELEASE/RECORDING-level credits (producer, engineer,
personnel, label-on-this-release, year, release relationships); where Discogs/Last.fm surface
ARTIST-LEVEL facts (label history, scene, biography, lineage), those belong to
SPEC-RADIO-KNOWLEDGE-008's dated/sourced fact store and its consensus — MBMIRROR-017 references
that ownership and does NOT record artist facts as a second, parallel store. This requirement
exists to make the boundary explicit and prevent duplication.

**Acceptance criteria:** see acceptance.md AC-MX-006.

---

## 10. Requirement Group MV — OPTIONAL FUTURE Volume, Sizing & Operations

Priority: Low (OPTIONAL future upgrade — applies only where the self-hosted mirror is enabled).

### REQ-MV-001 — Provision ~150 GB Hetzner volume for Variant A (Optional)

Where the mirror upgrade is enabled, the system shall provision a Hetzner volume sized for the
chosen variant — approximately **150 GB for Variant A** (Postgres + Solr + web service, ~100–150 GB
plus headroom for replication growth), ~50–80 GB for Variant B (Postgres-only), or ~15–25 GB for
Variant C (selective import). The size figures are documented so the operator provisions with
headroom; the mirror SHALL NOT be provisioned so tight that replication growth fills the volume
(which would break sync — see REQ-MV-002). When the mirror is not enabled (the default), there is
no volume to provision.

**Acceptance criteria:** see acceptance.md AC-MV-001.

### REQ-MV-002 — Disk-headroom + replication-growth monitoring (Optional; State-driven when enabled)

Where the mirror is enabled: while it runs, the system shall monitor volume free space and
replication growth so the operator is warned BEFORE the volume fills (a full volume halts
replication and eventually the web service). This monitoring lives with the mirror deployment; its
summarized status feeds the mirror health surface (REQ-MM-005). A volume-pressure or
replication-halt condition on the mirror shall trigger the brain's default public-API + cache path
(REQ-MB-002 / Group MC), never a brain error.

**Acceptance criteria:** see acceptance.md AC-MV-002.

### REQ-MV-003 — Documented operator runbook for the optional mirror (Optional) — Priority Low

Where the mirror upgrade is adopted, the system shall be accompanied by an operator RUNBOOK
documenting: initial provisioning + import, configuring the replication token (as a secret,
REQ-MM-004), enabling replication (REQ-MM-003), pointing the brain at the mirror
(`BRAIN_MB_MIRROR_HOST`, REQ-MB-001), the rebuild/resync path (REQ-MM-006), and the variant
trade-offs (REQ-MM-002). The runbook is documentation, NOT provisioning automation (which is out of
scope, Section 4.2); it ensures the mirror is operable and recoverable by the user without
reverse-engineering this SPEC. (The default path needs no runbook beyond setting the cache on.)

**Acceptance criteria:** see acceptance.md AC-MV-003.

---

## 11. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following:

- **The id3-sanitization / canonical-recording identification + write-back LOGIC** — owned by
  ENRICH-012; only the fast endpoint + cross-check coverage is here.
- **Host-talk generation, persona style, grounding gate** — owned by HOSTCTX-016 /
  PROGRAMMING-007 PG; only the rich facts are supplied.
- **The consensus ALGORITHM** — owned by ANALYSIS-006 REQ-AM-003 (`metadata.py` `consensus()`);
  only NEW sources (Discogs) are folded in.
- **Artist-FACT research + the dated/sourced fact store** — owned by KNOWLEDGE-008; only
  release/recording credits are surfaced (REQ-MX-006).
- **The download-dedup POLICY** — owned by SPEC-RADIO-DEDUP-014; only the canonical recording
  MBID is made available (via ENRICH-012).
- **AcoustID fingerprinting + a hosted AcoustID mirror** — AcoustID stays an ENRICH-012 hosted-
  service call; only the MusicBrainz database is mirrored.
- **A MusicBrainz-schema ORM / SQL layer in the brain** — avoided by recommending Variant A
  (HTTP, no schema coupling); any SQL for Variant B/C is an OPS detail behind the same client
  contract, not a brain product.
- **Mirroring Discogs / Last.fm / Wikidata** — those stay public rate-limited API calls.
- **Provisioning automation / IaC** — a runbook is provided (REQ-MV-003), not Terraform/Ansible.
- **A new datastore in the brain** — provenance rides on the existing `Track` record.
- **Putting the mirror on the local WSL2 box** — explicitly reversed by the locked Hetzner
  decision; the brain is a remote client only.

---

## 12. Non-Functional Requirements

### NFR-M-1 — Never block on metadata access (Ubiquitous) — Priority High
No metadata interaction (cache miss → public API, the optional mirror, or a cross-check) shall be
on the sub-1s `/api/next` pull path or able to stall the director/analysis-worker/daemon/stream;
all enrichment runs off the playout path, timeout-bounded, with graceful degradation
(REQ-MB-002/003). See acceptance.md AC-NFR-M-1.

### NFR-M-2 — Drop-in client, no schema coupling (Ubiquitous) — Priority High
The brain shall talk the same `musicbrainzngs` HTTP API on the default public-API path; adopting
the optional mirror shall change ONLY the host it points at, with the existing client calls
unchanged and zero MusicBrainz-schema knowledge in the brain on either path (REQ-MB-001). See
acceptance.md AC-NFR-M-2.

### NFR-M-3 — Secret safety (Ubiquitous) — Priority High
Any Discogs/Last.fm API keys — and the MetaBrainz replication token IF the optional mirror is
enabled — shall live only in gitignored `secrets/`/env, never in the repo, a SPEC, a
config-template, or a log line (REQ-MM-004). The default path needs no token. See acceptance.md
AC-NFR-M-3.

### NFR-M-4 — Resilience / graceful degradation (Ubiquitous) — Priority High
A failing endpoint — the public API being slow/down, or (when enabled) a mirror that is down,
lagging, mid-(re)build, unreachable, or volume-pressured — shall degrade to the cache, the
public-API path, or graceful no-enrichment WITHOUT crashing the worker, the director, or the
daemon, and without silencing the stream (REQ-MB-002, REQ-MC-002, REQ-MM-006, REQ-MV-002). See
acceptance.md AC-NFR-M-4.

### NFR-M-5 — Throughput via cache, not infra: 1 req/s + cache is sufficient at scale (Ubiquitous) — Priority High
The DEFAULT path (public API at 1 req/s + the persistent cache, Group MC) shall make the
ENRICH-012 whole-library id3 backfill and HOSTCTX-016 multi-include rich-fact lookups practical at
the station's scale: cache-once / reuse-forever turns the workload into a one-time ~500–1000-call
backfill (~10–20 min) plus a trickle — well under the 86,400 calls/day the 1/sec limit allows
(<1% used). Higher raw throughput is available via the optional mirror, but is NOT required at our
scale (REQ-MC-001/002/003, REQ-MB-004/005/006). See acceptance.md AC-NFR-M-5.

### NFR-M-6 — Per-field provenance + consensus integrity (Ubiquitous) — Priority High
Every enriched/cross-checked/cached value shall carry its source provenance + consensus level; a
single-source value shall never be recorded as "confirmed"; the cross-check shall fold into the
EXISTING consensus, not a fork (REQ-MX-003/004, REQ-MC-006). See acceptance.md AC-NFR-M-6.

### NFR-M-7 — Rate-limit compliance (Ubiquitous) — Priority Medium
The default public-API path (and any public-API fallback) shall keep the 1 req/s MusicBrainz
self-throttle; Discogs + Last.fm shall respect their published rate limits; only the optional
local mirror is high-throughput (and still timeout + local-cap bounded) (REQ-MB-004, REQ-MX-005).
See acceptance.md AC-NFR-M-7.

### NFR-M-8 — Simplicity / no over-engineering (Ubiquitous) — Priority Medium
This SPEC shall implement the smallest change that delivers accurate metadata + rich facts: the
DEFAULT is public API + a persistent cache (no token, no mirror infra); reuse the existing
providers/consensus; add one Discogs provider; no schema ORM, no new datastore, no
provisioning-automation product; the mirror stays a deferred, optional upgrade. Deferred items
(Section 11) MUST NOT be partially built. See acceptance.md AC-NFR-M-8.

### NFR-M-9 — Cache durability / persistence (Ubiquitous) — Priority High
The persistent local result cache (Group MC) shall be durable in the brain's DB — surviving brain
and Icecast restarts — so a track enriched once is never re-fetched and the default 1 req/s path
stays within budget across the station's lifetime; the cache is the load-bearing substrate of the
default path, not a transient in-memory optimization (REQ-MC-002/003). See acceptance.md AC-NFR-M-9.

---

## 13. Open Questions / Risks

- **R-M-0 — Default-path sufficiency (Low, DECIDED v0.2.0).** The risk that "1 req/s is too slow"
  is resolved by the cache: at ~500 tracks with cache-once / reuse-forever the backfill is a
  one-time ~500–1000 calls (<1% of the 86,400/day budget). The mirror (R-M-1..R-M-5 below) is an
  OPTIONAL future upgrade, so its risks are DEFERRED and do not block this SPEC's default path.
- **R-M-1 — Mirror variant choice (Low, DEFERRED — only if the mirror is ever adopted).** Variant A
  (full `musicbrainz-docker`) is the recommended upgrade for the zero-schema-coupling drop-in; B/C
  save disk at the cost of schema coupling + replication fragility. Mitigated by keeping the
  brain-facing contract identical across variants (REQ-MM-002 / REQ-MB-001) so the choice is
  reversible. **Only needs a ruling if/when the mirror upgrade is adopted** (Section 14, D-1).
- **R-M-2 — Hetzner volume sizing + cost (Low/Medium).** ~150 GB for Variant A is a real
  monthly cost; under-provisioning breaks replication when the DB grows. Mitigated by the
  documented sizing table (REQ-MV-001) + disk-headroom monitoring (REQ-MV-002) + the fallback
  on volume pressure. **Confirm the volume size + cost tolerance with the user** (D-2).
- **R-M-3 — Replication lag / catch-up (Medium).** If the mirror is offline a while, replication
  must catch up; if it falls too far behind, a re-import is needed. Mitigated by the rebuild/
  resync posture (REQ-MM-006) + lag monitoring (REQ-MM-005); while catching up or rebuilding,
  the brain runs on the public-API fallback so nothing blocks.
- **R-M-4 — Network reliability brain↔Hetzner (Medium).** The brain is local; the mirror is
  remote — a flaky link or Hetzner outage makes the mirror unreachable. Mitigated by the
  per-call timeout + automatic public-API fallback (REQ-MB-002) + the never-block rail
  (REQ-MB-003): a remote-mirror outage degrades to slower enrichment, never dead air.
- **R-M-5 — Mirror exposure / security (Medium).** The MB web service must be reachable by the
  brain but should not be an open public service. Mitigated by binding the mirror to the brain's
  access path (firewall / private network / auth as the operator chooses — an OPS posture in the
  runbook REQ-MV-003); this SPEC requires the brain reach it, not that it be public.
  **Confirm the access/network posture with the user** (D-3).
- **R-M-6 — `set_hostname` / `host:port` + HTTPS behavior (Low).** The brain repoint relies on
  `musicbrainzngs.set_hostname(host, use_https)` accepting a `host:port` and an HTTPS flag
  (documented). Mitigated by the config carrying both host and `use_https`, and by the fallback:
  if a repoint misconfiguration makes the mirror unusable, the brain falls back to the public API
  rather than failing. Verified against the musicbrainzngs docs during authoring.
- **R-M-7 — Discogs/Last.fm ToS + rate limits (Low/Medium).** Both have rate limits + ToS;
  abusing them risks a key ban. Mitigated by config-gated keys (absent → provider disabled,
  log-once, like the existing Last.fm provider), published-rate-limit compliance + timeout
  (REQ-MX-005), and treating cross-check as optional coverage that degrades gracefully. **Confirm
  whether a Discogs token will be provided** (D-4) — absent one, REQ-MX-001 stays dormant and the
  mirror + Last.fm still deliver the spine.
- **R-M-8 — AcoustID stays public (Low).** Only MusicBrainz is mirrored; ENRICH-012's AcoustID
  fingerprint lookups still hit the public AcoustID service. Acceptable: AcoustID is a separate
  service and fingerprint identification is a lower-volume path than text-match enrichment.
- **R-M-9 — MusicBrainz data licensing on supplementary tables (Low).** Core MB data is CC0;
  some supplementary tables are CC-BY-NC-SA. Self-hosting under the replication token is
  explicitly supported. Residual: if any mirror-derived data were redistributed, the
  CC-BY-NC-SA attribution/non-commercial terms attach. The brain only SERVES audio + spoken
  facts to listeners (not the database), so this is flagged, not blocking.

---

## 14. Design Decisions Needing the Orchestrator's Ruling

The following are surfaced for an explicit ruling before/at the Run phase (none block authoring
the SPEC; each has a recommended default this SPEC is written against):

- **D-0 — Default path (DECIDED v0.2.0, user-approved: public API + persistent cache).** The
  default-and-first build is Group MC (public API at 1 req/s + a durable cache); the mirror is a
  deferred optional upgrade. No further ruling needed unless a (a)/(b)/(c) trigger (Section 1.1)
  fires. D-1..D-3, D-5 below apply ONLY if the mirror upgrade is later adopted.
- **D-1 — Mirror variant, IF adopted (RECOMMENDED: Variant A, full `musicbrainz-docker`).** If the
  mirror upgrade is elected, the SPEC favors Variant A (drop-in, no schema coupling); B/C keep the
  brain contract identical but add a SQL/schema layer as an OPS detail. See R-M-1.
- **D-2 — Hetzner volume size + cost tolerance (RECOMMENDED: ~150 GB).** Confirm the ~150 GB
  Variant-A provision (vs ~50–80 GB / ~15–25 GB for B/C) and the monthly cost. See R-M-2.
- **D-3 — Mirror network/access posture (RECOMMENDED: private/firewalled, not public).** Confirm
  HOW the brain reaches the mirror (Hetzner private network / firewall allowlist / auth) so the
  mirror is reachable by the brain but not an open public service. See R-M-5.
- **D-4 — Discogs cross-check enablement (RECOMMENDED: optional, config-gated).** Confirm whether
  a Discogs token will be supplied. Absent one, REQ-MX-001 stays dormant (provider disabled,
  log-once) and the spine (mirror + Last.fm corroboration) still delivers. See R-M-7.
- **D-5 — Mirror `use_https` (RECOMMENDED: follow the deployment).** Confirm whether the mirror
  web service is served over HTTP (typical for a private `musicbrainz-docker`) or HTTPS, which
  sets the `use_https` flag on the repoint (REQ-MB-001). See R-M-6.

---

## 15. Out-of-Scope / Future SPEC Roadmap

- **SPEC-RADIO-ENRICH-012** (in progress) — the id3-sanitization engine that CONSUMES this
  mirror for volume; finished as its own SPEC, referenced here.
- **SPEC-RADIO-HOSTCTX-016** — the richer host talk that CONSUMES the rich facts; its own SPEC.
- **SPEC-RADIO-DEDUP-014** — download-duplication control keyed on the canonical recording MBID
  the mirror surfaces (via ENRICH-012); its own SPEC.
- **Wikidata / additional authoritative mirror** — if a future need outgrows MusicBrainz +
  Discogs + Last.fm; not built now.
- **Provisioning automation (IaC)** — if the mirror deployment becomes frequent enough to
  warrant Terraform/Ansible; a runbook suffices today (REQ-MV-003).

---

## 16. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md;
detailed Given-When-Then scenarios for the load-bearing requirements are in acceptance.md
Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-MC-001 | Default Path: Public API + Cache | High | Ubiquitous | AC-MC-001 |
| REQ-MC-002 | Default Path: Public API + Cache | High | Ubiquitous | AC-MC-002 |
| REQ-MC-003 | Default Path: Public API + Cache | High | Unwanted | AC-MC-003 |
| REQ-MC-004 | Default Path: Public API + Cache | Medium | State | AC-MC-004 |
| REQ-MC-005 | Default Path: Public API + Cache | High | Event | AC-MC-005 |
| REQ-MC-006 | Default Path: Public API + Cache | High | Ubiquitous | AC-MC-006 |
| REQ-MB-001 | Brain Client & Graceful Degradation | High | Ubiquitous | AC-MB-001 |
| REQ-MB-002 | Brain Client & Graceful Degradation | High | Unwanted | AC-MB-002 |
| REQ-MB-003 | Brain Client & Graceful Degradation | High | Unwanted | AC-MB-003 |
| REQ-MB-004 | Brain Client & Graceful Degradation | High | State | AC-MB-004 |
| REQ-MB-005 | Brain Client & Graceful Degradation | High | Event | AC-MB-005 |
| REQ-MB-006 | Brain Client & Graceful Degradation | High | Event | AC-MB-006 |
| REQ-MX-001 | Cross-Check & Provenance | Medium | Event | AC-MX-001 |
| REQ-MX-002 | Cross-Check & Provenance | Medium | Event | AC-MX-002 |
| REQ-MX-003 | Cross-Check & Provenance | High | Ubiquitous | AC-MX-003 |
| REQ-MX-004 | Cross-Check & Provenance | High | Event | AC-MX-004 |
| REQ-MX-005 | Cross-Check & Provenance | High | State | AC-MX-005 |
| REQ-MX-006 | Cross-Check & Provenance | Medium | Ubiquitous | AC-MX-006 |
| REQ-MM-001 | OPTIONAL FUTURE Mirror Provisioning & Sync | Low | Optional | AC-MM-001 |
| REQ-MM-002 | OPTIONAL FUTURE Mirror Provisioning & Sync | Low | Optional | AC-MM-002 |
| REQ-MM-003 | OPTIONAL FUTURE Mirror Provisioning & Sync | Low | Optional/Event | AC-MM-003 |
| REQ-MM-004 | OPTIONAL FUTURE Mirror Provisioning & Sync | High | Unwanted | AC-MM-004 |
| REQ-MM-005 | OPTIONAL FUTURE Mirror Provisioning & Sync | Low | Optional | AC-MM-005 |
| REQ-MM-006 | OPTIONAL FUTURE Mirror Provisioning & Sync | Low | Optional/State | AC-MM-006 |
| REQ-MV-001 | OPTIONAL FUTURE Volume, Sizing & Operations | Low | Optional | AC-MV-001 |
| REQ-MV-002 | OPTIONAL FUTURE Volume, Sizing & Operations | Low | Optional/State | AC-MV-002 |
| REQ-MV-003 | OPTIONAL FUTURE Volume, Sizing & Operations | Low | Optional | AC-MV-003 |
| NFR-M-1 | Non-Functional | High | Ubiquitous | AC-NFR-M-1 |
| NFR-M-2 | Non-Functional | High | Ubiquitous | AC-NFR-M-2 |
| NFR-M-3 | Non-Functional | High | Ubiquitous | AC-NFR-M-3 |
| NFR-M-4 | Non-Functional | High | Ubiquitous | AC-NFR-M-4 |
| NFR-M-5 | Non-Functional | High | Ubiquitous | AC-NFR-M-5 |
| NFR-M-6 | Non-Functional | High | Ubiquitous | AC-NFR-M-6 |
| NFR-M-7 | Non-Functional | Medium | Ubiquitous | AC-NFR-M-7 |
| NFR-M-8 | Non-Functional | Medium | Ubiquitous | AC-NFR-M-8 |
| NFR-M-9 | Non-Functional | High | Ubiquitous | AC-NFR-M-9 |
