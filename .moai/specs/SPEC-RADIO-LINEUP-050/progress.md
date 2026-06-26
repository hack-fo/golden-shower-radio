## SPEC-RADIO-LINEUP-050 Progress

- Started: 2026-06-26 (session run)
- Branch: feature/SPEC-RADIO-LINEUP-050 (off main)
- Methodology: TDD (brownfield-enhanced), per quality.yaml
- Seams verified real: angle_similarity shows.py:579, propose_show :688, is_novel :677, retire_active :729; assign_persona caps_ok=None default schedule.py:897-907 (D7 linchpin); discontinue_show+OB-014 lifecycle.py; remove_slot :863; NoOrphanBootstrap :961; ProgramDirector.plan_24h :1019; world_model schedule_context :78/:292; events_db_path config.py:870; PlayEventsStore pattern analytics.py:57
- Plan approved (M1->M6); branch strategy = feature branch

- Phase A complete (M1+M2): brain/lineup.py + test_lineup.py, 31 tests 100% cov, 0 regressions. Committed.
  - Boundary decisions ratified: fingerprint=JSON+flat text; SQ-003 re-vet corpus includes active rows registered during sleep (B9 hazard).
  - revet_reactivation() exposed as the clean entry point M4 will call.
