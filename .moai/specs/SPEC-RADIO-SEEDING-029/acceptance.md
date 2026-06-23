---
id: SPEC-RADIO-SEEDING-029-acceptance
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-SEEDING-029
---

# SPEC-RADIO-SEEDING-029 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR).
Section B carries detailed Given-When-Then scenarios for the load-bearing, boundary, and
resilience-critical requirements. Section C is the Definition of Done and the quality gates.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where
a criterion is marked [HARD] it is a must-pass gate (no compensation by other criteria).

Group prefixes: SB (Bootstrap / First-Run Decision Gate) / SS (Seed Sources / Ingest) / SF
(Taste-Fidelity Modes). 16 AC + 6 AC-NFR = 22, matching spec.md 16 REQ + 6 NFR. The three
fidelity modes: ANCHOR, COMPASS, WOPR.

---

## Section A — Per-Requirement Acceptance

### Group SB — Bootstrap / First-Run Decision Gate

**AC-SB-001 (REQ-SB-001 — first-run interactive seed choice via the run.sh setup step):**
- GIVEN a first run (no `seed_decided` marker in `db_dir`), WHEN the station is launched via
  `scripts/run.sh`, THEN an interactive setup step presents the operator a one-time choice
  (pre-seed or not; which sources; which fidelity mode; the seed-as-acquisition sub-option),
  mirroring `resolve_slskd()`'s TTY-prompt-with-default (`run.sh:295-323`).
- [HARD] The choice is captured OUTSIDE the headless brain (in the launcher / setup), before/at
  first launch (asserted: the prompt fires only on first run with a TTY; a non-interactive
  launch takes the safe default = decline → WOPR, REQ-SB-006).

**AC-SB-002 (REQ-SB-002 — persist the decision; never re-prompt on restart):**
- GIVEN a completed first-run decision, WHEN the setup step finishes, THEN a `seed_decided`
  marker is written in `db_dir` (mirroring `welcomed`, `config.py:225-229`) and while it is
  present the setup step is a no-op.
- [HARD] A restart never re-prompts; deleting the marker (or wiping the db) is the only re-arm
  (asserted: a second launch with the marker present does NOT prompt and reads the persisted
  config).

**AC-SB-003 (REQ-SB-003 — a mid-broadcast redeploy MUST NOT re-prompt or disturb playout):**
- GIVEN the station already on air, WHEN the brain/stack is redeployed, THEN the persisted
  marker + `seed-config.json` are read silently at startup and the station resumes with the
  already-chosen seed.
- [HARD] No re-prompt and no playout interruption occur; the gate is never a runtime barrier
  (asserted by the Section B redeploy scenario).

**AC-SB-004 (REQ-SB-004 — the persisted seed-config contract):**
- GIVEN a completed decision, WHEN it is persisted, THEN a single `seed-config.json` in `db_dir`
  captures at least: the fidelity mode (`anchor`|`compass`|`wopr`), the seed sources, the
  captured `{artist,title}` taste references and/or a dropped-file-taste marker, and the
  seed-as-acquisition flag (default off).
- [HARD] The brain reads this file at startup (consistent with the env-driven `Config`; an env
  var MAY point at it); the field layout is implementation detail but a single brain-readable
  contract capturing mode + sources + refs + acquisition flag is present (asserted: the brain
  boots from the file alone).

**AC-SB-005 (REQ-SB-005 — WEBUI-018 web wizard is a forward-compatible alternative):**
- GIVEN a first-run web wizard provided via WEBUI-018, WHEN it captures the seed choice, THEN it
  writes the SAME `seed-config.json` contract (AC-SB-004) + the SAME `seed_decided` marker, and
  the headless brain reads it identically.
- [HARD] [consistency] The run.sh setup step is PRIMARY and the wizard is an ALTERNATIVE not
  required for v0.1.0; SEEDING-029 does NOT re-own WEBUI-018's web surface (asserted: the brain
  is agnostic to which front-end wrote the contract; no wizard is required to pass the gate).

**AC-SB-006 (REQ-SB-006 — decline/undecided → WOPR; always boots and plays):**
- GIVEN the operator declines seeding, or no decision is reachable (non-interactive launch with
  no prior config, missing/corrupt `seed-config.json`), WHEN the station boots, THEN it runs in
  WOPR using today's behavior (`SEED_TRACKS` + freeform `curate_batch` with an empty
  `seed_reference`).
- [HARD] The boot and the stream are NEVER blocked on the seed choice; the station ALWAYS boots
  and plays (asserted: with no/declined seed, the station starts and serves audio exactly as
  today).

### Group SS — Seed Sources / Ingest

**AC-SS-001 (REQ-SS-001 — Spotify-CSV parse → {artist,title} taste references):**
- GIVEN a Spotify playlist CSV export, WHEN it is parsed, THEN it yields a list of
  `{artist,title}` taste references, accepting the Exportify schema (`"Track Name"`,
  `"Artist Name(s)"`, `"Album Name"`) with tolerant fallbacks to a minimal `artist,title` CSV
  and reasonable header variants.
- [HARD] The parsed references feed Group SF as the `seed_reference` content (asserted: an
  Exportify CSV and a minimal `artist,title` CSV both parse to the same `{artist,title}` shape).

**AC-SS-002 (REQ-SS-002 — tolerant parsing: skip malformed rows, never crash startup):**
- GIVEN a CSV with malformed/empty/column-missing rows, WHEN it is parsed, THEN those rows are
  SKIPPED and parsing continues; a wholly-unreadable or empty CSV yields ZERO references
  (degrading to WOPR-equivalent), logged, never fatal.
- [HARD] The parser NEVER raises or crashes startup on a bad CSV (asserted by the Section B
  tolerant-parse scenario).

**AC-SS-003 (REQ-SS-003 — CSV refs feed TASTE by default; auto-download is opt-in):**
- GIVEN parsed CSV references, WHEN no acquisition sub-option is enabled, THEN they feed
  `seed_reference` (TASTE) only and are NOT auto-downloaded.
- [HARD] Enqueuing them for acquisition is a SEPARATE opt-in (REQ-SS-005), off unless enabled
  (asserted: with the sub-option off, zero downloads are triggered by the seed; curation is
  biased toward the refs).

**AC-SS-004 (REQ-SS-004 — dropped files: a taste signal IN ADDITION to playable ingest):**
- GIVEN audio files dropped into `music_dir`, WHEN the watch ingests them, THEN they are PLAYABLE
  via the existing watch/scan (`config.py:160-168`; `library.py:292-340`) UNCHANGED, AND their
  artist/title/genre metadata ALSO become a taste signal feeding `seed_reference`.
- [HARD] [consistency] The two roles (playable rotation entry vs taste reference) are distinct;
  SEEDING-029 does NOT change the playable ingest (asserted: a dropped file appears in rotation
  AND contributes to the taste signal; the watch is referenced, not re-owned).

**AC-SS-005 (REQ-SS-005 — optional seed-as-acquisition via the existing, vetted enqueue seam):**
- GIVEN the seed-as-acquisition sub-option ENABLED, WHEN the CSV references are processed, THEN
  they are enqueued for download via `acquire.enqueue` (`acquire.py:134`).
- [HARD] Each enqueued grab passes the normal acquisition path UNCHANGED — the
  `attempts`/`in-flight`/`has_key` dedup (`acquire.py:140-145`), the size/duration cut, and the
  VETTING-027 pre-download vet (when built) — so the seed never bypasses any guard; ENRICH-012/
  MBMIRROR-017 resolve refs to real recordings via the existing pipeline (asserted: a
  seed-enqueued grab is indistinguishable downstream from a director-enqueued grab).

### Group SF — Taste-Fidelity Modes

**AC-SF-001 (REQ-SF-001 — ANCHOR: strong seed bias + seed-adjacent acquisition, still soft):**
- GIVEN fidelity mode ANCHOR, WHEN the director curates, THEN the seed is passed as
  `seed_reference` with framing that instructs the model to lean hard on it, AND acquisition is
  biased toward seed-adjacent material.
- [HARD] ANCHOR is expressed THROUGH the existing `curate_batch` hook (the `seed_reference` list
  + `_build_prompt` framing), not a new engine, AND remains SOFT (REQ-SF-004 — it raises the
  bias weight, it does NOT hard-filter to only-seed) (asserted: ANCHOR passes a non-empty
  `seed_reference` with strong framing; the library is never restricted to only-seed).

**AC-SF-002 (REQ-SF-002 — COMPASS: loose seed compass + deliberate outward exploration):**
- GIVEN fidelity mode COMPASS, WHEN the director curates, THEN the seed is passed as
  `seed_reference` with framing that invites exploration outward (adjacent genres, discovery)
  while staying tonally informed by the seed, with a lighter acquisition bias than ANCHOR.
- [HARD] COMPASS is a weaker, exploration-forward framing of the SAME hook than ANCHOR (asserted:
  COMPASS framing differs from ANCHOR framing; both pass the same `seed_reference` shape).

**AC-SF-003 (REQ-SF-003 — WOPR: full autonomy; also the no-preseed default = today's behavior):**
- GIVEN fidelity mode WOPR (chosen, or the no-preseed default), WHEN the director curates, THEN
  an EMPTY/absent `seed_reference` is passed and the AI self-directs from its persona + knowledge
  base.
- [HARD] WOPR equals EXACTLY today's behavior — freeform `curate_batch` with the built-in
  `SEED_TRACKS` resilience fallback (asserted: WOPR's curation path and `_seed_reference()=[]`
  are byte-for-byte today's no-seed behavior).

**AC-SF-004 (REQ-SF-004 — the seed is NON-BINDING at EVERY level; the golden rule wins):** [HARD]
[LOAD-BEARING]
- GIVEN any fidelity mode (including ANCHOR), WHEN the seed is applied, THEN it shifts curation
  WEIGHT (fed as the `seed_reference` the model MAY ignore, `llm.py:204-206`) and biases
  acquisition, but is NEVER a HARD WHITELIST restricting the library to only-seed material.
- [HARD] Even in ANCHOR, if seed-adjacent material runs dry the station KEEPS PLAYING — the
  golden rule (never stop) wins over the seed (asserted by the Section B non-binding scenario:
  the picker still serves the next available track on a dry seed-adjacent pool; the stream never
  silences).

**AC-SF-005 (REQ-SF-005 — enable toggle + bounded config; disabled = today's behavior):**
- GIVEN the config enable toggle, WHEN DISABLED (or with no `seed-config.json`), THEN
  `_seed_reference()` returns `[]` and the station is WOPR (no seed read, no fidelity bias); WHEN
  ENABLED with a valid config, the seed + fidelity mode operate per Groups SS/SF.
- [HARD] The toggle + the bounded `BRAIN_SEED_*` surface (enable, config path, default mode,
  seed-as-acquisition default) are the only config added; disabling restores today's behavior
  exactly (asserted: with the toggle off, the curation path and external behavior are byte-for-
  byte today's).

---

## Section A (cont.) — Non-Functional Acceptance

**AC-NFR-S-1 (NFR-S-1 — never blocks boot, the director loop, or playout):** [HARD] All
seeding/ingest/parse work (CSV parse, dropped-file taste read, seed-config read) is
exception-isolated and runs off the `<1s /api/next` pull; a malformed CSV row, an unreadable
drop, or a missing/corrupt `seed-config.json` logs and degrades to WOPR — it never fails boot,
crashes the director loop, or silences the stream (asserted: a forced parse/read failure yields
a normal boot + uninterrupted stream).

**AC-NFR-S-2 (NFR-S-2 — the non-binding invariant holds at every level):** [HARD] [LOAD-BEARING]
The seed is a SOFT bias at EVERY fidelity level: ANCHOR raises the `seed_reference` weight +
acquisition bias without hard-filtering; on a dry seed-adjacent pool the picker still serves the
next available track and the stream never silences; the seed never becomes a hard whitelist.

**AC-NFR-S-3 (NFR-S-3 — single-source-of-truth, reference not re-own):** [HARD] [consistency] No
code path re-owns or forks CORE-001's `curate_batch`/engine, PROGRAMMING-007's persona curation,
WEBUI-018's web surface, ENRICH-012/MBMIRROR-017's resolution, REQUEST-011's request lifecycle,
ANALYSIS-006's library watch, or VETTING-027's vet; each is referenced by id and consumed. The
SPEC is brain + launcher only + additive (a seed-config reader + a run.sh setup step + a
`seed-config.json`/`seed_decided` marker; no new service, no `curate_batch` signature change, no
required listener-website surface, no server DB).

**AC-NFR-S-4 (NFR-S-4 — first-run gate fires exactly once per genesis):** The seed decision is
captured at most ONCE per genesis and persisted (the `seed_decided` marker + `seed-config.json`),
mirroring `welcome_marker`: a restart/redeploy reads the decision and never re-prompts; deleting
the marker (or wiping the db) is the only re-arm.

**AC-NFR-S-5 (NFR-S-5 — tolerant/robust ingest by construction):** The CSV parser and the
dropped-file taste read are robust by construction — malformed rows skipped, header variants
accepted, an empty/garbage file yields zero references, no input crashes the parse or the boot;
partial parses are acceptable (whatever parsed feeds the seed).

**AC-NFR-S-6 (NFR-S-6 — brain + launcher only, additive; bounded config surface):** No code path
adds a new service, daemon, Liquidsoap change, `curate_batch` signature change, or required
listener-website surface: the change is a brain-side seed-config reader + a `scripts/run.sh`
setup step + a `seed-config.json`/`seed_decided` marker in `db_dir`, with a bounded `BRAIN_SEED_*`
config surface (enable, config path, default mode, seed-as-acquisition default).

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing / boundary / resilience-critical)

### B1 — The seed is non-binding even in ANCHOR; the golden rule wins (REQ-SF-001, REQ-SF-004, NFR-S-2) [HARD]

```
GIVEN fidelity mode ANCHOR with a small seed (a handful of artists)
WHEN the director curates and the library's seed-adjacent material is exhausted/dry
THEN curation still passes the seed as seed_reference with strong framing (a soft bias)
  AND the picker (library.pick_next) still serves the next available least-recently-played
      track — the library is NOT restricted to only-seed
  AND the stream NEVER silences waiting for seed-adjacent material
CONTRAST: a HARD-whitelist design WOULD stall on a dry seed pool — which is exactly why the seed
      is a soft bias, never a filter
```
Verification: assert ANCHOR raises bias weight (non-empty seed_reference + insistent framing) but
never hard-filters; on a dry seed-adjacent pool the next track still plays and the stream is
uninterrupted (the load-bearing non-binding invariant).

### B2 — First-run gate fires once; a redeploy never re-prompts or disturbs air (REQ-SB-002, REQ-SB-003, NFR-S-4) [HARD]

```
GIVEN a first run with no seed_decided marker in db_dir
WHEN scripts/run.sh runs its interactive setup step on a TTY
THEN the operator's choice is captured, seed-config.json is written, and the seed_decided marker
     is dropped (mirroring welcome_marker)
GIVEN the station now on air with the marker present
WHEN the brain/stack is redeployed mid-broadcast
THEN the setup step is a no-op (marker present), the brain reads seed-config.json silently at
     startup, resumes with the chosen seed
  AND NO re-prompt occurs and playout is NOT interrupted to ask
```
Verification: assert the prompt fires only on first run; a second launch / redeploy reads the
persisted decision with no prompt and no playout disturbance (the once-per-genesis guarantee).

### B3 — Tolerant CSV parse: malformed rows skipped, never crashes (REQ-SS-001, REQ-SS-002, NFR-S-5) [HARD]

```
GIVEN a Spotify CSV with a mix of valid Exportify rows, a minimal artist,title row, a
     column-missing row, an empty row, and a garbled row
WHEN the parser runs
THEN the valid + minimal rows yield {artist,title} taste references
  AND the malformed/empty/garbled rows are SKIPPED (logged), not fatal
GIVEN a wholly-empty or unreadable CSV
WHEN the parser runs
THEN it yields ZERO references and the station degrades to WOPR-equivalent freeform curation
  AND startup is NEVER crashed by the bad input
```
Verification: assert partial parses succeed (good rows in, bad rows skipped) and an empty/garbage
file yields zero refs without raising — the never-crash-startup tolerant-parse rail.

### B4 — Two roles for a dropped file: playable AND taste (REQ-SS-004) [HARD]

```
GIVEN audio files dropped into music_dir
WHEN the existing library watch/scan ingests them (config.py:160-168; library.py:292-340)
THEN each file is PLAYABLE in rotation exactly as today (the watch is unchanged)
  AND its artist/title/genre metadata ALSO becomes a taste signal feeding seed_reference
CONTRAST: SEEDING-029 does NOT alter the playable ingest; it ADDS a distinct taste read over the
     same files (the two roles stay distinct; the watch is referenced, not re-owned)
```
Verification: assert a dropped file is in the rotation AND contributes to the taste signal;
assert the watch/scan code path is unchanged (boundary discipline, NFR-S-3).

### B5 — Decline/undecided → WOPR = today's behavior; always boots and plays (REQ-SB-006, REQ-SF-003) [HARD]

```
GIVEN the operator declines seeding (or a non-interactive launch with no prior config, or a
     missing/corrupt seed-config.json)
WHEN the station boots
THEN it runs in WOPR: _seed_reference() returns [] and curate_batch runs freeform with the
     built-in SEED_TRACKS resilience fallback (byte-for-byte today's no-seed behavior)
  AND the boot and the stream are NEVER blocked on the seed choice — the station ALWAYS boots
     and plays
```
Verification: assert the no/declined-seed path equals today's behavior and the station starts +
serves audio regardless of the seed choice (the always-boot-and-play rail).

### B6 — Resilience: a seed-config/parse failure never touches boot or playout (REQ-SB-006, NFR-S-1) [HARD]

```
GIVEN a corrupt/unreadable seed-config.json (truncated JSON, bad permissions, wrong shape)
WHEN the brain reads it at startup
THEN the error is logged and dropped
  AND the brain boots in WOPR (degrade-to-today's-behavior)
  AND the director loop does not crash and the stream does not silence
  AND the seed read happened off the <1s /api/next pull path
```
Verification: assert a forced seed-config read failure yields a normal WOPR boot and an
uninterrupted stream — a lost seed config means lost preference, never a lost station.

### B7 — Fidelity maps onto the existing hook only; signature unchanged (REQ-SF-001/002/003, Section 2.2) [HARD]

```
GIVEN the three fidelity modes
WHEN each curates
THEN ANCHOR/COMPASS/WOPR are expressed PURELY via the existing curate_batch hook — the
     seed_reference list contents/length + the _build_prompt framing + the acquisition bias —
     NOT a new curation engine and NOT a change to curate_batch's signature
  AND a large CSV is sampled/prioritized into the prompt's seed_reference[:15] cap (the framing
     strength, not the raw count, carries the mode)
```
Verification: assert no new curation engine/LLM-call-shape is introduced; assert curate_batch's
signature is unchanged; assert the per-mode difference is framing + which refs are passed
(D-2 / R-S-2).

### B8 — Optional seed-as-acquisition rides the existing vetted seam (REQ-SS-005) [HARD]

```
GIVEN the seed-as-acquisition sub-option ENABLED
WHEN the CSV references are processed
THEN they are enqueued via acquire.enqueue (acquire.py:134) and pass the normal path: the
     attempts/in-flight/has_key dedup (acquire.py:140-145), the size/duration cut, and the
     VETTING-027 pre-download vet (when built)
  AND ENRICH-012/MBMIRROR-017 resolve them to real recordings via the existing pipeline
  AND with the sub-option DISABLED (default), zero downloads are triggered by the seed
```
Verification: assert a seed-enqueued grab is indistinguishable downstream from a
director-enqueued grab (no bypass of any guard); assert default-off triggers no downloads
(REQ-SS-003).

---

## Section C — Definition of Done & Quality Gates

A SEEDING-029 implementation is DONE when:

1. [HARD] All 16 REQ + 6 NFR Section A entries pass, and all Section B scenarios pass.
2. [HARD] **The seed is NON-BINDING at every fidelity level (REQ-SF-004, NFR-S-2, B1):** the
   seed shifts curation weight via `seed_reference`; ANCHOR raises weight but never hard-filters;
   on a dry seed-adjacent pool the station keeps playing — the golden rule wins. This is the
   load-bearing property.
3. [HARD] **First-run gate, once per genesis, never re-prompts (REQ-SB-002/003, NFR-S-4, B2):**
   the `seed_decided` marker + `seed-config.json` (mirroring `welcome_marker`) make the decision
   once; a restart/redeploy reads it silently with no re-prompt and no playout disturbance.
4. [HARD] **Headless mechanism (REQ-SB-001/004, B2):** the choice is captured OUTSIDE the brain
   by the `scripts/run.sh` setup step (mirroring `resolve_slskd`), written to a single
   brain-readable `seed-config.json` contract; the brain reads it at startup.
5. [HARD] **The station ALWAYS boots and plays (REQ-SB-006, REQ-SF-003, B5):** decline/undecided
   → WOPR = today's behavior (`SEED_TRACKS` + freeform curation, `_seed_reference()=[]`); the
   gate is a preference, never a barrier.
6. [HARD] **Tolerant CSV parse (REQ-SS-001/002, NFR-S-5, B3):** the Exportify schema (+ minimal
   `artist,title` fallback) parses to `{artist,title}` refs; malformed rows are skipped; an
   empty/garbage file yields zero refs; startup is never crashed.
7. [HARD] **Two roles for dropped files (REQ-SS-004, B4):** a dropped file is PLAYABLE via the
   unchanged watch AND a TASTE signal; the two roles stay distinct; the watch is referenced, not
   re-owned.
8. **CSV refs feed TASTE by default; auto-download opt-in (REQ-SS-003, REQ-SS-005, B8):** by
   default the refs only bias curation; the seed-as-acquisition sub-option (off by default)
   enqueues via the existing vetted/deduped seam, bypassing no guard.
9. [HARD] **Fidelity maps onto the existing hook only (REQ-SF-001/002/003, B7):** ANCHOR/COMPASS/
   WOPR are expressed via `seed_reference` contents + `_build_prompt` framing + acquisition bias;
   no new engine; `curate_batch`'s signature is unchanged; a large CSV is sampled into the
   `seed_reference[:15]` cap.
10. [HARD] **Resilience / never blocks playout (REQ-SB-006, NFR-S-1, B6):** a parse/seed-config
    failure logs + degrades to WOPR; the brain boots, the director loop never crashes, the stream
    never silences; the seed read is off the `/api/next` path.
11. [HARD] **Additive enable toggle (REQ-SF-005, NFR-S-6):** disabled (or no config) restores
    today's behavior exactly; the bounded `BRAIN_SEED_*` surface is the only config added.
12. [HARD] **Single-source-of-truth (NFR-S-3):** CORE-001's engine, PROGRAMMING-007's persona
    curation, WEBUI-018's web surface, ENRICH-012/MBMIRROR-017's resolution, REQUEST-011's
    request lifecycle, ANALYSIS-006's watch, and VETTING-027's vet are referenced, never re-owned;
    brain + launcher only + additive.
13. **WEBUI-018 wizard is a forward-compatible alternative (REQ-SB-005):** if built, it writes the
    same contract; it is NOT required for v0.1.0.

Quality gates (TRUST 5, inherited): Tested (the non-binding B1, the once-per-genesis B2, the
tolerant-parse B3, the two-roles B4, the always-boot B5, the resilience B6, the hook-mapping B7,
and the vetted-enqueue B8 scenarios are the must-pass characterization tests); Readable; Unified;
Secured (no live OAuth / no new external call of its own; the seed-config is operator/internal,
not on the listener website; a seed-enqueued grab passes the existing vet); Trackable (the
persisted `seed-config.json` + `seed_decided` marker make the cold-start decision auditable and
reproducible).

Parity check: 16 AC (Section A) + 6 AC-NFR = 22 acceptance entries, matching spec.md 16 REQ + 6
NFR; 1:1 REQ↔AC preserved. The three fidelity modes: ANCHOR, COMPASS, WOPR.
