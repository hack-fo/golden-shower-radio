---
id: SPEC-RADIO-MBMIRROR-017
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: High
issue_number: null
---

# SPEC-RADIO-MBMIRROR-017 — Self-Hosted MusicBrainz Mirror (on Hetzner) + Discogs/Last.fm Cross-Check

## HISTORY

- 2026-06-23 (v0.1.0): Initial draft. The metadata-INFRASTRUCTURE SPEC of the
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
  `musicbrainzngs.set_hostname(host, use_https)`). Total: 22 REQ + 8 NFR = 30, 1:1 REQ↔AC.

---

## 1. Overview & Background

### 1.1 Why this SPEC — "we need MusicBrainz at volume, and we cannot have it on the local box"

The brain already talks to MusicBrainz. `brain/metadata.py` has a `_provider_musicbrainz`
that lazy-imports `musicbrainzngs`, sets a User-Agent, and self-throttles to <= 1 request
per second (the published public-API policy). `brain/enrich.py` (ENRICH-012, in progress)
uses the same access for AcoustID-then-MusicBrainz canonical-recording identification to
correct garbled id3 tags. Two new demands break that 1 req/s ceiling:

1. **ENRICH-012 at volume.** Sanitizing the id3 tags of the WHOLE existing library plus
   every new download means thousands of MusicBrainz lookups. At 1 req/s the backfill
   crawls; the public API will throttle or rate-limit a sustained crawl, and the brain ends
   up doing slow, polite, perpetually-behind enrichment.
2. **HOSTCTX-016 rich facts.** The host wants to say the year, the album, who PRODUCED it,
   who is CREDITED, and which LABEL released it — release-relationship data that lives in
   MusicBrainz's relationship (`l_*`) tables and needs `includes=` expansions (artist-rels,
   release-rels, labels, recording-rels). Those are expensive multi-include calls; doing
   them per-talk-break against the public API is exactly the politeness budget MusicBrainz
   asks you NOT to spend.

The earlier analysis assumed a full mirror could not live on the local box (the music dir is
a Windows-hosted WSL2 bind mount, disk is scarce, a ~39 GB+ Postgres dump is hostile to that
layout). The orchestrator + user locked a different answer on 2026-06-23: **the mirror lives
on the user's Hetzner Cloud instance.** Disk is no longer scarce there. The brain (running in
WSL2/Docker locally) simply QUERIES the remote endpoint. This SPEC owns standing that mirror
up, keeping it synced, repointing the brain at it, and the Discogs/Last.fm cross-check for the
credits MusicBrainz alone does not cover.

### 1.2 The recommended variant, and why (the "how much" answer)

The backlog poses the sizing question directly. This SPEC RECOMMENDS the full
`musicbrainz-docker` stack and documents the two slimmer alternatives so the operator can
choose with eyes open:

| Variant | What runs | Approx. Hetzner volume | Brain change | Trade-off |
|---------|-----------|------------------------|--------------|-----------|
| **A — Full `musicbrainz-docker` (RECOMMENDED)** | Postgres + Solr search + the MB **web service** (mbslave/replication included) | ~100–150 GB (provision **~150 GB** for headroom + replication growth) | DROP-IN: repoint the hostname only (`musicbrainzngs.set_hostname`) — the brain calls the same HTTP API, no schema coupling | Largest disk; standard, well-trodden, easiest to keep in sync; matches the public API surface 1:1 |
| B — Postgres-only (no Solr, no web service) | Postgres + replication; brain queries by SQL joins / MBID | ~50–80 GB | INVASIVE: brain must learn the MB schema + write SQL; loses `search_recordings` text-match unless we add Solr or a text index | Smaller disk; couples the brain to the MB schema (a maintenance burden we explicitly avoid) |
| C — Selective import (subset of tables) | Postgres with only artist, recording, release, release_group, label, artist_credit, medium, track, and the `l_*` relationship tables | ~15–25 GB | MOST invasive: brain writes SQL against a partial schema; replication of a subset is fragile | Smallest disk; brittle sync; partial schema means missing-data surprises |

[HARD recommendation, not a hard rail] Variant A is recommended because Hetzner disk is not
the constraint and the brain change is the SMALLEST possible — repoint a hostname and the
existing `musicbrainzngs` calls (`search_recordings`, `get_recording_by_id` with `includes=`)
work UNCHANGED against the local web service. Variants B and C trade disk for schema coupling
and replication fragility, which is exactly the maintenance cost this SPEC exists to avoid. The
operator MAY choose B or C; this SPEC keeps the brain-facing contract identical across variants
(the brain only ever speaks the `musicbrainzngs` HTTP API + the fallback), so the variant choice
is an OPS decision behind a stable client seam.

### 1.3 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] MBMIRROR-017 owns the INFRASTRUCTURE (the mirror, its sync, its volume, its
availability posture) and the BRAIN CLIENT REPOINT (the host config + fallback). It MUST NOT
re-own, restate, or fork the id3-sanitization logic, the host-talk logic, the consensus
algorithm, or the artist-fact knowledge store.

OWNS:
- Standing up the MusicBrainz mirror on Hetzner, its variant choice + sizing, the
  replication-token sync, and the operational posture (Group MM / MV).
- The brain-side host repoint: config-gated mirror host, the `musicbrainzngs.set_hostname`
  seam, and the automatic public-API fallback (Group MB).
- The Discogs + Last.fm cross-check CLIENTS for credits/label/corroboration coverage that
  MusicBrainz alone lacks, rate-limited, with per-field provenance (Group MX).

REFERENCES (consumes / feeds; does not restate):
- **ENRICH-012** (`brain/enrich.py`, config `enrich_*`) — the canonical-recording
  identification + id3 write-back ENGINE. It is the PRIMARY CONSUMER: MBMIRROR-017 gives it
  a high-throughput MusicBrainz endpoint so it can sanitize at volume. The identification /
  correction / write-back logic, the confidence threshold, and the write-back-to-file
  decision stay in ENRICH-012; MBMIRROR-017 only changes WHERE the MusicBrainz bytes come
  from and adds cross-check coverage. ENRICH-012 is the metadata SPINE; this SPEC is its
  throughput + coverage substrate.
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

- **The brain NEVER blocks on the mirror.** Every mirror interaction is bounded by a timeout
  and falls back (public API → graceful no-enrichment) on any failure. A down/lagging/
  mid-sync/unreachable mirror is an expected operating state, never a defect and never dead air.
- **Secrets stay gitignored + orchestrator-perm-denied.** The replication token and any
  Discogs/Last.fm key live in the gitignored `secrets/` tree (or env), never in the repo,
  never in a SPEC, never logged. (The orchestrator is permission-denied in `secrets/`.)
- **Drop-in client, no schema coupling (Variant A).** The brain talks the same
  `musicbrainzngs` HTTP API; the ONLY brain change for the mirror is the host it points at.
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
the in-progress ENRICH-012; it is CONSUMED BY ENRICH-012 (throughput) and SPEC-RADIO-HOSTCTX-016
(rich facts). It references their subsystems by CONCEPT and, where a cited requirement is a
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

- **ENRICH-012** consumes the high-throughput MusicBrainz endpoint to sanitize id3 at volume.
- **SPEC-RADIO-HOSTCTX-016** consumes the rich release/recording relationships (producer,
  credits, labels) for grounded host talk.
- **SPEC-RADIO-DEDUP-014** consumes the canonical MusicBrainz **recording MBID** (surfaced via
  the mirror through ENRICH-012) as its dedup key; referenced, not owned here.

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

- **Group MM — Mirror Provisioning & Replication Sync.** Standing up the mirror on Hetzner
  (recommended Variant A `musicbrainz-docker`); the replication-token-driven keep-in-sync;
  the documented slimmer Variants B/C; the secret-handling discipline; the mirror's own
  health/observability surface.
- **Group MB — Brain Client Repoint & Fallback.** The config-gated mirror host; the
  `musicbrainzngs.set_hostname` repoint of the EXISTING client; the automatic public-API
  fallback; the never-block rail; the 1 req/s throttle ONLY on the public-API path (mirror is
  unthrottled-but-bounded); ENRICH-012 + HOSTCTX-016 query routing through this seam.
- **Group MX — Discogs / Last.fm Cross-Check & Provenance.** A Discogs client (new) +
  reuse of the existing Last.fm provider for the credits/label/corroboration coverage
  MusicBrainz lacks; rate-limited; per-field provenance; folded into the inherited
  ANALYSIS-006 consensus; the artist-fact boundary to KNOWLEDGE-008.
- **Group MV — Volume, Sizing & Operations.** The ~150 GB Hetzner volume provision for
  Variant A (with the B/C alternatives documented); replication lag monitoring; the
  resync/rebuild posture; cost/disk headroom.
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

- [HARD] **Mirror on Hetzner Cloud, not local WSL disk.** Locked 2026-06-23
  (`feature-backlog-2026-06-23.md`). The brain (local WSL2/Docker) is a remote CLIENT.
- [HARD] **Brain = the existing Python `brain/` package.** MBMIRROR-017 extends
  `config.py`, `metadata.py`, `enrich.py`; it adds a Discogs provider + a host setter, not a
  new service.
- [HARD] **Never block on the mirror.** Every mirror/external call is timeout-bounded and
  falls back; never on the sub-1s `/api/next` pull; never stalls the director/daemon/stream.
- [HARD] **Drop-in client for Variant A.** Repoint the hostname via
  `musicbrainzngs.set_hostname(host, use_https)`; the existing `search_recordings` /
  `get_recording_by_id(includes=...)` calls work unchanged. No schema coupling.
- [HARD] **Secrets gitignored + never logged.** Replication token + any API keys live in
  `secrets/` / env, never the repo, never a SPEC, never a log line.
- [HARD] **Public-API politeness preserved on the fallback path.** The 1 req/s MusicBrainz
  self-throttle (`_mb_throttle`) applies whenever the brain talks to `musicbrainz.org`; the
  mirror path is exempt from the 1 req/s limit but still bounded by timeout + a sane local cap.
- [HARD] **Per-field provenance + consensus.** Cross-checked values record their source and
  are folded into the inherited ANALYSIS-006 consensus; single-source values are flagged, not
  asserted as certain.
- [HARD] **No fork of the library store or the consensus algorithm.** Extend in place.
- **License/ToS awareness.** MusicBrainz data is CC0 (core) / CC-BY-NC-SA (some supplementary
  tables); self-hosting + replication is explicitly supported by MetaBrainz under the token.
  Discogs + Last.fm API use is bound by their ToS + rate limits (R-M-7). Flagged, not blocking.

---

## 6. Requirement Group MM — Mirror Provisioning & Replication Sync

Priority: High.

### REQ-MM-001 — Self-hosted MusicBrainz mirror on Hetzner (Ubiquitous) [HARD]

The system shall run a self-hosted MusicBrainz mirror on the user's Hetzner Cloud instance
(NOT on the local WSL2/Docker host), exposing — for the recommended Variant A — the MusicBrainz
WEB SERVICE over HTTP so the brain can query it with the same client protocol it uses for the
public API. The mirror is a SEPARATE deployment from the brain; the brain is a network client.

**Acceptance criteria:** see acceptance.md AC-MM-001.

### REQ-MM-002 — Recommended full `musicbrainz-docker` variant; slimmer variants documented (Ubiquitous)

The system shall deploy the mirror as the FULL `musicbrainz-docker` stack (Postgres + Solr
search + MB web service + replication) by default, because it gives the brain a DROP-IN local
web-service endpoint with NO schema coupling (Section 1.2 Variant A). The Postgres-only
(Variant B) and selective-import (Variant C) alternatives — with their disk savings and their
schema-coupling / replication-fragility trade-offs — shall be DOCUMENTED so the operator can
choose; whichever variant is chosen, the brain-facing contract (the `musicbrainzngs` HTTP API
+ the public-API fallback) shall remain identical (REQ-MB-001).

**Acceptance criteria:** see acceptance.md AC-MM-002.

### REQ-MM-003 — Replication-token keep-in-sync (Event-driven + self-scheduled) [HARD]

When the mirror is initialized and on the replication cadence thereafter, the system shall keep
the mirror current by applying the MetaBrainz live-data-feed REPLICATION PACKETS authorized by
the replication token, so the mirror's data tracks upstream MusicBrainz over time without a
manual full re-import. The replication mechanism is the standard `musicbrainz-docker`
replication (mbslave); MBMIRROR-017 requires that it is ENABLED and the token configured.

**Acceptance criteria:** see acceptance.md AC-MM-003.

### REQ-MM-004 — Replication token is a gitignored secret, never in the repo (Unwanted) [HARD]

The system shall store the MetaBrainz replication token (and any Discogs/Last.fm API keys) ONLY
in the gitignored `secrets/` tree or process environment on the deployment host; it SHALL NOT
commit the token to version control, SHALL NOT write it into any SPEC, config-template, or
documentation file, and SHALL NOT emit it in any log line or error message. A token leak is the
defect this requirement prevents.

**Acceptance criteria:** see acceptance.md AC-MM-004.

### REQ-MM-005 — Mirror health + replication-lag observability (Ubiquitous) — Priority Medium

The system shall surface the mirror's health and replication freshness — at least: reachable
yes/no, last successful replication timestamp / lag, and web-service responsiveness — so an
operator can tell whether the mirror is current and serving, and so the brain's fallback
decisions (Group MB) are diagnosable after the fact. Mirror-side metrics live with the mirror
deployment; the brain-side reachability/fallback status surfaces through the CORE-001
health/status surface (OPS-004 NFR-O-6).

**Acceptance criteria:** see acceptance.md AC-MM-005.

### REQ-MM-006 — Initial import + rebuild/resync posture (State-driven) — Priority Medium

While provisioning or recovering the mirror, the system shall support a bounded INITIAL IMPORT
(the upstream database dump) and a documented REBUILD/RESYNC path (re-import + resume
replication) for the case where replication falls too far behind to catch up incrementally or
the data volume is lost. During an initial import or rebuild — when the mirror is not yet
serving — the brain SHALL operate on the public-API fallback (REQ-MB-002), so a mirror that is
being (re)built never blocks enrichment or the stream.

**Acceptance criteria:** see acceptance.md AC-MM-006.

---

## 7. Requirement Group MB — Brain Client Repoint & Fallback

Priority: High.

### REQ-MB-001 — Config-gated mirror host, repointing the existing client (Ubiquitous) [HARD]

The system shall add a config-gated MIRROR HOST setting (e.g. `BRAIN_MB_MIRROR_HOST` →
`config.musicbrainz_mirror_host`, with an optional `use_https` flag) that, WHEN SET, repoints
the brain's EXISTING `musicbrainzngs` client at the mirror via the documented
`musicbrainzngs.set_hostname(host, use_https)` call (which accepts a `host:port` form) — so the
SAME `_provider_musicbrainz` / ENRICH-012 calls (`search_recordings`,
`get_recording_by_id(includes=...)`) execute against the local web service unchanged. WHEN
UNSET (empty), the brain shall use the public MusicBrainz API exactly as today. [HARD] This is
the only brain change required for Variant A; there shall be NO MusicBrainz-schema coupling in
the brain.

**Acceptance criteria:** see acceptance.md AC-MB-001.

### REQ-MB-002 — Automatic public-API fallback on any mirror failure (Unwanted) [HARD]

If the mirror is unset, unreachable, times out, returns an error, or is mid-(re)build, then the
brain shall AUTOMATICALLY fall back to the public MusicBrainz API (at the 1 req/s self-throttle)
for that lookup — and if the public API also fails, shall return gracefully empty (no
enrichment for that track) — so a mirror problem degrades to slower-or-absent enrichment, NEVER
to an error that propagates, a stall, or dead air. The fallback decision is per-call and
bounded by the configured timeout (`enrichment_http_timeout_seconds`).

**Acceptance criteria:** see acceptance.md AC-MB-002.

### REQ-MB-003 — The brain NEVER blocks on the mirror (Unwanted) [HARD]

If any mirror or external-metadata interaction is slow, queued, or hung, then it SHALL NOT be
on the sub-1s `/api/next` pull path and SHALL NOT stall the director loop, the analysis worker,
or the daemon: all enrichment (mirror or fallback) runs OFF the playout path, bounded by
timeout, and a track always plays whether or not its enrichment has completed (graceful
degradation, inherited from ANALYSIS-006 REQ-AP-003 / REQ-AT-006 + CORE-001 continuous
operation). [HARD] This is the defining rail of this SPEC.

**Acceptance criteria:** see acceptance.md AC-MB-003.

### REQ-MB-004 — Throttle policy: mirror unthrottled-but-bounded, public-API at 1 req/s (State-driven) [HARD]

While querying MusicBrainz, the system shall apply the 1 req/s self-throttle (`_mb_throttle`)
ONLY when the call targets the PUBLIC API (the politeness policy MetaBrainz requires); when the
call targets the local MIRROR, the system shall NOT apply the 1 req/s public limit (the whole
point of the mirror is volume) but SHALL still bound each call by the configured timeout and a
sane local concurrency/rate cap so a runaway backfill cannot saturate the mirror or the brain.
The mirror cap + the public-API throttle are TUNABLE config.

**Acceptance criteria:** see acceptance.md AC-MB-004.

### REQ-MB-005 — ENRICH-012 enrichment at volume routes through this seam (Event-driven) [HARD wiring]

When ENRICH-012 (`brain/enrich.py`) identifies/corrects a track's canonical recording, the
MusicBrainz calls it makes shall route through the Group MB client seam — using the mirror when
configured (fast, unthrottled-but-bounded) and the public-API fallback otherwise — so the id3
sanitization backfill of the WHOLE library and every new download proceeds at volume without
the public-API 1 req/s ceiling. [HARD] MBMIRROR-017 changes only WHERE the MusicBrainz bytes
come from; the ENRICH-012 identification, confidence-threshold, and write-back logic are
unchanged (referenced, not re-owned).

**Acceptance criteria:** see acceptance.md AC-MB-005.

### REQ-MB-006 — HOSTCTX-016 rich-fact lookups route through this seam with includes (Event-driven)

When SPEC-RADIO-HOSTCTX-016 requests rich facts for a track (first-release year, album/release,
producer, engineer + credited personnel, record label(s), release-group relationships), the
system shall fetch them via the Group MB client seam using the appropriate `musicbrainzngs`
`includes=` expansions (e.g. artist-rels, recording-rels, release-rels, labels) against the
mirror (or the fallback), and shall return the relationship data in a form HOSTCTX-016 consumes.
[HARD] These multi-include calls — expensive against the public API — are exactly why the mirror
exists; they run OFF the playout path (REQ-MB-003) and their results are cacheable with the
track record. The host-talk generation itself stays in HOSTCTX-016 (referenced).

**Acceptance criteria:** see acceptance.md AC-MB-006.

### REQ-MB-007 — Mirror/fallback result is cached + idempotent with the track record (Ubiquitous)

The system shall cache the mirror/fallback enrichment + rich-fact result with the existing
`Track` record (ANALYSIS-006 REQ-AD-001 / REQ-AE-002 idempotent-cache pattern) so a re-scan,
restart, or retry does not re-query the mirror for an unchanged track, and so HOSTCTX-016 can
read already-fetched facts without a fresh network call on the talk path. Cache invalidation
follows a schema/version bump or a changed file, mirroring ANALYSIS-006's caching.

**Acceptance criteria:** see acceptance.md AC-MB-007.

---

## 8. Requirement Group MX — Discogs / Last.fm Cross-Check & Provenance

Priority: Medium (MB / MM are the High-priority spine; cross-check is coverage enrichment).

### REQ-MX-001 — Discogs cross-check for credits/label coverage MusicBrainz lacks (Event-driven)

When MusicBrainz (mirror or fallback) lacks producer/engineer/personnel credits or
pressing/label detail for a release, the system shall OPTIONALLY query the Discogs API for that
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

## 9. Requirement Group MV — Volume, Sizing & Operations

Priority: Medium.

### REQ-MV-001 — Provision ~150 GB Hetzner volume for Variant A (Ubiquitous)

The system shall provision a Hetzner volume sized for the chosen variant — approximately
**150 GB for the recommended Variant A** (Postgres + Solr + web service, ~100–150 GB plus
headroom for replication growth), ~50–80 GB for Variant B (Postgres-only), or ~15–25 GB for
Variant C (selective import). The size figures are documented so the operator provisions with
headroom; the mirror SHALL NOT be provisioned so tight that replication growth fills the volume
(which would break sync — see REQ-MV-002).

**Acceptance criteria:** see acceptance.md AC-MV-001.

### REQ-MV-002 — Disk-headroom + replication-growth monitoring (State-driven) — Priority Medium

While the mirror runs, the system shall monitor volume free space and replication growth so the
operator is warned BEFORE the volume fills (a full volume halts replication and eventually the
web service). This monitoring lives with the mirror deployment; its summarized status feeds the
mirror health surface (REQ-MM-005). A volume-pressure or replication-halt condition on the
mirror shall trigger the brain's public-API fallback (REQ-MB-002), never a brain error.

**Acceptance criteria:** see acceptance.md AC-MV-002.

### REQ-MV-003 — Documented operator runbook (Ubiquitous) — Priority Low

The system shall be accompanied by an operator RUNBOOK documenting: initial provisioning + import,
configuring the replication token (as a secret, REQ-MM-004), enabling replication (REQ-MM-003),
pointing the brain at the mirror (`BRAIN_MB_MIRROR_HOST`, REQ-MB-001), the rebuild/resync path
(REQ-MM-006), and the variant trade-offs (REQ-MM-002). The runbook is documentation, NOT
provisioning automation (which is out of scope, Section 4.2); it ensures the mirror is operable
and recoverable by the user without reverse-engineering this SPEC.

**Acceptance criteria:** see acceptance.md AC-MV-003.

---

## 10. Exclusions (What NOT to Build)

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

## 11. Non-Functional Requirements

### NFR-M-1 — Never block on the mirror (Ubiquitous) — Priority High
No mirror or external-metadata interaction shall be on the sub-1s `/api/next` pull path or able
to stall the director/analysis-worker/daemon/stream; all enrichment runs off the playout path,
timeout-bounded, with fallback (REQ-MB-002/003). See acceptance.md AC-NFR-M-1.

### NFR-M-2 — Drop-in client, no schema coupling (Variant A) (Ubiquitous) — Priority High
For the recommended variant the brain shall change ONLY the host it points `musicbrainzngs` at;
the existing client calls shall work unchanged, with zero MusicBrainz-schema knowledge in the
brain (REQ-MB-001). See acceptance.md AC-NFR-M-2.

### NFR-M-3 — Secret safety (Ubiquitous) — Priority High
The replication token + any API keys shall live only in gitignored `secrets/`/env, never in the
repo, a SPEC, a config-template, or a log line (REQ-MM-004). See acceptance.md AC-NFR-M-3.

### NFR-M-4 — Resilience / graceful degradation (Ubiquitous) — Priority High
A mirror that is down, lagging, mid-(re)build, unreachable, or volume-pressured shall degrade to
the public-API fallback or graceful no-enrichment WITHOUT crashing the worker, the director, or
the daemon, and without silencing the stream (REQ-MB-002, REQ-MM-006, REQ-MV-002). See
acceptance.md AC-NFR-M-4.

### NFR-M-5 — Throughput (the mirror's reason to exist) (Ubiquitous) — Priority High
With the mirror configured, the brain shall enrich at materially higher throughput than the
public-API 1 req/s ceiling, so the ENRICH-012 whole-library id3 backfill and HOSTCTX-016
multi-include rich-fact lookups are practical at volume (REQ-MB-004/005/006). See acceptance.md
AC-NFR-M-5.

### NFR-M-6 — Per-field provenance + consensus integrity (Ubiquitous) — Priority High
Every enriched/cross-checked value shall carry its source provenance + consensus level; a
single-source value shall never be recorded as "confirmed"; the cross-check shall fold into the
EXISTING consensus, not a fork (REQ-MX-003/004). See acceptance.md AC-NFR-M-6.

### NFR-M-7 — Rate-limit compliance (Ubiquitous) — Priority Medium
The public-API fallback shall keep the 1 req/s MusicBrainz self-throttle; Discogs + Last.fm
shall respect their published rate limits; only the local mirror is high-throughput (and still
timeout + local-cap bounded) (REQ-MB-004, REQ-MX-005). See acceptance.md AC-NFR-M-7.

### NFR-M-8 — Simplicity / no over-engineering (Ubiquitous) — Priority Medium
This SPEC shall implement the smallest infra + client change that delivers volume + rich facts:
recommend Variant A so the brain change is a hostname; reuse the existing providers/consensus;
add one Discogs provider; no schema ORM, no new datastore, no provisioning-automation product.
Deferred items (Section 10) MUST NOT be partially built. See acceptance.md AC-NFR-M-8.

---

## 12. Open Questions / Risks

- **R-M-1 — Mirror variant choice (Low, RECOMMENDATION made).** Variant A (full
  `musicbrainz-docker`) is recommended for the zero-schema-coupling drop-in; B/C save disk at
  the cost of schema coupling + replication fragility. Mitigated by keeping the brain-facing
  contract identical across variants (REQ-MM-002 / REQ-MB-001) so the choice is reversible.
  **Needs the orchestrator's final ruling** (Section 13, D-1).
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

## 13. Design Decisions Needing the Orchestrator's Ruling

The following are surfaced for an explicit ruling before/at the Run phase (none block authoring
the SPEC; each has a recommended default this SPEC is written against):

- **D-1 — Mirror variant (RECOMMENDED: Variant A, full `musicbrainz-docker`).** The SPEC is
  written for Variant A (drop-in, no schema coupling). Confirm A, or elect B/C (which keeps the
  brain contract identical but adds a SQL/schema layer as an OPS detail). See R-M-1.
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

## 14. Out-of-Scope / Future SPEC Roadmap

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

## 15. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md;
detailed Given-When-Then scenarios for the load-bearing requirements are in acceptance.md
Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-MM-001 | Mirror Provisioning & Sync | High | Ubiquitous | AC-MM-001 |
| REQ-MM-002 | Mirror Provisioning & Sync | High | Ubiquitous | AC-MM-002 |
| REQ-MM-003 | Mirror Provisioning & Sync | High | Event/Self-scheduled | AC-MM-003 |
| REQ-MM-004 | Mirror Provisioning & Sync | High | Unwanted | AC-MM-004 |
| REQ-MM-005 | Mirror Provisioning & Sync | Medium | Ubiquitous | AC-MM-005 |
| REQ-MM-006 | Mirror Provisioning & Sync | Medium | State | AC-MM-006 |
| REQ-MB-001 | Brain Client Repoint & Fallback | High | Ubiquitous | AC-MB-001 |
| REQ-MB-002 | Brain Client Repoint & Fallback | High | Unwanted | AC-MB-002 |
| REQ-MB-003 | Brain Client Repoint & Fallback | High | Unwanted | AC-MB-003 |
| REQ-MB-004 | Brain Client Repoint & Fallback | High | State | AC-MB-004 |
| REQ-MB-005 | Brain Client Repoint & Fallback | High | Event | AC-MB-005 |
| REQ-MB-006 | Brain Client Repoint & Fallback | High | Event | AC-MB-006 |
| REQ-MB-007 | Brain Client Repoint & Fallback | Medium | Ubiquitous | AC-MB-007 |
| REQ-MX-001 | Cross-Check & Provenance | Medium | Event | AC-MX-001 |
| REQ-MX-002 | Cross-Check & Provenance | Medium | Event | AC-MX-002 |
| REQ-MX-003 | Cross-Check & Provenance | High | Ubiquitous | AC-MX-003 |
| REQ-MX-004 | Cross-Check & Provenance | High | Event | AC-MX-004 |
| REQ-MX-005 | Cross-Check & Provenance | High | State | AC-MX-005 |
| REQ-MX-006 | Cross-Check & Provenance | Medium | Ubiquitous | AC-MX-006 |
| REQ-MV-001 | Volume, Sizing & Operations | Medium | Ubiquitous | AC-MV-001 |
| REQ-MV-002 | Volume, Sizing & Operations | Medium | State | AC-MV-002 |
| REQ-MV-003 | Volume, Sizing & Operations | Low | Ubiquitous | AC-MV-003 |
| NFR-M-1 | Non-Functional | High | Ubiquitous | AC-NFR-M-1 |
| NFR-M-2 | Non-Functional | High | Ubiquitous | AC-NFR-M-2 |
| NFR-M-3 | Non-Functional | High | Ubiquitous | AC-NFR-M-3 |
| NFR-M-4 | Non-Functional | High | Ubiquitous | AC-NFR-M-4 |
| NFR-M-5 | Non-Functional | High | Ubiquitous | AC-NFR-M-5 |
| NFR-M-6 | Non-Functional | High | Ubiquitous | AC-NFR-M-6 |
| NFR-M-7 | Non-Functional | Medium | Ubiquitous | AC-NFR-M-7 |
| NFR-M-8 | Non-Functional | Medium | Ubiquitous | AC-NFR-M-8 |
