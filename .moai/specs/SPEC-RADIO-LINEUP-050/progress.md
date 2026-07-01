## SPEC-RADIO-LINEUP-050 Progress

- Started: 2026-06-26 (session run)
- Branch: feature/SPEC-RADIO-LINEUP-050 (off main)
- Methodology: TDD (brownfield-enhanced), per quality.yaml
- Seams verified real: angle_similarity shows.py:579, propose_show :688, is_novel :677, retire_active :729; assign_persona caps_ok=None default schedule.py:897-907 (D7 linchpin); discontinue_show+OB-014 lifecycle.py; remove_slot :863; NoOrphanBootstrap :961; ProgramDirector.plan_24h :1019; world_model schedule_context :78/:292; events_db_path config.py:870; PlayEventsStore pattern analytics.py:57
- Plan approved (M1->M6); branch strategy = feature branch

- Phase A complete (M1+M2): brain/lineup.py + test_lineup.py, 31 tests 100% cov, 0 regressions. Committed.
  - Boundary decisions ratified: fingerprint=JSON+flat text; SQ-003 re-vet corpus includes active rows registered during sleep (B9 hazard).
  - revet_reactivation() exposed as the clean entry point M4 will call.

- Phase B complete (M3+M4): lineup.py extended (LineupController, make_caps_ok, hiatus FSM). 33 new tests, 96% cov, 0 regressions. Committed.
  - PR-004 reachable: roster.validate_candidate (persona.py:445), composed same as lifecycle._caps_ok_predicate (lifecycle.py:277).
  - OB-014 by construction: hiatus->discontinued via lifecycle.discontinue_show; no show_relaunched emitted by LINEUP.
  - Ordered-bounds clamp (long lowered to max) = safe-degrade reading of AC-SY-002.
  - Config bounds read via getattr(cfg, "lineup_max_hiatus_seconds"/"lineup_long_hiatus_seconds", 90d/30d) — M6 adds the real knobs.

- Phase C complete (M5+M6): WeeklyMatrixPlanner + world_model feed + config knobs + docs. 26 new tests, 1819 passed 0 regressions, ruff clean. Committed.
  - program_cycle show_id wired at lineup layer (lazy import EV_PROGRAM_CYCLE), no schedule.py touch.
  - toggle-OFF byte-identical proven (test_schedule_context_byte_identical_when_lineup_off + zero-read counter).
  - NFR-LU-5: reused shows_novelty_threshold/shows_max_regenerate; NO second similarity knob (divergence ratified).
- ALL 6 MILESTONES CODE-COMPLETE. Remaining: quality pass (TRUST 5 + evaluator-active) + /moai sync -> PR.
