---
id: SPEC-RADIO-SEEDING-029
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: High
issue_number: 29
---

# SPEC-RADIO-SEEDING-029 — Initial Library Seeding & Taste-Fidelity Cold-Start

## HISTORY

- 2026-06-23 (v0.1.0): Initial draft, occupying the new global-incrementing SEEDING-029 id
  (the next number after SKIP-028). The INITIAL-SEEDING + TASTE-FIDELITY COLD-START subsystem
  of the golden-shower-radio autonomous AI radio station. It answers a direct user intent: on
  FIRST RUN, the operator wants a one-time interactive choice of whether/how to PRE-SEED the
  station's taste, plus a FIDELITY KNOB controlling how hard the AI treats that seed. The
  receiving end ALREADY EXISTS and is the primary hook: `brain/llm.py` `curate_batch` accepts
  `seed_reference: Optional[List[str]]` (`llm.py:215`) and weaves it into the prompt as
  NON-BINDING reference context ("the listener's taste - feel free to expand on or ignore it",
  `llm.py:194-208`); `brain/director.py` `_seed_reference()` (`director.py:47-51`) is a
  `# FUTURE:` stub returning `[]` today. SEEDING-029 supplies that reference from a persisted,
  operator-chosen seed and tunes its WEIGHT/FRAMING per fidelity mode. The first-run gate
  MIRRORS the existing once-per-genesis `welcome_marker` pattern (`config.py:225` `welcomed`
  marker; `main.py:89`; `server.py:218`). Because the brain is a HEADLESS Docker container with
  no runtime stdin, the PRIMARY first-run mechanism is an interactive setup step in
  `scripts/run.sh` (mirroring `resolve_slskd`, `run.sh:295-323`) that writes the operator's
  choice into a `seed-config.json` in `db_dir` and drops a `seed_decided` marker; the brain
  reads it at startup and NEVER re-prompts on restart. RADIO SPEC-IDs are GLOBAL-INCREMENTING
  (CORE-001, VOICE-002, CALLIN-003, OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007,
  KNOWLEDGE-008, TAGSTREAM-009, IMAGING-010, REQUEST-011, ENRICH-012, STATS-013, DEDUP-014,
  LIKE-015, HOSTCTX-016, MBMIRROR-017, WEBUI-018, ACQQUEUE-019, SHOWS-020, ALBUMART-021,
  DATASTORE-022, LOOKUPLOG-023, FILENAME-024, LONGFORM-025, REFLECT-026, VETTING-027,
  SKIP-028 authored; SEEDING = 029). It uses a DISTINCT REQ namespace — SB (bootstrap /
  first-run decision gate + persistence), SS (seed sources / ingest), SF (taste-fidelity
  modes) — chosen to dodge every existing radio prefix (CORE A-E+D, VOICE V-family, CALLIN
  CT/CL/CD/CM/CC/CF/CS/CG, OPS OA-OH/OX/OY, ORCH RL/RW/RE/RC/RD/RA/RN/RI, ANALYSIS AE/AT/AM/
  AD/AP, PROGRAMMING PR/PC/PS/PT/PL/PG/PV/PI, KNOWLEDGE KS/KF/KR/KG/KI, TAGSTREAM TW/TA/TX,
  IMAGING IG/IB/IP/IL/IS/IH/IX, REQUEST RQ/RM/RA/RWL/RS/RV/RD, DEDUP DK, LIKE LH/LD/LS/LA/LP/
  LX, LOOKUPLOG LL/LK/LC/LM/LG, FILENAME FD/FR/FS/FF, DATASTORE DE/DP/DX/DM/DC/DR, SKIP SK/SG/
  SC, VETTING VC/VK/VB/VG/VR). NOTE: SB/SS/SF do not collide with SKIP's SK/SG/SC; the full id
  (`REQ-SS-NNN`) is used everywhere to keep it distinct. Total: 16 REQ + 6 NFR = 22, 1:1
  REQ↔AC (SB=6, SS=5, SF=5). The three fidelity modes are named ANCHOR, COMPASS, and WOPR.

---

## 1. Overview & Background

### 1.1 Why this SPEC — "let me hand the station my taste on day one, and tell it how hard to lean on it"

A fresh station has no listening history and no library. Today it cold-starts from
`brain/llm.py`'s built-in `SEED_TRACKS` (a resilience fallback, not the operator's taste) and
freeform LLM curation. The user wants, on FIRST RUN, to optionally hand the station a
SEED of their own taste — a Spotify playlist export and/or a drop of music files — and a
FIDELITY KNOB that says how hard the AI should lean on that seed: base everything on it,
treat it as a loose compass, or ignore it entirely and run on full autonomy.

The receiving end is already built: `curate_batch(..., seed_reference=...)` (`llm.py:211-215`)
weaves a non-binding taste list into the prompt ("feel free to expand on or ignore it",
`llm.py:204-206`), and `director._seed_reference()` (`director.py:47-51`) is a `# FUTURE:`
stub returning `[]`. SEEDING-029 SUPPLIES that reference from a persisted, operator-chosen
seed, and tunes its WEIGHT + PROMPT FRAMING per fidelity mode, all against the existing hook.

SEEDING-029 adds the first-run decision gate (SB), the two file-based seed sources (SS), and
the three-mode fidelity knob (SF), all exception-isolated so a malformed CSV or an unreadable
drop never crashes startup or playout (the golden rule).

### 1.2 The load-bearing invariant — the seed is a NON-BINDING bias at EVERY fidelity level

[HARD][LOAD-BEARING] **The seed shifts curation WEIGHT; it is NEVER a hard whitelist.** At
every fidelity level — including ANCHOR — the seed is fed to `curate_batch` as the
`seed_reference` the model MAY ignore, and biases acquisition; it is NEVER a hard filter that
restricts the library to only-seed material. ANCHOR RAISES the bias weight and the prompt's
insistence; it does NOT hard-filter. [HARD] Even in ANCHOR, if seed-adjacent material runs
dry the station MUST keep playing — the golden rule (never stop) wins over the seed. This is
the heart of the SPEC: a fidelity mode changes HOW STRONGLY the AI leans on the seed, never
WHETHER the music can keep flowing. Encoded as REQ-SF-004 and restated as NFR-S-2.

### 1.3 The first-run gate mirrors the once-per-genesis welcome marker (the SB idea)

[HARD] The first-run seed decision is captured ONCE per station genesis and PERSISTED, so a
restart — including a mid-broadcast redeploy — NEVER re-prompts. This MIRRORS the existing
`welcome_marker_path` pattern (`config.py:225-229`: a `welcomed` sentinel in `db_dir`, armed
at `main.py:89` only when `not os.path.exists(...)`, written at `server.py:218`). SEEDING-029
adds a companion `seed_decided` marker in `db_dir` and a `seed-config.json` (the persisted
decision: mode + sources + the seed-as-acquisition sub-option). Present marker → the gate is
satisfied and the brain boots straight to the persisted seed config.

### 1.4 The headless-container mechanism (the SB constraint)

[HARD][CONSTRAINT] The brain is a HEADLESS Docker container (`docker compose up -d`,
`run.sh:352-359`) with NO runtime stdin: the brain process CANNOT prompt the operator while
running. `Config` is env-driven (`config.py:17-19`). Therefore the first-run choice MUST be
captured OUTSIDE the brain. PRIMARY mechanism: an interactive setup STEP in `scripts/run.sh`
— mirroring `resolve_slskd()`'s TTY-prompt-with-non-interactive-default
(`run.sh:295-323`) — that runs BEFORE/at first launch, writes the operator's choice into
`seed-config.json` in `db_dir`, and drops the `seed_decided` marker; the brain reads that
config at startup. ALTERNATIVE/future mechanism: a first-run WEB WIZARD served via WEBUI-018,
writing the SAME persisted `seed-config.json` contract. Both write the same contract; the
brain is agnostic to which wrote it.

### 1.5 Two file-based seed sources (the SS idea)

[HARD] SEEDING-029 ingests taste from FILES, never live OAuth (the
`SEED_ENRICHMENT_STUBS` Spotify/YouTube token surface, `config.py:264-270`, stays a
documented future, NOT a dependency):

- **Spotify playlist CSV export.** Accepts the common export schema (e.g. Exportify columns
  `"Track Name"`, `"Artist Name(s)"`, `"Album Name"`) with TOLERANT fallbacks to a minimal
  `artist,title` CSV. Parsed → a list of `{artist, title}` taste references. The parser is
  TOLERANT: it skips malformed rows and NEVER crashes startup. These references feed
  `seed_reference` (TASTE); they do NOT auto-download by default. OPTIONALLY (a sub-option)
  they may ALSO be enqueued for acquisition via `acquire.enqueue` (`acquire.py:134`).
- **Plain music files (audio drop).** Files the operator drops into `music_dir`. They become
  PLAYABLE via the EXISTING library watch (`config.py:160-168` `watch_enabled` /
  `watch_interval_seconds`; `library.py:292-340` `scan()`) — that role is unchanged. NEW: in
  ADDITION, their artist/title/genre metadata become a TASTE signal feeding `seed_reference`.
  The two roles (playable rotation entry vs taste reference) are DISTINCT and must not be
  conflated.

### 1.6 The three-mode taste-fidelity knob (the SF idea — ANCHOR / COMPASS / WOPR)

[HARD] The fidelity knob is set at first run and concretely changes the `seed_reference`
weight + prompt framing passed to `curate_batch`, and the acquisition bias:

- **ANCHOR** — "this is my taste, base everything on it." Curation strongly biases toward the
  seed's artists / genres / era and close neighbors; acquisition prioritizes seed-adjacent
  material. [HARD] STILL non-binding/soft (REQ-SF-004): even in ANCHOR, if seed-adjacent
  material runs dry the station keeps playing — ANCHOR raises the bias WEIGHT, it does NOT
  hard-filter the library to only-seed.
- **COMPASS** — "good tunes, surprise me." The seed is a loose starting compass; the AI
  deliberately explores outward (adjacent genres, discovery) while staying tonally informed
  by the seed.
- **WOPR** — "do whatever the hell you want." Full autonomy: the AI self-directs from scratch
  (its LLM persona + knowledge base), ignoring or not requiring any seed. This is ALSO the
  NO-PRESEED default: if the operator declines seeding, the station runs in WOPR — exactly
  today's behavior (the built-in `SEED_TRACKS` resilience fallback + freeform LLM curation).

### 1.7 No-preseed behavior — the station ALWAYS boots and plays (the SB/SF rail)

[HARD] If the operator DECLINES seeding (or no decision is reachable), the station runs in
WOPR using today's behavior (`SEED_TRACKS` + freeform `curate_batch` with an empty
`seed_reference`) and NEVER blocks. The first-run gate is a one-time PREFERENCE capture, never
a barrier: a missing, malformed, or undecided `seed-config.json` degrades to WOPR. The station
ALWAYS boots and plays regardless of the seed choice.

### 1.8 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] SEEDING-029 OWNS the first-run seed-decision gate + persistence + headless mechanism,
the two file-based seed sources + their parsers, and the three-mode fidelity knob + its
mapping onto the existing `seed_reference` hook. It MUST NOT restate, fork, or weaken any
CORE-001, PROGRAMMING-007, WEBUI-018, ENRICH-012, MBMIRROR-017, REQUEST-011, ANALYSIS-006, or
VETTING-027 requirement.

OWNS:
- The FIRST-RUN DECISION GATE (Group SB): the one-time interactive choice, the
  `seed_decided` marker + `seed-config.json` persistence (mirroring `welcome_marker`), the
  headless-container `run.sh`-setup primary mechanism, the WEBUI-018 web-wizard alternative,
  and the never-re-prompt-on-restart rule.
- The SEED SOURCES (Group SS): the tolerant Spotify-CSV parser (Exportify + minimal fallback)
  → `{artist,title}` taste references; the dropped-music-file taste signal (distinct from the
  existing playable ingest); the seed-as-acquisition sub-option.
- The TASTE-FIDELITY KNOB (Group SF): the three modes (ANCHOR / COMPASS / WOPR), their
  concrete `seed_reference` weight + prompt-framing + acquisition-bias mapping, the
  [HARD] non-binding-at-every-level invariant, and the WOPR-is-the-no-preseed-default rule.
- Plus NFRs (Section 8) and Risks (Section 9).

REFERENCES (consumes / extends / applies; does not restate):
- **CORE-001 — the engine PARENT.** Owns `SEED_TRACKS`, `curate_batch`, the never-stop
  identity, and the seed-as-reference (non-binding) principle. SEEDING-029 supplies the
  reference and tunes its weight; it does not redefine the engine or the principle.
- **PROGRAMMING-007 — curation / personas / anti-convergence.** SEEDING-029 supplies a
  STATION-LEVEL taste bias upstream of persona curation; it MUST NOT flatten the per-persona
  distinct-taste firewall PROGRAMMING-007 owns. Referenced, not re-owned.
- **WEBUI-018 — the web surface.** The ALTERNATIVE host for a first-run web wizard (writing
  the same `seed-config.json` contract). SEEDING-029 specifies run.sh as primary, the wizard
  as a forward-compatible alternative. Referenced, not re-owned.
- **ENRICH-012 / MBMIRROR-017 — identification + MB resolution.** Only the OPTIONAL
  seed-as-acquisition path needs CSV `{artist,title}` → real-recording resolution, which it
  gets from the EXISTING acquisition + enrich pipeline; SEEDING-029 performs no resolution of
  its own. Referenced, not re-owned.
- **REQUEST-011 — the acquisition-growth surface.** The seed-as-acquisition sub-option
  enqueues via the same `acquire.enqueue` seam; SEEDING-029 owns only the first-run
  CSV-enqueue trigger, not the request lifecycle. Referenced, not re-owned.
- **ANALYSIS-006 — the library watch + scan.** The dropped-file PLAYABLE ingest is
  ANALYSIS-006's `watch`/`scan`; SEEDING-029 adds a TASTE reading over the same files. The
  watch is referenced, not re-owned.
- **VETTING-027 — the vet cascade + ban-list.** A seed-enqueued grab passes through the
  pre-download vet exactly like any other grab; SEEDING-029 never bypasses it. Referenced,
  not re-owned.

### 1.9 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 intent and does NOT redefine it. SEEDING-029 is a COLD-START /
PREFERENCE substrate, not a creative override: it offers the operator a non-binding taste bias
and a fidelity dial, but the director still decides WHAT to play. At its strongest (ANCHOR)
the seed only raises a soft bias weight; at its weakest (WOPR) the AI is fully autonomous. The
seed NEVER becomes a hard constraint that homogenizes or starves the music.

### 1.10 Fixed engineering rails (the only hard constraints)

- **Exception-isolated; never crash startup or playout.** [HARD] A malformed CSV row, an
  unreadable drop, a missing/corrupt `seed-config.json` logs and degrades to WOPR; it NEVER
  fails the brain's boot, the director loop, or the stream (NFR-S-1).
- **The non-binding invariant.** [HARD][LOAD-BEARING] The seed is a soft bias at EVERY
  fidelity level; ANCHOR raises weight, it does not hard-filter; the golden rule wins
  (REQ-SF-004, NFR-S-2).
- **First-run gate, once per genesis, never re-prompts.** [HARD] Mirrors `welcome_marker`; a
  restart/redeploy reads the persisted decision, never re-asks (REQ-SB-002/003).
- **Headless mechanism.** [HARD] The choice is captured OUTSIDE the brain (run.sh-setup
  primary; WEBUI-018 wizard alternative), written to a single `seed-config.json` contract the
  headless brain reads at startup (REQ-SB-001/004/005).
- **File-based sources only; no live OAuth.** [HARD] Spotify CSV export + audio drop; the
  Spotify/YouTube token surface stays a documented future, not a dependency (REQ-SS-001/003).
- **Tolerant parsing.** [HARD] The CSV parser skips malformed rows and never crashes
  (REQ-SS-002).
- **The station ALWAYS boots and plays.** [HARD] Decline → WOPR = today's behavior; the gate
  is a preference, never a barrier (REQ-SB-006, REQ-SF-003).
- **Reference, don't re-own.** [HARD] CORE-001, PROGRAMMING-007, WEBUI-018, ENRICH-012,
  MBMIRROR-017, REQUEST-011, ANALYSIS-006, VETTING-027 are referenced, never restated
  (NFR-S-3).
- **Brain + launcher only; additive.** [HARD] A seed-config reader on the `brain/` package +
  a `run.sh` setup step + a `seed-config.json`/`seed_decided` marker in `db_dir`; no new
  service, no Liquidsoap change, no change to `curate_batch`'s signature, no required
  listener-website surface (NFR-S-3/6).

---

## 2. Dependencies

This SPEC DEPENDS ON the existing curation path (`brain/llm.py` `curate_batch` /
`_build_prompt` / the `seed_reference` parameter; `brain/director.py` `_seed_reference` /
`_tick`), the existing first-run marker pattern (`brain/config.py` `welcome_marker_path`;
`brain/main.py`; `brain/server.py` `_mark_welcomed`), the existing library watch/scan
(`brain/library.py` `scan` / `_read_tags`; `brain/config.py` `watch_enabled` /
`watch_interval_seconds`), the env-driven `Config` (`brain/config.py` `_env` / `load_config`),
and the operator launcher (`scripts/run.sh`, esp. `resolve_slskd`'s interactive-prompt
pattern). It REFERENCES SPEC-RADIO-CORE-001 (engine parent), SPEC-RADIO-PROGRAMMING-007
(curation/personas), SPEC-RADIO-WEBUI-018 (the web-wizard alternative), SPEC-RADIO-ENRICH-012
+ SPEC-RADIO-MBMIRROR-017 (CSV→recording resolution for the optional acquisition path),
SPEC-RADIO-REQUEST-011 (the `acquire.enqueue` growth seam), SPEC-RADIO-ANALYSIS-006 (the
library watch), and SPEC-RADIO-VETTING-027 (the vet a seed-enqueued grab passes through).

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any sibling requirement. Where it needs
a predecessor behavior it consumes it. Where a seeding/ingest action could conflict with
continuous operation, the inherited never-block / exception-isolated behavior WINS — the music
keeps playing and the brain never fails to boot because of the seed.

Consumed concepts (by name/number where stable):
- **`brain/llm.py` `curate_batch(seed_reference=...)` / `_build_prompt`** — the non-binding
  reference hook (`llm.py:194-208, 211-215`). SEEDING-029 supplies `seed_reference` and tunes
  its framing per mode. The signature is UNCHANGED (the reference is a `List[str]`); the
  per-mode WEIGHT is conveyed by which/how-many refs are passed and the framing text. The
  implementation caps the woven reference at the first 15 entries (`seed_reference[:15]`).
- **`brain/director.py` `_seed_reference()` / `_tick()`** — the `# FUTURE:` stub
  (`director.py:47-51`) SEEDING-029 makes return the persisted seed refs (or `[]` for WOPR).
- **`brain/config.py` `welcome_marker_path` + `_env` + `load_config`** — the once-per-genesis
  marker pattern SEEDING-029 mirrors for `seed_decided`, and the env-driven config the
  `BRAIN_SEED_*` knobs join.
- **`brain/library.py` `scan` / `_read_tags`; `config.py` `watch_enabled`** — the playable
  ingest of dropped files SEEDING-029 reads a TASTE signal over (it does not change the
  ingest).
- **`brain/acquire.py` `enqueue(artist,title)`** — the optional seed-as-acquisition seam
  (`acquire.py:134`).
- **`scripts/run.sh` `resolve_slskd()`** — the interactive-prompt-with-default pattern
  (`run.sh:295-323`) the run.sh seed-setup step mirrors.

### 2.1 Load-bearing dependency — the persisted seed-config contract

[HARD][CONSTRAINT] The headless brain reads the operator's choice from a single persisted
artifact — `seed-config.json` in `db_dir` plus the `seed_decided` marker. Both the run.sh
setup step (primary) and the WEBUI-018 wizard (alternative) MUST write the SAME contract. The
contract shape (mode + sources + seed-as-acquisition flag + the captured taste references) is
implementation detail bounded by REQ-SB-004; that BOTH writers produce the same brain-readable
contract is the rail. Surfaced as D-1.

### 2.2 Load-bearing dependency — the fidelity weight maps onto the existing hook only

[HARD][DEPENDENCY] SEEDING-029 must express ANCHOR / COMPASS / WOPR PURELY through what the
existing `curate_batch` hook can carry: the contents/length of the `seed_reference` list and
the prompt FRAMING (`_build_prompt`), plus the acquisition bias (which seed refs are enqueued
and how strongly the director re-tops toward seed-adjacent). It MUST NOT require a new curation
engine, a new LLM call shape, or a change to `curate_batch`'s signature. The per-mode framing
strength is the lever. Surfaced as D-2.

### bhive memory seam

bhive memory (AGENTS.md protocol) has no proven pattern for a "first-run interactive taste
pre-seed gate + fidelity-weighted non-binding seed bias on an LLM-curated radio stack"
(recorded gap; consistent with the standing bhive Stack Gap note). Re-run a bhive query on the
CSV-taste-seed + non-binding-bias-weighting pattern during implementation and contribute the
verified approach back per the AGENTS.md memory protocol.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Seed / seed reference** | The operator's taste signal handed to the station at first run: a list of `{artist,title}` references (from a Spotify CSV) and/or dropped-file metadata, fed to `curate_batch` as the NON-BINDING `seed_reference` (`llm.py:215`). Never a hard whitelist (Group SF, REQ-SF-004). |
| **First-run seed gate** | The one-time decision point — pre-seed or not, and how — captured at/before first launch and persisted, never re-prompted on restart. Mirrors the `welcome_marker` once-per-genesis pattern (Group SB). |
| **`seed_decided` marker** | A sentinel file in `db_dir` (mirroring `welcomed`, `config.py:225-229`) marking that the first-run seed decision has been made. Present → the gate is satisfied; the brain boots straight to the persisted config and never re-prompts. Delete to re-arm (REQ-SB-002). |
| **`seed-config.json`** | The persisted decision in `db_dir`: the chosen fidelity mode, the seed sources, the captured taste references, and the seed-as-acquisition flag. The single contract both the run.sh setup step and the WEBUI-018 wizard write and the headless brain reads (REQ-SB-004). |
| **run.sh setup step** | The PRIMARY first-run mechanism: an interactive step in `scripts/run.sh` mirroring `resolve_slskd()` (`run.sh:295-323`) that prompts the operator (TTY) with a non-interactive default, writes `seed-config.json`, and drops the marker BEFORE/at first launch (REQ-SB-001). |
| **Web wizard (alternative)** | The ALTERNATIVE/future first-run mechanism: a WEBUI-018-served wizard writing the SAME `seed-config.json` contract. Forward-compatible; not required for v0.1.0 (REQ-SB-005). |
| **Spotify CSV export** | A playlist CSV in the common Exportify schema (`"Track Name"`, `"Artist Name(s)"`, `"Album Name"`) with a tolerant fallback to a minimal `artist,title` CSV. Parsed → `{artist,title}` taste references (REQ-SS-001). |
| **Tolerant parser** | The CSV parser property: it skips malformed/empty rows, accepts header variants, and NEVER raises — a bad file degrades to whatever rows parsed (possibly none), never crashing startup (REQ-SS-002). |
| **Dropped-file taste signal** | The NEW second role of files dropped into `music_dir`: their artist/title/genre metadata become a taste reference, IN ADDITION to the existing playable-ingest the watch already performs. Distinct from the playable role (REQ-SS-004). |
| **Seed-as-acquisition (sub-option)** | The OPTIONAL behavior (OFF by default) where CSV `{artist,title}` references are ALSO enqueued for download via `acquire.enqueue` (`acquire.py:134`), so the seed grows the library, not just biases curation. Each grab still passes VETTING-027 (REQ-SS-005). |
| **ANCHOR** | Fidelity mode: "base everything on it." Strong bias toward seed artists/genres/era + close neighbors; acquisition prioritizes seed-adjacent. STILL soft — raises the bias weight, never hard-filters (REQ-SF-001, REQ-SF-004). |
| **COMPASS** | Fidelity mode: "good tunes, surprise me." Loose starting compass; deliberate outward exploration, tonally informed by the seed (REQ-SF-002). |
| **WOPR** | Fidelity mode: "do whatever the hell you want." Full autonomy, no seed needed/used. ALSO the no-preseed default = today's `SEED_TRACKS` + freeform curation (REQ-SF-003). |
| **Non-binding invariant** | [HARD][LOAD-BEARING] The seed is a soft bias at EVERY fidelity level; it shifts curation WEIGHT, never a hard whitelist; ANCHOR raises weight without hard-filtering; the golden rule (never stop) wins on a dry seed-adjacent pool (REQ-SF-004, NFR-S-2). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group SB — Bootstrap / First-Run Decision Gate.** The one-time interactive choice; the
  `seed_decided` marker + `seed-config.json` persistence (mirroring `welcome_marker`); the
  headless-container run.sh-setup primary mechanism; the WEBUI-018 web-wizard alternative; the
  never-re-prompt-on-restart rule; the always-boot-and-play-on-decline rule.
- **Group SS — Seed Sources / Ingest.** The tolerant Spotify-CSV parser (Exportify + minimal
  fallback) → `{artist,title}` taste references; the never-crash tolerant parsing; the
  taste-feeds-curation-not-auto-download default; the dropped-music-file taste signal
  (distinct from the existing playable ingest); the optional seed-as-acquisition sub-option.
- **Group SF — Taste-Fidelity Modes.** The three modes (ANCHOR / COMPASS / WOPR); their
  concrete `seed_reference` weight + prompt-framing + acquisition-bias mapping onto the
  existing hook; the WOPR-is-the-no-preseed-default rule; the [HARD] non-binding-at-every-
  level invariant.
- Plus **NFRs** (Section 8) and **Risks** (Section 9).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **The curation engine / `curate_batch`'s signature** — owned by CORE-001; SEEDING-029
  supplies `seed_reference` and framing, never re-implements curation or changes the
  signature.
- **Live Spotify/YouTube OAuth ingest** — the `SEED_ENRICHMENT_STUBS` token surface
  (`config.py:264-270`) stays a documented future; SEEDING-029 uses FILE-based ingest only.
- **The library watch / scan / playable ingest of dropped files** — owned by ANALYSIS-006;
  SEEDING-029 only reads a TASTE signal over the same files.
- **The acquisition pipeline / download workers / source preference** — owned by
  ACQQUEUE-019 + the existing acquirer; the seed-as-acquisition sub-option only TRIGGERS
  `acquire.enqueue`, it does not re-own acquisition.
- **CSV `{artist,title}` → canonical-recording RESOLUTION** — owned by ENRICH-012 +
  MBMIRROR-017; only the optional acquisition path resolves, via the existing pipeline.
- **The request lifecycle / request anti-abuse** — owned by REQUEST-011; SEEDING-029 only
  uses the `enqueue` seam for the first-run CSV-enqueue.
- **The vet cascade / ban-list** — owned by VETTING-027; a seed-enqueued grab passes through
  it unchanged; SEEDING-029 never bypasses or re-owns it.
- **The per-persona distinct-taste curation** — owned by PROGRAMMING-007; SEEDING-029 sets a
  station-level bias upstream and must not flatten the persona firewall.
- **A required listener-website surface** — the seed config is operator/internal; the WEBUI-018
  wizard is an OPTIONAL alternative front-end, never a v0.1.0 requirement.
- **A server DB / a hosted preference store / a cloud sync of the seed** — out of scope;
  brain-local `seed-config.json` only.
- **Re-prompting / multi-seed-merge / live re-seeding mid-broadcast** — out of scope for
  v0.1.0; the gate fires once per genesis (re-arm by deleting the marker). A richer re-seed
  surface is a future enhancement.
- **A taste/quality judgement of the seed** — SEEDING-029 records the operator's taste as-is;
  it does not vet, rank, or "improve" the seed.

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain + launcher only; additive.** A seed-config reader on the `brain/` package +
  a `scripts/run.sh` setup step + a `seed-config.json`/`seed_decided` marker in `db_dir`; no
  new service, no Liquidsoap change, no change to `curate_batch`'s signature, no required
  listener-website surface.
- [HARD] **Exception-isolated.** A malformed CSV row, an unreadable drop, or a
  missing/corrupt `seed-config.json` logs and degrades to WOPR; it NEVER fails the brain's
  boot, crashes the director loop, or silences the stream.
- [HARD][LOAD-BEARING] **The non-binding invariant.** The seed is a soft bias at EVERY
  fidelity level; ANCHOR raises weight, never hard-filters; the golden rule wins on a dry
  seed-adjacent pool.
- [HARD] **First-run gate, once per genesis, never re-prompts.** Mirrors `welcome_marker`; a
  restart/redeploy reads the persisted decision.
- [HARD] **Headless mechanism.** The choice is captured OUTSIDE the brain (run.sh-setup
  primary; WEBUI-018 wizard alternative), written to a single `seed-config.json` contract.
- [HARD] **File-based sources only; no live OAuth.** Spotify CSV export + audio drop.
- [HARD] **Tolerant parsing.** The CSV parser skips malformed rows and never crashes.
- [HARD] **The station ALWAYS boots and plays.** Decline → WOPR = today's behavior; the gate
  is a preference, never a barrier.
- [HARD] **Reference, don't re-own.** CORE-001, PROGRAMMING-007, WEBUI-018, ENRICH-012,
  MBMIRROR-017, REQUEST-011, ANALYSIS-006, VETTING-027 are referenced, never restated.
- [HARD] **Resilience.** A seed-config read failure logs and degrades to WOPR; the station
  proceeds exactly as if no seed were chosen (today's behavior).

---

## 6. Requirements

### Group SB — Bootstrap / First-Run Decision Gate

Priority: High (SB-001/002/003/004/006) / Medium (SB-005).

#### REQ-SB-001 — First-run interactive seed choice via the run.sh setup step (Event-driven) [HARD]

When the station is launched and no `seed_decided` marker exists in `db_dir` (a first run),
the system SHALL present the operator a ONE-TIME interactive choice — whether to pre-seed and
HOW (which sources, which fidelity mode, the seed-as-acquisition sub-option) — captured by an
interactive setup STEP in `scripts/run.sh` that mirrors the existing `resolve_slskd()`
TTY-prompt-with-default pattern (`run.sh:295-323`): prompt on a TTY, fall back to a safe
default (decline → WOPR) when non-interactive. [HARD] Because the brain is a HEADLESS Docker
container with no runtime stdin, this capture MUST happen in the launcher (or an equivalent
setup command) OUTSIDE the brain, BEFORE/at first launch. That the first-run choice is
captured by an interactive run.sh setup step outside the headless brain is the rail.

**Acceptance criteria:** see acceptance.md AC-SB-001.

#### REQ-SB-002 — Persist the decision; never re-prompt on restart (Ubiquitous) [HARD]

The system SHALL persist the first-run seed decision so it is captured ONCE per station
genesis and NEVER re-prompted on a restart — including a mid-broadcast redeploy. [HARD] This
MIRRORS the `welcome_marker_path` once-per-genesis pattern (`config.py:225-229`; armed at
`main.py:89` only when `not os.path.exists(...)`; written best-effort at `server.py:218`): a
`seed_decided` marker in `db_dir` records that the decision is made; while it is present, the
setup step is a no-op and the brain boots straight to the persisted config. Deleting the
marker (or wiping the db) re-arms the gate. That the decision is persisted once-per-genesis and
a restart never re-prompts is the rail.

**Acceptance criteria:** see acceptance.md AC-SB-002.

#### REQ-SB-003 — A mid-broadcast redeploy MUST NOT re-prompt or disturb playout (Unwanted) [HARD]

If the brain (or the stack) is redeployed while the station is already on air, then the system
SHALL NOT re-prompt for the seed decision and SHALL NOT block or interrupt playout to ask:
the persisted `seed_decided` marker + `seed-config.json` are read silently at startup and the
station resumes with the already-chosen seed. [HARD] The first-run gate SHALL NEVER become a
runtime barrier — a redeploy reads the decision, it never re-asks. That a redeploy is silent
(no re-prompt, no playout disturbance) is the rail.

**Acceptance criteria:** see acceptance.md AC-SB-003.

#### REQ-SB-004 — The persisted seed-config contract (mode + sources + refs + acquisition flag) (Ubiquitous) [HARD]

The system SHALL persist the decision as a single `seed-config.json` in `db_dir` whose content
captures at least: the chosen FIDELITY MODE (`anchor` | `compass` | `wopr`); the SEED SOURCES
used (the Spotify-CSV path/marker and/or the dropped-file taste signal); the captured TASTE
REFERENCES (the `{artist,title}` list parsed from the CSV, and/or a marker that dropped-file
metadata should be read); and the SEED-AS-ACQUISITION flag (default off). [HARD] The exact
field layout is implementation detail; that a single brain-readable `seed-config.json`
contract captures mode + sources + refs + the acquisition flag is the rail. The brain reads
this file at startup (consistent with the env-driven `Config`; an env var MAY point at it).

**Acceptance criteria:** see acceptance.md AC-SB-004.

#### REQ-SB-005 — A WEBUI-018 first-run web wizard is a forward-compatible alternative (Optional) [HARD] [consistency]

Where a first-run WEB WIZARD is provided via SPEC-RADIO-WEBUI-018, the system SHALL allow it to
capture the same first-run seed choice and write the SAME `seed-config.json` contract
(REQ-SB-004) + drop the SAME `seed_decided` marker, so the headless brain reads it identically
regardless of which front-end captured it. [HARD] [consistency] SEEDING-029 specifies the
run.sh setup step as the PRIMARY mechanism and the web wizard as an ALTERNATIVE; the wizard is
NOT required for v0.1.0 and SEEDING-029 does NOT re-own WEBUI-018's web surface. That the web
wizard is a forward-compatible alternative writing the same contract (not a v0.1.0
requirement) is the rail.

**Acceptance criteria:** see acceptance.md AC-SB-005.

#### REQ-SB-006 — Decline or undecided → WOPR; the station ALWAYS boots and plays (Unwanted) [HARD]

If the operator DECLINES seeding, or no decision is reachable (a non-interactive launch with no
prior config, a missing/corrupt `seed-config.json`), then the system SHALL boot the station in
WOPR using today's behavior (`SEED_TRACKS` + freeform `curate_batch` with an empty
`seed_reference`) and SHALL NEVER block the boot or the stream on the seed choice. [HARD] The
first-run gate is a one-time PREFERENCE capture, never a barrier: the station ALWAYS boots and
plays regardless of the seed choice. That decline/undecided degrades to WOPR and the station
always boots and plays is the rail.

**Acceptance criteria:** see acceptance.md AC-SB-006.

### Group SS — Seed Sources / Ingest

Priority: High (SS-001/002/004) / Medium (SS-003/005).

#### REQ-SS-001 — Spotify-CSV parse → {artist,title} taste references (Event-driven) [HARD]

When the operator supplies a Spotify playlist CSV export, the system SHALL parse it into a list
of `{artist, title}` taste references, accepting the common Exportify schema (the columns
`"Track Name"`, `"Artist Name(s)"`, `"Album Name"`) with TOLERANT FALLBACKS to a minimal
`artist,title` CSV (and reasonable header-name variants). [HARD] The parsed references feed the
fidelity layer (Group SF) as the `seed_reference` content; the album column MAY be captured for
context but the taste reference is `{artist,title}`. That the parser turns a Spotify CSV export
(Exportify schema, with a minimal-CSV fallback) into `{artist,title}` taste references is the
rail.

**Acceptance criteria:** see acceptance.md AC-SS-001.

#### REQ-SS-002 — Tolerant parsing: skip malformed rows, never crash startup (Unwanted) [HARD]

If a CSV row is malformed, empty, missing required columns, or otherwise unparseable, then the
system SHALL SKIP that row and continue, and SHALL NEVER raise or crash startup on a bad CSV.
[HARD] A wholly-unreadable or empty CSV degrades to ZERO taste references (and therefore to
WOPR-equivalent freeform curation), logged, never fatal — mirroring the brain's pervasive
best-effort posture (the tolerant `Library._load`, the never-raise `curate_batch`). That the
CSV parser skips malformed rows and never crashes startup is the rail.

**Acceptance criteria:** see acceptance.md AC-SS-002.

#### REQ-SS-003 — CSV refs feed TASTE by default; auto-download is the opt-in sub-option (Ubiquitous) [HARD]

The system SHALL, by DEFAULT, treat the parsed CSV references as a TASTE signal only — feeding
`seed_reference` (Group SF) so curation is biased toward them — and SHALL NOT auto-download
them. [HARD] Enqueuing the CSV references for ACQUISITION is a SEPARATE, OPT-IN sub-option
(REQ-SS-005), OFF unless the operator enables it. That CSV refs seed TASTE by default and
auto-download is an explicit opt-in (the two roles are distinct) is the rail.

**Acceptance criteria:** see acceptance.md AC-SS-003.

#### REQ-SS-004 — Dropped music files: a taste signal IN ADDITION to the existing playable ingest (Ubiquitous) [HARD] [consistency]

The system SHALL treat audio files the operator drops into `music_dir` as a TASTE SIGNAL — their
artist/title/genre metadata feeding `seed_reference` (Group SF) — IN ADDITION to the EXISTING
playable ingest the library watch already performs (`config.py:160-168` `watch_enabled` /
`watch_interval_seconds`; `library.py:292-340` `scan`). [HARD] [consistency] SEEDING-029 does
NOT change the playable ingest (the dropped file is still a normal rotation track); it ADDS a
distinct TASTE reading over the same files. The two roles — PLAYABLE rotation entry vs TASTE
reference — are kept distinct, and the watch is referenced, not re-owned. That dropped files
become a taste signal in addition to (not instead of) their existing playable role is the rail.

**Acceptance criteria:** see acceptance.md AC-SS-004.

#### REQ-SS-005 — Optional seed-as-acquisition via the existing enqueue seam; still vetted (Event-driven) — Priority Medium

When the operator ENABLES the seed-as-acquisition sub-option, the system SHALL enqueue the
parsed CSV `{artist,title}` references for download via the existing `acquire.enqueue`
(`acquire.py:134`), so the seed GROWS the library, not just biases curation. [HARD] Each
enqueued grab SHALL pass through the normal acquisition path UNCHANGED — including the
VETTING-027 pre-download vet (when built), the `attempts`/`in-flight`/`has_key` dedup
(`acquire.py:140-145`), and the size/duration cut — so the seed never bypasses any guard.
SEEDING-029 owns only the first-run CSV-enqueue TRIGGER; ENRICH-012/MBMIRROR-017 resolve the
references to real recordings via the existing pipeline. That the optional seed-as-acquisition
enqueues via the existing (vetted, deduped) seam is the rail.

**Acceptance criteria:** see acceptance.md AC-SS-005.

### Group SF — Taste-Fidelity Modes

Priority: High.

#### REQ-SF-001 — ANCHOR: strong seed bias + seed-adjacent acquisition, still soft (State-driven) [HARD]

While the fidelity mode is ANCHOR, the system SHALL bias curation STRONGLY toward the seed's
artists / genres / era and close neighbors — passing the seed as `seed_reference` with framing
that instructs the model to lean hard on it — AND bias acquisition toward seed-adjacent
material. [HARD] ANCHOR concretely RAISES the seed's weight (more/insistent `seed_reference`
framing, seed-adjacent acquisition preference); it MUST be expressible through the existing
`curate_batch` hook (the `seed_reference` list + `_build_prompt` framing), NOT a new engine
(Section 2.2). [HARD] ANCHOR remains SOFT (REQ-SF-004): it raises the bias weight, it does NOT
hard-filter the library to only-seed. That ANCHOR is a strong-but-soft seed bias mapped onto
the existing hook is the rail.

**Acceptance criteria:** see acceptance.md AC-SF-001.

#### REQ-SF-002 — COMPASS: loose seed compass + deliberate outward exploration (State-driven) [HARD]

While the fidelity mode is COMPASS, the system SHALL treat the seed as a LOOSE starting compass:
it SHALL pass the seed as `seed_reference` with framing that invites the model to EXPLORE
OUTWARD (adjacent genres, discovery, surprise) while staying tonally INFORMED by the seed.
[HARD] COMPASS is a weaker, exploration-forward framing of the SAME `seed_reference` hook than
ANCHOR — it is expressed by the prompt framing and a lighter acquisition bias, not by a new
mechanism. That COMPASS is a loose, exploration-forward seed compass mapped onto the existing
hook is the rail.

**Acceptance criteria:** see acceptance.md AC-SF-002.

#### REQ-SF-003 — WOPR: full autonomy; also the no-preseed default (= today's behavior) (State-driven) [HARD]

While the fidelity mode is WOPR, the system SHALL run with FULL autonomy — the AI self-directs
from its LLM persona + knowledge base, passing an EMPTY (or absent) `seed_reference`, ignoring
or not requiring any seed. [HARD] WOPR is ALSO the NO-PRESEED DEFAULT: when the operator
declines seeding (REQ-SB-006), the station runs in WOPR, which is EXACTLY today's behavior —
freeform `curate_batch` with the built-in `SEED_TRACKS` resilience fallback. That WOPR is full
autonomy AND the no-preseed default equal to today's behavior is the rail.

**Acceptance criteria:** see acceptance.md AC-SF-003.

#### REQ-SF-004 — The seed is NON-BINDING at EVERY fidelity level; the golden rule wins (Unwanted) [HARD] [LOAD-BEARING]

The system SHALL treat the seed as a NON-BINDING bias at EVERY fidelity level — including
ANCHOR: the seed shifts curation WEIGHT and is fed as the `seed_reference` the model MAY ignore
(`llm.py:204-206`), and it biases acquisition; it SHALL NEVER act as a HARD WHITELIST that
restricts the library to only-seed material. [HARD][LOAD-BEARING] Even in ANCHOR, if
seed-adjacent material runs dry the station MUST KEEP PLAYING — the golden rule (never stop)
wins over the seed. ANCHOR raises the bias weight; it does NOT hard-filter. That the seed is a
soft bias at every level and the never-stop golden rule always wins is the rail — this is the
heart of the SPEC.

**Acceptance criteria:** see acceptance.md AC-SF-004.

#### REQ-SF-005 — Enable toggle + bounded config surface; disabled is exactly today's behavior (Ubiquitous) — Priority Medium

The system SHALL provide a CONFIG enable toggle and a bounded `BRAIN_SEED_*` config surface for
the seeding subsystem (the enable toggle, the `seed-config.json` path, a default/override
fidelity mode, and the seed-as-acquisition default). [HARD] When DISABLED (or with no
`seed-config.json`), the curation/acquisition path runs EXACTLY as today — `_seed_reference()`
returns `[]` and the station is WOPR (no seed read, no fidelity bias applied); when ENABLED with
a valid config, the seed + fidelity mode operate per Groups SS/SF. [HARD] The toggle + the
bounded `BRAIN_SEED_*` surface are the only config this SPEC adds. That the subsystem is
opt-in/additive and disabling it restores today's behavior is the rail.

**Acceptance criteria:** see acceptance.md AC-SF-005.

---

## 7. User-Provisioned Prerequisites (the real user must provide / decide)

[HARD] SEEDING-029 provisions no external account or hardware. The following are flagged so the
user knows what is required / decided:

- **The seed itself.** To pre-seed, the operator must provide a Spotify playlist CSV export
  (e.g. via Exportify) and/or drop music files into `music_dir`. With neither, the station runs
  in WOPR (the default), which works exactly as today.
- **The fidelity-mode choice.** The operator chooses ANCHOR / COMPASS / WOPR at first run (the
  no-preseed default is WOPR). It is persisted; re-arm by deleting the `seed_decided` marker.
- **The seed-as-acquisition decision.** The operator decides whether CSV references are ALSO
  enqueued for download (default off). When on, downloads consume bandwidth and the slskd queue
  and pass the normal vet.
- **The mechanism.** v0.1.0 captures the choice via the `scripts/run.sh` setup step (primary).
  The WEBUI-018 web wizard is an OPTIONAL alternative; the user/orchestrator confirms whether
  to build it now or defer (D-3).
- **The seed-config contract.** The user/orchestrator confirms the `seed-config.json` shape so
  both the run.sh step and any future wizard write the same contract (D-1).

---

## 8. Non-Functional Requirements

### NFR-S-1 — Never blocks boot, the director loop, or playout (Ubiquitous) — Priority High
All seeding/ingest/parse work (the CSV parse, the dropped-file taste read, the seed-config
read) shall be exception-isolated and run OFF the `<1s /api/next` pull path; a malformed CSV
row, an unreadable drop, or a missing/corrupt `seed-config.json` shall log and degrade to WOPR
— it shall NEVER fail the brain's boot, crash the director loop, or silence the stream.
Inherits CORE-001's continuous-operation identity. See acceptance.md AC-NFR-S-1.

### NFR-S-2 — The non-binding invariant holds at every fidelity level (Ubiquitous) — Priority High [LOAD-BEARING]
The system shall guarantee the seed is a SOFT bias at EVERY fidelity level: ANCHOR raises the
`seed_reference` weight + acquisition bias without hard-filtering the library; on a dry
seed-adjacent pool the picker still serves the next available track and the stream never
silences. The seed never becomes a hard whitelist. This is the load-bearing correctness
property of the SPEC. See acceptance.md AC-NFR-S-2.

### NFR-S-3 — Single-source-of-truth: reference siblings, never re-own (Ubiquitous) — Priority High [consistency]
No code path shall re-own or fork CORE-001's `curate_batch`/engine, PROGRAMMING-007's persona
curation, WEBUI-018's web surface, ENRICH-012/MBMIRROR-017's resolution, REQUEST-011's request
lifecycle, ANALYSIS-006's library watch, or VETTING-027's vet; each is referenced by id and
consumed/extended/applied. SEEDING-029 owns the first-run gate + the seed sources + the
fidelity knob only, and is brain + launcher only + additive (a seed-config reader + a run.sh
setup step + a `seed-config.json`/`seed_decided` marker; no new service, no `curate_batch`
signature change, no required listener-website surface, no server DB). See acceptance.md
AC-NFR-S-3.

### NFR-S-4 — First-run gate fires exactly once per genesis (Ubiquitous) — Priority High
The seed decision shall be captured at most ONCE per station genesis and persisted (the
`seed_decided` marker + `seed-config.json`), mirroring the `welcome_marker` guarantee: a
restart/redeploy reads the decision and never re-prompts; deleting the marker (or wiping the
db) is the only re-arm. See acceptance.md AC-NFR-S-4.

### NFR-S-5 — Tolerant / robust ingest by construction (Ubiquitous) — Priority Medium
The CSV parser and the dropped-file taste read shall be robust by construction: malformed rows
are skipped, header variants are accepted, an empty/garbage file yields zero references, and no
input ever crashes the parse or the boot. The seed is captured best-effort; partial parses are
acceptable (whatever parsed feeds the seed). See acceptance.md AC-NFR-S-5.

### NFR-S-6 — Brain + launcher only, additive; bounded config surface (Ubiquitous) — Priority Medium
No code path shall add a new service, daemon, Liquidsoap change, `curate_batch` signature
change, or required listener-website surface: the change is a brain-side seed-config reader on
the existing `brain/` package + a `scripts/run.sh` setup step + a `seed-config.json` /
`seed_decided` marker in `db_dir`, with a bounded `BRAIN_SEED_*` config surface (enable toggle,
config path, default fidelity mode, seed-as-acquisition default). See acceptance.md AC-NFR-S-6.

---

## 9. Open Questions / Risks

- **R-S-1 — The seed-config contract must be agreed across two writers (Medium, design).** The
  run.sh setup step (primary) and the WEBUI-018 wizard (alternative) must write the SAME
  `seed-config.json`. Mitigated: REQ-SB-004 fixes the contract fields; both writers target it.
  **Surfaced as D-1.**
- **R-S-2 — Expressing fidelity through the existing hook (Medium, design).** ANCHOR/COMPASS
  must be expressed purely via `seed_reference` contents + `_build_prompt` framing + the
  acquisition bias, not a new engine, and the prompt caps the reference at 15 entries
  (`seed_reference[:15]`). Mitigated: the per-mode framing strength + which refs are passed are
  the lever; a large CSV is sampled/prioritized into the cap. **Surfaced as D-2.**
- **R-S-3 — WEBUI-018 wizard timing (Low/Medium, dependency).** The web wizard is an
  alternative, not a v0.1.0 requirement. Mitigated: run.sh is the primary mechanism; the wizard
  is forward-compatible (same contract). **Surfaced as D-3.**
- **R-S-4 — Anchor could feel "stuck on the seed" (Medium, UX).** A strong ANCHOR bias on a
  small seed could narrow the flow. Mitigated: the non-binding invariant (REQ-SF-004) keeps it
  soft; even ANCHOR explores when seed-adjacent runs dry; COMPASS exists for those who want more
  surprise; the director's `recent`-avoidance still prevents repeats.
- **R-S-5 — Seed-as-acquisition bandwidth/queue load (Low/Medium, operational).** Enqueuing a
  large CSV could flood the slskd queue. Mitigated: it is OPT-IN (off by default), passes the
  existing rate limiter + dedup + VETTING-027, and the director's normal low-watermark pacing
  applies. **Surfaced as a default-off operational note.**
- **R-S-6 — Conflict with PROGRAMMING-007 per-persona distinct taste (Medium, boundary).** A
  station-level seed bias could homogenize personas. Mitigated: SEEDING-029 sets a soft
  upstream bias only and must not flatten the persona firewall; the boundary is referenced, not
  re-owned (NFR-S-3). **Surfaced as D-4.**
- **R-S-7 — bhive had no proven pattern for this stack (Low, recorded gap).** No bhive
  instruction exists for a first-run taste-seed gate + fidelity-weighted non-binding bias.
  Mitigated: grounded in the codebase (the `seed_reference` hook, the `welcome_marker` pattern,
  the run.sh prompt pattern, the library watch). Action: re-run a bhive query during
  implementation and contribute back per AGENTS.md.

---

## 10. Design Decisions Needing the Orchestrator's Ruling

These are surfaced (not silently assumed) for an explicit ruling before/within the Run phase:

- **D-1 — The `seed-config.json` contract (decides REQ-SB-004/005).** The persisted decision
  shape (mode + sources + captured refs + acquisition flag). RECOMMENDATION: a single JSON in
  `db_dir` (e.g. `seed-config.json`) with `{mode, sources, references, acquire}`; an env var
  (`BRAIN_SEED_CONFIG_PATH`) points the brain at it. Both the run.sh step and any future wizard
  write it. Confirm the field layout.
- **D-2 — How fidelity maps onto the existing hook (decides REQ-SF-001/002/003).** Express
  ANCHOR/COMPASS/WOPR via the `seed_reference` contents + `_build_prompt` framing + the
  acquisition bias, NOT a new engine; account for the `seed_reference[:15]` cap.
  RECOMMENDATION: per-mode framing strings + a per-mode acquisition-bias weight; sample a large
  CSV into the cap (prioritize most-representative refs). Confirm the framing/weighting
  approach.
- **D-3 — run.sh setup step (primary) vs WEBUI-018 web wizard (alternative) timing (decides
  REQ-SB-001/005).** RECOMMENDATION: build the run.sh setup step now (it matches the existing
  `resolve_slskd` pattern and the headless constraint); defer the web wizard to a WEBUI-018
  increment as a forward-compatible alternative writing the same contract. Confirm.
- **D-4 — Station-seed bias vs PROGRAMMING-007 per-persona taste (decides the SF↔PR boundary).**
  The seed sets a station-level bias upstream of persona curation. RECOMMENDATION: SEEDING-029
  feeds a soft station-level `seed_reference`; PROGRAMMING-007's per-persona distinct-taste
  curation still applies downstream and is never flattened. Confirm the layering when
  PROGRAMMING-007 is built.

---

## 11. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 +
the Section 10 deferrals, as the mandatory exclusions list):

- **A new curation engine or any change to `curate_batch`'s signature** — owned by CORE-001;
  SEEDING-029 supplies `seed_reference` + framing only (REQ-SF-001/002/003, NFR-S-3/6).
- **Live Spotify/YouTube OAuth ingest** — the `SEED_ENRICHMENT_STUBS` token surface stays a
  documented future; SEEDING-029 uses FILE-based ingest only (REQ-SS-001).
- **Changing the library watch / scan / playable ingest** — owned by ANALYSIS-006; SEEDING-029
  only reads a TASTE signal over the same dropped files (REQ-SS-004, NFR-S-3).
- **Re-owning the acquisition pipeline / source preference** — the seed-as-acquisition
  sub-option only TRIGGERS `acquire.enqueue`; ACQQUEUE-019 + the acquirer own acquisition
  (REQ-SS-005, NFR-S-3).
- **CSV → canonical-recording RESOLUTION** — owned by ENRICH-012/MBMIRROR-017; only the
  optional acquisition path resolves, via the existing pipeline (REQ-SS-005, NFR-S-3).
- **The request lifecycle / request anti-abuse** — owned by REQUEST-011; SEEDING-029 uses only
  the `enqueue` seam (REQ-SS-005, NFR-S-3).
- **Re-owning or bypassing the vet / ban-list** — owned by VETTING-027; a seed-enqueued grab
  passes the vet unchanged (REQ-SS-005, NFR-S-3).
- **Flattening PROGRAMMING-007's per-persona distinct taste** — SEEDING-029 sets a soft
  station-level bias upstream only (NFR-S-3, D-4).
- **A hard-whitelist seed / a seed that can stop the music** — the seed is NON-BINDING at every
  level; ANCHOR raises weight, never hard-filters; the golden rule always wins
  (REQ-SF-004, NFR-S-2).
- **Blocking boot or playout on the seed choice / making the gate a runtime barrier** — the
  station ALWAYS boots and plays; decline → WOPR = today's behavior (REQ-SB-003/006, NFR-S-1).
- **Re-prompting on restart / live mid-broadcast re-seeding / multi-seed merge** — the gate
  fires once per genesis (re-arm by deleting the marker); a richer re-seed surface is a future
  enhancement (REQ-SB-002, NFR-S-4, Section 4.2).
- **A required listener-website surface / a web wizard as a v0.1.0 requirement** — the WEBUI-018
  wizard is an OPTIONAL alternative; run.sh is primary (REQ-SB-005, NFR-S-6).
- **A server DB / a hosted preference store / a cloud sync of the seed** — brain-local
  `seed-config.json` only (NFR-S-6).
- **A taste/quality judgement, ranking, or "improvement" of the seed** — SEEDING-029 records
  the operator's taste as-is (Section 4.2).

---

## 12. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md;
detailed Given-When-Then scenarios for the load-bearing requirements are in acceptance.md
Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-SB-001 | Bootstrap / First-Run Gate | High | Event | AC-SB-001 |
| REQ-SB-002 | Bootstrap / First-Run Gate | High | Ubiquitous | AC-SB-002 |
| REQ-SB-003 | Bootstrap / First-Run Gate | High | Unwanted | AC-SB-003 |
| REQ-SB-004 | Bootstrap / First-Run Gate | High | Ubiquitous | AC-SB-004 |
| REQ-SB-005 | Bootstrap / First-Run Gate | Medium | Optional | AC-SB-005 |
| REQ-SB-006 | Bootstrap / First-Run Gate | High | Unwanted | AC-SB-006 |
| REQ-SS-001 | Seed Sources / Ingest | High | Event | AC-SS-001 |
| REQ-SS-002 | Seed Sources / Ingest | High | Unwanted | AC-SS-002 |
| REQ-SS-003 | Seed Sources / Ingest | Medium | Ubiquitous | AC-SS-003 |
| REQ-SS-004 | Seed Sources / Ingest | High | Ubiquitous | AC-SS-004 |
| REQ-SS-005 | Seed Sources / Ingest | Medium | Event | AC-SS-005 |
| REQ-SF-001 | Taste-Fidelity Modes | High | State | AC-SF-001 |
| REQ-SF-002 | Taste-Fidelity Modes | High | State | AC-SF-002 |
| REQ-SF-003 | Taste-Fidelity Modes | High | State | AC-SF-003 |
| REQ-SF-004 | Taste-Fidelity Modes | High | Unwanted | AC-SF-004 |
| REQ-SF-005 | Taste-Fidelity Modes | Medium | Ubiquitous | AC-SF-005 |
| NFR-S-1 | Non-Functional | High | Ubiquitous | AC-NFR-S-1 |
| NFR-S-2 | Non-Functional | High | Ubiquitous | AC-NFR-S-2 |
| NFR-S-3 | Non-Functional | High | Ubiquitous | AC-NFR-S-3 |
| NFR-S-4 | Non-Functional | High | Ubiquitous | AC-NFR-S-4 |
| NFR-S-5 | Non-Functional | Medium | Ubiquitous | AC-NFR-S-5 |
| NFR-S-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-S-6 |

Parity: 16 REQ + 6 NFR = 22 specified items; 22 acceptance entries (16 AC + 6 AC-NFR);
1:1 REQ↔AC.

REQ-group prefixes + counts: SB (Bootstrap / First-Run Decision Gate) = 6, SS (Seed Sources /
Ingest) = 5, SF (Taste-Fidelity Modes) = 5 → 6+5+5 = 16 REQ across 3 groups. NFR-S-1…6 = 6 NFR.
Total = 16 + 6 = 22 specified items, 22 acceptance entries, 1:1 REQ↔AC. The three fidelity
modes: ANCHOR, COMPASS, WOPR.
