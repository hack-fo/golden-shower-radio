# SPEC Implementation Audit — golden-shower-radio

**Date:** 2026-07-01
**Branch:** feature/SPEC-RADIO-LINEUP-050
**Method:** 7 parallel read-only audit agents cross-referenced each SPEC's EARS requirements + acceptance criteria against actual `brain/*.py` code, production wiring (`main.py` / `director.py` / `server.py`), and test coverage. **Frontmatter `status:` was ignored** (51/52 say `draft` and it is stale/unreliable).

> Caveat: verdicts are evidence-based agent assessments (file:line cited), not a line-by-line human re-verification of all 52. `%` is a coarse completeness estimate (0/25/50/75/100 buckets). Treat as a high-confidence map, not a certified ledger.

## Scoreboard

- **Total SPECs:** 52
- 🟢 **IMPLEMENTED (built + wired + tested):** 16
- 🟡 **PARTIAL (meaningful gaps or unwired):** 17
- ⏸️ **NOT-BUILT (little/no code):** 19

### The three load-bearing patterns

1. **"Complete-but-unwired islands"** — fully coded, fully unit-tested, but instantiated *nowhere outside tests*, so they never run in production: **ORCH-005, MEMORY-031, HOSTLIFE-032, LINEUP-050**. Highest leverage: small wiring effort → activates a whole subsystem.
2. **"Built but flag-OFF by default"** — implemented and wired, but gated behind a default-OFF config knob so a stock deploy never exercises them: **OPS-004** (`scheduling/lifecycle/imaging_enabled=0`), **SHOWS-020** (`shows_enabled=0`), and the whole persona-minting/growth path (`lifecycle_enabled=0`).
3. **"Same-name trap"** — a module whose name matches a SPEC but implements a *different* SPEC: `craft.py` is PROGRAMMING-007 set-design (not INTERVIEW-CRAFT-034); `longform.py` holds only PROGRAMMING-007 Group PT ethics (not LONGFORM-025's engine); `grounding.py`/`humanlint.py` are prose anti-slop (not INTEGRITY-033's knowledge governance).

---

## 🟢 IMPLEMENTED (16)

| SPEC | % | Notes |
|------|---|-------|
| ADMIN-041 (cost/debug/emergency panel) | 100 | All 7 reqs wired + tested; SSE `/admin/stream`. |
| SKIP-028 (forceful on-air skip) | 95 | End-to-end: SkipGovernor → Liquidsoap harbor :7138, 5 guards, tests. |
| HOSTVOICE-049 (human DJ voice) | 95 | humanlint + break taxonomy + persona; only the `HOST_PERSONA` alias-repoint deferred. |
| ALBUMART-021 (cover-art embed) | 95 | CAA fetch + idempotent APIC/FLAC embed, wired in enrich worker. |
| STATS-013 (analytics site) | 95 | play_events ledger + tops/LastWave/taste-map + `/stats`, 25 tests. |
| CORE-001 (v1 core engine) | 90 | Full autonomous loop live; self-*editing* website (REQ-E) is static-only. |
| PERSONACHARTER-035 (taste-charter) | 90 | Complete engine; only runs when minting driven (lifecycle OFF). |
| HOSTCTX-016 (year/album/grounded cues) | 90 | Threaded into live talk path. |
| SEEDING-029 (initial seeding) | 90 | Anchor/compass/CSV/dropped-file taste, wired to acquisition. |
| FILENAME-024 (filename↔id3) | 90 | Atomic rename-under-lock, worker wired. |
| KNOWLEDGE-008 (artist knowledge base) | 90 | Entities/facts/consensus/provenance, feeds talk + showprep. |
| VETTING-027 (content vet + ban-list) | 90 | 3 gates wired (pre-download/pre-play/request), soft-reversible, 5 test files. |
| WEBUI-018 (website + durable ring) | 90 | Durable `recent_ring.json`, 2026 redesign, wired. |
| DATASTORE-022 (JSON→SQLite) | 90 | `brain.db` migration + WAL live; `state.db` provisioned-but-underused. |
| OPS-004 (program director + imaging) | 85 | Built + wired but 3 flags default OFF. |
| SHOWS-020 (per-persona show validation) | 85 | Fully wired behind `shows_enabled` (default OFF). |

---

## 🟡 PARTIAL (17)

### 3a. Complete-but-unwired islands (code done, zero prod callers)

| SPEC | % | What's missing |
|------|---|----------------|
| LINEUP-050 (weekly grid/hiatus/flagship) | 60 | ShowRegistry/LineupController/WeeklyMatrixPlanner instantiated only in tests; `world_model.show_registry` never fed; `lineup_enabled` OFF. 90 tests pass, zero live wiring. |
| HOSTLIFE-032 (lived-experience loop) | 55 | Full 4-stage loop coded + 27 tests, but imported by 0 runtime files; `inject_lived_experience_context` never called. |
| ORCH-005 (awareness/nervous system) | 50 | 6 modules + `wire_orch()` seam coded + tested, but `wire_orch()` has no prod caller; only the EventLedger half is live. |
| MEMORY-031 (four-layer memory) | 50 | DocumentStore/MemoryPurge/ReferentialBackbone coded + tested but orphaned; live purge/bootstrap use independent code paths. |

### 3b. Genuinely half-built (partial feature surface)

| SPEC | % | What's missing |
|------|---|----------------|
| LIKE-015 (listener heart) | 80 | Full backend + HMAC + 27 tests, but **no heart button rendered on the site** — listeners can't actually like. |
| ANALYSIS-006 (track intelligence) | 75 | Core BPM/key/energy/LUFS/cues wired; beat-grid, spectral-flux boundary, LLM sonic-desc not built; thin tests. |
| MBMIRROR-017 (MusicBrainz access) | 75 | Public-API + cache + provenance live; Discogs cross-check + mirror `set_hostname` repoint not wired. |
| PROGRAMMING-007 (hosts/personas/craft) | 75 | Bulk live; Group PT long-form subsystem orphaned in `longform.py`; growth path behind `lifecycle_enabled` OFF. |
| LOOKUPLOG-023 (lookup ledger) | 70 | Ledger + negative-dedup + prune live; Group LK fingerprint-primary identity (3 HARD reqs) unmet; AcoustID path unrecorded. |
| ENRICH-012 (metadata enrichment) | 60 | Identity + MBID/barcode widening built; Discogs cross-check (Group EX) + reversibility baseline not built. |
| SETUP-040 (first-run wizard) | 55 | v0.1 wizard + splash live; v0.2 (`--reconfigure`/`--menu`/`--all`, splash-leads) not built. **Actively edited.** |
| HOSTLIFE-032 | — | (listed above) |
| DEDUP-014 (version-aware dedup) | 50 | `classify` primitive correct + tested but **observe-only** — never gates/prunes; fuzzy fallback + override + health-surface missing. |
| TAGSTREAM-009 (tag/artwork/exposure) | 50 | Group TW file-tag writing built; Group TA (TheAudioDB/fanart/Pillow) + website render (TX display/table/ICY) unbuilt. |
| VOICE-002 (TTS voice layer) | 50 | English Kokoro→Piper live; Faroese teldutala client, per-persona voice, Liquidsoap ducking, ElevenLabs, episode assembly, call-in seam all absent. |
| APIKEYGUARD-043 (billing guard) | 50 | 3 guard layers pre-exist; SPEC's own deliverables missing: no `test_apikeyguard.py`, no AK-5 missing-key warning. |
| IMAGING-010 (imaging production) | 40 | OPS-004 production pipeline works; IMAGING-010's own scope (local ACE-Step primary + GPU sidecar, per-show imaging library, hosted-break) unbuilt. |
| RESEARCH-036 (integrated research) | 25 | Only Go-removal (RG) done; analysis-context packet, candidate fit-scoring, press ingestion, dedup registry, Discogs provider all absent. |

---

## ⏸️ NOT-BUILT (19)

| SPEC | % | Note |
|------|---|------|
| ADMIN-046 (admin panel v2) | 0 | No soft/hard limits, staged-auth, usage tab, reset-confirm UI. Plan done, code not. |
| AIDECISION-037 (decision contract) | 0 | No DecisionLedger / rationale table / `/api/decisions`. |
| CALLIN-003 (live phone call-in) | 0 | Fully aspirational; no WebRTC/Pipecat/STT/harbor/moderation. |
| ACQQUEUE-019 (low-queue source pref) | 0 | No queue-aware ranking; spec describes current code *as the gap*. |
| KNOWLEDGE-038 (concerts/lyrics/press) | 0 | No event/figure entity types, no setlist.fm/Genius providers. |
| KNOWLEDGE-039 (priority queue/context) | 0 | Research batch is pure FIFO; no prioritization. |
| MULTIBACKEND-047 (multi-LLM backend) | 0 | No provider abstraction (research-and-design SPEC). |
| LLMROUTER-048 (routing/failover) | 0 | No router; depends on 047. |
| PROMPTCRAFT-044 (prompt hardening) | 0 | `llm.py` untouched; all 9 reqs unmet. |
| PROMPTFMT-051 (per-provider format) | 0 | Depends on 047; nothing built. |
| PROMPTSLIM-052 (talk-prompt compaction) | 0 | No prompt contract / compaction / flag. |
| INTEGRITY-033 (memory integrity/anti-slop) | 0 | No trust-tier/epistemic-state governance (grounding.py is a *different* defense). |
| BROADCASTERLEARN-042 (conversation learning) | 0 | No diarize→model→extract→validate pipeline; depends on 033. |
| INTERVIEW-CRAFT-034 (journalist craft) | 5 | `craft.py` is a same-name trap; no Whisper STT / technique corpus. |
| REQUEST-011 (listener requests) | 5 | No `/api/request`, matcher, advisory weight, growth viz. |
| SELFHEAL-030 (self-healing control plane) | 5 | Mandates a sidecar outside brain; no healthcheck/watchdog in compose. |
| REFLECT-026 (self-model memory) | 15 | `hypotheses` DDL exists but its EventsStore is never constructed in prod. |
| LONGFORM-025 (long-form documentary) | 15 | `longform.py` is a narrow unwired ethics stub; engine (LE/LB/LR/LN/LT/LQ) absent. |
| DOCS-045 (documentation cleanup) | 15 | 27 files still carry stale SPEC refs; Groups A/B undone. **Actively edited.** |

---

## Recommended build priorities

**Tier 1 — Activation wins (small wiring, big payoff; code already written + tested):**
- **LINEUP-050** — wire ShowRegistry/matrix into `main.py`, feed `world_model.show_registry`, enable flag. (Also the data backbone the new schedule/show-pages SPEC-053 needs.)
- **ORCH-005** — call `wire_orch()` in prod; instantiate the 6 awareness modules.
- **HOSTLIFE-032** — schedule `LivedExperienceLoop`, call `inject_lived_experience_context` from talk.
- **LIKE-015** — render the heart button in `website.py` (backend + token endpoint already live).

**Tier 2 — Finish genuine half-builds:**
- DEDUP-014 (promote observe-only → real pre-download gate), TAGSTREAM-009 (website render), VOICE-002 (Faroese + ducking), SETUP-040 (v0.2 flags), APIKEYGUARD-043 (add its test lock + AK-5 warning).

**Tier 3 — Net-new, high listener value:** REQUEST-011 (listener requests), KNOWLEDGE-038/039 (richer host knowledge).

**Tier 4 — Net-new, heavy infra:** CALLIN-003, BROADCASTERLEARN-042, SELFHEAL-030, the LLM router chain (047/048/051/052), INTEGRITY-033, LONGFORM-025.

**Housekeeping:** DOCS-045 + ADMIN-046 have finished plans; both are pure execution.
