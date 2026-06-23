---
id: SPEC-RADIO-MBMIRROR-017-acceptance
version: 0.1.0
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

Group prefixes: MM (Mirror Provisioning & Replication Sync) / MB (Brain Client Repoint & Fallback) /
MX (Discogs/Last.fm Cross-Check & Provenance) / MV (Volume, Sizing & Operations).
22 AC + 8 AC-NFR = 30, matching spec.md 22 REQ + 8 NFR.

---

## Section A — Per-Requirement Acceptance

### Group MM — Mirror Provisioning & Replication Sync

**AC-MM-001 (REQ-MM-001 — self-hosted MusicBrainz mirror on Hetzner):** [HARD]
- GIVEN the deployment, WHEN the mirror runs, THEN it runs on the user's Hetzner Cloud instance (NOT on
  the local WSL2/Docker host) and, for the recommended Variant A, exposes the MusicBrainz WEB SERVICE
  over HTTP reachable by the brain.
- [HARD] The mirror is a SEPARATE deployment from the brain; the brain is a network client (asserted: a
  GET against the mirror's web-service base URL returns a MusicBrainz web-service response, and the mirror
  host is not `localhost`/the brain container).

**AC-MM-002 (REQ-MM-002 — recommended full `musicbrainz-docker`; slimmer variants documented):**
- GIVEN the deployment choice, WHEN documented, THEN the FULL `musicbrainz-docker` stack (Postgres + Solr
  + MB web service + replication) is the default, and Variants B (Postgres-only) and C (selective import)
  are documented with their disk savings and schema-coupling / replication-fragility trade-offs.
- [HARD] Whichever variant is chosen, the brain-facing contract is IDENTICAL (the `musicbrainzngs` HTTP
  API + the public-API fallback, REQ-MB-001) — asserted: the brain code is unchanged across variants; the
  variant is an OPS choice behind the client seam.

**AC-MM-003 (REQ-MM-003 — replication-token keep-in-sync):** [HARD]
- GIVEN an initialized mirror, WHEN the replication cadence elapses, THEN the standard `musicbrainz-docker`
  replication (mbslave) applies MetaBrainz live-data-feed REPLICATION PACKETS authorized by the token, so
  the mirror data tracks upstream over time without a manual full re-import.
- [HARD] Replication is ENABLED and the token configured (asserted: after a replication cycle, the mirror's
  last-replication timestamp advances; no manual full re-import is required for incremental currency).

**AC-MM-004 (REQ-MM-004 — replication token is a gitignored secret, never in the repo):** [HARD]
- GIVEN the replication token (and any Discogs/Last.fm API keys), WHEN stored, THEN they live ONLY in the
  gitignored `secrets/` tree or process environment on the deployment host.
- [HARD] The token is NOT committed to version control, NOT written into any SPEC / config-template /
  documentation file, and NOT emitted in any log line or error message (asserted: a repo-wide grep for the
  token value returns nothing; logs/errors redact it; `secrets/` is gitignored).

**AC-MM-005 (REQ-MM-005 — mirror health + replication-lag observability):**
- GIVEN the running mirror, WHEN its status is queried, THEN it surfaces at least: reachable yes/no, last
  successful replication timestamp / lag, and web-service responsiveness.
- The brain-side reachability/fallback status surfaces through the CORE-001 health/status surface (OPS-004
  NFR-O-6), so a fallback decision is diagnosable after the fact.

**AC-MM-006 (REQ-MM-006 — initial import + rebuild/resync posture):**
- GIVEN provisioning or recovery, WHEN the mirror is (re)built, THEN a bounded INITIAL IMPORT (upstream
  dump) and a documented REBUILD/RESYNC path (re-import + resume replication) are supported for the case
  where replication falls too far behind or the volume is lost.
- [HARD] While the mirror is not yet serving (initial import / rebuild), the brain operates on the
  public-API fallback (REQ-MB-002) — a (re)building mirror never blocks enrichment or the stream.

### Group MB — Brain Client Repoint & Fallback

**AC-MB-001 (REQ-MB-001 — config-gated mirror host, repointing the existing client):** [HARD]
- GIVEN a config-gated mirror host (`BRAIN_MB_MIRROR_HOST` → `config.musicbrainz_mirror_host`, with an
  optional `use_https`), WHEN it is SET, THEN the brain repoints its EXISTING `musicbrainzngs` client via
  `musicbrainzngs.set_hostname(host, use_https)` (accepting `host:port`) so the SAME
  `_provider_musicbrainz` / ENRICH-012 calls (`search_recordings`, `get_recording_by_id(includes=...)`)
  execute against the local web service unchanged; WHEN UNSET (empty), the brain uses the public API
  exactly as today.
- [HARD] This is the ONLY brain change required for Variant A; there is NO MusicBrainz-schema coupling in
  the brain (asserted: no SQL/ORM against the MB schema exists in `brain/`; only the hostname changes).

**AC-MB-002 (REQ-MB-002 — automatic public-API fallback on any mirror failure):** [HARD]
- GIVEN a lookup, WHEN the mirror is unset, unreachable, times out, returns an error, or is mid-(re)build,
  THEN the brain AUTOMATICALLY falls back to the public MusicBrainz API (at the 1 req/s self-throttle) for
  that lookup; and if the public API also fails, returns gracefully empty (no enrichment for that track).
- [HARD] A mirror problem degrades to slower-or-absent enrichment, NEVER an error that propagates, a stall,
  or dead air; the fallback decision is per-call and bounded by `enrichment_http_timeout_seconds`
  (asserted by the Section B fallback scenario).

**AC-MB-003 (REQ-MB-003 — the brain NEVER blocks on the mirror):** [HARD — defining rail]
- GIVEN any mirror or external-metadata interaction that is slow, queued, or hung, THEN it is NOT on the
  sub-1s `/api/next` pull path and does NOT stall the director loop, the analysis worker, or the daemon.
- [HARD] All enrichment (mirror or fallback) runs OFF the playout path, bounded by timeout, and a track
  always plays whether or not its enrichment has completed (graceful degradation, inherited from
  ANALYSIS-006 REQ-AP-003 / REQ-AT-006 + CORE-001 continuous operation) — asserted by the Section B
  never-block scenario; this is the defining rail of the SPEC.

**AC-MB-004 (REQ-MB-004 — mirror unthrottled-but-bounded, public-API at 1 req/s):** [HARD]
- GIVEN a MusicBrainz call, WHEN it targets the PUBLIC API, THEN the 1 req/s self-throttle (`_mb_throttle`)
  applies; WHEN it targets the local MIRROR, THEN the 1 req/s public limit does NOT apply.
- [HARD] The mirror path is still bounded by the configured timeout AND a sane local concurrency/rate cap
  so a runaway backfill cannot saturate the mirror or the brain; the mirror cap + the public-API throttle
  are TUNABLE config (asserted: mirror calls bypass `_mb_throttle` but pass through the local cap; public
  calls pass through `_mb_throttle`).

**AC-MB-005 (REQ-MB-005 — ENRICH-012 enrichment at volume routes through this seam):** [HARD wiring]
- GIVEN ENRICH-012 identifying/correcting a track's canonical recording, WHEN it makes MusicBrainz calls,
  THEN they route through the Group MB client seam — the mirror when configured (fast, unthrottled-but-
  bounded), the public-API fallback otherwise — so the whole-library id3 backfill and every new download
  proceed at volume without the 1 req/s ceiling.
- [HARD] MBMIRROR-017 changes ONLY where the MusicBrainz bytes come from; the ENRICH-012 identification,
  confidence-threshold, and write-back logic are unchanged (asserted: no ENRICH-012 identification/write-back
  logic is re-implemented here; ENRICH-012 calls resolve via the seam).

**AC-MB-006 (REQ-MB-006 — HOSTCTX-016 rich-fact lookups route through this seam with includes):**
- GIVEN HOSTCTX-016 requesting rich facts (first-release year, album/release, producer, engineer + credited
  personnel, record label(s), release-group relationships), WHEN they are fetched, THEN they go via the
  Group MB seam using the appropriate `musicbrainzngs` `includes=` expansions (e.g. artist-rels,
  recording-rels, release-rels, labels) against the mirror (or fallback), returned in a form HOSTCTX-016
  consumes.
- [HARD] These multi-include calls run OFF the playout path (REQ-MB-003) and their results are cacheable
  with the track record; the host-talk generation stays in HOSTCTX-016 (asserted: the include expansions
  are issued through the seam and no host-talk generation is implemented here).

**AC-MB-007 (REQ-MB-007 — mirror/fallback result is cached + idempotent with the track record):**
- GIVEN an enrichment / rich-fact result, WHEN it is produced, THEN it is cached with the existing `Track`
  record (ANALYSIS-006 REQ-AD-001 / REQ-AE-002 idempotent-cache pattern) so a re-scan / restart / retry
  does NOT re-query the mirror for an unchanged track, and HOSTCTX-016 reads already-fetched facts without
  a fresh network call on the talk path.
- Cache invalidation follows a schema/version bump or a changed file, mirroring ANALYSIS-006's caching
  (asserted: a second lookup for an unchanged track issues no new network call).

### Group MX — Discogs / Last.fm Cross-Check & Provenance

**AC-MX-001 (REQ-MX-001 — Discogs cross-check for credits/label coverage MusicBrainz lacks):**
- GIVEN MusicBrainz (mirror or fallback) lacking producer/engineer/personnel credits or pressing/label
  detail, WHEN cross-check runs, THEN a NEW Discogs provider (alongside MusicBrainz/TheAudioDB/Last.fm in
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

### Group MV — Volume, Sizing & Operations

**AC-MV-001 (REQ-MV-001 — provision ~150 GB Hetzner volume for Variant A):**
- GIVEN the chosen variant, WHEN the volume is provisioned, THEN it is sized accordingly — ~150 GB for
  recommended Variant A (Postgres + Solr + web service, ~100–150 GB plus headroom), ~50–80 GB for Variant B
  (Postgres-only), or ~15–25 GB for Variant C (selective import) — documented so the operator provisions
  with headroom.
- The mirror is NOT provisioned so tight that replication growth fills the volume and breaks sync (ties
  REQ-MV-002).

**AC-MV-002 (REQ-MV-002 — disk-headroom + replication-growth monitoring):**
- GIVEN the running mirror, WHEN volume free space and replication growth are monitored, THEN the operator
  is warned BEFORE the volume fills (a full volume halts replication and eventually the web service); the
  summarized status feeds the mirror health surface (REQ-MM-005).
- [HARD] A volume-pressure or replication-halt condition on the mirror triggers the brain's public-API
  fallback (REQ-MB-002), NEVER a brain error (asserted: mirror unavailability from disk pressure degrades
  to fallback, not a crash).

**AC-MV-003 (REQ-MV-003 — documented operator runbook):**
- GIVEN the deliverable, WHEN it is produced, THEN an operator RUNBOOK documents: initial provisioning +
  import, configuring the replication token as a secret (REQ-MM-004), enabling replication (REQ-MM-003),
  pointing the brain at the mirror (`BRAIN_MB_MIRROR_HOST`, REQ-MB-001), the rebuild/resync path
  (REQ-MM-006), and the variant trade-offs (REQ-MM-002).
- The runbook is documentation, NOT provisioning automation (out of scope); it ensures the mirror is
  operable + recoverable without reverse-engineering the SPEC (asserted: the runbook file exists and covers
  each named step).

---

## Section A (cont.) — Non-Functional Acceptance

**AC-NFR-M-1 (NFR-M-1 — never block on the mirror):** [HARD] No mirror or external-metadata interaction is
on the sub-1s `/api/next` pull path or able to stall the director / analysis-worker / daemon / stream; all
enrichment runs off the playout path, timeout-bounded, with fallback (asserted: request/enrichment
processing runs off the playout path; ties REQ-MB-002/003).

**AC-NFR-M-2 (NFR-M-2 — drop-in client, no schema coupling, Variant A):** [HARD] For the recommended variant
the brain changes ONLY the host it points `musicbrainzngs` at; the existing client calls work unchanged with
ZERO MusicBrainz-schema knowledge in the brain (asserted: no SQL/ORM against the MB schema in `brain/`; ties
REQ-MB-001).

**AC-NFR-M-3 (NFR-M-3 — secret safety):** [HARD] The replication token + any API keys live only in gitignored
`secrets/`/env, never in the repo, a SPEC, a config-template, or a log line (asserted: repo-wide grep finds
no token value; logs redact; ties REQ-MM-004).

**AC-NFR-M-4 (NFR-M-4 — resilience / graceful degradation):** [HARD] A mirror that is down, lagging,
mid-(re)build, unreachable, or volume-pressured degrades to the public-API fallback or graceful
no-enrichment WITHOUT crashing the worker / director / daemon and without silencing the stream (ties
REQ-MB-002, REQ-MM-006, REQ-MV-002).

**AC-NFR-M-5 (NFR-M-5 — throughput, the mirror's reason to exist):** [HARD] With the mirror configured, the
brain enriches at materially higher throughput than the public-API 1 req/s ceiling, so the ENRICH-012
whole-library id3 backfill and HOSTCTX-016 multi-include rich-fact lookups are practical at volume (asserted:
mirror-path calls are not subject to `_mb_throttle`; ties REQ-MB-004/005/006).

**AC-NFR-M-6 (NFR-M-6 — per-field provenance + consensus integrity):** [HARD] Every enriched/cross-checked
value carries its source provenance + consensus level; a single-source value is NEVER recorded "confirmed";
the cross-check folds into the EXISTING consensus, not a fork (ties REQ-MX-003/004).

**AC-NFR-M-7 (NFR-M-7 — rate-limit compliance):** The public-API fallback keeps the 1 req/s MusicBrainz
self-throttle; Discogs + Last.fm respect their published rate limits; only the local mirror is high-throughput
(and still timeout + local-cap bounded) (ties REQ-MB-004, REQ-MX-005).

**AC-NFR-M-8 (NFR-M-8 — simplicity / no over-engineering):** The implementation is the smallest infra +
client change delivering volume + rich facts: Variant A so the brain change is a hostname; reuse of the
existing providers/consensus; one Discogs provider added; no schema ORM, no new datastore, no
provisioning-automation product. Deferred items (spec.md Section 10) are NOT partially built (asserted: the
diff adds a host setter + one Discogs provider + config + a runbook, nothing in the excluded set).

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing / never-block / provenance-critical)

### B1 — The brain NEVER blocks on the mirror (REQ-MB-003, NFR-M-1, NFR-M-4) [HARD — defining rail]

```
GIVEN the mirror is configured AND becomes slow / unreachable / hung
WHEN ENRICH-012 enrichment or a HOSTCTX-016 rich-fact lookup is requested for a track
THEN the lookup runs OFF the playout path, bounded by enrichment_http_timeout_seconds
  AND it is NOT on the sub-1s /api/next pull path and does NOT stall the director loop, the analysis
      worker, or the daemon
  AND the track plays regardless of whether its enrichment completed (graceful degradation)
  AND the stream never goes to dead air because of the mirror
```
Verification: assert no mirror/external call exists on the `/api/next` path; assert enrichment runs in an
off-path worker bounded by timeout; assert a hung mirror produces a played track with absent-or-fallback
enrichment, never a stall (the defining rail; addresses R-M-4).

### B2 — Automatic public-API fallback on any mirror failure (REQ-MB-002, REQ-MM-006, REQ-MV-002) [HARD]

```
GIVEN a MusicBrainz lookup
WHEN the mirror is unset, OR unreachable, OR times out, OR returns an error, OR is mid-(re)build, OR is
     volume-pressured/replication-halted
THEN the brain AUTOMATICALLY falls back to the public MusicBrainz API at the 1 req/s self-throttle for
     that lookup
  AND if the public API also fails, the brain returns gracefully empty (no enrichment for that track)
  AND no error propagates, no stall occurs, the stream is unaffected
  AND the fallback decision is per-call and timeout-bounded (enrichment_http_timeout_seconds)
```
Verification: assert each failure mode (unset / unreachable / timeout / error / rebuilding / volume-pressure)
independently routes to the public-API fallback, then to graceful-empty; assert no failure mode raises to the
caller (addresses R-M-3, R-M-4).

### B3 — Drop-in client, hostname-only repoint, no schema coupling (REQ-MB-001, NFR-M-2) [HARD]

```
GIVEN BRAIN_MB_MIRROR_HOST is SET (with use_https per the deployment)
WHEN the brain initializes the musicbrainzngs client
THEN it calls musicbrainzngs.set_hostname(host, use_https) (accepting host:port) to repoint the EXISTING
     client at the mirror
  AND the same _provider_musicbrainz / ENRICH-012 calls (search_recordings, get_recording_by_id(includes=...))
      execute UNCHANGED against the local web service
GIVEN BRAIN_MB_MIRROR_HOST is UNSET (empty)
WHEN the brain initializes the client
THEN it uses the public MusicBrainz API exactly as today
  AND in BOTH cases there is NO SQL/ORM against the MusicBrainz schema anywhere in brain/
```
Verification: assert the only mirror-related brain change is the hostname (set via `set_hostname`); assert no
MB-schema coupling exists; assert the variant choice (A/B/C) does not change the brain code (addresses R-M-1,
R-M-6).

### B4 — Mirror unthrottled-but-bounded; public-API stays at 1 req/s (REQ-MB-004, REQ-MB-005, NFR-M-5, NFR-M-7) [HARD]

```
GIVEN an ENRICH-012 whole-library id3 backfill issuing thousands of MusicBrainz lookups
WHEN the mirror is configured and the lookups route through the Group MB seam
THEN mirror-targeted calls are NOT subject to the 1 req/s _mb_throttle (volume is the point)
  AND mirror-targeted calls ARE still bounded by the configured timeout AND a sane local concurrency/rate
      cap (a runaway backfill cannot saturate the mirror or the brain)
WHEN any call instead targets the PUBLIC API (fallback path)
THEN the 1 req/s _mb_throttle applies (MetaBrainz politeness preserved)
  AND the mirror cap + the public throttle are tunable config
  AND the ENRICH-012 identification / confidence-threshold / write-back logic is unchanged (only the
      endpoint changed)
```
Verification: assert mirror calls bypass `_mb_throttle` but pass the local cap; assert public calls pass
`_mb_throttle`; assert no ENRICH-012 logic is re-implemented in MBMIRROR-017 (the throughput rationale,
NFR-M-5).

### B5 — Cross-check folds into consensus; single-source never "confirmed" (REQ-MX-004, REQ-MX-003, NFR-M-6) [HARD]

```
GIVEN a field (e.g. producer) supplied by Discogs only, and another field (e.g. release year) supplied by
      both the mirror-MusicBrainz and Discogs
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

### B8 — Variant choice is an OPS decision behind a stable client seam (REQ-MM-002, REQ-MM-001, NFR-M-8)

```
GIVEN the operator may choose Variant A (full musicbrainz-docker), B (Postgres-only), or C (selective import)
WHEN the brain queries MusicBrainz
THEN the brain-facing contract is IDENTICAL across variants: the musicbrainzngs HTTP API + the public-API
     fallback
  AND the brain code does not change when the variant changes (the SQL layer for B/C is an OPS detail behind
      the same client contract, not a brain product)
  AND Variant A is the recommended default for zero schema coupling + the smallest brain change
```
Verification: assert the brain client seam is variant-agnostic; assert no brain-owned MB-schema product
exists; assert the recommendation + documented trade-offs are present (addresses R-M-1; simplicity NFR-M-8).

---

## Section C — Definition of Done & Quality Gates

An MBMIRROR-017 implementation is DONE when:

1. [HARD] All 22 REQ + 8 NFR Section A entries pass, and all Section B scenarios pass.
2. [HARD] **The brain NEVER blocks on the mirror (REQ-MB-003, NFR-M-1, the defining rail):** no mirror or
   external call is on the `/api/next` pull path; all enrichment runs off-path, timeout-bounded; a track
   always plays; the stream never goes dead air for a mirror problem (B1).
3. [HARD] **Automatic public-API fallback on any mirror failure (REQ-MB-002, NFR-M-4):** unset / unreachable
   / timeout / error / rebuilding / volume-pressured all route to the public-API fallback, then to
   graceful-empty; no failure propagates (B2).
4. [HARD] **Drop-in client, hostname-only, no schema coupling (REQ-MB-001, NFR-M-2):** the only mirror brain
   change is `set_hostname(host, use_https)`; no MB-schema SQL/ORM in `brain/`; unset → public API as today
   (B3).
5. [HARD] **Mirror unthrottled-but-bounded; public-API at 1 req/s (REQ-MB-004, NFR-M-5/M-7):** mirror calls
   bypass `_mb_throttle` but obey timeout + local cap; public calls keep 1 req/s; throughput materially
   exceeds the public ceiling (B4).
6. [HARD] **ENRICH-012 routes through the seam unchanged (REQ-MB-005):** only the MusicBrainz endpoint
   changes; ENRICH-012 identification / confidence / write-back logic is referenced, not re-owned (B4).
7. **HOSTCTX-016 rich-fact include-expansion lookups route through the seam, off-path, cached (REQ-MB-006,
   REQ-MB-007):** multi-include calls run off the playout path; results cache idempotently with the `Track`
   record.
8. [HARD] **Per-field provenance + consensus integrity (REQ-MX-003/004, NFR-M-6):** every enriched/
   cross-checked value carries source provenance + consensus level; single-source values are never
   "confirmed"; the cross-check folds into the EXISTING `consensus()`, not a fork (B5).
9. [HARD] **Cross-check is rate-limited, optional, off-path (REQ-MX-001/005, NFR-M-7):** Discogs/Last.fm obey
   published rate limits + timeout, run off the playout path downstream of acquisition; absent-token →
   dormant; a failing cross-check degrades to no-coverage, never a block (B6).
10. **Last.fm reused, not re-owned; artist-fact boundary to KNOWLEDGE-008 (REQ-MX-002/006):** no second
    Last.fm client; only release/recording credits are surfaced; no parallel artist-fact store.
11. [HARD] **Secret safety (REQ-MM-004, NFR-M-3):** the replication token + any keys live only in gitignored
    `secrets/`/env; never committed, never in a SPEC/template/doc, never logged (B7).
12. [HARD] **Mirror on Hetzner, separate deployment, replication enabled (REQ-MM-001/003):** the mirror runs
    on Hetzner (not local), the brain is a client, replication keeps it current without manual full
    re-import.
13. **Variant A recommended; B/C documented; contract identical across variants (REQ-MM-002, NFR-M-8):** the
    variant is an OPS choice behind a stable client seam (B8).
14. **Initial-import / rebuild-resync posture + health/lag observability (REQ-MM-005/006):** a (re)building
    mirror runs the brain on fallback; reachability + last-replication + responsiveness are surfaced.
15. **Volume sizing + headroom monitoring + runbook (REQ-MV-001/002/003):** ~150 GB Variant-A provision (with
    B/C documented); volume-pressure triggers fallback, never a brain error; an operator runbook covers
    provisioning, token-as-secret, replication, brain repoint, rebuild, and variant trade-offs.
16. [HARD] **Single-source-of-truth / no fork (NFR-M-8 + dependency rails):** the ENRICH-012 logic, the
    ANALYSIS-006 `consensus()` + `Track` provenance fields, the KNOWLEDGE-008 artist-fact store, the OPS-004
    source list + acquisition throttle, and the CORE-001 continuous-operation rail are referenced by id,
    never re-owned; brain-only + additive (a host setter + one Discogs provider + config + a runbook); no new
    service, no new datastore, no schema ORM.

Quality gates (TRUST 5, inherited): Tested (the never-block B1, the fallback B2, the no-schema-coupling B3,
the throttle-policy B4, the consensus/provenance B5, and the secret-safety B7 are the must-pass
characterization tests); Readable; Unified; Secured (the gitignored-secret discipline + redacted logging +
rate-limit compliance + the private/firewalled mirror posture); Trackable (per-field provenance + consensus
level on the `Track` record give an auditable origin for every enriched value).

Parity check: 22 AC (Section A) + 8 AC-NFR = 30 acceptance entries, matching spec.md 22 REQ + 8 NFR; 1:1
REQ↔AC preserved.
