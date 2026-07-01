# SPEC-RADIO-LIVEMIX-060 — Implementation Plan

> Companion to `spec.md`. WHAT/WHY live in the SPEC; this file records the technical approach,
> milestones (priority-ordered, no time estimates), and risks. SPEC ONLY — no code is written here.

## 1. Technical Approach

A small, additive, playout-only control layered on the EXISTING OPS-004 selection pipeline. Three
moving parts, all brain-only:

1. **`brain/livemix.py` (NEW) — the live-cut classifier + theme detector.**
   - `is_live_cut(track) -> bool`: reuses `dedup.version_signals` (`dedup.py:64`) over
     `Track.title` + `Track.album`, intersected with the LIVE SUBSET of `DEFAULT_VERSION_TOKENS`
     (`dedup.py:52`). Pure, empty-safe, exception-isolated → NOT-live on any fault (REQ-LV-001/002/003).
   - `theme_relaxation(theme: str) -> RelaxSpec`: reuses the same whole-word tokenizer over the THEME
     vocabulary (live subset + theme-only phrases gig/tour/legendary concert/past concerts/live at) to
     return a relaxation spec: `none` (default lane), `partial` (raise ceiling), or `invert`
     (REQ-LZ-001/002/003/004).
   - `live_density_penalty(candidate, live_share, ceiling, lambda_, *, invert) -> float`: the additive
     term, mirroring `_family_balance_penalty` (`schedule.py:549`): `lambda_ * max(0, live_share -
     ceiling)`; on invert, the symmetric term penalizes NON-live candidates.

2. **`brain/schedule.py` (MODIFY) — wire one soft term into `SelectionRefiner`.**
   - Add the live-density term to the composite score loop (`schedule.py:610-620`), alongside
     `_soft_penalty` / `_family_balance_penalty`. Computed from a windowed live-share (derived from
     the same `recent_artists`/window inputs `refine` already receives, extended with per-play live
     flags) and the classifier.
   - Extend `refine(...)` with a `live_relax` argument (a precomputed `RelaxSpec` / ceiling +
     invert flag), parallel to the existing `is_unscheduled` argument — the scorer stays a pure
     function of its arguments (D-3). Reuse the empty-set relaxation (`schedule.py:599`) unchanged so
     an all-penalized set still returns a pick (REQ-LW-001).
   - `SelectionConfig` gains `live_ceiling`, `live_lambda`, `live_separation_enabled`,
     `live_separation_lambda` (defaults from config).

3. **`brain/server.py` (MODIFY) — supply the live-theme flag at the pick.**
   - In `_pick_refined` (`server.py:273`), compute the active-theme relaxation (from
     `ShowPrep.theme` / the world-model `schedule_context` current-show identity) and pass it into
     `refine(..., live_relax=...)`. Best-effort: theme unreadable → default lane (REQ-LZ-004).
   - The byte-identical `pick_next` branch (`server.py:257-259`) is UNTOUCHED (REQ-LW-004, NFR-LM-3/5).

4. **`brain/config.py` (MODIFY) — `_env` knobs.**
   - `livemix_enabled` (default ON — modest cap), `live_ceiling`, `live_lambda`,
     `live_window` (reuse/align with `recent_window`), `live_separation_enabled` + weight,
     `live_theme_relax_factor`, `live_theme_invert` (REQ-LY-001/002).

Design invariants enforced by construction: the term is ADDITIVE and SOFT (re-orders, never filters);
it lives only in the off-pull refiner; it reuses DEDUP-014 tokens; it degrades to byte-identical when
off/unwired.

## 2. Milestones (priority-ordered)

- **M1 (Priority High) — Classifier + theme detector (`brain/livemix.py`).** `is_live_cut`,
  `theme_relaxation`, `live_density_penalty`; pure-function unit tests incl. the fixtures
  (REQ-LV-001/002/003, REQ-LZ-002). No wiring yet.
- **M2 (Priority High) — Soft term in `SelectionRefiner`.** Add the live-density term + the
  `live_relax` argument to `refine(...)`; windowed live-share computation; inherit empty-set
  relaxation; determinism preserved (REQ-LW-001/002, NFR-LM-1/3/4). Characterize the existing
  `refine` behaviour first (DDD PRESERVE) so the added term is provably additive.
- **M3 (Priority High) — Theme wiring at the pick (`server.py`).** Thread the active-theme relaxation
  into `_pick_refined`; default-lane fallback when theme unreadable (REQ-LZ-001/003/004, NFR-LM-5).
- **M4 (Priority Medium) — Config knobs + disable-entirely (`config.py`).** `_env` knobs; assert the
  master-off path is byte-identical (REQ-LY-001/002, NFR-LM-5).
- **M5 (Priority Medium) — Observability.** Decision logging + optional health-surface live-share
  figure (REQ-LY-003).
- **M6 (Priority Medium) — No-back-to-back-live separation.** The optional adjacency separation,
  independently toggle-able and pool-pressure-relaxed (REQ-LW-003).

Sequencing: M1 → M2 → M3 gate the load-bearing behaviour; M4–M6 refine. M2 depends on M1; M3 depends
on M2; M4 threads through M2/M3.

## 3. Test Strategy (per Run phase)

- **Classifier fixtures (M1):** the spec's positive/negative set — "Roads (Live From The Roseland
  Ballroom)"→live, "MTV Unplugged" (album)→live, "Feeling Good (Live at Montreux)"→live, "Living on a
  Prayer"→NOT live, "Olivia"→NOT live; empty title+album→NOT live.
- **Additivity / never-starve (M2):** with the term added, an all-live legal set still returns a pick
  (empty-set relaxation path); the LRP/no-repeat + hard artist rails are unchanged vs the
  characterization baseline.
- **Theme relaxation (M3):** live-oriented theme raises ceiling / inverts; partial theme raises
  ceiling only; absent theme → default lane.
- **Byte-identical when off (M4):** master toggle off, and `refiner is None`, both yield the exact
  pre-SPEC pick sequence for a fixed fixture library.
- **Determinism (M2/M4):** identical state → identical pick (no RNG).

## 4. Delta / Brownfield Impact Map

| File | Delta | Change |
|------|-------|--------|
| `brain/livemix.py` | [NEW] | `is_live_cut` (reuses `dedup.version_signals` + live subset), `theme_relaxation`, `live_density_penalty` (mirrors `_family_balance_penalty`). Pure, exception-isolated (Groups LV/LZ). |
| `brain/schedule.py` | [MODIFY] | Add the live-density soft term to the `SelectionRefiner.refine` composite loop (`schedule.py:610-620`) + a `live_relax` argument; `SelectionConfig` gains live knobs. NO fork of the scorer, the hard rails, or the empty-set relaxation (Group LW). |
| `brain/server.py` | [MODIFY] | In `_pick_refined`, compute + pass `live_relax` from the active theme; the byte-identical `pick_next` branch is untouched (Groups LZ/LW; NFR-LM-3/5). |
| `brain/config.py` | [MODIFY] | New `_env` knobs (Group LY): `livemix_enabled` (default ON), `live_ceiling`, `live_lambda`, `live_window`, `live_separation_*`, `live_theme_relax_factor`, `live_theme_invert`. |
| `brain/dedup.py` | [READ-ONLY] | Source of the live token subset + `version_signals` tokenizer. NOT modified (NFR-LM-2). |

NOTE: `brain/library.py` (`pick_next`/`legal_candidates`) and `brain/taste.py` (`diversity_rerank`)
are NOT modified — the picker hot path stays byte-identical and the acquisition re-rank is out of
scope (§1.5).

## 5. Rollout / Config Defaults

- Ship with `livemix_enabled` default ON (a MODEST cap) per the operator ask, but the effective
  behaviour also requires the OPS-004 selection layer (`scheduling_enabled`) to be wired (D-2) — Run
  phase must document this coupling and recommend enabling the selection layer.
- All thresholds tunable via `_env`; disabling the toggle is byte-identical (REQ-LY-002).

## 6. Open Decisions (carried from spec.md §11)

- D-1: playout-primary vs acquisition — recommend playout-primary (this SPEC), acquisition deferred.
- D-2: fold into `SelectionRefiner` (recommended) vs a minimal always-on hook.
- D-3: how the live-theme flag reaches `refine(...)` — recommend a precomputed argument.
- D-4: default ceiling / window / lambda / relaxation factor — tune at Run time against real data.
