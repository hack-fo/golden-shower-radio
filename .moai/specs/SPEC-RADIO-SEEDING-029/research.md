# SPEC-RADIO-SEEDING-029 — Research (Plan-Phase Codebase Grounding)

This is the plan-phase research artifact for SPEC-RADIO-SEEDING-029 ("Initial Library
Seeding & Taste-Fidelity Cold-Start"). It records, with `file:line` citations, what the
station does TODAY around taste-seeding and library ingest, what this SPEC ADDS, and the
exact integration points. No implementation code is written here.

---

## 1. What seeding does TODAY (verified by reading)

### 1.1 The non-binding seed reference already exists end-to-end (the primary hook)

The LLM curation path ALREADY accepts a non-binding taste reference and weaves it into the
prompt — but nothing feeds it yet.

- `brain/llm.py:55` — `SEED_TRACKS: List[Dict[str, str]]` is a hardcoded fallback list of
  ~32 real, well-known tracks across genres. Its DOCSTRING-level purpose (`llm.py:53-54`)
  is "Keeps the station alive when the LLM is unreachable / quota-limited." It is a
  RESILIENCE fallback, NOT a taste seed in the user sense.
- `brain/llm.py:211` — `curate_batch(model, batch_size=25, recent=None, seed_reference=None)`
  is the curation entry point. It `NEVER raises; always returns >=1`. On any SDK
  error / quota / empty parse it falls back to a SHUFFLED copy of `SEED_TRACKS`
  (`llm.py:237-241`).
- `brain/llm.py:215` — the signature ALREADY declares
  `seed_reference: Optional[List[str]] = None`. This is the parameter this SPEC wires the
  user's taste into.
- `brain/llm.py:194-208` — `_build_prompt(batch_size, recent, seed_reference)`. When
  `seed_reference` is non-empty it appends (verbatim, `llm.py:203-207`):
  `"For loose reference only (the listener's taste - feel free to expand on or ignore it): "
  + "; ".join(seed_reference[:15]) + "."`. This is the EXACT framing of a NON-BINDING bias:
  the model MAY ignore it. Note the implementation caps the reference at the first 15
  entries (`seed_reference[:15]`).
- `brain/llm.py:230` — a successful curation logs `llm.curated`; an empty parse logs
  `llm.empty_parse`; an error logs `llm.error_fallback_to_seed` (`llm.py:232,234`).

**Conclusion:** the receiving end of seeding is built and exercised. SEEDING-029 does NOT
need to touch `curate_batch`'s contract — it only needs to SUPPLY `seed_reference` and tune
the prompt framing per fidelity mode.

### 1.2 The director passes NO seed today (the `# FUTURE:` stub)

- `brain/director.py:52-59` — `_tick()` calls
  `llm.curate_batch(model=..., batch_size=..., recent=recent, seed_reference=self._seed_reference())`.
- `brain/director.py:47-51` — `_seed_reference()` returns `[]` with the comment:
  `"# FUTURE: pull the user's Spotify/YouTube liked tracks here as NON-BINDING reference
  context (see brain.config.SEED_ENRICHMENT_STUBS). Phase 1: none."`
- The director loop (`director.py:75-100`) scans the library, ticks an immediate batch on
  start, then re-ticks when the wishlist+library drop below `wishlist_low_watermark` or the
  `director_interval_seconds` schedule is due. Every tick is exception-wrapped
  (`_safe_tick`, `director.py:102-106`) — the loop never crashes.

**Conclusion:** `_seed_reference()` is the single function SEEDING-029 makes return the
persisted seed taste references (and, per fidelity mode, possibly an empty list for WOPR).

### 1.3 The future seed-enrichment config surface is documented but NOT built

- `brain/config.py:264-270` — `SEED_ENRICHMENT_STUBS` is a commented-out dict documenting
  the intended Spotify/YouTube OAuth token surface
  (`SPOTIFY_REFRESH_TOKEN`, `YOUTUBE_REFRESH_TOKEN`). It is explicitly "Stubs for FUTURE
  seed enrichment (NOT built in phase 1)." SEEDING-029 does NOT require live OAuth — it uses
  FILE-based ingest (CSV export + dropped audio), which needs no token.

### 1.4 Dropped music files are ALREADY auto-ingested as playable (the library watch)

- `brain/library.py:292-340` — `Library.scan()` recursively walks `music_dir`, reads tags
  via mutagen (`_read_tags`, `library.py:177-202`, falling back to "Artist - Title"
  filename parsing, `_parse_filename`, `library.py:167-174`), dedups on
  `normalize_key(artist, title)` (`library.py:37-43`), and adds new `Track`s. It skips
  dot-dirs (e.g. `.talk`) and partial-download suffixes (`.part/.tmp/.ytdl`).
- `brain/config.py:160-168` — the WATCH (ANALYSIS-006 REQ-AP-007): `watch_enabled`
  (default on) + `watch_interval_seconds` (default 120) drive a periodic stat-scan that
  picks up manually-dropped files. The comment notes inotify is unreliable on the WSL2 bind
  mount, so the stat-scan is authoritative.

**Conclusion:** dropping MP3s into `music_dir` ALREADY makes them PLAYABLE. What SEEDING-029
ADDS is a SECOND role for those same files: their artist/title/genre metadata become a
TASTE signal feeding `seed_reference`. The two roles are distinct (playable rotation entry
vs taste reference) and must not be conflated.

### 1.5 The "once per station genesis" marker pattern (the model for the first-run gate)

- `brain/config.py:225-229` — `welcome_marker_path` returns
  `os.path.join(self.db_dir, "welcomed")`. The docstring: "Present -> the welcome is NOT
  re-armed on the next start (once per station genesis). Lives in DB_DIR so it survives
  brain restarts; delete it (or wipe the db) to re-arm."
- `brain/main.py:89` — armed only when `cfg.talk_enabled and cfg.welcome_enabled and not
  os.path.exists(cfg.welcome_marker_path)` → `state.arm_welcome()`.
- `brain/server.py:218-228` — `_mark_welcomed()` writes the sentinel
  (`open(path,"w").write("welcomed\n")`), best-effort (a write failure only risks
  re-welcoming, never breaks playout). It is written at serve time
  (`server.py:171-172`), AFTER the welcome clip is actually handed out.

**Conclusion:** SEEDING-029 MIRRORS this exact pattern — a `seed_decided` marker in
`db_dir` that, once present, suppresses the first-run prompt forever (a mid-broadcast
redeploy must NOT re-prompt). The seed CONFIG itself (which mode, which sources) is a
companion `seed-config.json` in `db_dir`.

### 1.6 The brain is a HEADLESS container; config is env-driven; run.sh is the operator door

- `brain/config.py:17-22, 22-23` — `Config` is a frozen dataclass; every field reads from
  the environment via `_env(name, default)` (`config.py:17-19`). There is no interactive
  config path inside the brain — it reads env at construction (`load_config()`,
  `config.py:260-261`).
- `scripts/run.sh` — the turnkey launcher (a LAUNCHER, not an installer, `run.sh:8-9`). It
  renders configs from secrets, preflight-checks, brings the compose stack up, verifies the
  live station. Critically it ALREADY has an interactive-prompt pattern:
  `resolve_slskd()` (`run.sh:295-323`) prints `"Launch slskd ...? [Y/n]"` and reads stdin
  WHEN `[[ -t 0 ]]` (a TTY), with a non-interactive default when piped. Precedence: flag >
  env > prompt > default.
- The compose `brain` service is headless: there is no live stdin to the brain process at
  runtime (it runs under docker compose `up -d`, `run.sh:352-359`). So the brain process
  CANNOT prompt the operator at runtime.

**Conclusion (the mechanism decision):** the first-run seed choice MUST be captured OUTSIDE
the headless brain. The RECOMMENDED primary path is an interactive setup STEP in
`scripts/run.sh` (mirroring `resolve_slskd`'s TTY-prompt-with-default), which writes the
operator's choice into `seed-config.json` in `db_dir` and drops the `seed_decided` marker
BEFORE/at first launch; the brain then reads that file at startup (an env var can point at
it, consistent with the env-driven `Config`). The ALTERNATIVE/future path is a WEBUI-018
first-run web wizard writing the SAME persisted seed-config contract.

### 1.7 The optional seed-as-acquisition seam

- `brain/acquire.py:134-147` — `Acquirer.enqueue(artist, title)` queues a `{artist,title}`
  for download unless it is already in the library, already attempted
  (`attempts.should_skip`), or in flight. The director already calls this per curated track
  (`director.py:64`).

**Conclusion:** the CSV seed's `{artist,title}` references CAN be enqueued for acquisition
via this exact call (a sub-option, OFF by default). When enabled, each enqueued grab still
passes through VETTING-027's pre-download vet (when built) — SEEDING-029 does not bypass it.

---

## 2. What this SPEC ADDS (the delta)

1. **A first-run seed-decision gate (Group SB).** A one-time interactive choice — pre-seed
   or not, and HOW (which sources, which fidelity mode) — captured at/before first launch,
   persisted to `seed-config.json` + a `seed_decided` marker in `db_dir`, never re-prompted
   on restart. Primary mechanism = a `scripts/run.sh` setup step (the headless-container
   constraint); alternative = a WEBUI-018 web wizard writing the same contract.
2. **Two file-based seed sources (Group SS).** (a) A Spotify-playlist CSV export parser
   (Exportify schema with tolerant fallbacks to a minimal `artist,title` CSV) → a list of
   `{artist,title}` taste references that feed `seed_reference` (and OPTIONALLY enqueue for
   acquisition, a sub-option). (b) Dropped audio files whose metadata becomes a taste
   signal IN ADDITION to the existing playable-ingest role.
3. **A three-mode taste-fidelity knob (Group SF).** ANCHOR / COMPASS / WOPR, set at first
   run, concretely changing the `seed_reference` weight + prompt framing passed to
   `curate_batch` and the acquisition bias — implemented against the EXISTING
   `seed_reference` hook. WOPR is also the no-preseed default.

What it does NOT add: no new service, no live OAuth, no change to `curate_batch`'s
signature, no change to the watch/scan, no listener-website surface (beyond the optional
WEBUI-018 wizard alt path).

---

## 3. Integration points (where the wiring attaches)

| Integration point | File:line (today) | What SEEDING-029 does |
|---|---|---|
| Non-binding taste reference | `brain/llm.py:194-208` `_build_prompt` / `:211-215` `curate_batch(seed_reference=...)` | SUPPLIES `seed_reference`; tunes the framing per fidelity mode. Does NOT change the signature. |
| Director seed feed | `brain/director.py:47-51` `_seed_reference()` (returns `[]`) | MAKES it return the persisted seed refs (or `[]` for WOPR). |
| First-run gate | `brain/config.py:225-229` `welcome_marker_path`; `main.py:89`; `server.py:218` | MIRRORS the marker pattern: a `seed_decided` marker + a `seed-config.json` in `db_dir`. |
| Operator setup door | `scripts/run.sh:295-323` `resolve_slskd()` (TTY-prompt-with-default) | ADDS a parallel interactive seed-setup step that writes `seed-config.json` + the marker before first launch. |
| Env-driven config | `brain/config.py:17-19` `_env` / `:260-261` `load_config` | ADDS `BRAIN_SEED_*` knobs (enable, config path, fidelity-mode default, seed-as-acquisition toggle) read at startup. |
| Dropped-file taste signal | `brain/library.py:292-340` `scan()` + `config.py:160-168` watch | READS dropped-file metadata (artist/title/genre) as a taste signal IN ADDITION to the playable-ingest it already does. |
| Optional seed-as-acquisition | `brain/acquire.py:134-147` `enqueue` | OPTIONALLY enqueues CSV `{artist,title}` refs (sub-option, off by default); still subject to VETTING-027. |
| CSV → real recording | ENRICH-012 (`brain/enrich.py`) / MBMIRROR-017 | CSV `{artist,title}` strings stay STRINGS for `seed_reference` (the LLM resolves loosely); only the OPTIONAL acquisition path resolves them to real files via the existing acquisition+enrich pipeline. |

---

## 4. Sibling SPEC relationships (reference, do not re-own)

- **CORE-001** — the engine PARENT. It owns `SEED_TRACKS`, `curate_batch`, the never-stop
  identity, and the "seed-as-reference (non-binding)" principle. SEEDING-029 inherits and
  applies it; it does not redefine it.
- **PROGRAMMING-007** — curation / personas / anti-convergence. SEEDING-029 supplies a
  station-level taste bias UPSTREAM of persona curation; it must not flatten the
  per-persona distinct-taste firewall PROGRAMMING-007 owns.
- **WEBUI-018** — the listener page + web surface; the ALTERNATIVE host for a first-run web
  wizard (writing the same `seed-config.json` contract). SEEDING-029 specifies run.sh as
  primary, the wizard as a forward-compatible alternative.
- **ENRICH-012 / MBMIRROR-017** — identification + MB resolution. Only the OPTIONAL
  seed-as-acquisition path needs CSV `{artist,title}` → real recording resolution, which it
  gets from the EXISTING acquisition + enrich pipeline; SEEDING-029 does not perform its own
  resolution.
- **REQUEST-011** — listener-request / acquisition-growth surface. The optional
  seed-as-acquisition sub-option enqueues via the same `acquire.enqueue` seam REQUEST-011
  also rides; SEEDING-029 owns only the first-run CSV-enqueue trigger, not the request
  lifecycle.
- **VETTING-027** — the vet cascade + ban-list. A seed-enqueued grab passes through the
  pre-download vet exactly like any other grab; SEEDING-029 never bypasses it.

---

## 5. House rules grounding (the golden rule everywhere)

- The brain keeps running and the stream NEVER stops. Every seeding/ingest/parse path is
  exception-isolated: a malformed CSV row is SKIPPED (never crashes the parse), an
  unreadable drop is IGNORED, a missing/corrupt `seed-config.json` degrades to WOPR (today's
  behavior). This mirrors the existing best-effort posture throughout the brain
  (`_safe_tick`, the tolerant `Library._load`, the best-effort `_mark_welcomed`,
  `curate_batch`'s never-raise contract). Encoded as an NFR.
- The seed is a NON-BINDING bias at every fidelity level — it shifts curation weight, it is
  never a hard whitelist. This is the load-bearing invariant and is grounded directly in the
  `_build_prompt` framing ("feel free to ... ignore it", `llm.py:204-206`).
- The station ALWAYS boots and plays regardless of the seed choice (decline → WOPR = today's
  SEED_TRACKS + freeform curation).

---

## 6. bhive memory seam

bhive memory (AGENTS.md protocol) has no proven pattern for a "first-run interactive taste
pre-seed gate + fidelity-weighted non-binding seed bias on an LLM-curated radio stack"
(recorded gap; consistent with the standing bhive Stack Gap note). Re-run a bhive query on
the CSV-taste-seed + non-binding-bias-weighting pattern during implementation and contribute
the verified approach back per the AGENTS.md memory protocol.
