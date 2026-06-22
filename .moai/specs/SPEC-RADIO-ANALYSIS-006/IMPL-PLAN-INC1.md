# ANALYSIS-006 — Increment 1 Implementation Contract

Authoritative build contract for the FIRST implementation increment of SPEC-RADIO-ANALYSIS-006 into the LIVE golden-shower-radio Python brain. Derived from the design+audit workflow (verdict: SHIP WITH FIXES). The 5 audit must-fixes are integrated below. Read the SPEC (`spec.md`/`acceptance.md`) and the current `brain/` source for full detail; this doc is the ordered, file-disjoint unit plan + the safety rails.

## Golden rules
- The stream is LIVE. Implementation only EDITS FILES — it does NOT rebuild/deploy. The build+test happens in a THROWAWAY image; live deploy is a separate, reviewed step.
- Not a git repo → units are SEQUENTIAL with disjoint file sets; verify (py_compile + unit tests) between units.
- Never raise into the `/api/next` pull path. Analysis is background-only.
- `field(default_factory=...)` for every mutable default (no bare `[]`/`{}`).

## VERIFIED GROUND TRUTH
- `Track` = flat dataclass `brain/library.py:39-48`; loaded via `Track(**rec)` at `:106`; the `except` at `:109` SILENTLY WIPES the index on `TypeError`. **The old loader provably crashes on the new schema (`TypeError: unexpected keyword argument 'bpm'`).** The tolerant loader (U1) is the #1 safety item — build + test it in isolation FIRST.
- `scan()` `library.py:125-173` runs under `self._lock` (RLock) on the hot path and persists on EVERY call (`if added or True:` `:169`). Analysis MUST NOT run inside `scan()`.
- `/api/next` annotate chokepoint: `_annotate_uri()` `server.py:37-58`, called `:226`. Current form `annotate:artist=<q>,title=<q>,mix_mode=<q>:<path>`, `q()=json.dumps`. expert-backend's work is LIVE — EXTEND, never replace.
- `NextItem` carries the full `Track` (`server.py:68`).
- Background-loop pattern: daemon thread + `stop_event.wait(N)` + per-tick try/except (see `Director`/`TalkDirector`). Wire-in `main.py:59-64` + `:80-83`.
- `Config` = `@dataclass(frozen=True)` `config.py:22`, `_env()` pattern.
- Image has ffmpeg, libsndfile1, soundfile, CPU torch, kokoro. NOT installed: librosa/pyloudnorm/musicbrainzngs/pylast.
- `StationState.downloading()` returns `List[str]` (state.py:129-131) — NOT an int. `acquirer.pending()` returns the int.

## SCOPE
IN: AD data model (extend Track in place + tolerant loader + schema version + query/adjacency/stats + allowlist set_analysis), AE engine (`analysis.py` librosa: bpm/key+camelot/energy/LUFS/cues/true_end/sonic-character, CPU/cached/idempotent), AM enrichment (`metadata.py`: MusicBrainz + TheAudioDB + filename/embedded fallback + multi-source consensus; Last.fm only if key), AP pipeline (`analyzer.py` bounded serialized non-blocking worker + stat-only watch + cache + graceful degradation), AT wiring (emit liq_cue_in/liq_cue_out/bpm/camelot/energy via existing annotate; grounded theory hints).
DEFERRED (reserve fields, do not build): offline beat-grid + rubberband club render; Essentia (librosa covers it, no cp312 wheel + AGPL); LLM sonic descriptions (`sonic_description` stays empty); content embeddings (`embedding_ref` unused); per-persona profile authoring/firewall (ANALYSIS provides dimensions+query only — PROGRAMMING-007/OPS own policy).

## AUDIT MUST-FIXES (integrated; non-negotiable)
- **B1 disk** — DONE before build (≥10 GB free confirmed).
- **B2 throttle** — Analyzer throttle MUST use `len(self.state.downloading())` (or wire `acquirer.pending()`); NEVER `state.downloading() >= int` (that's list>=int, silent dead throttle).
- **B3 index bloat** — DO NOT persist `beat_grid`/`downbeats` in `library.json` (they're the heaviest field and only for the DEFERRED render). Leave them as reserved empty lists in the Track (not populated/persisted this increment), so `_save_locked` stays small + fast. In Verify, MEASURE `_save_locked` wall-time on a fully-analyzed 240-track index under concurrent scan and assert `/api/next` stays <1s.
- **B4+M3 librosa/numba install + timeouts** — Install librosa/pyloudnorm in the SAME Dockerfile step as torch/kokoro (or pin numpy+numba to versions compatible with the torch/kokoro numpy), so pip's resolver sees the full constraint set. Add a runtime import check that includes `import numba` explicitly. Set EXPLICIT short timeouts (httpx `timeout=10`; `musicbrainzngs` module timeout) on every network call.
- **M5 set_analysis allowlist** — `set_analysis` MUST write only an ALLOWLIST of known analysis field names; hard-exclude `key`, `path`, `artist`, `title`. A metadata provider returning a field literally named `key` must NOT corrupt the dedup slug.
- **M1 content_sig** — `content_sig="<size>:<mtime>"`; tolerate mtime instability on the /mnt/f WSL2 mount by relying on the bounded batch + working throttle to cap any re-analysis storm; document it. (Cheap content-hash optional, not required this increment.)
- **M2 long-file guard** — tracks over ~15 min get a conservative cue default + low_confidence flag instead of a full decode; bound worker memory.
- **M4 no move-hash** — DROP the bespoke move/rename content-hash logic; rely on the existing `normalize_key` dedup + content_sig (Enforce Simplicity).
- **Minor** — loudness reference: use the existing configured target (talk targets -16 LUFS, config.py:82), not a hardcoded -18. Heuristic sonic buckets (`production`, `instrumentation_feel`) land as `audio-hint`/`candidate` in provenance, never `confirmed`.

## ORDERED UNITS (disjoint files; verify between)
- **U1** `brain/library.py` + `brain/config.py` — extend Track (all new fields default-empty; `beat_grid`/`downbeats` reserved-empty, NOT persisted-heavy; `key` dedup slug vs new `musical_key`); tolerant `_load()` (filter each rec to `{f.name for f in fields(Track)}`, per-record try/except, never wipe index); `SCHEMA_VERSION`; new methods `needs_analysis`/`set_analysis`(ALLOWLIST)/`query`/`adjacency`/`analysis_stats`/`note_source`; config knobs (analysis + enrichment + watch) incl. `lastfm_api_key` optional, `manifest_path`. GATE: py_compile + migration test on a COPY of the real `library.json` (load all ~240, no wipe; unknown-key dropped; missing-fields default; round-trip parity; set_analysis with a `{"key":...}`/`{"musical_key":...}` payload leaves dedup `.key` untouched). MUST PASS before U2.
- **U2** `brain/analysis.py` (new) + `requirements.txt` + `deploy/Dockerfile.brain` — librosa CPU engine behind a thin swappable interface; `analyze_file(path, low_conf_threshold)->dict|None` (never raises); bpm(+conf), key+camelot via Krumhansl-Schmuckler chroma argmax (+conf→low_confidence_flags), energy, LUFS (pyloudnorm, fallback RMS), cues (cue_out vs true_end NOT duration), sonic_character (mfcc/spectral, feature-grounded), `transition_hints` (camelot neighbours only when key_confidence≥threshold). Lazy-import librosa inside the fn. Deps + Dockerfile per B4 (same-step/pinned + `import numba` check + long-file guard).
- **U3** `brain/metadata.py` (new) — `enrich(...)->dict` never raises; providers MusicBrainz (1 req/s self-throttle + UA + timeout), TheAudioDB (key 123, timeout), Last.fm (ONLY if key, else log-once + `{}`, never construct/raise), embedded, audio-hints; `consensus(...)` (>=min_sources allowlisted → confirmed; single-source → candidate/flagged; precedence MB>others>embedded>audio-hint; crowd-tag noise filter). AUDIO/GENRE/FEATURE consensus only (artist-FACT consensus is KNOWLEDGE-008). GATE: consensus unit tests + Last.fm-absent graceful test.
- **U4** `brain/analyzer.py` (new) + `brain/main.py` + `brain/server.py` + `brain/acquire.py` — bounded serialized (1 worker) non-blocking `Analyzer` (daemon thread, `needs_analysis`→`analyze_file` OFF-lock→`enrich`→`set_analysis` brief-lock; throttle via `len(state.downloading())` [B2]; cache via content_sig [AE-002]; mark failed files schema=current to avoid retry-loop; stat-only watch scan + manifest, NO move-hash [M4]); wire into main.py; `note_source` in acquire.py (only edit there); extend `_annotate_uri` with optional `extra` dict emitting `liq_cue_in/liq_cue_out/bpm/camelot/energy` ONLY when `track.schema_version>0` else IDENTICAL legacy string [AT-006]; add `analysis` block to `_handle_status`.

## VERIFY (throwaway image, then PAUSE for orchestrator review — NO live deploy in the workflow)
1. py_compile all touched modules.
2. Build a TEST image `docker build -f deploy/Dockerfile.brain -t gsr-brain-verify .` — if it fails (librosa/numba resolver), STOP + report. Confirm the audio-stack + `import numba` sanity check passes in the build.
3. Run the test image in a THROWAWAY container against a COPY of the live `library.json`: assert migration loads ~240 with no wipe (`library.loaded count≈240`); `/health`→ok; `/api/next`<1s returning a valid annotate (legacy-identical for an unanalyzed track [AT-006]); analyze 5-10 real tracks → records written, idempotent on 2nd tick (AE-002), worker survives a corrupt file; `/status` has the `analysis` block.
4. B3 proof: fully-analyze the index copy, time `_save_locked` + `/api/next` under concurrent scan → assert <1s.
5. Report all evidence + a SHIP/REVISE verdict. DO NOT run `scripts/run.sh` / deploy to the live brain — the orchestrator reviews the evidence and performs the live deploy separately.

Source: design+audit workflow wf_af99b13c-0d3 (2026-06-22).
