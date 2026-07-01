# SPEC-RADIO-LIVEMIX-060 — Acceptance Criteria

> 1:1 REQ ↔ AC. Section A is the per-requirement acceptance list; Section B gives Given-When-Then
> scenarios for the load-bearing requirements and the edge cases. All criteria are observable
> (test output / deterministic pick sequence / structured log fields).

## Section A — Per-Requirement Acceptance

### Group LV — Live-cut Classifier

- **AC-LV-001** — Given a `Track`, `is_live_cut` returns True iff `version_signals` (from
  `brain/dedup.py`) over `title`+`album` intersects the live subset
  `{live, concert, unplugged, session, sessions}`. A code/test assertion proves the subset is derived
  from `DEFAULT_VERSION_TOKENS` (e.g. `LIVE_TOKENS <= dedup.DEFAULT_VERSION_TOKENS`) and that
  `version_signals` (not a second tokenizer) is the matcher.
- **AC-LV-002** — Whole-word, empty-safe: "Living on a Prayer" and "Olivia" → NOT live; a track with
  empty/missing title AND album → NOT live; classification reads the version-bearing stored text
  (a test proves a title carrying "(Live …)" is still live when a separately cruft-stripped variant
  would not be).
- **AC-LV-003** — `is_live_cut` mutates no `Track` field (verified: input object unchanged), removes
  no candidate, and returns NOT-live when its internals raise (exception-isolated); its only caller is
  the Group LW scoring term.

### Group LW — Live-density Cap in Rotation

- **AC-LW-001** — The live-density term is added into the `SelectionRefiner` composite score
  (alongside `_soft_penalty`/`_family_balance_penalty`); a test proves it only re-orders
  `library.legal_candidates` and never shrinks the set, that the LRP/no-repeat + hard artist rails are
  unchanged vs the characterization baseline, and that an ALL-LIVE legal set still returns a pick
  (empty-set relaxation path, logged).
- **AC-LW-002** — For a live candidate the penalty equals `live_lambda * max(0, live_share -
  live_ceiling)` over the rolling window; it is 0 while `live_share <= live_ceiling`; and it decays as
  live cuts age out of the window (a windowed-history test shows the penalty drop as live plays exit
  the window).
- **AC-LW-003** — With the separation knob on and the just-aired track live, a live candidate carries
  the extra separation penalty; with only live candidates remaining, the separation relaxes and a live
  cut still plays; with the knob off, only the share ceiling (AC-LW-002) applies.
- **AC-LW-004** — The term is computed only in `server.py:_pick_refined`; `library.pick_next` and the
  `refiner is None` branch are byte-identical (a fixed-fixture pick sequence is unchanged); no blocking
  or network call is added on the pick path.

### Group LZ — Theme-aware Relaxation / Inversion

- **AC-LZ-001** — Given a live-oriented active theme, the effective ceiling is raised (relaxation)
  and, where invert is configured, the penalty applies to NON-live candidates instead — a test shows a
  live cut that would be penalized in the default lane is unpenalized/preferred under a live theme.
- **AC-LZ-002** — `theme_relaxation` detects live intent from the theme string via the same whole-word
  tokenizer over the theme vocabulary (live subset + gig/tour/legendary concert/past concerts/live at);
  an empty/absent theme → not live-oriented; a test asserts the cut-classifier subset stays a strict
  subset of `DEFAULT_VERSION_TOKENS`.
- **AC-LZ-003** — A partly-live theme (mixed signal) yields a raised ceiling but NOT full inversion; an
  exclusively-live theme signal yields inversion — the two boundaries are distinguished by the detector
  and are test-covered.
- **AC-LZ-004** — With no resolvable theme (or the theme feed absent/erroring), the default modest cap
  applies and the pick does not stall or error (best-effort, degrades to default lane).

### Group LY — Config, Toggle & Observability

- **AC-LY-001** — Each knob is read via `_env` (`config.py` pattern): `livemix_enabled` (default ON),
  `live_ceiling`, `live_lambda`, `live_window`, `live_separation_*`, `live_theme_relax_factor`,
  `live_theme_invert`; defaults give a modest cap that re-orders without dominating the LRP base.
- **AC-LY-002** — With `livemix_enabled` off (and independently, with `refiner is None`), no
  live-density term is added and the pick sequence is byte-identical to the pre-SPEC baseline for a
  fixed fixture library.
- **AC-LY-003** — When the term materially changes a pick, a `log_event` records `live_share`,
  effective `live_ceiling` (post-relaxation), `theme_live_oriented`, and whether the chosen candidate
  changed; logging is best-effort and never blocks the pick.

### Non-Functional

- **AC-NFR-LM-1** — No input, config, or fault causes the control to remove a candidate, empty the
  legal set, or silence the stream (all-live library / drained non-live pool both still play).
- **AC-NFR-LM-2** — Static/test check: LIVEMIX imports `DEFAULT_VERSION_TOKENS` + `version_signals`
  from `brain/dedup.py`; it defines no independent version-token list and no second tokenizer.
- **AC-NFR-LM-3** — The pick path adds no blocking/network call; `library.pick_next` and `/api/next`
  are untouched (grep/architecture check + the byte-identical baseline test).
- **AC-NFR-LM-4** — Identical (candidates, windowed history, theme) yields an identical pick across
  repeated runs (no RNG).
- **AC-NFR-LM-5** — Feature off, classifier fault, theme unreadable, or `refiner is None` each degrade
  to today's behaviour with a byte-identical pull.
- **AC-NFR-LM-6** — Only `brain/livemix.py` (new) + additive edits to `schedule.py`/`server.py`/
  `config.py`; no new service, no datastore, no Liquidsoap change, no fork of the picker, the
  SelectionRefiner, or `brain/dedup.py`.
- **AC-NFR-LM-7** — No deferred item is partially built (no acquisition-side companion, no
  audio-content live detector, no per-persona policy).

## Section B — Given-When-Then (load-bearing scenarios + edge cases)

### B-1 — The classifier fixtures (REQ-LV-001/002)
- GIVEN a track titled "Roads" with album "Live From The Roseland Ballroom"
  WHEN `is_live_cut` runs THEN it returns True (whole-word "live" present).
- GIVEN a track whose album is "MTV Unplugged" WHEN classified THEN True ("unplugged").
- GIVEN "Feeling Good (Live at Montreux)" WHEN classified THEN True.
- GIVEN "Living on a Prayer" (title) with empty album WHEN classified THEN False ("living" ≠ "live").
- GIVEN a track titled "Olivia" WHEN classified THEN False.
- GIVEN empty title AND empty album WHEN classified THEN False (empty-safe).

### B-2 — Never-starve: an all-live legal set still plays (REQ-LW-001, NFR-LM-1) [HARD]
- GIVEN a library whose ENTIRE legal candidate set is live cuts and the feature ON
  WHEN the SelectionRefiner scores them THEN every candidate is penalized equally-or-more but the set
  is NOT emptied; the empty-set relaxation path returns a live cut and logs
  `schedule.selection_relaxed`; the stream never goes silent.

### B-3 — Default lane: a modest cap re-orders, does not ban (REQ-LW-002, REQ-LZ-004)
- GIVEN mixed studio+live candidates, no active live theme, and `live_share` already above the ceiling
  WHEN scored THEN live candidates carry a positive penalty and a comparable studio candidate is
  preferred; BUT when the non-live pool is exhausted a live cut is still chosen (soft, not a filter).

### B-4 — Live-oriented theme relaxes/inverts (REQ-LZ-001/002) [HARD]
- GIVEN an active theme "Legendary Live Concerts" WHEN the relaxation is computed THEN it is
  `invert` (or ceiling raised toward 1.0); a live candidate that would be penalized in B-3 is now
  unpenalized or preferred, and a non-live candidate carries the penalty under inversion.

### B-5 — Partly-live theme: graded relaxation (REQ-LZ-003)
- GIVEN a theme "Studio classics with the odd legendary live take" WHEN the relaxation is computed
  THEN it is `partial` (ceiling raised, NOT inverted): more live cuts than the default lane, but
  non-live candidates are not penalized and live cuts are not flooded in.

### B-6 — Byte-identical when off or unwired (REQ-LY-002, NFR-LM-5) [HARD]
- GIVEN `livemix_enabled=false` OR `scheduling_enabled` off (`refiner is None`)
  WHEN a fixed fixture library is played out THEN the pick sequence is byte-identical to the
  pre-SPEC baseline; no live-density term is computed on the pick path.

### B-7 — Shared token source with DEDUP-014 (NFR-LM-2) [HARD]
- GIVEN the LIVEMIX live subset WHEN checked against `brain/dedup.py` THEN it is a subset of
  `DEFAULT_VERSION_TOKENS` and the matcher is `version_signals`; a divergent second token list or a
  reimplemented tokenizer is a defect.

### B-8 — Title-cleaning must not hide the live signal (REQ-LV-002, R-LM-4)
- GIVEN a track whose stored display title retains "(Live at …)" while a cruft-stripped variant would
  drop it WHEN `is_live_cut` runs THEN it reads the version-bearing stored text and returns True.

## Definition of Done

- [ ] All 14 REQ + 7 NFR acceptance criteria pass (1:1).
- [ ] Section B scenarios B-1…B-8 covered by tests; B-2/B-4/B-6/B-7 (the [HARD] rails) explicitly
      asserted.
- [ ] The pre-SPEC pick sequence is byte-identical with the feature off AND with `refiner is None`.
- [ ] No modification to `library.pick_next`, `/api/next`, `brain/dedup.py`, or `brain/taste.py`.
- [ ] Classifier + penalty + theme detector are pure/deterministic and exception-isolated.
- [ ] Full existing test suite still green (no regression in OPS-004 SelectionRefiner behaviour).
- [ ] TRUST 5 gates pass; MX tags added where the new soft term touches the high-fan_in
      `SelectionRefiner.refine`.
