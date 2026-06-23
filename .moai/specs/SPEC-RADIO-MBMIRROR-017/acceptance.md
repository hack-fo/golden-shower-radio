---
id: SPEC-RADIO-MBMIRROR-017-acceptance
version: 0.2.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-MBMIRROR-017
---

# SPEC-RADIO-MBMIRROR-017 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR). Section B
carries detailed Given-When-Then scenarios for the load-bearing, never-block, and provenance/consensus
critical requirements. Section C is the Definition of Done and the quality gates.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where a
criterion is marked [HARD] it is a must-pass gate (no compensation by other criteria).

Group prefixes: MC (Default Path: Public API + Persistent Result Cache) / MB (Brain Client &
Graceful Degradation) / MX (Discogs/Last.fm Cross-Check & Provenance) / MM (OPTIONAL FUTURE Mirror
Provisioning & Replication Sync) / MV (OPTIONAL FUTURE Volume, Sizing & Operations).
27 AC + 9 AC-NFR = 36, matching spec.md 27 REQ + 9 NFR.

---

## Section A — Per-Requirement Acceptance

### Group MC — Default Path: Public API + Persistent Result Cache (build FIRST)

**AC-MC-001 (REQ-MC-001 — default access is the public MusicBrainz API at 1 req/s, no token):** [HARD]
- GIVEN the default configuration (no mirror host set), WHEN the brain accesses MusicBrainz, THEN it queries
  the PUBLIC `musicbrainz.org` web-service API through the existing `_provider_musicbrainz` at the <= 1 req/s
  self-throttle (`_mb_throttle`), requiring NO replication token and NO self-hosted infrastructure.
- [HARD] At the station's scale (~500 tracks), backed by the persistent cache (REQ-MC-002), call volume is a
  one-time ~500–1000-call backfill plus a trickle — well under 86,400 calls/day (asserted: the default path
  works with no token/mirror; the mirror is an optional upgrade, not a prerequisite).

**AC-MC-002 (REQ-MC-002 — persistent local result cache, cache-once / reuse-forever):** [HARD]
- GIVEN a successful MusicBrainz (or cross-check) enrichment result, WHEN it is produced, THEN it is persisted
  in a DURABLE local cache in the brain's DB (on the `Track` record / its idempotent-cache pattern,
  ANALYSIS-006 REQ-AD-001 / REQ-AE-002), reused forever across re-scans, restarts, and retries.
- [HARD] The cache survives brain and Icecast restarts and is the substrate that makes the 1 req/s default
  path viable at volume (asserted: a result fetched once is served from the cache after a restart with no
  new network call).

**AC-MC-003 (REQ-MC-003 — never re-fetch a cached track):** [HARD]
- GIVEN a track whose MusicBrainz result is already cached and still valid (not invalidated per REQ-MC-004),
  WHEN it is looked up again, THEN the system serves the cached result and issues NO new MusicBrainz network
  call.
- [HARD] Re-querying an unchanged, already-cached track is the waste this prevents and what keeps the 1 req/s
  default well within budget (asserted: a second lookup of an unchanged cached track issues zero network
  calls).

**AC-MC-004 (REQ-MC-004 — cache refresh / invalidation policy):**
- GIVEN a cached entry, WHEN it is held, THEN it is invalidated (and re-fetch allowed) only on a well-defined
  trigger — an enrichment schema/version bump, a changed underlying file, or an explicit operator-requested
  refresh — mirroring ANALYSIS-006's cache-invalidation discipline.
- Absent such a trigger the entry is durably valid (cache-once); the policy does NOT silently expire entries
  on a timer at this scale (asserted: only a defined trigger invalidates an entry; no timer-based expiry).

**AC-MC-005 (REQ-MC-005 — one cache serves ENRICH-012, HOSTCTX-016, and DEDUP-014):** [HARD wiring]
- GIVEN ENRICH-012 needing canonical-recording data, HOSTCTX-016 needing rich facts, or DEDUP-014 needing the
  canonical recording MBID, WHEN any of them looks up a track, THEN they are served from the ONE persistent
  cache (filled from the public API or the optional mirror on a miss) — fetched once, reused by all
  consumers.
- [HARD] MBMIRROR-017 supplies the cached access; the consumers' own logic (ENRICH-012 identification/write-
  back, HOSTCTX-016 talk, DEDUP-014 policy) stays in those SPECs (asserted: no consumer re-fetches what
  another already cached; no consumer logic is re-implemented here).

**AC-MC-006 (REQ-MC-006 — per-field cache provenance + fetched-at):** [HARD]
- GIVEN any cached value, WHEN it is recorded, THEN it carries WHICH source supplied it (public-MusicBrainz /
  mirror-MusicBrainz / Discogs / Last.fm / TheAudioDB / embedded / audio-hint), WHEN it was fetched, and the
  consensus level (Group MX).
- [HARD] A cached value with no recorded source/fetched-at is the defect this prevents; this is the cache-side
  face of REQ-MX-003, not a second store (asserted: every cached value has a source tag + fetched-at +
  consensus level; no provenance-less value is cached).

### Group MM — OPTIONAL FUTURE Mirror Provisioning & Replication Sync (deferred)

**AC-MM-001 (REQ-MM-001 — self-hosted MusicBrainz mirror on Hetzner):** [HARD when enabled]
- GIVEN the OPTIONAL mirror upgrade is enabled, WHEN the mirror runs, THEN it runs on the user's Hetzner Cloud
  instance (NOT on the local WSL2/Docker host) and, for Variant A, exposes the MusicBrainz WEB SERVICE over
  HTTP reachable by the brain.
- [HARD when enabled] The mirror is a SEPARATE deployment from the brain; the brain is a network client
  (asserted: a GET against the mirror's web-service base URL returns a MusicBrainz web-service response, and
  the mirror host is not `localhost`/the brain container). When the mirror is NOT enabled (the default), this
  is dormant and the brain uses the Group MC default path.

**AC-MM-002 (REQ-MM-002 — full `musicbrainz-docker`; slimmer variants documented):** (Optional)
- GIVEN the mirror is enabled and a variant must be chosen, WHEN documented, THEN the FULL `musicbrainz-docker`
  stack (Postgres + Solr + MB web service + replication) is the default among the mirror variants, and Variants
  B (Postgres-only) and C (selective import) are documented with their disk savings and schema-coupling /
  replication-fragility trade-offs.
- Whichever variant is chosen, the brain-facing contract is IDENTICAL (the `musicbrainzngs` HTTP API + the
  local cache + the public-API path, REQ-MB-001 / REQ-MC-002) — asserted: the brain code is unchanged across
  variants; the variant is an OPS choice behind the client seam.

**AC-MM-003 (REQ-MM-003 — replication-token keep-in-sync):** [HARD when enabled]
- GIVEN the mirror is enabled and initialized, WHEN the replication cadence elapses, THEN the standard
  `musicbrainz-docker` replication (mbslave) applies MetaBrainz live-data-feed REPLICATION PACKETS authorized
  by the token, so the mirror data tracks upstream over time without a manual full re-import.
- [HARD when enabled] The token is used ONLY by this optional path; the default Group MC path needs no token,
  so the token stays UNUSED until the mirror is adopted (asserted: after a replication cycle the mirror's
  last-replication timestamp advances; the default path runs with no token).

**AC-MM-004 (REQ-MM-004 — replication token, when used, is a gitignored secret, never in the repo):** [HARD]
- GIVEN the replication token (IF the mirror is enabled) and any Discogs/Last.fm API keys, WHEN stored, THEN
  they live ONLY in the gitignored `secrets/` tree or process environment on the deployment host.
- [HARD] They are NOT committed to version control, NOT written into any SPEC / config-template / documentation
  file, and NOT emitted in any log line or error message (asserted: a repo-wide grep for the token value
  returns nothing; logs/errors redact it; `secrets/` is gitignored). The default path has no token to leak.

**AC-MM-005 (REQ-MM-005 — mirror health + replication-lag observability):** (Optional)
- GIVEN the mirror is enabled and running, WHEN its status is queried, THEN it surfaces at least: reachable
  yes/no, last successful replication timestamp / lag, and web-service responsiveness.
- The brain-side reachability/degradation status surfaces through the CORE-001 health/status surface (OPS-004
  NFR-O-6), so a degradation decision is diagnosable after the fact. When the mirror is not enabled, this is
  dormant.

**AC-MM-006 (REQ-MM-006 — initial import + rebuild/resync posture):** (Optional)
- GIVEN the mirror is enabled and being provisioned or recovered, WHEN it is (re)built, THEN a bounded INITIAL
  IMPORT (upstream dump) and a documented REBUILD/RESYNC path (re-import + resume replication) are supported
  for the case where replication falls too far behind or the volume is lost.
- [HARD when enabled] While the mirror is not yet serving (initial import / rebuild), the brain operates on the
  default public-API + cache path (Group MC / REQ-MB-002) — a (re)building mirror never blocks enrichment or
  the stream.

### Group MB — Brain Client & Graceful Degradation

**AC-MB-001 (REQ-MB-001 — default endpoint = public API; config-gated optional mirror host):** [HARD]
- GIVEN the brain's default `musicbrainzngs` endpoint is the PUBLIC API, and a config-gated mirror host
  (`BRAIN_MB_MIRROR_HOST` → `config.musicbrainz_mirror_host`, with an optional `use_https`), WHEN the mirror
  host is SET, THEN the brain repoints its EXISTING client via `musicbrainzngs.set_hostname(host, use_https)`
  (accepting `host:port`) so the SAME `_provider_musicbrainz` / ENRICH-012 calls (`search_recordings`,
  `get_recording_by_id(includes=...)`) execute against whichever endpoint is configured, unchanged, behind the
  SAME cache; WHEN UNSET (the default), the brain uses the public API.
- [HARD] Pointing at a mirror is the only brain change to adopt it; there is NO MusicBrainz-schema coupling in
  the brain on either path (asserted: no SQL/ORM against the MB schema exists in `brain/`; only the hostname
  changes).

**AC-MB-002 (REQ-MB-002 — graceful degradation: cache → public API → empty):** [HARD]
- GIVEN a lookup, WHEN it misses the cache and the configured endpoint (public API by default, or the optional
  mirror if set) is unreachable, times out, returns an error, or (mirror only) is mid-(re)build, THEN the brain
  degrades gracefully — serving the cache when present, falling back to the public API when the optional mirror
  is the one failing, and returning gracefully empty (no enrichment for that track) when no source answers.
- [HARD] Any metadata-access problem degrades to slower-or-absent enrichment, NEVER an error that propagates, a
  stall, or dead air; the decision is per-call and bounded by `enrichment_http_timeout_seconds` (asserted by the
  Section B fallback scenario).

**AC-MB-003 (REQ-MB-003 — the brain NEVER blocks on metadata access):** [HARD — defining rail]
- GIVEN any metadata interaction (cache miss → public API, the optional mirror, or a cross-check) that is slow,
  queued, or hung, THEN it is NOT on the sub-1s `/api/next` pull path and does NOT stall the director loop, the
  analysis worker, or the daemon.
- [HARD] All enrichment runs OFF the playout path, bounded by timeout, and a track always plays whether or not
  its enrichment has completed (graceful degradation, inherited from ANALYSIS-006 REQ-AP-003 / REQ-AT-006 +
  CORE-001 continuous operation) — asserted by the Section B never-block scenario; this holds identically for
  the default public-API path and the optional mirror; this is the defining rail of the SPEC.

**AC-MB-004 (REQ-MB-004 — public API at 1 req/s; optional mirror unthrottled-but-bounded):** [HARD]
- GIVEN a MusicBrainz call, WHEN it targets the PUBLIC API (the default path), THEN the 1 req/s self-throttle
  (`_mb_throttle`) applies; WHEN it targets the OPTIONAL local MIRROR, THEN the 1 req/s public limit does NOT
  apply.
- [HARD] On the default path the 1 req/s throttle is not a bottleneck because the persistent cache (Group MC)
  reduces volume to a one-time backfill plus a trickle; the mirror path is still bounded by timeout AND a sane
  local concurrency/rate cap; the mirror cap + the public throttle are TUNABLE config (asserted: mirror calls
  bypass `_mb_throttle` but pass the local cap; public calls pass `_mb_throttle`).

**AC-MB-005 (REQ-MB-005 — ENRICH-012 enrichment routes through this seam + the cache):** [HARD wiring]
- GIVEN ENRICH-012 identifying/correcting a track's canonical recording, WHEN it makes MusicBrainz calls, THEN
  they route through the Group MB client seam and the Group MC cache — serving the cache on a hit, and on a miss
  using the public API by default (or the optional mirror if configured), then caching the result — so the
  whole-library id3 sanitization is a one-time cached backfill and each new download is a single cached lookup,
  within the 1 req/s budget.
- [HARD] MBMIRROR-017 changes ONLY where the MusicBrainz bytes come from and that they are cached; the
  ENRICH-012 identification, confidence-threshold, and write-back logic are unchanged (asserted: no ENRICH-012
  identification/write-back logic is re-implemented here; ENRICH-012 calls resolve via the seam + cache).

**AC-MB-006 (REQ-MB-006 — HOSTCTX-016 rich-fact lookups route through this seam + cache with includes):**
- GIVEN HOSTCTX-016 requesting rich facts (first-release year, album/release, producer, engineer + credited
  personnel, record label(s), release-group relationships), WHEN they are fetched, THEN they go via the Group MB
  seam and the Group MC cache using the appropriate `musicbrainzngs` `includes=` expansions (e.g. artist-rels,
  recording-rels, release-rels, labels) against the public API by default (or the optional mirror), returned in
  a form HOSTCTX-016 consumes.
- [HARD] These multi-include calls run OFF the playout path (REQ-MB-003) and their results are CACHED
  (REQ-MC-002) so each track's rich facts are fetched once and the per-talk-break path reads the cache; the
  host-talk generation stays in HOSTCTX-016 (asserted: the include expansions are issued through the seam, are
  cached, and no host-talk generation is implemented here).

### Group MX — Discogs / Last.fm Cross-Check & Provenance

**AC-MX-001 (REQ-MX-001 — Discogs cross-check for credits/label coverage MusicBrainz lacks):**
- GIVEN MusicBrainz (public API by default, or the optional mirror) lacking producer/engineer/personnel
  credits or pressing/label detail, WHEN cross-check runs, THEN a NEW Discogs provider (alongside
  MusicBrainz/TheAudioDB/Last.fm in
  `brain/metadata.py`) is OPTIONALLY queried for that coverage, config-gated by a Discogs token.
- [HARD] Absent the token, the provider is DISABLED, logs-once, and returns empty (exactly like the existing
  Last.fm provider); Discogs is COVERAGE for fields MusicBrainz lacks, not a mirror replacement (asserted:
  no token → provider dormant, no error).

**AC-MX-002 (REQ-MX-002 — Last.fm cross-check reuses the existing provider for corroboration):**
- GIVEN genre/mood/tag corroboration or crowd context, WHEN cross-check runs, THEN the EXISTING
  `_provider_lastfm` (`brain/metadata.py`, already optional/config-gated/log-once) is REUSED as a
  cross-check/corroboration source — NOT a second Last.fm client.
- MBMIRROR-017 does not re-own Last.fm; it ensures Last.fm corroboration feeds the SAME consensus as the
  new Discogs coverage (asserted: no duplicate Last.fm client is added).

**AC-MX-003 (REQ-MX-003 — per-field provenance on every cross-checked value):** [HARD]
- GIVEN any enriched or cross-checked value, WHEN it is recorded, THEN per supplied field the system
  records WHICH source provided it — mirror-MusicBrainz / public-MusicBrainz / Discogs / Last.fm /
  TheAudioDB / embedded / audio-hint — and the resulting consensus level, persisted on the `Track` record
  (ANALYSIS-006 REQ-AD-001).
- [HARD] A value with no recorded provenance is the defect this prevents (asserted: every cross-checked
  field on the `Track` record carries a source tag + consensus level; no provenance-less value is stored).

**AC-MX-004 (REQ-MX-004 — cross-check folds into the inherited consensus, never asserts single-source as certain):** [HARD]
- GIVEN more than one source (now including Discogs) supplying a value for the same field, WHEN it is
  reconciled, THEN it goes through the EXISTING ANALYSIS-006 REQ-AM-003 consensus discipline
  (`brain/metadata.py` `consensus()`): authoritative MusicBrainz outranks crowd folksonomy
  (Discogs/Last.fm/TheAudioDB) which outranks embedded/audio-hints.
- [HARD] A value is recorded "confirmed" only on multi-source consensus (or one authoritative source);
  single-source / low-consensus values are FLAGGED "candidate", NEVER stated as certain; MBMIRROR-017 ADDS
  Discogs into the existing precedence + threshold (its base confidence + precedence rank are TUNABLE
  config) and does NOT fork the algorithm (asserted by the Section B consensus scenario).

**AC-MX-005 (REQ-MX-005 — cross-check is rate-limited and off the playout path):** [HARD]
- GIVEN cross-checking, WHEN it runs, THEN it respects each external source's published RATE LIMITS
  (Discogs + Last.fm their own; the local mirror does not throttle; the public-API fallback keeps 1 req/s),
  bounds each call by the configured timeout, and runs strictly OFF the playout path and downstream of
  acquisition (coordinating with OPS-004 REQ-OH-006 so a download burst + cross-check do not jointly
  overload the box).
- [HARD] A cross-check that is slow, rate-limited, or failing degrades to no-coverage for that field, never
  to a block (asserted: a failing/rate-limited cross-check yields an absent field, not an error/stall).

**AC-MX-006 (REQ-MX-006 — artist-fact boundary to KNOWLEDGE-008):**
- GIVEN the cross-check, WHEN it runs, THEN it is scoped to RELEASE/RECORDING-level credits (producer,
  engineer, personnel, label-on-this-release, year, release relationships).
- Where Discogs/Last.fm surface ARTIST-LEVEL facts (label history, scene, biography, lineage), those belong
  to SPEC-RADIO-KNOWLEDGE-008's dated/sourced fact store and consensus — MBMIRROR-017 references that
  ownership and does NOT record artist facts as a second parallel store (asserted: no artist-fact store is
  created here).

### Group MV — OPTIONAL FUTURE Volume, Sizing & Operations (deferred)

**AC-MV-001 (REQ-MV-001 — provision ~150 GB Hetzner volume for Variant A):** (Optional)
- GIVEN the OPTIONAL mirror upgrade is enabled and a variant is chosen, WHEN the volume is provisioned, THEN it
  is sized accordingly — ~150 GB for Variant A (Postgres + Solr + web service, ~100–150 GB plus headroom),
  ~50–80 GB for Variant B (Postgres-only), or ~15–25 GB for Variant C (selective import) — documented so the
  operator provisions with headroom.
- The mirror is NOT provisioned so tight that replication growth fills the volume and breaks sync (ties
  REQ-MV-002). When the mirror is not enabled (the default), there is no volume to provision.

**AC-MV-002 (REQ-MV-002 — disk-headroom + replication-growth monitoring):** (Optional)
- GIVEN the mirror is enabled and running, WHEN volume free space and replication growth are monitored, THEN the
  operator is warned BEFORE the volume fills (a full volume halts replication and eventually the web service);
  the summarized status feeds the mirror health surface (REQ-MM-005).
- [HARD when enabled] A volume-pressure or replication-halt condition on the mirror triggers the brain's default
  public-API + cache path (REQ-MB-002 / Group MC), NEVER a brain error (asserted: mirror unavailability from
  disk pressure degrades to the default path, not a crash).

**AC-MV-003 (REQ-MV-003 — documented operator runbook for the optional mirror):** (Optional)
- GIVEN the mirror upgrade is adopted, WHEN the deliverable is produced, THEN an operator RUNBOOK documents:
  initial provisioning + import, configuring the replication token as a secret (REQ-MM-004), enabling
  replication (REQ-MM-003), pointing the brain at the mirror (`BRAIN_MB_MIRROR_HOST`, REQ-MB-001), the
  rebuild/resync path (REQ-MM-006), and the variant trade-offs (REQ-MM-002).
- The runbook is documentation, NOT provisioning automation (out of scope); it ensures the mirror is operable +
  recoverable without reverse-engineering the SPEC (asserted: the runbook file exists and covers each named
  step). The default path needs no runbook beyond setting the cache on.

---

## Section A (cont.) — Non-Functional Acceptance

**AC-NFR-M-1 (NFR-M-1 — never block on metadata access):** [HARD] No metadata interaction (cache miss →
public API, the optional mirror, or a cross-check) is on the sub-1s `/api/next` pull path or able to stall
the director / analysis-worker / daemon / stream; all enrichment runs off the playout path, timeout-bounded,
with graceful degradation (asserted: enrichment processing runs off the playout path; ties REQ-MB-002/003).

**AC-NFR-M-2 (NFR-M-2 — drop-in client, no schema coupling):** [HARD] The brain talks the same `musicbrainzngs`
HTTP API on the default public-API path; adopting the optional mirror changes ONLY the host it points at, with
existing client calls unchanged and ZERO MusicBrainz-schema knowledge in the brain on either path (asserted: no
SQL/ORM against the MB schema in `brain/`; ties REQ-MB-001).

**AC-NFR-M-3 (NFR-M-3 — secret safety):** [HARD] Any Discogs/Last.fm API keys — and the MetaBrainz replication
token IF the optional mirror is enabled — live only in gitignored `secrets/`/env, never in the repo, a SPEC, a
config-template, or a log line; the default path needs no token (asserted: repo-wide grep finds no token value;
logs redact; ties REQ-MM-004).

**AC-NFR-M-4 (NFR-M-4 — resilience / graceful degradation):** [HARD] A failing endpoint — the public API being
slow/down, or (when enabled) a mirror that is down, lagging, mid-(re)build, unreachable, or volume-pressured —
degrades to the cache, the public-API path, or graceful no-enrichment WITHOUT crashing the worker / director /
daemon and without silencing the stream (ties REQ-MB-002, REQ-MC-002, REQ-MM-006, REQ-MV-002).

**AC-NFR-M-5 (NFR-M-5 — throughput via cache: 1 req/s + cache is sufficient at scale):** [HARD] The DEFAULT path
(public API at 1 req/s + the persistent cache) makes the ENRICH-012 whole-library id3 backfill and HOSTCTX-016
multi-include rich-fact lookups practical at the station's scale: cache-once / reuse-forever turns the workload
into a one-time ~500–1000-call backfill plus a trickle — <1% of the 86,400 calls/day the 1/sec limit allows;
higher raw throughput is available via the optional mirror but is NOT required (asserted: cached tracks issue no
new calls; default path completes the backfill within budget; ties REQ-MC-001/002/003, REQ-MB-004/005/006).

**AC-NFR-M-6 (NFR-M-6 — per-field provenance + consensus integrity):** [HARD] Every enriched/cross-checked/cached
value carries its source provenance + consensus level; a single-source value is NEVER recorded "confirmed";
the cross-check folds into the EXISTING consensus, not a fork (ties REQ-MX-003/004, REQ-MC-006).

**AC-NFR-M-7 (NFR-M-7 — rate-limit compliance):** The default public-API path (and any public-API fallback) keeps
the 1 req/s MusicBrainz self-throttle; Discogs + Last.fm respect their published rate limits; only the optional
local mirror is high-throughput (and still timeout + local-cap bounded) (ties REQ-MB-004, REQ-MX-005).

**AC-NFR-M-8 (NFR-M-8 — simplicity / no over-engineering):** The implementation is the smallest change delivering
accurate metadata + rich facts: the DEFAULT is public API + a persistent cache (no token, no mirror infra); reuse
of the existing providers/consensus; one Discogs provider added; no schema ORM, no new datastore, no
provisioning-automation product; the mirror stays a deferred optional upgrade. Deferred items (spec.md Section 11)
are NOT partially built (asserted: the default-path diff adds a persistent cache + config + one Discogs provider,
nothing in the excluded set; the mirror is not stood up by default).

**AC-NFR-M-9 (NFR-M-9 — cache durability / persistence):** [HARD] The persistent local result cache (Group MC) is
durable in the brain's DB — surviving brain and Icecast restarts — so a track enriched once is never re-fetched
and the default 1 req/s path stays within budget across the station's lifetime; the cache is load-bearing, not a
transient in-memory optimization (asserted: after a restart, cached results are served with no new network call;
ties REQ-MC-002/003).

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing / never-block / provenance-critical)

### B0 — Default path: cache-once / reuse-forever makes 1 req/s sufficient (REQ-MC-001/002/003, NFR-M-5, NFR-M-9) [HARD]

```
GIVEN the DEFAULT configuration (no mirror host set; no replication token)
WHEN ENRICH-012 runs the whole-library id3 backfill over ~500 tracks
THEN each uncached track is fetched once from the public MusicBrainz API at <= 1 req/s and the result is
     written to the PERSISTENT cache in the brain's DB
  AND a track already cached and still valid issues ZERO new MusicBrainz network calls
  AND the total backfill is a one-time ~500-1000 calls (~10-20 min at 1/sec) - well under 86,400 calls/day
WHEN the brain (and/or Icecast) restarts and the same tracks are looked up again
THEN every result is served from the durable cache with NO new network call
WHEN HOSTCTX-016 and DEDUP-014 later need the same track's facts / MBID
THEN they are served from the SAME one cache, never re-fetched per consumer (REQ-MC-005)
```
Verification: assert cached tracks issue no network call; assert the cache survives a restart; assert one
cache serves all consumers; assert the default path needs no token/mirror (the load-bearing v0.2.0 idea).

### B1 — The brain NEVER blocks on metadata access (REQ-MB-003, NFR-M-1, NFR-M-4) [HARD — defining rail]

```
GIVEN the default public-API path (or, when enabled, the optional mirror) becomes slow / unreachable / hung
WHEN ENRICH-012 enrichment or a HOSTCTX-016 rich-fact lookup is requested for a track
THEN the lookup runs OFF the playout path, bounded by enrichment_http_timeout_seconds
  AND it is NOT on the sub-1s /api/next pull path and does NOT stall the director loop, the analysis
      worker, or the daemon
  AND the track plays regardless of whether its enrichment completed (graceful degradation)
  AND the stream never goes to dead air because of a metadata-access problem
```
Verification: assert no metadata call exists on the `/api/next` path; assert enrichment runs in an off-path
worker bounded by timeout; assert a hung endpoint produces a played track with cached-or-absent enrichment,
never a stall (the defining rail; holds for the default path and the optional mirror; addresses R-M-4).

### B2 — Graceful degradation: cache → public API → empty (REQ-MB-002, REQ-MC-002, REQ-MM-006, REQ-MV-002) [HARD]

```
GIVEN a MusicBrainz lookup
WHEN it misses the cache AND the configured endpoint fails: the public API is slow/down/errored, OR (mirror
     only, when enabled) the mirror is unset/unreachable/timed-out/errored/mid-(re)build/volume-pressured
THEN the brain serves the cached result if present
  AND when the optional mirror is the one failing, it falls back to the public MusicBrainz API at 1 req/s
  AND if no source answers, the brain returns gracefully empty (no enrichment for that track)
  AND no error propagates, no stall occurs, the stream is unaffected
  AND the decision is per-call and timeout-bounded (enrichment_http_timeout_seconds)
```
Verification: assert each failure mode independently degrades to cache → public-API → graceful-empty; assert
no failure mode raises to the caller (addresses R-M-3, R-M-4).

### B3 — Default = public API; optional mirror = hostname-only repoint, no schema coupling (REQ-MB-001, NFR-M-2) [HARD]

```
GIVEN BRAIN_MB_MIRROR_HOST is UNSET (empty) — the DEFAULT
WHEN the brain initializes the musicbrainzngs client
THEN it uses the public MusicBrainz API (no token, no mirror), behind the persistent cache
GIVEN BRAIN_MB_MIRROR_HOST is SET (with use_https per the deployment) — the optional upgrade
WHEN the brain initializes the musicbrainzngs client
THEN it calls musicbrainzngs.set_hostname(host, use_https) (accepting host:port) to repoint the EXISTING
     client at the mirror, behind the SAME cache
  AND the same _provider_musicbrainz / ENRICH-012 calls (search_recordings, get_recording_by_id(includes=...))
      execute UNCHANGED against whichever endpoint is configured
  AND in BOTH cases there is NO SQL/ORM against the MusicBrainz schema anywhere in brain/
```
Verification: assert the default is the public API with no mirror/token; assert the only mirror-adoption brain
change is the hostname (set via `set_hostname`); assert no MB-schema coupling exists; assert the variant choice
(A/B/C) does not change the brain code (addresses R-M-1, R-M-6).

### B4 — Public API at 1 req/s + cache; optional mirror unthrottled-but-bounded (REQ-MB-004, REQ-MB-005, REQ-MC-003, NFR-M-5, NFR-M-7) [HARD]

```
GIVEN an ENRICH-012 whole-library id3 backfill over ~500 tracks routed through the Group MB seam + MC cache
WHEN the DEFAULT public API is the endpoint
THEN public calls obey the 1 req/s _mb_throttle (MetaBrainz politeness preserved)
  AND cached tracks issue no call at all, so the backfill is a one-time ~500-1000 calls within budget
WHEN the optional mirror is instead configured
THEN mirror-targeted calls are NOT subject to the 1 req/s _mb_throttle (volume is the point)
  AND mirror-targeted calls ARE still bounded by the configured timeout AND a sane local concurrency/rate cap
  AND the mirror cap + the public throttle are tunable config
  AND in BOTH cases the ENRICH-012 identification / confidence-threshold / write-back logic is unchanged
      (only the endpoint changed; results are cached either way)
```
Verification: assert public calls pass `_mb_throttle` and cached tracks issue none; assert mirror calls bypass
`_mb_throttle` but pass the local cap; assert no ENRICH-012 logic is re-implemented in MBMIRROR-017 (the
cache-makes-1req/s-sufficient rationale, NFR-M-5).

### B5 — Cross-check folds into consensus; single-source never "confirmed" (REQ-MX-004, REQ-MX-003, NFR-M-6) [HARD]

```
GIVEN a field (e.g. producer) supplied by Discogs only, and another field (e.g. release year) supplied by
      both MusicBrainz (public API or mirror) and Discogs
WHEN the values are reconciled
THEN reconciliation goes through the EXISTING ANALYSIS-006 REQ-AM-003 consensus() — authoritative
     MusicBrainz outranks crowd folksonomy (Discogs/Last.fm/TheAudioDB) outranks embedded/audio-hints
  AND the Discogs-only producer is recorded "candidate" (single-source), FLAGGED, NEVER stated as certain
  AND the multi-source / authoritative-MusicBrainz year is recorded "confirmed"
  AND every supplied field carries per-field provenance (which source) + the consensus level on the Track
      record (REQ-MX-003)
  AND Discogs's base confidence + precedence rank are read from tunable config; the algorithm is NOT forked
```
Verification: assert single-source values are never "confirmed"; assert provenance + consensus level are
persisted per field; assert MBMIRROR-017 adds Discogs into the existing precedence + threshold rather than
restating `consensus()` (provenance/consensus integrity, NFR-M-6).

### B6 — Cross-check is rate-limited, optional, and degrades to no-coverage (REQ-MX-005, REQ-MX-001, NFR-M-7) [HARD]

```
GIVEN cross-check enabled (Discogs token present) and a field MusicBrainz lacks
WHEN Discogs/Last.fm are queried
THEN each external source's published rate limits are respected (the local mirror does not throttle; the
     public-API fallback keeps 1 req/s)
  AND each call is timeout-bounded and runs strictly OFF the playout path, downstream of acquisition
      (coordinating with OPS-004 REQ-OH-006 so a download burst + cross-check do not jointly overload the box)
GIVEN the Discogs token is ABSENT
THEN the Discogs provider is disabled, logs once, returns empty (like the existing Last.fm provider)
GIVEN a cross-check is slow / rate-limited / failing
THEN it degrades to no-coverage for that field, never to a block or an error
```
Verification: assert rate-limit compliance per source; assert absent-token dormancy with a single log line;
assert a failing cross-check yields an absent field, not a stall (addresses R-M-7).

### B7 — Secret safety: the replication token never leaks (REQ-MM-004, NFR-M-3) [HARD]

```
GIVEN the MetaBrainz replication token (and any Discogs/Last.fm key)
WHEN the mirror syncs and the brain runs
THEN the token lives ONLY in the gitignored secrets/ tree or process environment on the deployment host
  AND it appears in NO committed file (no SPEC, no config-template, no documentation)
  AND it appears in NO log line or error message (redacted)
  AND a repo-wide search for the token value returns nothing
```
Verification: assert `secrets/` is gitignored; assert a grep for the token value across the repo is empty;
assert logging/error paths redact secrets (the leak this requirement prevents).

### B8 — Optional mirror variant is an OPS decision behind a stable client seam (REQ-MM-002, REQ-MM-001, NFR-M-8)

```
GIVEN the default path is public API + cache, AND IF the optional mirror is adopted the operator may choose
      Variant A (full musicbrainz-docker), B (Postgres-only), or C (selective import)
WHEN the brain queries MusicBrainz
THEN the brain-facing contract is IDENTICAL whether the endpoint is the public API or any mirror variant:
     the musicbrainzngs HTTP API + the same persistent cache (Group MC)
  AND the brain code does not change when the variant changes (the SQL layer for B/C is an OPS detail behind
      the same client contract, not a brain product)
  AND Variant A is the recommended mirror upgrade for zero schema coupling + the smallest brain change
```
Verification: assert the brain client seam is endpoint- and variant-agnostic; assert no brain-owned MB-schema
product exists; assert the default path needs no mirror and the recommendation + documented trade-offs are
present for the optional upgrade (addresses R-M-1; simplicity NFR-M-8).

---

## Section C — Definition of Done & Quality Gates

An MBMIRROR-017 implementation is DONE when:

1. [HARD] All 27 REQ + 9 NFR Section A entries pass, and all Section B scenarios pass.
2. [HARD] **Default path: public API + persistent cache makes 1 req/s sufficient (REQ-MC-001/002/003/005,
   NFR-M-5/M-9, the load-bearing v0.2.0 idea):** the default needs no token/mirror; the backfill is a one-time
   ~500–1000-call crawl; cached tracks issue no new calls; the cache is durable across restarts; one cache
   serves ENRICH-012 + HOSTCTX-016 + DEDUP-014 (B0).
3. [HARD] **The brain NEVER blocks on metadata access (REQ-MB-003, NFR-M-1, the defining rail):** no metadata
   call is on the `/api/next` pull path; all enrichment runs off-path, timeout-bounded; a track always plays;
   the stream never goes dead air for a metadata-access problem (B1).
4. [HARD] **Graceful degradation: cache → public API → empty (REQ-MB-002, NFR-M-4):** a slow/down public API,
   or (when the mirror is enabled) unset / unreachable / timeout / error / rebuilding / volume-pressured, all
   degrade to cache → public-API → graceful-empty; no failure propagates (B2).
5. [HARD] **Default = public API; optional mirror = hostname-only, no schema coupling (REQ-MB-001, NFR-M-2):**
   unset → public API + cache (the default); the only mirror-adoption brain change is `set_hostname(host,
   use_https)`; no MB-schema SQL/ORM in `brain/` on either path (B3).
6. [HARD] **Public API at 1 req/s + cache; optional mirror unthrottled-but-bounded (REQ-MB-004, NFR-M-5/M-7):**
   public calls keep 1 req/s and cached tracks issue none; mirror calls (if enabled) bypass `_mb_throttle` but
   obey timeout + local cap (B4).
7. [HARD] **ENRICH-012 routes through the seam + cache unchanged (REQ-MB-005):** only the MusicBrainz endpoint
   changes (and results are cached); ENRICH-012 identification / confidence / write-back logic is referenced,
   not re-owned (B4).
8. **HOSTCTX-016 rich-fact include-expansion lookups route through the seam + cache, off-path (REQ-MB-006,
   REQ-MC-002):** multi-include calls run off the playout path; results cache durably so the talk path reads
   the cache.
9. [HARD] **Per-field provenance + consensus integrity (REQ-MX-003/004, REQ-MC-006, NFR-M-6):** every enriched/
   cross-checked/cached value carries source provenance + consensus level; single-source values are never
   "confirmed"; the cross-check folds into the EXISTING `consensus()`, not a fork (B5).
10. [HARD] **Cross-check is rate-limited, optional, off-path (REQ-MX-001/005, NFR-M-7):** Discogs/Last.fm obey
    published rate limits + timeout, run off the playout path downstream of acquisition; absent-token →
    dormant; a failing cross-check degrades to no-coverage, never a block (B6).
11. **Last.fm reused, not re-owned; artist-fact boundary to KNOWLEDGE-008 (REQ-MX-002/006):** no second
    Last.fm client; only release/recording credits are surfaced; no parallel artist-fact store.
12. [HARD] **Secret safety (REQ-MM-004, NFR-M-3):** any Discogs/Last.fm keys — and the replication token IF the
    optional mirror is enabled — live only in gitignored `secrets/`/env; never committed, never in a
    SPEC/template/doc, never logged; the default path has no token to leak (B7).
13. **OPTIONAL mirror (deferred) is correct WHEN enabled (REQ-MM-001/002/003/005/006, REQ-MV-001/002/003,
    NFR-M-8):** where adopted, the mirror runs on Hetzner (not local) as a separate deployment with replication
    enabled, Variant A recommended with B/C documented, the brain contract identical across variants (B8),
    initial-import / rebuild-resync posture + health/lag observability present, ~150 GB sizing + headroom
    monitoring + an operator runbook; while (re)building or volume-pressured the brain runs the default
    public-API + cache path; the mirror is NOT stood up by default.
14. [HARD] **Single-source-of-truth / no fork (NFR-M-8 + dependency rails):** the ENRICH-012 logic, the
    ANALYSIS-006 `consensus()` + `Track` provenance fields, the KNOWLEDGE-008 artist-fact store, the OPS-004
    source list + acquisition throttle, and the CORE-001 continuous-operation rail are referenced by id,
    never re-owned; brain-only + additive (a persistent cache + config + one Discogs provider, plus the
    optional host setter + runbook if the mirror is adopted); no new service, no schema ORM.

Quality gates (TRUST 5, inherited): Tested (the cache/default-path B0, the never-block B1, the degradation B2,
the no-schema-coupling B3, the throttle+cache B4, the consensus/provenance B5, and the secret-safety B7 are the
must-pass characterization tests); Readable; Unified; Secured (the gitignored-secret discipline + redacted
logging + rate-limit compliance +, if the optional mirror is enabled, the private/firewalled mirror posture);
Trackable (per-field provenance + consensus level + fetched-at on the cache/`Track` record give an auditable
origin for every enriched value).

Parity check: 27 AC (Section A) + 9 AC-NFR = 36 acceptance entries, matching spec.md 27 REQ + 9 NFR; 1:1
REQ↔AC preserved.
