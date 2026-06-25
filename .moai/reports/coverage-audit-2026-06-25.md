# Coverage Audit — golden-shower-radio
**Date:** 2026-06-25  
**Auditor:** independent coverage fork  
**Method:** cross-reference spec.md REQ groups vs brain/*.py implementations + git tracked test files

---

## Coverage Table

| SPEC | Status | Evidence | Gap |
|------|--------|----------|-----|
| CORE-001 | ✅ BUILT | brain/main.py, server.py, library.py; test_characterize_server.py, test_characterize_library.py | — |
| VOICE-002 | ✅ BUILT | brain/voice.py (Kokoro + Piper + teldutala.fo seam) | VOICE-002 A/B harness (DEFERRED per roadmap — needs GPU in Docker) |
| ANALYSIS-006 | ✅ BUILT | brain/analysis.py (868L: analyze_file, _detect_cues, _sonic_character, _transition_hints); test_cue_trim.py | — |
| CALLIN-003 | ❌ UNBUILT | No callin.py; only a "callin_cf" binding stub in segment_registry.py | Full spec: WebRTC ingress (Pipecat), caller+host air mix, LiveSegment FSM, moderation |
| DATASTORE-022 | ✅ BUILT | brain/sqlite_store.py; test_characterize_datastore.py | — |
| DEDUP-014 | ✅ BUILT | brain/dedup.py; test_characterize_dedup.py | — |
| ENRICH-012 | ✅ BUILT | brain/enrich.py (AcoustID, filename corroboration, backfill worker); test_enrich.py | — |
| FILENAME-024 | ✅ BUILT | brain/filename.py; test_characterize_filename.py | — |
| HOSTCTX-016 | ✅ BUILT | brain/talk.py (year/album backsell, curiosa, grounded context); test_hostctx.py | HY-003 multi-break harness pending PG gate (see PROGRAMMING-007 PG) |
| HOSTLIFE-032 | ✅ BUILT | brain/hostlife.py (SELECT→ENGAGE→TASTE→FRAME loop); test_hostlife.py | — |
| IMAGING-010 | ✅ BUILT | brain/imaging.py (868L: ImagingSystem, BedRegistry, BedSourcer, ClipMixer, ReadyBuffer, GenerationWorker, ImagingPlayer); test_imaging.py | REQ-IB-003 paid-tier bed ledger extends OPS-004 OE-010 — wiring present |
| INTEGRITY-033 | ❌ UNBUILT | No integrity.py; scan_anti_slop() in grounding.py is ONE piece of the anti-slop rail only | Full spec: governance write-path chokepoint (REQ-IT-006), epistemic status state machine (REQ-IT-002), hypotheses table, anti-loop cardinal rule enforcement |
| INTERVIEW-CRAFT-034 | ❌ UNBUILT | No interview_craft.py; no interview-format code in showprep.py or talk.py | Full spec: interview-format segment type, guest persona model, transcript-learning |
| KNOWLEDGE-008 | ✅ BUILT | brain/knowledge.py v0.3.0 (KS/KF/KR/KG/KI groups); test_knowledge.py | — |
| KNOWLEDGE-038 | ❌ UNBUILT | Spec only (ccdbc3c) | Full spec: concerts/cultural-context/lyrics/press curiosa editorial fields |
| KNOWLEDGE-039 | ❌ UNBUILT | Spec only (ccdbc3c) | Full spec: prioritize() deque, director notify, knowledge_available signal, library matcher |
| LIKE-015 | ✅ BUILT | brain/like.py (LikeGate + DropOffEngine); test_like.py | — |
| LONGFORM-025 | ✅ BUILT | brain/longform.py (LongformEpisode, build_solstice_hour, episode_airable, interleave_plan); test_longform.py | — |
| LOOKUPLOG-023 | ✅ BUILT | brain/lookuplog.py; test_lookuplog.py | — |
| MBMIRROR-017 | ✅ BUILT | brain/mb_cache.py (persistent MB cache + Discogs seam); test_characterize_mbmirror.py | MX (Discogs full-mirror) deferred by design per spec |
| MEMORY-031 | ✅ BUILT | brain/memory.py (DocumentStore, MemoryCoherence, VectorSeam stub, MemoryPurge, ReferentialBackbone); 5 test files tracked (in conftest collect_ignore pending MEMORY-031 ship — remove collect_ignore entries) | VectorSeam is enabled=False stub |
| OPS-004 | ✅ BUILT | brain/director.py, news.py, imaging.py, lifecycle.py, showprep.py, news_feeds.py, news_ledger.py + full test suite (test_imaging.py, test_news.py, test_lifecycle.py, test_of_liveliness.py, test_oh_library.py, etc.) | — |
| ORCH-005 | ✅ BUILT | brain/action_surface.py, world_model.py, event_reaction.py, listener_memory.py, ledger.py, director.py; ALL 5 previously-untracked test files now tracked (test_rn_news_feeds.py, test_ri_listener_memory.py, test_re_event_reaction.py, test_rl_director_loop.py, test_rd_degradation.py) | — |
| PERSONACHARTER-035 | ✅ BUILT | brain/persona.py, minting.py, schedule.py; test_persona.py, test_minting.py, test_schedule.py | — |
| PROGRAMMING-007 | ✅ BUILT | ALL 9 groups implemented: PR (persona.py, minting.py), PG (grounding.py: FactContract, run_gate, tier1/tier2), PV (persona_voice.py: VoiceCard, PVLintContext, scan_warmth_crutch, scan_blunt_praise), PI (persona_identity.py: AnchorBlock, DistinctnessCanary, AnchorAudit), PC (playbook.py: DaypartPreset, backtime_talk), PS (ear_writing.py: scan_long_sentences, scan_missing_contractions), PL (taste.py: TasteProfile, AcquisitionDiary, GrabReason), PT (craft.py: SequencingJournal, observe_sequence), CL (humandj.py: HumanDjRegistry, refract_for_persona) | — |
| ACQQUEUE-019 | ⚠️ PARTIAL | brain/acquire.py + slskd.py; test_characterize_acquire.py. Candidate has `has_free_slot` (REQ-QR-002 partial). Tests pass. | REQ-QR-001: peer queue depth field (`queue_length`) missing from Candidate. REQ-QR-002: queue-depth ranking not implemented (only has_free_slot). REQ-QT-001/002: configurable queue threshold/ceiling not present. REQ-QW-001/002: bounded wait + next-best fallback unclear. |
| AIDECISION-037 | ❌ UNBUILT | No DecisionLedger class, no decision_rationale table, no /api/decisions endpoint found in any brain/*.py | Full spec: REQ-DC-001 decision_rationale table, REQ-DI-001..007 decision insertion points, REQ-DQ-001 /api/decisions endpoint, REQ-DP-001 candidate snapshot logging |
| ALBUMART-021 | ✅ BUILT | brain/albumart.py (Cover Art Archive fetch + embed); test_albumart.py | — |
| REFLECT-026 | ❌ UNBUILT | No reflect.py; world_model._fill_self_reflection_results() is a minimal stub only | Full spec: hypotheses table, REQ-RF-001..005 reflect run-mode, REQ-RM-001..005 model schema, REQ-RV-001..005 lifecycle, REQ-RH-001..005 evidence gathering |
| REQUEST-011 | ⚠️ PARTIAL | brain/wishlist.py (WishlistStore — REQ-RWL-001/002/003 off-catalog wishlist only) | REQ-RQ-001..003 (request backend + CALLIN-003 channel) missing. REQ-RM-001..003 (fuzzy match + typeahead) missing. REQ-RA-001..005 (advisory picker bias + anti-gaming) missing. REQ-RS-001..003 (rate limit + moderation + honeypot) missing. REQ-RV-001..003 (growth surface UI) missing. |
| RESEARCH-036 | ⚠️ PARTIAL | RG group ✅ (Go removed, dc7d1c4). RP group ✅ (brain/news_feeds.py: FeedPoller, REPUTABLE-PRESS tier in knowledge.py, news_ledger.py). | RA group ❌ (analysis context packet not wired into director). RS group ❌ (LLM fit-scoring / candidate-pool scoring not found in director.py). |
| SEEDING-029 | ✅ BUILT | brain/seeding.py, persona_seeding.py; test_seeding.py, test_persona_seeding.py | — |
| SELFHEAL-030 | ❌ UNBUILT | brain/disk_guard.py (131L, DiskGuard only = Group SO fragment). No sidecar, no LLM-reasoning tier, no allow-list executor. | Full spec: Groups SO/SD/SR/SI/SL/SX/SV/SE/SP. Only SO (observability, partially) exists. |
| SETUP-040 | ❌ UNBUILT | Spec only (ccdbc3c) | Full spec: first-run wizard, secret sanitisation, RoboCop splash, auth-mode selection |
| ADMIN-041 | ❌ UNBUILT | Spec only (ccdbc3c) | Full spec: admin panel, token cost tracking, LLM log ring buffer, emergency controls, reset scopes |
| SHOWS-020 | ✅ BUILT | brain/shows.py (deep Last.fm research, show session model); test_shows.py | — |
| SKIP-028 | ✅ BUILT | brain/skipguard.py; test_sc_skip_channel.py, test_sg_skip_governor.py, test_sk_skip_mechanism.py | — |
| STATS-013 | ✅ BUILT | brain/analytics.py (PlayEventsStore, StatsAggregator); test_analytics.py | — |
| TAGSTREAM-009 | ✅ BUILT | brain/tagstream.py; test_tagstream.py | — |
| VETTING-027 | ✅ BUILT | brain/vetting.py, banlist.py; test_vc_vet_cascade.py, test_vb_ban_list.py, test_vg_gate_wiring.py, test_vk_false_positive_guard.py, test_vr_offensive_verdict.py | — |
| WEBUI-018 | ✅ BUILT | brain/website.py, state.py (durable ring); test_characterize_state.py | — |

---

## Summary

| Status | Count | SPECs |
|--------|-------|-------|
| ✅ BUILT | 29 | CORE-001, VOICE-002, ANALYSIS-006, DATASTORE-022, DEDUP-014, ENRICH-012, FILENAME-024, HOSTCTX-016, HOSTLIFE-032, IMAGING-010, KNOWLEDGE-008, LIKE-015, LONGFORM-025, LOOKUPLOG-023, MBMIRROR-017, MEMORY-031, OPS-004, ORCH-005, PERSONACHARTER-035, PROGRAMMING-007, ALBUMART-021, SEEDING-029, SHOWS-020, SKIP-028, STATS-013, TAGSTREAM-009, VETTING-027, WEBUI-018, KNOWLEDGE-008 |
| ⚠️ PARTIAL | 3 | ACQQUEUE-019, REQUEST-011, RESEARCH-036 |
| ❌ UNBUILT | 9 | CALLIN-003, INTEGRITY-033, INTERVIEW-CRAFT-034, KNOWLEDGE-038, KNOWLEDGE-039, AIDECISION-037, REFLECT-026, SELFHEAL-030, SETUP-040, ADMIN-041 |

*(Total: 41 SPECs)*

---

## Priority Assessment

### PARTIAL — highest priority gaps

**RESEARCH-036 RA + RS** — The analysis context packet (RA) and LLM fit-scoring (RS) are the core "AI decision intelligence" of the spec. They wire into the director's curation tick; without them the director picks tracks without any LLM-scored candidate context.

**ACQQUEUE-019 QR-001/002** — Peer queue depth is the whole point of this spec; `has_free_slot` is a proxy but not queue depth. The configurable thresholds (QT) are also missing.

**REQUEST-011** — WishlistStore is only the off-catalog wishlist portion. The actual listener-request flow (search, fuzzy match, advisory picker bias, rate limiting, UI) is wholly absent.

### UNBUILT — load-bearing vs. optional

**Load-bearing for station autonomy (build soon):**
1. **AIDECISION-037** — Audit trail for every AI decision; needed for trust/debugging
2. **INTEGRITY-033** — Governance write-path; protects durable memory from AI hallucination/loop. REFLECT-026 and any new memory writes are unsafe without it.
3. **SETUP-040** — First-run wizard (operators can't set up without it safely)
4. **ADMIN-041** — Token visibility, emergency stop

**Feature-complete but station works without them:**
5. **REFLECT-026** — Self-model; station works without, but no self-improvement loop
6. **SELFHEAL-030** — Self-healing; station works but requires human restart on failure
7. **KNOWLEDGE-039** — Knowledge priority queue; improves TTS quality but not blocking
8. **KNOWLEDGE-038** — Editorial fields; enrichment, not blocking
9. **INTERVIEW-CRAFT-034** — Interview format shows; not blocking
10. **CALLIN-003** — Live call-in; future feature, not blocking

### Recommended build order

1. SETUP-040 (unblocks safe operator onboarding)
2. ADMIN-041 (unblocks cost visibility + emergency controls)
3. RESEARCH-036 RA+RS (wires LLM decision intelligence into director)
4. ACQQUEUE-019 QR-001/002 + QT (completes queue-aware acquisition)
5. INTEGRITY-033 (governance layer before adding more durable memory writes)
6. AIDECISION-037 (audit trail)
7. REFLECT-026 (depends on INTEGRITY-033)
8. SELFHEAL-030 (sidecar / restart automation)
9. KNOWLEDGE-039 (knowledge priority queue)
10. REQUEST-011 remainder (listener requests)
11. KNOWLEDGE-038 (editorial expansion)
12. INTERVIEW-CRAFT-034 (interview show format)
13. CALLIN-003 (live call-in, complex infrastructure)
