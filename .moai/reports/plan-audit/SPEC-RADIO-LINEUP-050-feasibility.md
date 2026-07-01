# LINEUP-050 §11 Frozen-Engine Feasibility Audit

Reasoning context ignored per M1 Context Isolation. Verdict derived from the real code only.

Verdict: PASS

Scope: ONLY the §11 claim "LINEUP does NOT modify `brain/shows.py` or `brain/lifecycle.py` — it
consumes them as-is." Tested against the two genuinely-new behaviors against the CURRENT public APIs.

## (a) Cross-persona show-similarity scan — FEASIBLE-AS-LAYERED

Public surface that makes it work:
- `angle_similarity(a, b)` is a **module-level function** (`shows.py:579`), not a method — freely
  importable, stateless, reusable cross-persona with zero engine access.
- Per-persona retired-show ledger is publicly exposed: `ShowEngine.history(persona_id)`
  (`shows.py:658`) and `ShowEngine.recent_angles(persona_id)` (`shows.py:663`). `is_novel`
  (`shows.py:677`) is also public but per-persona by design.
- Injection point is real: `Schedule.assign_persona(..., caps_ok=Callable[[str,str],bool])`
  (`schedule.py:897`) genuinely gates the bind at `schedule.py:907-908`. Proven in production by
  `LifecycleEngine._caps_ok_predicate` (`lifecycle.py:277`) → `_stage_reassignment`
  (`lifecycle.py:305-310`), which already rides this exact hook. The cross-persona / one-per-day
  gate can ride it identically.

One real (but already-satisfied) dependency: `ShowEngine` exposes **no enumerator of persona_ids**
(`_ledger`/`_active` are private; `active_show(None)` yields only one). So the LINEUP layer cannot
discover "all personas" from `ShowEngine` — it must supply the roster itself. It already does: it is
the cross-persona assignment layer and gets the roster from `LifecycleEngine.active_curators()`
(`lifecycle.py:555`) / `all_personas_including_retired()` (`lifecycle.py:562`) or `Roster` directly,
then loops `history(pid)`/`recent_angles(pid)` + module `angle_similarity`. **No new accessor on
shows.py is forced.**

## (b) `hiatus` resting state — FEASIBLE-AS-LAYERED

- `discontinue_show` (`lifecycle.py:491`) is atomic live→`retire_active`→`propose_show` successor
  with no pause — confirmed. The persona FSM is `active/retiring/retired` (`lifecycle.py:55-57`);
  show transition markers `live/discontinued/relaunched` (`lifecycle.py:62-64`) are **ledger event
  markers, not a stored status**. Stored show statuses live in shows.py
  (`proposed/rejected/active/retired`, `shows.py:389-392`). No `hiatus`/`paused` status exists
  anywhere.
- Representation: the recurring-show `hiatus` lives in LINEUP's **own** `show_registry` table (§11
  delta: `lineup.py [NEW] … the hiatus state machine`), a concept distinct from ShowEngine's
  per-persona editorial-angle `Show`. The persona stays `active`; only the recurring show is parked.
  No new state in lifecycle.py's persona FSM is required.
- Always-staffed (OB-014) reconciliation rides schedule.py's EXISTING surface:
  `remove_slot(slot_id, discontinue=True)` (`schedule.py:863`) drops the slot so resolution degrades
  to `HOUSE_LANE` (`schedule.py:957`, byte-identical house-voice+music), or `assign_persona` rebinds
  the house lane. schedule.py is already `[MODIFY]` in §11 and is NOT one of the two frozen files.
  **lifecycle.py stays untouched.**

Caveat (design-quality, not an API blocker): ShowEngine's only public way to clear an active angle
is `retire_active` (`shows.py:729`), which pushes the angle into the novelty ledger as RETIRED —
there is no public "park-and-resume-the-same-angle." A truly resumable hiatus must therefore be
modeled at the LINEUP/`show_registry` level (re-bind + re-propose on resume), not by round-tripping
ShowEngine's active show. This is exactly what §11 specifies, so it does not force a shows.py edit.

## Conclusion

Both new behaviors are implementable on the current public APIs of shows.py and lifecycle.py without
editing either file. §11's frozen-engine claim HOLDS; the DELTA does NOT need to flip shows.py or
lifecycle.py to `[MODIFY]`. The `caps_ok` injection seam at `schedule.py:897` is the real, already-
exercised binding point for the cross-persona gate.
