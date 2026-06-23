---
id: SPEC-RADIO-VETTING-027-acceptance
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-VETTING-027
---

# SPEC-RADIO-VETTING-027 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR). Section B
carries detailed Given-When-Then scenarios for the load-bearing, boundary, and resilience-critical
requirements. Section C is the Definition of Done and the quality gates.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where a
criterion is marked [HARD] it is a must-pass gate (no compensation by other criteria).

Group prefixes: VC (Vet Cascade) / VK (Combine-Signals Guard) / VB (Ban-List Store + Lifecycle) /
VG (Three-Gate Wiring) / VR (Offensive-Request Verdict).
22 AC + 7 AC-NFR = 29, matching spec.md 22 REQ + 7 NFR.

---

## Section A — Per-Requirement Acceptance

### Group VC — Vet Cascade

**AC-VC-001 (REQ-VC-001 — tiered cascade, cheapest signal first):**
- GIVEN a candidate/file to vet, WHEN the vet runs, THEN it evaluates Tier 1 (duration/size,
  metadata) first, then Tier 2 (keyword/category, metadata) only if Tier 1 did not decide, then
  Tier 3 (speech-vs-music, decode) only for the ambiguous middle that Tiers 1-2 left unresolved.
- [HARD] A candidate clearly accepted or rejected by a cheaper tier does NOT trigger the more
  expensive tier (asserted: a Tier-1/Tier-2 decision short-circuits before any decode runs).

**AC-VC-002 (REQ-VC-002 — Tier 1 reuses the shipped hotfix; never re-owns it):**
- GIVEN the shipped 200 MB / 2400 s hotfix (`max_download_mb` / `max_download_duration_seconds`
  through `slskd.acceptable` `max_size_bytes` and `ytdlp.fetch` `--max-filesize` / `--match-filter`),
  WHEN VETTING-027 defines Tier 1, THEN it references those knobs as Tier 1 and does NOT
  re-implement, duplicate, or re-tune them.
- [HARD] [consistency] Tier 1 is the shipped pathological-outlier cut, not a "long = bad" rule, and
  is referenced not re-owned (asserted: no second size/duration cap is introduced; the existing
  knobs are the only Tier-1 source).

**AC-VC-003 (REQ-VC-003 — Tier 2: keyword/category metadata, no decode):**
- GIVEN a candidate that passed Tier 1, WHEN Tier 2 runs, THEN it evaluates keyword/category signals
  from metadata ONLY (filename, slskd metadata, yt-dlp metadata) — e.g. `podcast`, `audiobook`,
  `interview`, `lecture`, `sermon`, `asmr`, `full episode`, chapter-numbering, known non-music
  category — without decoding the audio.
- [HARD] Tier 2 is metadata-only (no full-file fetch, no decode), and a Tier-2 hit is ONE signal that
  alone never bans (asserted: a song legitimately titled "Interview" is not rejected on the keyword
  alone — VK).

**AC-VC-004 (REQ-VC-004 — Tier 3: decode speech-vs-music; depends on ANALYSIS-006, degrades):**
- GIVEN a candidate that passed Tiers 1-2 but remains ambiguous, WHEN Tier 3 runs AND ANALYSIS-006
  has supplied a speech-vs-music signal, THEN the vet uses that signal to judge talk-vs-music.
- [HARD] [dependency] WHEN the speech-vs-music signal is UNAVAILABLE (ANALYSIS-006 not yet extended,
  or analysis failed/pending), Tier 3 degrades to unavailable, the cascade decides on Tiers 1-2 only,
  and a missing Tier-3 signal NEVER bans on its own (allow-by-default on the ambiguous middle —
  asserted by the Section B degradation scenario).

**AC-VC-005 (REQ-VC-005 — non-music verdict on air skips, never silences):**
- GIVEN a confident non-music verdict for a file at a pre-play gate, WHEN the picker selects, THEN
  the file is excluded/marked-not-airable and the picker moves to the next track.
- [HARD] A non-music verdict NEVER causes a silence or a stall; the verdict is computed off the <1s
  pull path and a pending verdict defaults to allow (asserted by the Section B never-silence
  scenario).

### Group VK — Combine-Signals Guard

**AC-VK-001 (REQ-VK-001 — duration alone never bans; ≥2 signals required):**
- GIVEN a file with ONLY an adverse duration/size signal and no other, WHEN the vet decides, THEN it
  does NOT ban/reject — a ban requires at least TWO corroborating signals across {duration-or-size,
  keyword/category, speech-vs-music}.
- [HARD] Duration alone never bans; a long file is rejected only when a second signal corroborates
  (asserted by the Section B combine-signals scenario).

**AC-VK-002 (REQ-VK-002 — long-form music is protected):**
- GIVEN a long file that presents as music (no non-music keyword/category, not speech-dominant) —
  a DJ-mix, an ambient album, a "full album", a long mixtape — WHEN the vet decides, THEN it treats
  the file as allowed regardless of duration.
- [HARD] Length is not evidence of non-music; long-form music is never rejected on length (asserted:
  a 90-minute music-presenting file is allowed).

**AC-VK-003 (REQ-VK-003 — long-form legitimacy deferred to LONGFORM-025):**
- GIVEN a long file whose long-form legitimacy is in question, WHEN VETTING-027 vets it, THEN it does
  NOT decide long-form legitimacy and defers that judgement to LONGFORM-025, only guaranteeing its
  own vet never condemns the file for length.
- [HARD] [consistency] VETTING-027 does not restate or fork LONGFORM-025's long-form criteria; a long
  file LONGFORM-025 (or its absence) does not condemn is treated as allowed (asserted: no
  length-based ban; deferral is by reference).

### Group VB — Ban-List Store + Lifecycle

**AC-VB-001 (REQ-VB-001 — loop-breaker: attempts != "success" AND a ban row):**
- GIVEN a fetch that lands a file the vet then REJECTS (a post-fetch reject), WHEN the reject is
  recorded, THEN the system (a) records the `AttemptsIndex` outcome with a status that is NOT
  `"success"`, AND (b) adds a `banned` row for that content/key.
- [HARD] [LOAD-BEARING] BOTH writes occur; the system does NOT record `"success"` for a rejected
  fetch; the `banned` row is the cooldown-independent block consulted before re-searching (asserted
  by the Section B loop-breaker scenario — the canonical test of this SPEC).

**AC-VB-002 (REQ-VB-002 — ban record fieldset: status / cooldown / evidence / confidence):**
- GIVEN a ban is recorded, WHEN the `banned` row is written, THEN it carries at least: a `key`
  (the `normalize_key` slug or a content/file identity), a `status` (≥ `banned` and `pending_review`),
  a `cooldown`, the `evidence` (which tiers/signals fired + their values), a `confidence`, and
  `created_at` / `updated_at`.
- [HARD] The soft-ban fieldset (status + cooldown + evidence + confidence) is present on every ban
  record (asserted: a written ban row exposes all required fields).

**AC-VB-003 (REQ-VB-003 — bans are soft / revisable, not permanent):**
- GIVEN a ban, WHEN it is later re-evaluated (a contradicting higher-confidence signal, an elapsed
  cooldown, or an operator action), THEN the ban can be downgraded (`banned` → `pending_review`) or
  cleared.
- [HARD] A ban is NOT an irreversible silent permanent deletion; its `evidence` + `confidence` make
  it auditable and revisable (asserted: a ban is downgradable/clearable, not write-once-permanent).

**AC-VB-004 (REQ-VB-004 — explicit un-ban path honored by the gates):**
- GIVEN an operator (or a higher-confidence later signal) lifts a ban, WHEN the un-ban runs, THEN the
  `banned` record is cleared/downgraded, the mutation is auditable (records who/what + when), and the
  VG gates no longer block the content on the cleared ban.
- An explicit un-ban path exists and is honored by all three gates after it runs (asserted: after
  un-ban, the pre-download/pre-play/pre-request gates allow the previously-banned content).

**AC-VB-005 (REQ-VB-005 — dual substrate: JSON today, `brain.db` when DATASTORE-022 ships):**
- GIVEN DATASTORE-022 is not yet built, WHEN the ban-list operates, THEN it works on a brain-local
  JSON substrate coexisting with the JSON `AttemptsIndex` (`attempts.json`) without requiring the
  SQLite layer; AND its design maps cleanly to DATASTORE-022's `brain.db` (RECOMMENDED, co-located
  with `attempts`) when 022 ships.
- [HARD] [consistency] VETTING-027 does NOT hard-require the unbuilt SQLite layer; the `banned`
  store migrates with DATASTORE-022's idempotent JSON→SQLite import (keep-JSON-as-backup +
  idempotent-upsert) when it lands (asserted by the Section B dual-substrate scenario).

**AC-VB-006 (REQ-VB-006 — enable toggle; disabled is today's behavior):**
- GIVEN the vet/ban subsystem is DISABLED via config, WHEN acquisition/play/request-honor run, THEN
  they behave EXACTLY as today (no vet beyond the shipped Tier-1 cut, no `banned` store consulted or
  written, the gates are pass-through); GIVEN it is ENABLED, THEN the cascade + ban-list + gates +
  verdict operate per VC/VK/VB/VG/VR.
- [HARD] The subsystem is opt-in/additive; disabling it restores today's behavior (asserted:
  disabled-mode behavior is identical to the pre-VETTING-027 baseline).

### Group VG — Three-Gate Wiring

**AC-VG-001 (REQ-VG-001 — PRE-DOWNLOAD gate: ban check + metadata tiers before fetching):**
- GIVEN the acquisition path is about to fetch a candidate, WHEN the pre-download gate runs, THEN it
  consults the `banned` store (short-circuiting a banned, not-cleared/cooldown-elapsed key BEFORE a
  new search/fetch) AND applies the metadata tiers (Tier 1 shipped size/duration + Tier 2 keyword/
  category).
- [HARD] A banned key is short-circuited before a new search/fetch is issued (the loop-breaker pays
  off here); the gate attaches to the ACQQUEUE-019 hook and adds the vet/ban predicate without
  re-owning queue ranking (asserted by the Section B loop-breaker scenario).

**AC-VG-002 (REQ-VG-002 — PRE-PLAY gate: confirm music before air; route reject through loop-breaker):**
- GIVEN a landed/queued file is about to go on air, WHEN the pre-play gate runs, THEN it consults the
  `banned` store AND applies the vet (incl. Tier 3 where ANALYSIS-006 supplied the signal); a
  confident non-music verdict SKIPS the file and triggers the post-fetch reject path (REQ-VB-001).
- [HARD] The pre-play vet runs OFF the <1s pull path and a pending verdict defaults to allow, so the
  gate NEVER silences/stalls the stream; this gate INTRODUCES the post-land reject the loop-breaker
  presumes (asserted by the Section B pre-play + never-silence scenarios).

**AC-VG-003 (REQ-VG-003 — PRE-REQUEST-HONOR gate: offensive verdict + ban check before honoring):**
- GIVEN a listener request is about to be honored, WHEN the pre-request-honor gate runs, THEN it
  applies the offensive-request verdict (VR) and consults the `banned` store — an identity-hate
  request is not honored, a provocative-but-allowed request proceeds.
- [HARD] The gate attaches to the REQUEST-011 ingest hook; VETTING-027 applies the verdict, REQUEST-011
  owns the request lifecycle (asserted: an identity-hate request is blocked at honor; a provocative
  request is honored).

**AC-VG-004 (REQ-VG-004 — every gate exception-isolated; fails toward continuous operation):**
- GIVEN a gate's vet or ban check raises/fails, WHEN the failure occurs, THEN it is logged and the
  gate degrades: pre-download/pre-request fail toward NOT-blocking (allow-by-default), and pre-play
  fails toward ALLOW (the music keeps playing).
- [HARD] A gate failure NEVER crashes a download worker, the picker, the director loop, or the
  request path; the ONLY block on a non-confirmed verdict is a CONFIRMED `banned` row; an uncertain/
  errored vet allows (asserted by the Section B resilience scenario).

### Group VR — Offensive-Request Verdict

**AC-VR-001 (REQ-VR-001 — conservative, allow-by-default; bans only identity-hate):**
- GIVEN a listener request, WHEN the offensive verdict runs, THEN it bans ONLY a request targeting
  identity-hate (sexuality-bashing / homophobia / racism); any request that is not a clear
  identity-hate target is allowed; an uncertain/borderline request defaults to ALLOW.
- [HARD] The verdict is allow-by-default and bans only identity-hate (asserted: a clear identity-hate
  request is banned; a borderline/uncertain request is allowed).

**AC-VR-002 (REQ-VR-002 — never bans provocative art / dark / explicit / political):**
- GIVEN a request that is provocative, transgressive, dark, sexually explicit, profane, or
  politically edgy but does NOT promote sexuality-bashing / homophobia / racism, WHEN the verdict
  runs, THEN it is ALLOWED.
- [HARD] Provocative art is never banned (only identity-hate is); the station's art-forward,
  unsanitized identity is preserved (asserted by the Section B never-censor-art scenario).

**AC-VR-003 (REQ-VR-003 — consumes CALLIN-003 moderation floor; does not re-own it):**
- GIVEN the SPEC-RADIO-CALLIN-003 moderation-floor primitive (Group CM/CC, the identity-hate floor),
  WHEN the offensive verdict runs, THEN it CONSUMES that floor and applies it to the REQUEST path
  (pre-request-honor gate); where CALLIN-003 is not yet built, the verdict runs as a forward-compatible
  standalone on the same identity-hate definition.
- [HARD] [consistency] VETTING-027 does NOT restate, fork, or weaken CALLIN-003's floor (which also
  owns the live-call path); VR only applies it to requests (asserted: the identity-hate definition is
  referenced, not re-owned; reconciliation to CALLIN-003 is deferred — D-4).

**AC-VR-004 (REQ-VR-004 — identity-hate ban is a soft, reviewable VB entry):**
- GIVEN the offensive verdict bans a request, WHEN it records the ban, THEN it writes a SOFT,
  reviewable `banned` entry (Group VB) with `status` + `evidence` + `confidence`, not a silent
  permanent block.
- The offensive verdict uses the SAME soft/reversible ban-list (not a separate permanent denylist),
  so even an identity-hate ban is auditable and correctable via the un-ban path (REQ-VB-004)
  (asserted: a false-positive identity-hate ban can be reviewed and un-banned).

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing / boundary / resilience)

### B-1 — The loop-breaker (REQ-VB-001 / NFR-V-7 / REQ-VG-001 / REQ-VG-002) [HARD][LOAD-BEARING]

This is the canonical correctness test of the SPEC.

- GIVEN a wishlist item whose only available source is a non-music file (e.g. a 2-hour podcast
  matching the artist+title),
- AND the vet is enabled,
- WHEN the acquisition worker fetches the file and the pre-play vet reaches a confident non-music
  verdict (a post-fetch reject) and the file is removed,
- THEN the system records the `AttemptsIndex` outcome with a status that is NOT `"success"` AND adds a
  `banned` row for the key,
- AND WHEN time advances beyond `RETRY_COOLDOWN` (6h) and the item is re-enqueued / re-considered,
- THEN the pre-download gate consults the `banned` store, finds the key banned, and SHORT-CIRCUITS
  before issuing any new slskd search or yt-dlp fetch,
- AND THEN the file is NEVER re-fetched (no unbounded fetch→delete→re-fetch loop), even across a
  daemon restart (the ban is durable and cooldown-independent).
- [HARD] Counter-assertion: if the ban row were absent and only `"failed"` (or nothing) were
  recorded, `AttemptsIndex.should_skip` would return `False` after 6h and the loop would recur — the
  test MUST demonstrate the ban row is what prevents recurrence.
- [HARD] Counter-assertion: the system MUST NOT record `"success"` for the rejected fetch (the file is
  gone; a false `"success"` would mislead `should_skip` and any attempts-log consumer).

### B-2 — Combine-signals guard: duration alone never bans (REQ-VK-001 / REQ-VK-002) [HARD]

- GIVEN a 90-minute file that presents as music (no non-music keyword/category, speech-vs-music
  signal absent or music-leaning),
- WHEN the vet decides,
- THEN it does NOT ban/reject — a single adverse duration signal is insufficient,
- AND the file is treated as allowed (long-form music is protected, VK-002).
- AND GIVEN a 90-minute file that ALSO has a non-music keyword (`podcast`) AND a speech-dominant
  Tier-3 classification, WHEN the vet decides, THEN it MAY reject (≥2 corroborating signals present).
- [HARD] A ban/reject requires ≥2 corroborating signals; duration on its own never bans.

### B-3 — Tier-3 degradation when ANALYSIS-006 has not supplied the signal (REQ-VC-004) [HARD][dependency]

- GIVEN a 40-minute file with a clean title that passes Tiers 1-2 but remains ambiguous,
- AND ANALYSIS-006 has NOT yet been extended to emit a speech-vs-music signal (today's state),
- WHEN Tier 3 is reached,
- THEN Tier 3 degrades to UNAVAILABLE, the cascade decides on Tiers 1-2 alone, and the ambiguous file
  is ALLOWED (allow-by-default on a missing signal — VK), NOT banned.
- [HARD] A missing Tier-3 signal never bans on its own; the vet never crashes for lack of the signal.

### B-4 — Never silence the stream (REQ-VC-005 / REQ-VG-002 / NFR-V-1) [HARD]

- GIVEN the picker is selecting the next track and a candidate's vet verdict is still PENDING (the
  decode-based Tier 3 is computing on the background path),
- WHEN the picker needs a track within the <1s budget,
- THEN the pending verdict defaults to ALLOW (or the picker moves to the next ready track) and the
  stream is NEVER silenced or stalled waiting for the verdict,
- AND a confident non-music verdict, when it later resolves, SKIPS the file and routes through the
  loop-breaker (B-1) — but the air path never waited on it.
- [HARD] No vet computation is on the synchronous <1s pull path; a pending/in-progress vet never
  silences playout.

### B-5 — Dual substrate: JSON today, maps to `brain.db` later (REQ-VB-005) [HARD][consistency]

- GIVEN DATASTORE-022 is not built (the SQLite layer does not exist),
- WHEN the ban-list operates today,
- THEN it persists a brain-local JSON `banned` store coexisting with `attempts.json`, and the vet/ban
  subsystem works end-to-end WITHOUT the SQLite layer,
- AND GIVEN DATASTORE-022 later ships its idempotent JSON→SQLite migration,
- THEN the `banned` store maps to `brain.db` (RECOMMENDED, co-located with `attempts`) under the same
  keep-JSON-as-backup + idempotent-upsert posture, with no behavior change to the gates.
- [HARD] [consistency] VETTING-027 never hard-requires the unbuilt SQLite layer; the migration is a
  substrate swap behind an unchanged ban-list API.

### B-6 — Never censor provocative art (REQ-VR-001 / REQ-VR-002) [HARD]

- GIVEN a request for a track that is sexually explicit, violent in theme, profane, or politically
  charged but does NOT promote sexuality-bashing / homophobia / racism,
- WHEN the offensive verdict runs at the pre-request-honor gate,
- THEN the request is ALLOWED (provocative art is never banned),
- AND GIVEN a request that clearly targets identity-hate (a racist or homophobic slur-track meant as
  an attack on people for who they are), WHEN the verdict runs, THEN it is banned as a soft, reviewable
  VB entry (VR-004).
- [HARD] Only identity-hate is banned; provocative art is always allowed; the conservative default on
  uncertainty is ALLOW.

### B-7 — Gate resilience: a vet/ban error never breaks continuous operation (REQ-VG-004 / NFR-V-2) [HARD]

- GIVEN any gate's vet or ban check raises (a classifier exception, a corrupt/locked `banned` store, a
  missing signal),
- WHEN the error occurs,
- THEN it is logged via `log_event` and the gate degrades: pre-download/pre-request allow-by-default,
  pre-play allows (the music keeps playing),
- AND the download worker, the picker, the director loop, and the request path all continue
  uninterrupted,
- AND the ONLY thing that still blocks is a CONFIRMED `banned` row (an explicit prior verdict); an
  uncertain/errored vet allows.
- [HARD] A vet/ban failure never crashes acquisition or playout (the golden rule); allow-by-default on
  uncertainty, honor only confirmed bans.

---

## Section C — Non-Functional Acceptance + Definition of Done

### AC-NFR-V-1 (never blocks / silences playout) [HARD]
- All vet computation (especially decode-based Tier 3) and all ban-store writes run OFF the <1s
  `/api/next` pull path (on the acquisition / background / analysis path); a pending verdict defaults
  to allow; the picker never waits and the stream is never silenced (asserted by Section B-4).

### AC-NFR-V-2 (exception-isolated; never crashes acquisition or playout) [HARD]
- A vet or ban-store error logs via `log_event` and degrades gracefully — it never raises into a
  download worker, the picker, the director loop, or the request path, never crashes the daemon, and
  never silences the stream; a failed vet allows-by-default, only a confirmed ban blocks (asserted by
  Section B-7).

### AC-NFR-V-3 (single-source-of-truth: reference siblings, never re-own) [HARD][consistency]
- No code path re-owns or forks the shipped Tier-1 knobs, ACQQUEUE-019's queue ranking, ANALYSIS-006's
  DSP engine, REQUEST-011's request lifecycle, DATASTORE-022's SQLite substrate, CALLIN-003's
  moderation floor, or LONGFORM-025's long-form criteria; each is referenced by id and
  consumed/extended/applied. VETTING-027 owns the cascade + guard + ban-list + gates + verdict only,
  brain-only + additive (asserted by code review of the boundary).

### AC-NFR-V-4 (conservative / low-false-positive by construction) [HARD]
- The vet does not reject legitimate music: the combine-signals guard (≥2 signals, VK), the long-form
  protection (VK-002), allow-by-default on a missing/uncertain signal (VC-004, VG-004), and the
  allow-by-default offensive verdict (VR-001) together bound the false-positive rate; a single weak
  signal never bans (asserted by Sections B-2, B-3, B-6).

### AC-NFR-V-5 (cheapest-first / cost-bounded)
- The cascade is cost-bounded: the decode-based Tier 3 runs ONLY for the ambiguous middle (VC-001),
  Tiers 1-2 are metadata-only (no decode, no full-file fetch), and the vet adds NO new external
  network call of its own (it reuses the existing slskd/yt-dlp metadata + the ANALYSIS-006 decode that
  already runs) (asserted: enabling the vet adds no new external call type).

### AC-NFR-V-6 (brain-only, additive; bounded config surface)
- No code path adds a new service, daemon, Liquidsoap change, or listener-website surface: a
  brain-only vet/ban module on `brain/` + a `banned` store (JSON today, `brain.db` later), with a
  bounded `BRAIN_*` config surface (enable toggle, keyword list, speech thresholds, ban-store path,
  cooldown/confidence defaults) beside the shipped Tier-1 knobs (asserted by config + dependency
  review).

### AC-NFR-V-7 (the loop-breaker holds: no unbounded fetch→delete→re-fetch loop) [HARD][LOAD-BEARING]
- A post-fetch reject does NOT recur into an unbounded fetch→delete→re-fetch loop: because the reject
  records `AttemptsIndex` status != `"success"` AND adds a durable `banned` row (REQ-VB-001), and the
  pre-download gate (VG-001) consults the `banned` store before re-searching, a rejected file is never
  re-fetched (cooldown-independent, survives restart). This is the load-bearing correctness property
  (asserted by Section B-1, the canonical test).

### Definition of Done

- [ ] All 22 Section A AC entries pass (1:1 with REQ-VC/VK/VB/VG/VR).
- [ ] All 7 Section C AC-NFR entries pass (1:1 with NFR-V-1…7).
- [ ] All 7 Section B scenarios (B-1…B-7) pass, with B-1 (the loop-breaker) and B-4 (never-silence) as
      must-pass gates.
- [ ] [HARD] The loop-breaker invariant is demonstrated: a post-fetch reject writes attempts !=
      `"success"` AND a `banned` row, and the pre-download gate short-circuits a re-fetch (B-1).
- [ ] [HARD] Duration alone never bans; a ban requires ≥2 corroborating signals; long-form music is
      protected (B-2).
- [ ] [HARD] Tier 3 degrades gracefully when ANALYSIS-006 has not supplied the speech-vs-music signal;
      a missing signal never bans (B-3).
- [ ] [HARD] No vet computation is on the <1s pull path; a pending/failed vet never silences the
      stream (B-4, B-7).
- [ ] [HARD] The ban-list works on JSON today and maps to `brain.db` when DATASTORE-022 ships; no hard
      SQLite dependency (B-5).
- [ ] [HARD] The offensive verdict bans only identity-hate and never provocative art (B-6).
- [ ] [HARD] Every gate is exception-isolated and fails toward continuous operation; only a confirmed
      ban blocks (B-7).
- [ ] The enable toggle restores exactly today's behavior when disabled (AC-VB-006).
- [ ] No sibling SPEC requirement is restated, forked, or weakened (AC-NFR-V-3); the shipped Tier-1
      hotfix is referenced, not re-owned (AC-VC-002).
- [ ] Structured `log_event`s are emitted for vet rejections, ban additions, and un-bans (OPS-004
      accounting may consume them).
- [ ] A bhive write-back is filed per AGENTS.md after the verified speech-vs-music gating +
      ban-as-loop-breaker pattern is implemented.
