# Full-Spec Completion Roadmap — PROGRAMMING-007 → OPS-004 → ORCH-005

Authored 2026-06-24. User directive: build the three big specs to FULL spec coverage, in order.
STANDING RULE (load-bearing, see memory [[build-in-full-not-limped]]): every build is FULL spec scope,
never a silent partial/slice. If a build genuinely can't be full in one pass, STOP and tell the user up
front + get consent. Quality rigor stays (characterization-first, full suite green, behavior-preserving,
ruff-clean); scope is full. Domain caps (e.g. MAX_ROSTER, ≤2 hosts/show) are real features, NOT crippling.

## Build discipline (every step)
- Group-by-group / spec-by-spec, dependency order. ONE brain/ editor at a time (no races).
- Each step: manager-ddd full-scope build → orchestrator VERIFIES independently (full `pytest brain/ -q`
  green + ruff-clean + a REQ-by-REQ coverage table + no regressions to prior suites) → atomic commit.
- A git restore point/tag at clean baselines. All on branch build/foundation (main untouched).
- Behavior preservation [HARD]: default/empty/disabled paths stay byte-identical; additions are additive.

## DONE — today's partials closed to full (2026-06-24)
SHOWS-020 `59836f0` · PERSONACHARTER-035 spec `fe6eaf4` + code `f395502` · HOSTCTX-016 `db90b82` ·
minting `d56452d` · SEEDING-029 `38f215d`. Suite at 518 green, ruff clean.

## PHASE 1 — PROGRAMMING-007 (biggest spec; only Group PR built)
Build the 8 unbuilt groups, dependency order. Each FULL.
1. **PG** — Grounded host voice + forbidden-fact quality gate (PG-005). IN PROGRESS (build-pg-gate).
   The most-referenced missing piece (HOSTCTX-016/SHOWS-020/HOSTLIFE-032/INTERVIEW-CRAFT-034 all stub it).
2. **PV** — Per-persona voice card / delivery craft (HOSTCTX-016 HD-002 leaned on this).
3. **PI** — Persona identity anchors (the FROZEN per-persona ANCHOR BLOCK).
4. **PC** — Radio-craft playbook content + talk-generation rules.
5. **PS** — Script-side ear-writing.
6. **PT** — Show formats (incl. Solstice Hour) + fictional-persona ethics/disclaimers.
7. **PL** — Taste self-learning, provenance & feedback (greenfield; measured craft loop + canary + floors).
8. **CL** — Per-persona DJ-craft learning (multi-source human-DJ).
Note: PG/PV/PI/PC carry the FROZEN invariant set (never-ship-a-FAIL, grounding/fact-contract,
anti-convergence firewall, banned-phrase firewall, persona anchor block, craft-learning honesty rails).

## PHASE 1.5 — VOICE-002 (Qwen-TTS + Chatterbox providers + A/B) [user-placed 2026-06-24]
The render layer (speaks what PROGRAMMING-007 writes). Add QWEN-TTS (24 kHz) + CHATTERBOX (22.05 kHz)
provider classes behind the EXISTING pluggable TTSProvider interface (brain/voice.py; Kokoro primary + Piper
fallback + teldutala.fo Faroese already there), plus an A/B harness that renders identical sample scripts
per engine. The CODE is build-now (provider classes + harness, model calls stubbable in tests). The A/B
DECISION — picking the primary — is USER-IN-THE-LOOP and needs: engines installed + the RTX 2000 Ada
plumbed into Docker (not done) + the user's ears. User leans QWEN as frontrunner (confirm on the real GPU,
don't bank it pre-test). The pluggable seam = the winner swaps in without touching personas/talk/minting.
Settles PV-018's long-form ducked-bed render dependency. See [[voice-tts-ab]].

## PHASE 2 — OPS-004 (program director; only thin director-loop surface built)
Build the unbuilt bulk, FULL. Groups (read the spec for the full set): imaging/IDs, the NEWS ANCHOR
(news source list under INTEGRITY-033 SU governance + factual newscast + Faroese angle), world-model
inputs, the **OD-007 ledger substrate** (REQUIRED before ORCH-005), dayparting/format-clock, editorial
self-expansion, the fact-check gate stage (invokes PROGRAMMING-007 PG once built). Acquisition default
gate decision still open (BRAIN_ACQUIRE_ENABLED).

## PHASE 3 — ORCH-005 (orchestration / nervous system; only thin surface built)
BLOCKED on OPS-004 OD-007 ledger. Build the world-model / action-surface / awareness groups FULL once
the ledger lands.

## Cross-cutting (fold in as the owning group is built, do not silently skip)
- INTEGRITY-033 enforcement module (the single governance write-path REQ-IT-006 + cardinal anti-loop) is
  SPEC'd but UNBUILT — relevant when PL/news/world-model write durable knowledge. Build with PL/OPS news.
- The HOSTCTX-016 HY-003 + HD-001 documented boundaries close once PG (gate) + a multi-break harness exist.
- Docs-sync: refresh docs/components when each subsystem lands (see [[docs-sync-requirement]]).

## After PHASE 3
The other older partials remain candidates: metadata chain audit (MBMIRROR-017 MX/Discogs deferred;
ENRICH/DEDUP/ALBUMART/LOOKUPLOG/FILENAME/TAGSTREAM verify-vs-full-spec), INTERVIEW-CRAFT-034 build,
MEMORY-031 build, HOSTLIFE-032 build, the persona→show→schedule playout wiring (Step 5) + MAX_ROSTER knob.
Run the independent coverage audit to get the definitive map before committing to these.

Relates to [[autonomous-build-foundation]], [[build-in-full-not-limped]], [[ai-director-identity]].
