---
id: SPEC-RADIO-VETTING-027
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: High
issue_number: 27
---

# SPEC-RADIO-VETTING-027 — Conservative Content-Vetting + Soft Reversible Ban-List

## HISTORY

- 2026-06-23 (v0.1.0): Initial draft, occupying the new global-incrementing VETTING-027 id (the next
  number after REFLECT-026). The CONTENT-VETTING + BAN-LIST subsystem of the golden-shower-radio
  autonomous AI radio station. It answers a direct user concern: the acquisition path
  (`brain/acquire.py` + `brain/slskd.py` + `brain/ytdlp.py`) can fetch the WRONG KIND of file — a
  2-hour podcast, a spoken-word lecture, a 12-hour rain-noise loop, an audiobook, a non-music asset —
  and, separately, a listener REQUEST can ask for genuinely hateful content. VETTING-027 adds a
  CONSERVATIVE, allow-by-default content-vetting cascade wired at THREE gates (pre-download, pre-play,
  pre-request-honor) plus a SOFT, REVERSIBLE ban-list that is the durable loop-breaker for a
  post-fetch reject. The duration/size PRE-DOWNLOAD tier is ALREADY PARTLY SHIPPED (the 200 MB /
  2400 s hotfix: `Config.max_download_mb` / `max_download_duration_seconds`, threaded through
  `slskd.acceptable`→`collect_candidates`→`best_candidate` as `max_size_bytes`, and through
  `ytdlp.fetch` as `--max-filesize NM` + `--match-filter "duration < N"`); this SPEC references that
  as the existing VC pre-download tier and builds the keyword/category and speech-vs-music tiers on
  top. RADIO SPEC-IDs are GLOBAL-INCREMENTING (CORE-001, VOICE-002, CALLIN-003, OPS-004, ORCH-005,
  ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009, IMAGING-010, REQUEST-011, ENRICH-012,
  STATS-013, DEDUP-014, LIKE-015, HOSTCTX-016, MBMIRROR-017, WEBUI-018, ACQQUEUE-019, SHOWS-020,
  ALBUMART-021, DATASTORE-022, LOOKUPLOG-023, FILENAME-024, LONGFORM-025, REFLECT-026 authored;
  VETTING = 027). It uses a DISTINCT REQ namespace — VC (vet cascade), VK (combine-signals
  false-positive guard), VB (ban-list store + lifecycle), VG (three-gate wiring), VR (offensive-
  request verdict) — chosen to dodge VOICE-002's V-family (V-A…V-F) and every other radio prefix
  (CORE A-E+D, CALLIN CT/CL/CD/CM/CC/CF/CS/CG, OPS OA/OB/OC/OD/OE/OF/OG/OH/OX/OY, ORCH
  RL/RW/RE/RC/RD/RA/RN/RI, ANALYSIS AE/AT/AM/AD/AP, PROGRAMMING PR/PC/PS/PT/PL/PG/PV/PI, KNOWLEDGE
  KS/KF/KR/KG/KI, TAGSTREAM TW/TA/TX, IMAGING IG/IB/IP/IL/IS/IH/IX, REQUEST RQ/RM/RA/RWL/RS/RV/RD,
  DEDUP DK, LIKE LH/LD/LS/LA/LP/LX, LOOKUPLOG LL/LK/LC/LM/LG, FILENAME FD/FR/FS/FF, DATASTORE
  DE/DP/DX/DM/DC/DR). NOTE: VC ≠ VOICE's V-C; the full id (`REQ-VC-NNN`) is used everywhere to keep
  it distinct. Total: 22 REQ + 7 NFR = 29, 1:1 REQ↔AC (VC=5, VK=3, VB=6, VG=4, VR=4).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "stop fetching the wrong kind of file, and never get stuck doing it"

The brain turns a wishlist of `{artist, title}` into files on disk: `slskd` search → rank candidates
→ enqueue best → wait for the file to land; if `slskd` yields nothing, fall back to `yt-dlp`
(`brain/acquire.py`). Two distinct hazards motivate this SPEC:

1. **Non-music gets through.** A search for an artist+title can match a 2-hour interview upload, a
   spoken-word lecture, an audiobook chapter, a podcast episode, a multi-hour ambient/rain loop, or a
   bare non-music asset. The just-shipped 200 MB / 2400 s hotfix (`max_download_mb` /
   `max_download_duration_seconds`) is a BLUNT first cut — it rejects pathologically large/long files
   pre-download — but it is a single axis (size/duration), and a 2-hour podcast under 200 MB still
   slips through, while a legitimate 70-minute DJ-mix or a 90-minute ambient album would be wrongly
   rejected if duration alone decided. A real cascade is needed: cheap size/duration first, then
   keyword/category, then (for the ambiguous middle) an audio speech-vs-music check.

2. **The fetch→reject→re-fetch loop.** [HARD][LOAD-BEARING] Here is the trap the ban-list exists to
   break. On a landed file, `_acquire_one` calls `attempts.record(key, "success")`
   (`brain/acquire.py` line 183/188). `AttemptsIndex.should_skip` (lines 81-89) returns `True`
   forever for a `"success"` key, and `False` for a `"failed"` key once `RETRY_COOLDOWN` (6h, line 34)
   elapses. If a vet rejects a file AFTER it lands and the file is DELETED, then: (a) recording
   `"success"` would be a lie (the file is gone, so `Library.has_key` is False after the next
   `scan()`), and (b) recording `"failed"` (or nothing) means `should_skip` returns `False` again
   after 6 hours → the brain re-searches, re-fetches the SAME wrong file, re-rejects it, re-deletes
   it, forever. An UNBOUNDED fetch→delete→re-fetch loop that wastes the network and the slskd queue
   indefinitely. **The ban-list row is the loop-breaker:** a post-fetch reject MUST both record an
   `AttemptsIndex` status that is NOT `"success"` AND add a durable ban-list row, so the next
   `enqueue` / `_acquire_one` is short-circuited by the ban check before it ever re-searches.

3. **Offensive requests.** Separately, the listener-request path (REQUEST-011, code not yet written)
   can carry a request for genuinely hateful content. The station's posture is CONSERVATIVE and
   allow-by-default: it is a provocative, art-forward station, NOT a sanitized one. It bans ONLY
   identity-hate — sexuality-bashing / homophobia / racism — and NEVER provocative art, dark themes,
   explicit language, or political edge.

VETTING-027 adds the vet cascade (VC), the false-positive guard (VK), the ban-list (VB), the
three-gate wiring (VG), and the offensive-request verdict (VR), all exception-isolated so a vet
failure never crashes acquisition or playout (the golden rule).

### 1.2 The load-bearing invariant (the loop-breaker — the heart of this SPEC)

[HARD][LOAD-BEARING] **A post-fetch reject MUST record an `AttemptsIndex` status that is NOT
`"success"` AND add a ban-list row.** The ban-list row is the loop-breaker. Without it,
`AttemptsIndex.should_skip` returns `False` after `RETRY_COOLDOWN` (6h) and the brain re-enters an
unbounded fetch→delete→re-fetch loop on the same rejected content. This is REQ-VB-001 and is restated
as NFR-V-7. The two writes together are the rail: the attempts status keeps the cooldown machinery
honest (no false `"success"`), and the ban-list row is the durable, cooldown-independent block that
`enqueue` / `_acquire_one` consult BEFORE re-searching.

### 1.3 The vet cascade is a tiered funnel, cheapest-first (the VC idea)

[HARD] The vet runs as a TIERED CASCADE, cheapest signal first, so the expensive audio analysis is
only reached for the ambiguous middle:

- **Tier 1 — duration/size (pre-download, ALREADY PARTLY SHIPPED).** The 200 MB / 2400 s hotfix:
  `slskd.acceptable` skips a candidate whose `size > max_size_bytes`; `ytdlp.fetch` passes
  `--max-filesize {max_mb}M` + `--match-filter "duration < {max_duration_seconds}"`. This rejects the
  pathologically large/long BEFORE any byte is fetched. VETTING-027 REFERENCES this as the existing
  VC Tier 1 and extends the cascade above it; it does not re-own the hotfix.
- **Tier 2 — keyword + category (pre-download / pre-play, metadata-only).** Cheap textual signals from
  the candidate filename / slskd metadata / yt-dlp metadata: tokens like `podcast`, `audiobook`,
  `interview`, `lecture`, `sermon`, `asmr`, `full episode`, a chapter-numbering pattern, a known
  non-music category. Metadata-only, no decode.
- **Tier 3 — audio speech-vs-music (pre-play, decode-based).** For the AMBIGUOUS middle that passes
  Tiers 1-2 but could still be talk (a 40-minute file with a clean title), a decode-based
  speech-vs-music signal. [HARD][DEPENDENCY] This tier DEPENDS on extending ANALYSIS-006, which TODAY
  DISCLAIMS speech detection (`brain/analysis.py` extracts BPM / key / energy / LUFS / cues, NOT a
  speech-vs-music classifier). Until ANALYSIS-006 supplies the signal, Tier 3 degrades to UNAVAILABLE
  and the cascade decides on Tiers 1-2 alone (allow-by-default on the ambiguous middle, never a ban
  on missing signal — VK).

### 1.4 The combine-signals guard (the VK invariant — duration alone NEVER bans)

[HARD] **Duration ALONE never bans.** A ban (or a vet reject) requires COMBINED signals, never a
single axis. Long-form music is legitimate and PROTECTED: a 70-minute DJ-mix, a 90-minute ambient
album, a continuous "full album" upload, a long-form mixtape are all real music the station WANTS.
The size/duration Tier 1 hotfix is a coarse pathological-outlier cut (multi-hour / multi-hundred-MB),
NOT a "long = bad" rule. The legitimacy judgement for genuine LONG-FORM content is DEFERRED to
SPEC-RADIO-LONGFORM-025 (the deep-shows / long-form engine); VETTING-027 MUST NOT ban a file for
being long, and MUST treat a long file that LONGFORM-025 (or its absence) does not condemn as
allowed. The rail: a reject needs corroborating signal across at least two of {duration/size,
keyword/category, speech-vs-music}, never duration on its own.

### 1.5 The ban-list is SOFT and REVERSIBLE (the VB idea)

[HARD] The ban-list is a SOFT, REVERSIBLE store, not a permanent blacklist. A `banned` record carries
a `status` (e.g. `banned` | `pending_review`), a `cooldown`, the `evidence` (which tiers fired, the
signal values), a `confidence`, and an explicit UN-BAN path (an operator or a higher-confidence later
signal can clear or downgrade a ban). A ban is a working hypothesis the station can revise — never a
silent, irreversible deletion of a possibility. The ban-list keys on the same content/identity basis
the acquisition path already uses (the `normalize_key(artist, title)` slug for the request/wishlist
axis; a content/file identity where a specific landed file is the culprit).

### 1.6 The dual-substrate requirement (works TODAY on JSON, maps to SQLite WHEN built)

[HARD][SUBSTRATE] SPEC-RADIO-DATASTORE-022 (the JSON→SQLite migration) is still DRAFT/UNIMPLEMENTED.
TODAY, acquisition outcomes live in JSON: `AttemptsIndex` persists `attempts.json` via
`brain/acquire.py`. Therefore VETTING-027 MUST specify the ban-list to:

- **(a) work TODAY** alongside the JSON `AttemptsIndex` — a JSON-backed (or equivalently simple
  brain-local) `banned` store that coexists with `attempts.json`, requiring NO unbuilt SQLite layer;
  AND
- **(b) map to DATASTORE-022's substrate WHEN built** — the `banned` table belongs in DATASTORE-022's
  `brain.db` (it is core-operational, consulted on the acquisition path, and co-written with the
  `attempts` write that is the loop-breaker's other half — see the one-atomic-grab-write rationale,
  REQ-DP-003) OR, if the orchestrator prefers an analytics framing, exposed for `events.db`; the
  RECOMMENDED mapping (D-1) is `brain.db` so the ban-write and the attempts-write can be co-located.

[HARD] This GRACEFUL COEXISTENCE is mandatory: VETTING-027 MUST NOT hard-require the unbuilt SQLite
layer. The ban-list works on the JSON substrate today and migrates with DATASTORE-022's idempotent
JSON→SQLite import when that ships (the same `keep-JSON-as-backup` + idempotent-upsert posture,
REQ-DM-001/002/003, applies to the `banned` store).

### 1.7 The offensive-request verdict is CONSERVATIVE, allow-by-default (the VR idea)

[HARD] The offensive-request verdict is CONSERVATIVE and ALLOW-BY-DEFAULT. It bans ONLY
identity-hate: sexuality-bashing / homophobia / racism. It NEVER bans provocative art, dark or
transgressive themes, explicit language, political edge, or anything that is merely uncomfortable —
the station's identity is art-forward and unsanitized. The verdict CONSUMES the CALLIN-003
moderation-floor primitive (Group CM / CC — the fail-closed moderation floor + conduct rules), which
is SPEC-ONLY (no code yet). VETTING-027 references that floor and does NOT re-own it; where CALLIN-003
defines the identity-hate floor, VETTING-027 applies it to the REQUEST path (pre-request-honor gate,
VG), not the live-call path CALLIN-003 owns.

### 1.8 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] VETTING-027 OWNS the vet cascade logic, the combine-signals guard, the soft/reversible
ban-list store + lifecycle, the three-gate wiring, and the conservative offensive-request verdict.
It MUST NOT restate, fork, or weaken any ACQQUEUE-019, ANALYSIS-006, REQUEST-011, DATASTORE-022,
OPS-004, CALLIN-003, or LONGFORM-025 requirement.

OWNS:
- The VET CASCADE (Group VC): the tiered funnel (duration/size → keyword/category → speech-vs-music),
  referencing the shipped Tier 1 hotfix and adding Tiers 2-3.
- The COMBINE-SIGNALS GUARD (Group VK): the [HARD] duration-alone-never-bans rule, the long-form
  protection, the defer-long-form-legitimacy-to-LONGFORM-025 rule.
- The BAN-LIST STORE + LIFECYCLE (Group VB): the `banned` store, its soft/reversible status + cooldown
  + evidence + confidence + un-ban path, the dual-substrate (JSON-today / SQLite-when-built) rule, and
  the LOAD-BEARING loop-breaker invariant.
- The THREE-GATE WIRING (Group VG): the [HARD] pre-download / pre-play / pre-request-honor gates.
- The OFFENSIVE-REQUEST VERDICT (Group VR): the conservative, allow-by-default, identity-hate-only
  verdict that consumes the CALLIN-003 moderation-floor primitive.
- Plus NFRs (Section 8) and Risks (Section 9).

REFERENCES (consumes / extends / applies; does not restate):
- **ACQQUEUE-019 — the pre-download vet hook.** The acquisition-queue / source-preference layer is the
  seam the pre-download vet attaches to (the candidate-rank / `acceptable` / wait-loop path). The vet
  is an additional accept/reject predicate alongside the queue-length preference; ACQQUEUE-019 owns
  WHOM-to-grab-from, VETTING-027 owns IS-THIS-THE-RIGHT-KIND-of-file. Referenced, not re-owned.
- **ANALYSIS-006 — the speech-vs-music signal PRODUCER.** Tier 3 needs a decode-based speech-vs-music
  classification that ANALYSIS-006 does NOT produce today (it DISCLAIMS speech detection;
  `brain/analysis.py` extracts BPM/key/energy/LUFS/cues only). VETTING-027 DEPENDS on extending
  ANALYSIS-006 to emit a speech-vs-music signal (an `AT`/`AM`-family field); until then Tier 3
  degrades to unavailable. Referenced, not re-owned.
- **REQUEST-011 — the request-ingest hook.** The pre-request-honor gate attaches to REQUEST-011's
  request-ingest path (Group RQ/RM/RS); REQUEST-011's RS anti-abuse group has no code yet. VETTING-027
  applies the offensive-request verdict at that gate; REQUEST-011 owns the request lifecycle.
- **DATASTORE-022 — the `banned` table → `brain.db` substrate.** When DATASTORE-022 ships, the
  `banned` store maps to its partitioned SQLite (RECOMMENDED `brain.db`, co-located with `attempts`);
  until then it is JSON-backed. Referenced, not re-owned.
- **OPS-004 — accounting.** The vet/ban outcomes are accountable station-operation events OPS-004's
  accounting/self-learning playbook may consume (rejection counts, ban additions, un-bans). The vet
  emits structured `log_event`s; OPS-004 reads. Referenced, not re-owned.
- **CALLIN-003 Group CM / CC — the moderation-floor primitive.** The fail-closed identity-hate
  moderation floor + conduct rules (SPEC-only, no code). VETTING-027's offensive-request verdict
  consumes this floor for the REQUEST path. Referenced, not re-owned.
- **LONGFORM-025 — long-form legitimacy.** The judgement of whether a long file is legitimate
  long-form content (DJ-mix / album-doc / artist-retrospective) is LONGFORM-025's; VETTING-027 defers
  to it and never bans for length. Referenced, not re-owned.

### 1.9 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 intent and does NOT redefine it. VETTING-027 is a SAFETY / HYGIENE
substrate, not a creative act: it keeps the wrong KIND of file off the air and blocks genuinely
hateful requests, but it does NOT homogenize taste, narrow the music, or sanitize the station's
art-forward edge. It is conservative and allow-by-default by design (VK + VR). The director still
decides WHAT to play; the vet only removes non-music and identity-hate from the candidate space.

### 1.10 Fixed engineering rails (the only hard constraints)

- **Exception-isolated; never crash acquisition or playout.** [HARD] A vet/ban error logs and is
  dropped; it NEVER fails a download worker, never blocks the picker, never silences the stream
  (NFR-V-1/2). The golden rule wins.
- **The loop-breaker invariant.** [HARD][LOAD-BEARING] A post-fetch reject records `AttemptsIndex`
  status != `"success"` AND adds a ban-list row (REQ-VB-001, NFR-V-7).
- **Cheapest-tier-first cascade.** [HARD] Duration/size → keyword/category → speech-vs-music; expensive
  decode only for the ambiguous middle (REQ-VC-001).
- **Duration alone never bans; combine signals.** [HARD] A ban needs ≥2 corroborating signals;
  long-form music is protected; legitimacy of long-form is LONGFORM-025's (REQ-VK-001/002/003).
- **Soft + reversible ban-list.** [HARD] Status / cooldown / evidence / confidence / un-ban path; a ban
  is revisable, never a silent permanent delete (REQ-VB-002/003/004).
- **Dual substrate: JSON today, SQLite when DATASTORE-022 ships.** [HARD] Coexists with the JSON
  `AttemptsIndex`; maps to `brain.db` when built; does NOT hard-require the unbuilt SQLite layer
  (REQ-VB-005).
- **Three gates.** [HARD] Pre-download, pre-play, pre-request-honor (REQ-VG-001/002/003).
- **Conservative, allow-by-default offensive verdict; identity-hate only.** [HARD] Bans only
  sexuality-bashing / homophobia / racism; never provocative art; consumes CALLIN-003 CM/CC
  (REQ-VR-001/002/003).
- **Reference, don't re-own.** [HARD] ACQQUEUE-019, ANALYSIS-006, REQUEST-011, DATASTORE-022, OPS-004,
  CALLIN-003, LONGFORM-025 are referenced, never restated (NFR-V-3).
- **Brain-only; additive.** [HARD] A vet/ban module on the existing `brain/` package + a `banned`
  store; no new service, no Liquidsoap change, no listener-website surface (NFR-V-3/6).

---

## 2. Dependencies

This SPEC DEPENDS ON the existing acquisition path (`brain/acquire.py` `AttemptsIndex` /
`_acquire_one` / `_try_slskd` / `_try_ytdlp`; `brain/slskd.py` `acceptable` / `collect_candidates` /
`best_candidate`; `brain/ytdlp.py` `fetch`) and the shipped 200 MB / 2400 s hotfix
(`Config.max_download_mb` / `max_download_duration_seconds`). It REFERENCES SPEC-RADIO-ACQQUEUE-019
(pre-download vet hook), SPEC-RADIO-ANALYSIS-006 (the speech-vs-music signal it needs ANALYSIS-006 to
add), SPEC-RADIO-REQUEST-011 (the request-ingest hook), SPEC-RADIO-DATASTORE-022 (the `banned` →
`brain.db` substrate mapping), SPEC-RADIO-OPS-004 (accounting), SPEC-RADIO-CALLIN-003 Group CM/CC (the
moderation-floor primitive), and SPEC-RADIO-LONGFORM-025 (long-form legitimacy).

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any sibling requirement. Where it needs a
predecessor behavior it consumes it. Where a vet/ban action could conflict with continuous operation,
the inherited never-block / exception-isolated behavior WINS — the music keeps playing and
acquisition never crashes because of the vet.

Consumed concepts (by name/number where stable):
- **`brain/acquire.py` `AttemptsIndex.should_skip` / `record` / `RETRY_COOLDOWN`** — the idempotency
  cache the loop-breaker invariant pivots on. `should_skip` returns `True` for a `"success"` key and
  `True` for a `"failed"` key only within `RETRY_COOLDOWN` (6h); the ban-list provides the durable,
  cooldown-independent block a post-fetch reject needs (REQ-VB-001).
- **`brain/acquire.py` `_acquire_one` / `enqueue` / `_try_slskd` / `_wait_for_download` /
  `_try_ytdlp`** — the worker path the pre-download and (post-land) pre-play vets and the ban check
  attach to. The `record(key,"success")` calls (lines 183/188) are the ones a post-fetch reject must
  NOT make.
- **`brain/slskd.py` `acceptable` / `collect_candidates` / `best_candidate` + `max_size_bytes`** — the
  candidate-accept predicate the pre-download keyword/category Tier 2 extends (alongside the shipped
  Tier 1 size cap).
- **`brain/ytdlp.py` `fetch` + `--max-filesize` / `--match-filter "duration < N"`** — the yt-dlp arm
  of the shipped Tier 1; the vet adds keyword/category filtering on yt-dlp metadata.
- **`brain/analysis.py` (`analyze_file` feature record)** — the engine that would emit the
  speech-vs-music Tier 3 signal once ANALYSIS-006 is extended; today it DISCLAIMS speech detection.
- **`brain/config.py` `max_download_mb` / `max_download_duration_seconds`** — the shipped Tier 1
  knobs; VETTING-027 adds its own `BRAIN_*` toggles beside them (vet enable, ban-list path, the
  keyword list, the speech-vs-music thresholds).

### 2.1 Load-bearing dependency — ANALYSIS-006 must add a speech-vs-music signal

[HARD][DEPENDENCY] Tier 3 of the cascade (REQ-VC-004) and the speech-vs-music half of the
combine-signals guard need a decode-based SPEECH-VS-MUSIC classification. TODAY ANALYSIS-006 does NOT
produce it: `brain/analysis.py` extracts BPM + key + energy + LUFS + cues and EXPLICITLY scopes itself
to music-feature DSP, with no speech/talk classifier. VETTING-027 DEPENDS on ANALYSIS-006 adding a
speech-vs-music signal (e.g. a `speech_likelihood` field on the feature record, an `AT`/`AM`-family
requirement). Until ANALYSIS-006 supplies it, Tier 3 degrades to UNAVAILABLE: the cascade decides on
Tiers 1-2 only, and — per VK — a missing speech signal NEVER bans on its own (allow-by-default on the
ambiguous middle). Surfaced as D-2.

### 2.2 Load-bearing dependency — the post-fetch delete path must be wired to the loop-breaker

[HARD][DEPENDENCY] The loop-breaker (REQ-VB-001) presumes a place where a LANDED file is rejected and
removed. TODAY no such post-fetch reject/delete exists in `_acquire_one` — a landed file is scanned
into the library and recorded `"success"` unconditionally. VETTING-027's pre-play vet (VG) introduces
the post-land reject; that reject path is precisely where the loop-breaker MUST fire (record !=
`"success"` + ban row). The vet and the loop-breaker are co-dependent: the vet creates the reject, the
ban-list makes the reject durable. Surfaced as D-3.

### bhive memory seam

bhive memory (AGENTS.md protocol) has no proven pattern for a "tiered non-music content vet +
soft/reversible ban-list as an idempotency-cache loop-breaker" on this Go/Python+Liquidsoap+slskd
radio stack (recorded gap; consistent with the standing bhive Stack Gap note and DATASTORE-022's
query `dbc89f85-a8bf-48f1-b7b8-9569acd05665`). Re-run a bhive query on the speech-vs-music gating +
fetch-loop-breaker-via-durable-ban pattern during implementation and contribute the verified approach
back per the AGENTS.md memory protocol.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Vet cascade** | The tiered accept/reject funnel applied to a candidate / a landed file: Tier 1 duration/size (pre-download, shipped), Tier 2 keyword/category (metadata), Tier 3 speech-vs-music (decode). Cheapest signal first (Group VC). |
| **Tier 1 (duration/size)** | The shipped 200 MB / 2400 s pre-download cut: `slskd.acceptable` skips `size > max_size_bytes`; `ytdlp.fetch` passes `--max-filesize {max_mb}M` + `--match-filter "duration < N"`. A coarse pathological-outlier cut, NOT a "long = bad" rule (REQ-VC-002). |
| **Tier 2 (keyword/category)** | Metadata-only textual signals (filename / slskd metadata / yt-dlp metadata): `podcast` / `audiobook` / `interview` / `lecture` / `sermon` / `asmr` / `full episode` / chapter-numbering / known non-music category. No decode (REQ-VC-003). |
| **Tier 3 (speech-vs-music)** | A decode-based speech-vs-music signal for the ambiguous middle; DEPENDS on ANALYSIS-006 adding it (it DISCLAIMS speech detection today). Degrades to unavailable until then (REQ-VC-004, Section 2.1). |
| **Combine-signals guard** | The [HARD] rule that a ban / vet reject needs ≥2 corroborating signals across {duration/size, keyword/category, speech-vs-music}; duration alone NEVER bans (Group VK). |
| **Long-form protection** | The protection of legitimate long music (DJ-mix / ambient album / "full album" / mixtape) from being rejected for length; legitimacy is DEFERRED to LONGFORM-025 (REQ-VK-002/003). |
| **Ban-list / `banned` store** | The soft, reversible store of banned content/requests: per record `status` (`banned` \| `pending_review`), `cooldown`, `evidence` (tiers fired + values), `confidence`, and an un-ban path. Keyed on the `normalize_key` slug (request axis) or a content/file identity (Group VB). |
| **Soft / reversible** | The ban-list property: a ban is a revisable working hypothesis, not a permanent blacklist; an operator or a higher-confidence later signal can clear/downgrade it (REQ-VB-003/004). |
| **The loop-breaker invariant** | [HARD][LOAD-BEARING] A post-fetch reject records `AttemptsIndex` status != `"success"` AND adds a ban-list row, so `should_skip` does not re-permit the fetch after `RETRY_COOLDOWN` (6h) → no unbounded fetch→delete→re-fetch loop (REQ-VB-001, NFR-V-7). |
| **Dual substrate** | The ban-list works TODAY on JSON (beside `attempts.json`) and maps to DATASTORE-022's `brain.db` WHEN built; it does NOT hard-require the unbuilt SQLite layer (REQ-VB-005, Section 1.6). |
| **Three gates** | The points the vet runs: PRE-DOWNLOAD (before fetching a candidate), PRE-PLAY (before a landed/queued file goes on air), PRE-REQUEST-HONOR (before a listener request is honored) (Group VG). |
| **Offensive-request verdict** | The conservative, allow-by-default verdict on a listener request: bans ONLY identity-hate (sexuality-bashing / homophobia / racism), NEVER provocative art. Consumes the CALLIN-003 CM/CC moderation floor (Group VR). |
| **Moderation-floor primitive (CALLIN-003 CM/CC)** | The fail-closed identity-hate moderation floor + conduct rules CALLIN-003 defines (SPEC-only, no code). VETTING-027's VR applies it to the REQUEST path; CALLIN-003 owns it (REQ-VR-003). |
| **`AttemptsIndex` (referenced)** | The existing JSON idempotency cache (`brain/acquire.py`): `should_skip` returns `True` for `"success"` keys and for `"failed"` keys within `RETRY_COOLDOWN` (6h). The loop-breaker pivots on it (REQ-VB-001). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group VC — Vet Cascade.** The tiered funnel (duration/size → keyword/category → speech-vs-music);
  the reference to the shipped Tier 1 hotfix; the metadata-only Tier 2; the decode-based Tier 3
  (depending on ANALYSIS-006); the cheapest-first ordering.
- **Group VK — Combine-Signals False-Positive Guard.** The [HARD] duration-alone-never-bans rule; the
  ≥2-corroborating-signals requirement; the long-form protection; the defer-long-form-legitimacy-to-
  LONGFORM-025 rule.
- **Group VB — Ban-List Store + Lifecycle.** The `banned` store; its soft/reversible status + cooldown
  + evidence + confidence + un-ban path; the dual-substrate (JSON-today / SQLite-when-built) rule; and
  the LOAD-BEARING loop-breaker invariant.
- **Group VG — Three-Gate Wiring.** The [HARD] pre-download, pre-play, and pre-request-honor gates;
  the ban-list consultation at each.
- **Group VR — Offensive-Request Verdict.** The conservative, allow-by-default, identity-hate-only
  verdict; the consumption of the CALLIN-003 CM/CC moderation-floor primitive; the never-ban-
  provocative-art rule.
- Plus **NFRs** (Section 8) and **Risks** (Section 9).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **The duration/size knobs themselves (the shipped hotfix)** — `max_download_mb` /
  `max_download_duration_seconds` and the `slskd`/`ytdlp` threading are ALREADY SHIPPED; VETTING-027
  references them as Tier 1, it does not re-implement or re-tune them.
- **The speech-vs-music DSP engine** — owned by ANALYSIS-006 (which must add the signal); VETTING-027
  CONSUMES the signal, it does not implement the classifier.
- **The acquisition-queue / source-preference logic (WHOM to grab from)** — owned by ACQQUEUE-019;
  VETTING-027 adds an orthogonal accept/reject predicate (IS-THIS-THE-RIGHT-KIND), it does not re-own
  queue ranking.
- **The request lifecycle / request anti-abuse (RS) / request matching (RM)** — owned by REQUEST-011;
  VETTING-027 only applies the offensive verdict at the request-honor gate.
- **The SQLite substrate / the `banned`-table DDL / the JSON→SQLite migration mechanics** — owned by
  DATASTORE-022; VETTING-027 specifies the dual-substrate REQUIREMENT and the recommended `brain.db`
  mapping, not the migration code.
- **The live-call moderation / broadcast-delay / dump path** — owned by CALLIN-003 (Group CD/CM/CC);
  VETTING-027 consumes the moderation FLOOR for the REQUEST path only, never the live-call path.
- **The long-form legitimacy judgement** — owned by LONGFORM-025; VETTING-027 defers and never bans
  for length.
- **A server DB / a hosted moderation service / an external content-classification API** — out of
  scope; brain-local only.
- **Any listener-website surface** — the ban-list is internal/operational only; it is NEVER exposed on
  the public listener site.
- **A retroactive purge of already-on-air non-music** — VETTING-027 vets going forward (pre-download /
  pre-play / pre-request-honor); it does not sweep the existing library (a future enhancement; the
  pre-play gate will catch existing non-music as it comes up for air).
- **A taste / quality / "is this good music" judgement** — VETTING-027 vets KIND (music vs non-music)
  and identity-hate, NOT quality or taste; the director / PROGRAMMING-007 own taste.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain-only + additive.** A vet/ban module on the existing `brain/` package + a `banned`
  store; no new service, no Liquidsoap change, no listener-website surface.
- [HARD] **Exception-isolated.** A vet/ban error logs and is dropped; it NEVER fails a download
  worker, crashes the daemon, blocks the picker, or silences the stream.
- [HARD][LOAD-BEARING] **The loop-breaker invariant.** A post-fetch reject records `AttemptsIndex`
  status != `"success"` AND adds a ban-list row (the cooldown-independent block).
- [HARD] **Cheapest-tier-first cascade.** Duration/size → keyword/category → speech-vs-music; decode
  only for the ambiguous middle.
- [HARD] **Duration alone never bans.** A ban needs ≥2 corroborating signals; long-form music is
  protected; legitimacy of long-form is LONGFORM-025's.
- [HARD] **Soft + reversible ban-list.** Status / cooldown / evidence / confidence / un-ban path.
- [HARD] **Dual substrate.** JSON today (beside `attempts.json`), `brain.db` when DATASTORE-022 ships;
  no hard requirement on the unbuilt SQLite layer.
- [HARD] **Three gates.** Pre-download, pre-play, pre-request-honor.
- [HARD] **Conservative, allow-by-default offensive verdict.** Bans only identity-hate (sexuality-
  bashing / homophobia / racism); never provocative art; consumes CALLIN-003 CM/CC.
- [HARD] **Reference, don't re-own.** ACQQUEUE-019, ANALYSIS-006, REQUEST-011, DATASTORE-022, OPS-004,
  CALLIN-003, LONGFORM-025 are referenced, never restated.
- [HARD][DEPENDENCY] **Tier 3 depends on ANALYSIS-006** adding a speech-vs-music signal (today it
  disclaims speech detection); until then Tier 3 degrades to unavailable (Section 2.1, D-2).
- [HARD] **Resilience.** A ban-store open/write failure logs and degrades to no-ban-store; acquisition
  proceeds exactly as if the ban-list were disabled (the vet still allows-by-default).

---

## 6. Requirements

### Group VC — Vet Cascade

Priority: High.

#### REQ-VC-001 — Tiered cascade, cheapest signal first (Ubiquitous) [HARD]

The system SHALL apply the content vet as a TIERED CASCADE evaluated cheapest-signal-first: Tier 1
duration/size (metadata, pre-download), then Tier 2 keyword/category (metadata), then Tier 3
speech-vs-music (decode-based), so the EXPENSIVE decode-based Tier 3 is reached ONLY for the
ambiguous middle that passes Tiers 1-2 but remains unresolved. [HARD] A candidate clearly accepted or
rejected by a cheaper tier SHALL NOT trigger the more expensive tier. That the vet is a cheapest-first
tiered cascade is the rail; the exact thresholds are config.

**Acceptance criteria:** see acceptance.md AC-VC-001.

#### REQ-VC-002 — Tier 1 reuses the shipped duration/size pre-download cut; never re-owns it (Ubiquitous) [HARD] [consistency]

The system SHALL treat the ALREADY-SHIPPED 200 MB / 2400 s hotfix as the VC Tier 1 pre-download cut:
`Config.max_download_mb` / `max_download_duration_seconds`, threaded through `slskd.acceptable`
(skip a candidate whose `size > max_size_bytes`) and `ytdlp.fetch` (`--max-filesize {max_mb}M` +
`--match-filter "duration < {max_duration_seconds}"`). [HARD] [consistency] VETTING-027 SHALL NOT
re-implement, duplicate, or re-tune these knobs; it references them as the existing Tier 1 and builds
Tiers 2-3 above them. [HARD] Tier 1 is a coarse PATHOLOGICAL-OUTLIER cut (multi-hour / multi-hundred-
MB), explicitly NOT a "long = bad" rule (VK governs). That Tier 1 is the shipped hotfix, referenced
not re-owned, is the rail.

**Acceptance criteria:** see acceptance.md AC-VC-002.

#### REQ-VC-003 — Tier 2: keyword/category metadata signals, no decode (Event-driven) [HARD]

When a candidate passes Tier 1, the system SHALL evaluate Tier 2 KEYWORD/CATEGORY signals from
metadata ONLY (the candidate filename, the slskd response metadata, the yt-dlp metadata) — detecting
non-music markers such as `podcast`, `audiobook`, `interview`, `lecture`, `sermon`, `asmr`,
`full episode`, a chapter-numbering pattern, or a known non-music category — WITHOUT decoding the
audio. [HARD] Tier 2 is metadata-only (no fetch of the full file, no decode); the keyword/category set
is config (a sane default list). A Tier-2 hit is ONE signal that, per VK, must combine with another to
ban (it never bans on its own — a song legitimately titled "Interview" must not be rejected on the
keyword alone). That Tier 2 is metadata-only keyword/category detection is the rail.

**Acceptance criteria:** see acceptance.md AC-VC-003.

#### REQ-VC-004 — Tier 3: decode-based speech-vs-music for the ambiguous middle; depends on ANALYSIS-006 (State-driven) [HARD] [dependency]

While a candidate has passed Tiers 1-2 but remains ambiguous (e.g. a 40-minute file with a clean
title), the system SHALL evaluate Tier 3 — a DECODE-BASED SPEECH-VS-MUSIC signal — to decide whether
the content is talk (speech-dominant) rather than music. [HARD] [dependency] This signal is PRODUCED
by ANALYSIS-006, which TODAY DISCLAIMS speech detection (`brain/analysis.py` extracts BPM/key/energy/
LUFS/cues, not a speech classifier); VETTING-027 DEPENDS on ANALYSIS-006 adding it (Section 2.1).
[HARD] When the speech-vs-music signal is UNAVAILABLE (ANALYSIS-006 not yet extended, or analysis
failed/pending), Tier 3 degrades to UNAVAILABLE and the cascade decides on Tiers 1-2 alone — and per
VK a missing Tier-3 signal NEVER bans on its own (allow-by-default on the ambiguous middle). That
Tier 3 is a decode-based speech-vs-music signal that degrades gracefully when ANALYSIS-006 has not
supplied it is the rail.

**Acceptance criteria:** see acceptance.md AC-VC-004.

#### REQ-VC-005 — Non-music verdict on the air path defaults to reject-the-file, never silence the stream (Unwanted) [HARD]

If the cascade reaches a confident NON-MUSIC verdict for a file at a PRE-PLAY gate, then the system
SHALL exclude that file from going on air (skip it in the picker / mark it not-airable) and SHALL
ensure the picker moves on to the next track — it SHALL NEVER let a non-music verdict cause a SILENCE
or a stall on the air path. [HARD] The vet REMOVES a candidate; it never blocks the stream waiting for
a verdict (the verdict is computed off the <1s pull path, on the background/analysis path, and a
pending verdict defaults to allow so the music keeps playing). That a non-music verdict skips-and-
continues (never silences) is the rail.

**Acceptance criteria:** see acceptance.md AC-VC-005.

### Group VK — Combine-Signals False-Positive Guard

Priority: High.

#### REQ-VK-001 — Duration ALONE never bans; a ban requires ≥2 corroborating signals (Unwanted) [HARD]

The system SHALL NOT ban or reject content on the DURATION (or size) axis ALONE: a ban / vet reject
SHALL require at least TWO corroborating signals across the set {duration-or-size, keyword/category,
speech-vs-music}. [HARD] A long file with no other adverse signal is ALLOWED; a long file is rejected
only when a SECOND signal (a non-music keyword/category AND/OR a speech-dominant Tier-3 classification)
corroborates. This is the central false-positive guard: it prevents a coarse size/duration outlier cut
from ever, by itself, condemning a track. (Tier 1's pre-download pathological-outlier cut is a separate
coarse network-protection measure, not a "ban"; VK governs the BAN/REJECT decision that adds a
`banned` row.) That duration alone never bans and a ban needs ≥2 signals is the rail.

**Acceptance criteria:** see acceptance.md AC-VK-001.

#### REQ-VK-002 — Long-form music is protected (DJ-mix / ambient / full-album / mixtape) (Ubiquitous) [HARD]

The system SHALL PROTECT legitimate LONG-FORM music — a long DJ-mix, a continuous ambient album, a
"full album" upload, a long-form mixtape — from being rejected for its length. [HARD] A long file that
presents as music (no non-music keyword/category, not speech-dominant) SHALL be treated as allowed
regardless of duration; length is NOT evidence of non-music. The station WANTS long-form music. That
long-form music is protected and never rejected on length is the rail.

**Acceptance criteria:** see acceptance.md AC-VK-002.

#### REQ-VK-003 — Long-form legitimacy judgement is deferred to LONGFORM-025 (Ubiquitous) [HARD] [consistency]

The system SHALL DEFER the judgement of whether a long file is LEGITIMATE long-form content (a curated
DJ-mix, an album documentary, an artist retrospective, an era spotlight) to SPEC-RADIO-LONGFORM-025.
[HARD] [consistency] VETTING-027 does NOT decide long-form legitimacy; it only ensures its own vet
NEVER condemns a file for being long (VK-001/002). Where LONGFORM-025 (or its absence) does not
condemn a long file, VETTING-027 treats it as allowed. VETTING-027 SHALL NOT restate or fork
LONGFORM-025's long-form criteria. That long-form legitimacy is LONGFORM-025's and VETTING-027 only
guarantees no-ban-for-length is the rail.

**Acceptance criteria:** see acceptance.md AC-VK-003.

### Group VB — Ban-List Store + Lifecycle

Priority: High (VB-001/002/005) / Medium (VB-003/004/006).

#### REQ-VB-001 — Loop-breaker: a post-fetch reject records attempts != "success" AND adds a ban row (Event-driven) [HARD] [LOAD-BEARING]

When a fetch lands a file that the vet then REJECTS (a post-fetch reject), the system SHALL (a) record
the `AttemptsIndex` outcome with a status that is NOT `"success"` (so `should_skip` does not treat the
key as permanently done), AND (b) add a `banned` row for that content/key. [HARD] [LOAD-BEARING] BOTH
writes are mandatory and together are the LOOP-BREAKER: without the ban row, `AttemptsIndex.should_skip`
returns `False` again once `RETRY_COOLDOWN` (6h) elapses (`brain/acquire.py` lines 81-89, 34), and the
brain re-searches → re-fetches the SAME rejected file → re-rejects → re-deletes → forever (an unbounded
fetch→delete→re-fetch loop). The `banned` row is the durable, cooldown-INDEPENDENT block that
`enqueue` / `_acquire_one` consult (VG) BEFORE re-searching. [HARD] The system SHALL NOT record
`"success"` for a rejected fetch (the file is gone; a false `"success"` would also mislead any consumer
of the attempts log). That a post-fetch reject writes attempts!="success" AND a ban row is the rail —
this is the heart of the SPEC.

**Acceptance criteria:** see acceptance.md AC-VB-001.

#### REQ-VB-002 — The `banned` store: status / cooldown / evidence / confidence (Ubiquitous) [HARD]

The system SHALL persist a `banned` store whose every record carries at least: a `key` (the content/
identity the ban applies to — the `normalize_key(artist,title)` slug for the request/wishlist axis, or
a content/file identity where a specific landed file is the culprit); a `status` (at least `banned`
and `pending_review`); a `cooldown` (a time bound after which the ban may be re-evaluated, distinct
from a permanent block); the `evidence` (which tiers/signals fired and their values — e.g.
`keyword=podcast`, `speech_likelihood=0.91`, `duration_s=7200`); a `confidence` (how sure the verdict
is); and a `created_at` / `updated_at`. [HARD] The exact column/field layout is implementation detail
bounded by the dual-substrate rule (REQ-VB-005); that a ban record carries status + cooldown +
evidence + confidence (the soft-ban fieldset) is the rail.

**Acceptance criteria:** see acceptance.md AC-VB-002.

#### REQ-VB-003 — Bans are SOFT (a revisable hypothesis, not a permanent blacklist) (Ubiquitous) [HARD]

The system SHALL treat a ban as a SOFT, revisable hypothesis rather than a permanent blacklist: a ban
has a `status` and a `cooldown` so it can be re-evaluated, downgraded (`banned` → `pending_review`), or
cleared, and a higher-confidence LATER signal (or an operator action, REQ-VB-004) can revise it.
[HARD] A ban SHALL NOT be an irreversible, silent permanent deletion of a possibility. The `evidence`
+ `confidence` on the record make a ban auditable and revisable. That bans are soft/revisable, not
permanent, is the rail.

**Acceptance criteria:** see acceptance.md AC-VB-003.

#### REQ-VB-004 — An explicit UN-BAN path exists (operator and/or signal-driven) (Event-driven) — Priority Medium

When an operator (or a higher-confidence later signal) determines a ban was wrong or should be lifted,
the system SHALL provide an explicit UN-BAN path that clears or downgrades the `banned` record so the
content is once again eligible for acquisition/play/request-honor. [HARD-adjacent] The un-ban is an
auditable mutation of the `banned` store (it records WHO/WHAT un-banned and WHEN), and after an un-ban
the VG gates SHALL no longer block the content on the cleared ban. The un-ban surface (an operator
toggle, a config-driven clear, and/or an automatic downgrade on a contradicting later signal) is
implementation detail; that an explicit un-ban path exists and is honored by the gates is the rail.

**Acceptance criteria:** see acceptance.md AC-VB-004.

#### REQ-VB-005 — Dual substrate: works on JSON today, maps to DATASTORE-022 `brain.db` when built (Ubiquitous) [HARD] [consistency]

The system SHALL implement the `banned` store so that it (a) WORKS TODAY on the JSON substrate —
brain-local, coexisting with the JSON `AttemptsIndex` (`attempts.json`) without requiring the
unbuilt SQLite layer — AND (b) MAPS to SPEC-RADIO-DATASTORE-022's partitioned SQLite WHEN that ships,
with the RECOMMENDED placement being `brain.db` (core-operational, consulted on the acquisition path,
and co-locatable with the `attempts` write so the loop-breaker's two writes can share a file — cf.
DATASTORE-022 REQ-DP-003's one-atomic-grab-write rationale). [HARD] [consistency] VETTING-027 SHALL
NOT hard-require the unbuilt SQLite layer; when DATASTORE-022's idempotent JSON→SQLite migration runs,
the `banned` store migrates with it under the same keep-JSON-as-backup + idempotent-upsert posture
(REQ-DM-001/002/003). The `banned` TABLE's substrate placement is DATASTORE-022's to finalize;
VETTING-027 owns the dual-substrate REQUIREMENT and the recommended mapping. That the ban-list works
on JSON today and maps cleanly to `brain.db` later (no hard SQLite dependency) is the rail.

**Acceptance criteria:** see acceptance.md AC-VB-005.

#### REQ-VB-006 — Enable toggle; disabled is exactly today's behavior (Ubiquitous) — Priority Medium

The system SHALL provide a CONFIG enable toggle for the vet/ban subsystem. [HARD] When DISABLED,
acquisition / play / request-honor run EXACTLY as today (no vet runs beyond the already-shipped Tier 1
size/duration cut, no `banned` store is consulted or written, the gates are pass-through); when
ENABLED, the cascade + the ban-list + the three gates operate per Groups VC/VK/VB/VG/VR. [HARD] The
toggle (plus the keyword list, the speech thresholds, the ban-store path, and the cooldown defaults)
are the only config surface this SPEC adds, beside the shipped Tier-1 knobs. That the subsystem is
opt-in/additive and disabling it restores today's behavior is the rail.

**Acceptance criteria:** see acceptance.md AC-VB-006.

### Group VG — Three-Gate Wiring

Priority: High.

#### REQ-VG-001 — PRE-DOWNLOAD gate: vet + ban check before fetching a candidate (Event-driven) [HARD]

When the acquisition path is about to FETCH a candidate (the `enqueue` / `_acquire_one` /
`_try_slskd` / `_try_ytdlp` decision point, and the `slskd.acceptable` / `best_candidate` ranking),
the system SHALL run the PRE-DOWNLOAD gate: consult the `banned` store (short-circuit if the key is
banned and not in a cleared/cooldown-elapsed state) AND apply the metadata-only vet tiers (Tier 1
size/duration — the shipped cut — and Tier 2 keyword/category) to the candidate. [HARD] A banned key
SHALL be short-circuited BEFORE a new search/fetch is issued (this is where the loop-breaker pays off —
a previously-rejected file is never re-fetched). This gate attaches to the ACQQUEUE-019 hook;
ACQQUEUE-019 owns queue ranking, VETTING-027 adds the vet/ban predicate. That a pre-download gate
consults the ban-list + the metadata tiers before fetching is the rail.

**Acceptance criteria:** see acceptance.md AC-VG-001.

#### REQ-VG-002 — PRE-PLAY gate: vet + ban check before a file goes on air (Event-driven) [HARD]

When a landed/queued file is about to go ON AIR (the picker / air-path selection point), the system
SHALL run the PRE-PLAY gate: consult the `banned` store AND apply the vet (including Tier 3
speech-vs-music where ANALYSIS-006 has supplied the signal) to confirm the file is music, not talk.
[HARD] A confident non-music verdict at the pre-play gate SKIPS the file and triggers the post-fetch
reject path (REQ-VB-001: record attempts != `"success"` + add a ban row) — this is the gate that
INTRODUCES the post-land reject the loop-breaker presumes (Section 2.2). [HARD] The pre-play vet runs
OFF the <1s pull path (on the background/analysis path) and a PENDING verdict defaults to allow, so the
gate NEVER silences or stalls the stream (REQ-VC-005, NFR-V-1). That a pre-play gate confirms music
before air and routes a non-music verdict through the loop-breaker, without ever silencing the stream,
is the rail.

**Acceptance criteria:** see acceptance.md AC-VG-002.

#### REQ-VG-003 — PRE-REQUEST-HONOR gate: offensive-request verdict before honoring a request (Event-driven) [HARD]

When a listener REQUEST is about to be HONORED (the REQUEST-011 request-ingest / honor decision point),
the system SHALL run the PRE-REQUEST-HONOR gate: apply the offensive-request verdict (Group VR) and
consult the `banned` store, so a request for identity-hate content (sexuality-bashing / homophobia /
racism) is NOT honored, while a provocative-but-allowed request proceeds. [HARD] This gate attaches to
the REQUEST-011 ingest hook (REQUEST-011's RS anti-abuse group has no code yet); VETTING-027 applies
the verdict, REQUEST-011 owns the request lifecycle. That a pre-request-honor gate applies the
offensive verdict + the ban-list before honoring a request is the rail.

**Acceptance criteria:** see acceptance.md AC-VG-003.

#### REQ-VG-004 — Every gate is exception-isolated and fails toward continuous operation (Unwanted) [HARD]

If any gate's vet or ban check raises or fails (a vet exception, a ban-store read error, a missing
signal), then the system SHALL log the error and DEGRADE so that continuous operation is preserved:
the pre-download and pre-request gates fail toward NOT-blocking (allow-by-default — a vet failure must
not stop legitimate acquisition or a legitimate request), and the pre-play gate fails toward ALLOW (the
music keeps playing; a failed vet never silences the stream). [HARD] A gate failure SHALL NEVER crash a
download worker, the picker, the director loop, or the request path. The ONLY exception to
allow-by-default is a CONFIRMED `banned` row (an explicit prior verdict), which the gates honor; an
UNCERTAIN/errored vet allows. That every gate is exception-isolated and fails toward continuous
operation (allow-by-default on uncertainty, honor only confirmed bans) is the rail.

**Acceptance criteria:** see acceptance.md AC-VG-004.

### Group VR — Offensive-Request Verdict

Priority: High (VR-001/002/003) / Medium (VR-004).

#### REQ-VR-001 — Conservative, allow-by-default; bans ONLY identity-hate (Ubiquitous) [HARD]

The system SHALL apply the offensive-request verdict CONSERVATIVELY and ALLOW-BY-DEFAULT: it SHALL
ban a request ONLY when the request targets IDENTITY-HATE — specifically sexuality-bashing /
homophobia / racism. [HARD] Any request that is not a clear identity-hate target is ALLOWED. The
default verdict for an uncertain or borderline request is ALLOW (the conservative direction here is
toward permitting, not toward censoring). That the verdict is allow-by-default and bans only
identity-hate is the rail.

**Acceptance criteria:** see acceptance.md AC-VR-001.

#### REQ-VR-002 — NEVER bans provocative art, dark themes, explicit language, or political edge (Unwanted) [HARD]

The system SHALL NOT ban a request for being provocative, transgressive, dark, sexually explicit,
profane, politically edgy, or merely uncomfortable. [HARD] The station's identity is art-forward and
UNSANITIZED; the offensive verdict targets identity-HATE (an attack on people for who they are), NOT
provocative ART (which may be challenging, explicit, or dark without attacking an identity). A track
that is explicit, violent in theme, or politically charged but does NOT promote sexuality-bashing /
homophobia / racism is ALLOWED. That provocative art is never banned (only identity-hate is) is the
rail.

**Acceptance criteria:** see acceptance.md AC-VR-002.

#### REQ-VR-003 — Consumes the CALLIN-003 moderation-floor primitive; does not re-own it (Ubiquitous) [HARD] [consistency]

The system SHALL CONSUME the SPEC-RADIO-CALLIN-003 moderation-floor primitive (Group CM fail-closed
moderation + Group CC conduct rules — the identity-hate floor CALLIN-003 defines, SPEC-only / no code)
and apply it to the REQUEST path at the pre-request-honor gate (VG-003). [HARD] [consistency]
VETTING-027 SHALL NOT restate, fork, or weaken CALLIN-003's moderation floor; CALLIN-003 OWNS the
identity-hate floor + the conduct semantics (and the live-call path), and VETTING-027 APPLIES that
floor to listener REQUESTS. Where CALLIN-003 is not yet built, VETTING-027's verdict operates on the
same identity-hate definition (sexuality-bashing / homophobia / racism) as a forward-compatible
standalone, to be reconciled to CALLIN-003's floor when it lands. That VR consumes CALLIN-003's floor
(applied to requests) and never re-owns it is the rail.

**Acceptance criteria:** see acceptance.md AC-VR-003.

#### REQ-VR-004 — An identity-hate ban is a soft, reviewable ban-list entry (Event-driven) — Priority Medium

When the offensive verdict bans a request for identity-hate, the system SHALL record it as a SOFT,
reviewable `banned` entry (Group VB) — with `status`, `evidence` (the identity-hate signal), and
`confidence` — rather than a silent permanent block, so a mis-classified request (a false positive on
the conservative verdict) can be reviewed and un-banned (REQ-VB-004). [HARD-adjacent] Consistency with
VB: the offensive verdict uses the SAME soft/reversible ban-list, not a separate permanent denylist,
so even an identity-hate ban is auditable and correctable. That an identity-hate ban is a soft,
reviewable VB entry (not a silent permanent block) is the rail.

**Acceptance criteria:** see acceptance.md AC-VR-004.

---

## 7. User-Provisioned Prerequisites (the real user must provide / decide)

[HARD] VETTING-027 provisions no external account or hardware. The following are flagged so the user
knows what is required / decided:

- **The keyword/category list + the speech-vs-music thresholds.** REQ-VC-003/004 ship sane defaults;
  the operator may tune the non-music keyword set and the `speech_likelihood` ban threshold for their
  catalog.
- **The cooldown + confidence defaults.** REQ-VB-002/003 ship sane defaults; the operator may tune the
  ban cooldown and the confidence floor at which a single-pass verdict is recorded.
- **The ANALYSIS-006 extension (for Tier 3).** Until ANALYSIS-006 adds a speech-vs-music signal, Tier 3
  is unavailable and the cascade decides on Tiers 1-2 (allow-by-default on the ambiguous middle). The
  user/orchestrator confirms ANALYSIS-006 will add it (D-2).
- **The substrate decision.** The `banned` store is JSON today; the user/orchestrator confirms the
  DATASTORE-022 mapping (RECOMMENDED `brain.db`) when 022 ships (D-1).
- **The CALLIN-003 reconciliation.** The offensive verdict uses CALLIN-003's identity-hate floor; the
  user/orchestrator confirms the reconciliation when CALLIN-003 is built (D-4).

---

## 8. Non-Functional Requirements

### NFR-V-1 — Never blocks / silences playout (Ubiquitous) — Priority High
All vet computation (especially the decode-based Tier 3) and all ban-store writes shall run OFF the
`<1s /api/next` pull path (on the acquisition / background / analysis path); a pending or in-progress
vet verdict defaults to ALLOW so the picker never waits and the stream is never silenced. Inherits
CORE-001's continuous-operation identity. See acceptance.md AC-NFR-V-1.

### NFR-V-2 — Exception-isolated; never crashes acquisition or playout (Ubiquitous) — Priority High
A vet or ban-store error (open/read/write failure, a corrupt store, a missing signal, a classifier
exception) shall LOG via `log_event` and degrade gracefully — it shall NEVER raise into a download
worker, the picker, the director loop, or the request path, never crash the daemon, and never silence
the stream (REQ-VG-004). A failed vet allows-by-default; only a confirmed `banned` row blocks.
See acceptance.md AC-NFR-V-2.

### NFR-V-3 — Single-source-of-truth: reference siblings, never re-own (Ubiquitous) — Priority High [consistency]
No code path shall re-own or fork the shipped Tier-1 hotfix knobs, ACQQUEUE-019's queue ranking,
ANALYSIS-006's DSP engine, REQUEST-011's request lifecycle, DATASTORE-022's SQLite substrate,
CALLIN-003's moderation floor, or LONGFORM-025's long-form criteria; each is referenced by id and
consumed/extended/applied. VETTING-027 owns the cascade logic + the combine-signals guard + the
ban-list + the gates + the offensive verdict only, and is brain-only + additive (a vet/ban module +
a `banned` store; no new service, no listener-website surface, no server DB). See acceptance.md
AC-NFR-V-3.

### NFR-V-4 — Conservative / low-false-positive by construction (Ubiquitous) — Priority High
The vet shall be CONSERVATIVE: it shall not reject legitimate music. The combine-signals guard
(≥2 signals, duration-alone-never-bans, VK), the long-form protection (VK-002), the allow-by-default
on a missing/uncertain signal (VC-004, VG-004), and the allow-by-default offensive verdict (VR-001)
together bound the false-positive rate. A single weak signal never bans; uncertainty allows.
See acceptance.md AC-NFR-V-4.

### NFR-V-5 — Cheapest-first / cost-bounded (Ubiquitous) — Priority Medium
The cascade shall be cost-bounded: the expensive decode-based Tier 3 runs ONLY for the ambiguous
middle (REQ-VC-001), and Tiers 1-2 are metadata-only (no decode, no full-file fetch). The vet shall
add NO new external network call of its own (it reuses the existing slskd/yt-dlp metadata and the
ANALYSIS-006 decode that already runs). See acceptance.md AC-NFR-V-5.

### NFR-V-6 — Brain-only, additive; bounded config surface (Ubiquitous) — Priority Medium
No code path shall add a new service, daemon, Liquidsoap change, or listener-website surface: the
change is a brain-only vet/ban module on the existing `brain/` package + a `banned` store (JSON today,
`brain.db` when DATASTORE-022 ships), with a bounded `BRAIN_*` config surface (enable toggle, keyword
list, speech thresholds, ban-store path, cooldown/confidence defaults) beside the shipped Tier-1 knobs.
See acceptance.md AC-NFR-V-6.

### NFR-V-7 — The loop-breaker holds: no unbounded fetch→delete→re-fetch loop (Ubiquitous) — Priority High [LOAD-BEARING]
The system shall guarantee that a post-fetch reject does NOT recur into an unbounded fetch→delete→
re-fetch loop: because a post-fetch reject records `AttemptsIndex` status != `"success"` AND adds a
durable `banned` row (REQ-VB-001), and because the pre-download gate (VG-001) consults the `banned`
store BEFORE re-searching, a rejected file is never re-fetched (the ban is cooldown-independent and
survives restart). This is the load-bearing correctness property of the SPEC. See acceptance.md
AC-NFR-V-7.

---

## 9. Open Questions / Risks

- **R-V-1 — ANALYSIS-006 does not yet produce a speech-vs-music signal (Medium, dependency).** Tier 3
  needs a decode-based speech classification ANALYSIS-006 disclaims today. Mitigated: Tier 3 degrades
  to unavailable and the cascade decides on Tiers 1-2 (allow-by-default on the ambiguous middle, VK);
  a missing signal never bans. **Needs ANALYSIS-006 to add the field (D-2).**
- **R-V-2 — No post-fetch delete path exists today (Medium, dependency).** `_acquire_one` records a
  landed file `"success"` unconditionally; there is no reject/delete branch yet. The pre-play vet (VG)
  introduces it, and that is exactly where the loop-breaker must fire. Mitigated: the SPEC specifies
  both together (the vet creates the reject, the ban makes it durable). **Surfaced as D-3.**
- **R-V-3 — DATASTORE-022 substrate not built (Low/Medium, dependency).** The `banned` store maps to
  `brain.db` when 022 ships but must work on JSON today. Mitigated: the dual-substrate requirement
  (REQ-VB-005) mandates JSON-today coexistence with `attempts.json` and a clean later migration.
  **Surfaced as D-1.**
- **R-V-4 — CALLIN-003 moderation floor is SPEC-only (Low/Medium, dependency).** The offensive verdict
  consumes a primitive with no code yet. Mitigated: VR operates on the same identity-hate definition as
  a forward-compatible standalone, reconciled to CALLIN-003's floor when it lands (REQ-VR-003).
  **Surfaced as D-4.**
- **R-V-5 — False positives on legitimate music (Medium, correctness).** A song titled "Interview",
  "Sermon", or "Podcast", or a sparse-vocal track read as speech, could be wrongly flagged. Mitigated:
  the combine-signals guard (≥2 signals, VK-001), the long-form protection (VK-002), and
  allow-by-default-on-uncertainty (NFR-V-4) mean a single weak signal never bans; the soft/reversible
  ban + un-ban path (VB-003/004) makes any false positive correctable.
- **R-V-6 — Over-reach of the offensive verdict (Medium, identity).** An over-eager verdict could
  censor provocative art and erode the station's identity. Mitigated: the conservative allow-by-default
  posture (VR-001), the explicit never-ban-provocative-art rule (VR-002), and the soft/reviewable ban
  (VR-004) bound it; the verdict bans ONLY identity-hate.
- **R-V-7 — bhive had no proven pattern for this stack (Low, recorded gap).** No bhive instruction
  exists for a tiered non-music vet + a ban-list-as-loop-breaker on this radio stack. Mitigated:
  grounded in the codebase (`AttemptsIndex` / `should_skip` / `RETRY_COOLDOWN`, the shipped Tier-1
  hotfix, the slskd/ytdlp seams). Action: re-run a bhive query during implementation and contribute
  back per AGENTS.md.

---

## 10. Design Decisions Needing the Orchestrator's Ruling

These are surfaced (not silently assumed) for an explicit ruling before/within the Run phase:

- **D-1 — `banned`-store substrate (decides REQ-VB-005).** JSON today (coexisting with
  `attempts.json`) mapping to DATASTORE-022's `brain.db` when built. RECOMMENDATION: `brain.db` (core-
  operational, on the acquisition path, co-locatable with the `attempts` write so the loop-breaker's
  two writes share a file per REQ-DP-003's one-atomic-grab-write rationale), NOT `events.db`. Confirm
  the mapping when DATASTORE-022 ships.
- **D-2 — ANALYSIS-006 must add a speech-vs-music signal (blocks REQ-VC-004 Tier 3).** ANALYSIS-006's
  feature record must add a `speech_likelihood` (or equivalent) field (today it disclaims speech
  detection). RECOMMENDATION: ANALYSIS-006 adds it (an `AT`/`AM`-family requirement); until then Tier 3
  is unavailable and the cascade decides on Tiers 1-2. Confirm ANALYSIS-006 will provide it.
- **D-3 — Where the post-fetch reject/delete lives (decides REQ-VG-002 / REQ-VB-001 wiring).** No
  post-land reject exists today; the pre-play vet introduces it. RECOMMENDATION: the reject is a
  branch in/after `_acquire_one`'s post-land path (and/or the picker's pre-play check) that, on a
  confident non-music verdict, removes the file, records attempts != `"success"`, and adds the ban row
  — the two-write loop-breaker. Confirm the exact insertion point in the Run phase.
- **D-4 — CALLIN-003 reconciliation (decides REQ-VR-003).** The offensive verdict consumes CALLIN-003's
  identity-hate floor (SPEC-only today). RECOMMENDATION: VR runs as a forward-compatible standalone on
  the same identity-hate definition now, reconciled to CALLIN-003's CM/CC floor when CALLIN-003 is
  built. Confirm the reconciliation posture.

---

## 11. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 + the
Section 10 deferrals, as the mandatory exclusions list):

- **Re-implementing or re-tuning the shipped Tier-1 duration/size hotfix** — `max_download_mb` /
  `max_download_duration_seconds` and the slskd/ytdlp threading are ALREADY shipped; VETTING-027
  references them as Tier 1 (REQ-VC-002, NFR-V-3).
- **The speech-vs-music DSP engine itself** — owned by ANALYSIS-006 (which must add the signal);
  VETTING-027 consumes the signal, never implements the classifier (REQ-VC-004, NFR-V-3).
- **ACQQUEUE-019's queue ranking / source-preference (WHOM to grab from)** — VETTING-027 adds an
  orthogonal accept/reject predicate (IS-THIS-THE-RIGHT-KIND), never re-owns queue ranking (NFR-V-3).
- **REQUEST-011's request lifecycle / RM matching / RS anti-abuse** — VETTING-027 only applies the
  offensive verdict at the request-honor gate (REQ-VG-003, NFR-V-3).
- **DATASTORE-022's SQLite substrate / the `banned`-table DDL / the JSON→SQLite migration code** —
  VETTING-027 owns the dual-substrate REQUIREMENT + the recommended `brain.db` mapping, not the
  migration mechanics (REQ-VB-005, NFR-V-3).
- **CALLIN-003's live-call moderation / broadcast-delay / dump path** — VETTING-027 consumes the
  moderation FLOOR for the REQUEST path only, never the live-call path (REQ-VR-003, NFR-V-3).
- **LONGFORM-025's long-form legitimacy judgement** — VETTING-027 defers and never bans for length
  (REQ-VK-003, NFR-V-3).
- **A taste / quality / "is this good music" judgement** — VETTING-027 vets KIND (music vs non-music)
  and identity-hate, NOT taste or quality (Section 4.2).
- **Banning provocative art / dark themes / explicit language / political edge** — only identity-hate
  is banned; the station is art-forward and unsanitized (REQ-VR-002).
- **Banning on duration alone / rejecting long-form music for its length** — a ban needs ≥2
  corroborating signals; long-form music is protected (REQ-VK-001/002).
- **A permanent / irreversible blacklist** — bans are SOFT and REVERSIBLE with an un-ban path
  (REQ-VB-003/004).
- **A server DB / a hosted moderation service / an external content-classification API** — brain-local
  only; no new external call (NFR-V-5/6).
- **Any listener-website surface** — the ban-list is internal/operational only; never exposed on the
  public listener site (Section 4.2).
- **A retroactive sweep/purge of the existing library** — VETTING-027 vets going forward; the pre-play
  gate catches existing non-music as it comes up for air (Section 4.2).
- **A new service, a Liquidsoap change, or hard-requiring the unbuilt SQLite layer** — brain-only +
  additive; JSON-today substrate (REQ-VB-005, NFR-V-6).

---

## 12. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements are in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-VC-001 | Vet Cascade | High | Ubiquitous | AC-VC-001 |
| REQ-VC-002 | Vet Cascade | High | Ubiquitous | AC-VC-002 |
| REQ-VC-003 | Vet Cascade | High | Event | AC-VC-003 |
| REQ-VC-004 | Vet Cascade | High | State | AC-VC-004 |
| REQ-VC-005 | Vet Cascade | High | Unwanted | AC-VC-005 |
| REQ-VK-001 | Combine-Signals Guard | High | Unwanted | AC-VK-001 |
| REQ-VK-002 | Combine-Signals Guard | High | Ubiquitous | AC-VK-002 |
| REQ-VK-003 | Combine-Signals Guard | High | Ubiquitous | AC-VK-003 |
| REQ-VB-001 | Ban-List Store + Lifecycle | High | Event | AC-VB-001 |
| REQ-VB-002 | Ban-List Store + Lifecycle | High | Ubiquitous | AC-VB-002 |
| REQ-VB-003 | Ban-List Store + Lifecycle | High | Ubiquitous | AC-VB-003 |
| REQ-VB-004 | Ban-List Store + Lifecycle | Medium | Event | AC-VB-004 |
| REQ-VB-005 | Ban-List Store + Lifecycle | High | Ubiquitous | AC-VB-005 |
| REQ-VB-006 | Ban-List Store + Lifecycle | Medium | Ubiquitous | AC-VB-006 |
| REQ-VG-001 | Three-Gate Wiring | High | Event | AC-VG-001 |
| REQ-VG-002 | Three-Gate Wiring | High | Event | AC-VG-002 |
| REQ-VG-003 | Three-Gate Wiring | High | Event | AC-VG-003 |
| REQ-VG-004 | Three-Gate Wiring | High | Unwanted | AC-VG-004 |
| REQ-VR-001 | Offensive-Request Verdict | High | Ubiquitous | AC-VR-001 |
| REQ-VR-002 | Offensive-Request Verdict | High | Unwanted | AC-VR-002 |
| REQ-VR-003 | Offensive-Request Verdict | High | Ubiquitous | AC-VR-003 |
| REQ-VR-004 | Offensive-Request Verdict | Medium | Event | AC-VR-004 |
| NFR-V-1 | Non-Functional | High | Ubiquitous | AC-NFR-V-1 |
| NFR-V-2 | Non-Functional | High | Ubiquitous | AC-NFR-V-2 |
| NFR-V-3 | Non-Functional | High | Ubiquitous | AC-NFR-V-3 |
| NFR-V-4 | Non-Functional | High | Ubiquitous | AC-NFR-V-4 |
| NFR-V-5 | Non-Functional | Medium | Ubiquitous | AC-NFR-V-5 |
| NFR-V-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-V-6 |
| NFR-V-7 | Non-Functional | High | Ubiquitous | AC-NFR-V-7 |

Parity: 22 REQ + 7 NFR = 29 specified items; 29 acceptance entries (22 AC + 7 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: VC (Vet Cascade) = 5, VK (Combine-Signals Guard) = 3, VB (Ban-List Store
+ Lifecycle) = 6, VG (Three-Gate Wiring) = 4, VR (Offensive-Request Verdict) = 4 → 5+3+6+4+4 = 22 REQ
across 5 groups. NFR-V-1…7 = 7 NFR. Total = 22 + 7 = 29 specified items, 29 acceptance entries,
1:1 REQ↔AC.
