# SPEC Review Report: SPEC-RADIO-LINEUP-050
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.58

Reasoning context ignored per M1 Context Isolation — this audit is grounded only in
`spec.md`, `acceptance.md`, the real `brain/` source, and the sibling SPECs (OPS-004,
SHOWS-020, DATASTORE-022, PROGRAMMING-007). Every finding below cites a concrete line.

## Must-Pass Results

- [PASS] **MP-1 REQ number consistency**: SH-001..004, SY-001..004, SQ-001..003, SN-001..003
  are sequential with no gaps/dupes (spec.md:692-705); NFR-LU-1..6 sequential (spec.md:706-711).
  14 REQ + 6 NFR = 20, matching the Section 12 parity claim (spec.md:713).
- [PASS] **MP-2 EARS format compliance**: Every Section-6 requirement is a well-formed `SHALL`
  statement with an identifiable EARS shape (spec.md:352-535). acceptance.md uses Given/When/Then,
  which is the correct form for *acceptance criteria* (not mislabeled EARS). NOTE: several
  EARS *type tags* in the spec/traceability table are mis-assigned vs the actual wording — see D10
  (MINOR), which does not breach the firewall.
- [PASS] **MP-3 YAML frontmatter validity**: `id/version/status/created/updated/author/priority/
  issue_number` all present (spec.md:1-10). This matches the project's own frozen schema (verified
  against OPS-004, SHOWS-020, DATASTORE-022, HOSTVOICE-049 frontmatter — none use `labels` and all
  use `created` not `created_at`). The MoAI-canonical `labels`/`created_at` fields are absent but
  that is the *project standard*, not a per-SPEC defect; recorded as informational only.
- [N/A] **MP-4 Section 22 language neutrality**: single-project Python SPEC; no multi-language
  tooling enumeration in scope. Auto-passes.

The verdict is driven by the Must-Pass-independent firewall in §M5: four BLOCKING boundary
defects (D1-D4) that no high category score can offset.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.50 | 0.50 (multiple reqs need interpretation; reasonable engineers would implement differently) | SY-003 vs OB-014 fallback is self-contradictory (D2); SY-001 `discontinued` semantics contradict the live code (D3); similarity metric undefined (D6); two unrelated hiatus bounds (D8) |
| Completeness | 0.60 | 0.50-0.75 (sections all present, but a load-bearing rail and two edge behaviors are missing) | Flagship-pin rail absent (D4); max-hiatus-exceeded behavior absent (D8); no migration AC (D9). All 7 structural sections + Exclusions (spec.md:539-578) present |
| Testability | 0.60 | 0.50 (several ACs require judgment / an undefined metric) | AC-SQ-002 "scores at/above 0.6" untestable without a defined metric (acceptance.md:83-89, D6); rest are observable |
| Traceability | 0.95 | 1.0-band, docked for the unmapped `show_relaunched` event | Clean 1:1: 20 REQ/NFR ↔ 20 AC, all ids present and valid (acceptance.md confirmed 20 AC-*); no orphans, no dangling refs. Minor: `show_relaunched` reuse claimed but maps to no SY transition (D3) |

## Defects Found

### D1. `shows` table violates the FROZEN DATASTORE-022 partition map — BLOCKING
- **Where**: spec.md:196-199, 354-362 (REQ-SH-001), 678 (Delta), 645-648 (R-LU-5) vs
  DATASTORE-022 spec.md:103, 145-146, 149.
- **Defect**: LINEUP places a table literally named `shows` in `brain.db` ("core-operational
  partition... this SPEC names it `library.db`"). DATASTORE-022 declares the four-file partition
  **and its table→file mapping FROZEN** (DATASTORE-022 spec.md:19-20, 195-197) and explicitly
  maps `shows` → **`events.db`** ("append-heavy analytics: `play_events` + `likes` + `shows`
  (future STATS-013)", DATASTORE-022:103; "`play_events`/`likes`/`shows` are STATS-013/LIKE-015's",
  DATASTORE-022:149). `brain.db`'s frozen contents are `tracks + attempts + watch_manifest`
  (DATASTORE-022:101) — `shows` is **not** listed. So LINEUP (a) adds an unlisted table to a
  frozen partition and (b) creates a same-name table in a *different file* than the frozen map
  assigns. DATASTORE-022's safety model is "one table name → one file" with ATTACH-based
  cross-file reads (DATASTORE-022:117-125, 155); a duplicate `shows` across `brain.db` and
  `events.db` makes those joins ambiguous. The SPEC *acknowledges* the collision (R-LU-5,
  Section 1.4) but "they measure different things" is not a resolution — it ships the hazard.
- **Remediation**: Rename LINEUP's editorial table to a non-colliding name (e.g.
  `show_registry` or `lineup_shows`) and update REQ-SH-001 / AC-SH-001 / Delta map accordingly;
  OR obtain an explicit amendment to DATASTORE-022 reassigning the `shows` name. Drop the
  invented "library.db" alias (D11). Until reconciled, REQ-SH-001 cannot be implemented without
  breaching a frozen sibling.

### D2. SY-003 house-lane fallback contradicts OPS-004 REQ-OB-014 (and itself) — BLOCKING
- **Where**: spec.md:271 (glossary), 433-441 (REQ-SY-003), 331 ("OB-014 ... WINS"), 226 vs
  OPS-004 spec.md:1418-1430 (REQ-OB-014 full text).
- **Defect**: SY-003 says a discontinuation may "return the slot to the OPS-004 REQ-OA-008
  no-orphan house/unscheduled lane (`show_or_episode_id` reset to `unscheduled`, served by the
  `NoOrphanBootstrap` house voice)" — i.e. a **hostless** slot (`persona_id=""`). OB-014 forbids
  exactly that during a transition: "if no eligible successor can be bound... the transition is
  REJECTED — the persona STAYS ON AIR — ... **a hostless slot is never produced**" (OPS-004:1424-
  1428), and OB-014's trigger list explicitly includes "discontinue" (OPS-004:1419). LINEUP
  simultaneously asserts the house-lane fallback **and** "the OPS-004 REQ-OB-014 always-staffed
  invariant WINS" (spec.md:331) / "OBEYS REQ-OB-014 unchanged" (spec.md:175). Both cannot hold:
  if OB-014 wins, the discontinuation is rejected and the incumbent show stays `active` (no house
  lane); if the house lane is reachable, OB-014 is weakened. This is the exact SQ↔SY-003↔OB-014
  junction flagged: there is no deadlock (the firewall escalation routes to the house lane,
  spec.md:479), but that route is precisely the one OB-014 forbids.
- **Remediation**: Pick one and make it normative. Recommended: when no vetted replacement
  clears the firewall, the discontinuation **does not commit** (OB-014 rejection rule) — the
  incumbent show stays `active` and the director is escalated; the house lane is reachable ONLY
  for a slot that was already `unscheduled` (bootstrap), never as the *product of* a discontinue.
  Rewrite REQ-SY-003 + AC-SY-003 + B4 to delete the "OR returns to the house lane" branch for
  staffed-curator discontinuation, or explicitly carve a documented exception to OB-014 (which
  requires an OPS-004 amendment, since OB-014 is [HARD]).

### D3. SY-001 `discontinued` semantics contradict the live OB-012 implementation — BLOCKING
- **Where**: spec.md:405-418 (REQ-SY-001), 413-416 (`show_relaunched` reuse) vs
  brain/lifecycle.py:490-545 (`discontinue_show`) and OPS-004 spec.md:1380-1388 (REQ-OB-012).
- **Defect**: The real, shipped OB-012 path (`brain/lifecycle.py:490-545`) performs
  `live → discontinued → relaunched` as **one atomic flow that immediately invents a successor**
  via `ShowEngine.propose_show` (lifecycle.py:524-540) and emits `show_discontinued` *then*
  `show_relaunched`. LINEUP's SY FSM redefines `discontinued` as a **durable resting state** whose
  only legal exit is `discontinued → retired` and states "No other transitions are legal"
  (spec.md:411-412) — there is **no `discontinued → active` relaunch** in LINEUP's FSM. Yet
  SY-001 claims to reuse the `show_relaunched` seam (spec.md:413-414). In LINEUP's own FSM no
  transition emits `show_relaunched` (the successor is a *fresh concept*, i.e. a `concept→active`
  of a different row). So LINEUP both (a) changes the meaning of a discontinue from "atomic
  discontinue-and-relaunch-successor" to "discontinue into a resting state" — contradicting the
  existing code and OB-012 — and (b) reuses an event (`show_relaunched`) that maps to none of its
  declared transitions. The Section-1.4 claim that SY merely "EXTENDS" the FSM "unchanged"
  (spec.md:173-176) is therefore inaccurate: it overrides OB-012's discontinue contract.
- **Remediation**: State explicitly how LINEUP's `discontinued` relates to OB-012's atomic
  discontinue→relaunch (does LINEUP *replace* OB-012's auto-successor with the SY-003
  replacement/escalation path? If so, say so and flag it as a behavioral change, not an
  extension). Define which SY transition emits `show_relaunched` (likely the SQ-003 hiatus→active
  reactivation, or the successor-concept binding) or drop the reuse claim. Reconcile with
  `lifecycle.discontinue_show` so the two do not double-emit `show_discontinued`/`show_relaunched`
  with conflicting semantics.

### D4. Missing requirement: no pin/protect rail for PROGRAMMING-007 PT flagship shows — BLOCKING
- **Where**: gap across Group SY (spec.md:401-454) vs PROGRAMMING-007 spec.md:557-558, 1057-1058,
  1126-1128 (Solstice Hour / Summarrødd flagship, [HARD] ethics guardrail) and LINEUP SY-002
  (spec.md:422-429), Exclusions (spec.md:577-578).
- **Defect**: LINEUP grants the director full freedom to hiatus/discontinue/**retire any show**
  (spec.md:204-211, SY-001). PROGRAMMING-007 Group PT owns the flagship long-form "Solstice
  Hour"/"Summarrødd" — a recurring, [HARD]-ethics-guardrailed format (PROGRAMMING-007:700,
  1057-1058). Nothing in LINEUP prevents the AI from auto-retiring that flagship. SY-002 then
  makes retirement **permanent and irreversible** ("a retired show... NEVER... returns to
  `active`", spec.md:411; "Reviving a retired show — barred", spec.md:577-578), and the SQ
  firewall would actively **block re-creating a similar concept** (spec.md:117-123). Net effect:
  the director can permanently destroy a [HARD] flagship format and the firewall guarantees it can
  never be re-minted. This is an unbounded-autonomy hazard the SPEC's own "hard rails" section
  (spec.md:204-211) does not cover.
- **Remediation**: Add a REQ (e.g. REQ-SY-005) for a `pinned`/`protected` show attribute (set for
  PT flagship formats) that bars `hiatus`/`discontinued`/`retired` transitions without explicit
  human/director override, with a matching AC. Reference PROGRAMMING-007 REQ-PT-001/002 as the
  source of the pinned set.

### D5. SQ firewall duplicates the existing SHOWS-020 novelty machinery; boundary section mischaracterizes ShowEngine — MAJOR
- **Where**: spec.md:93-97 (1.1 premise), 187-189 / 553-555 (ShowEngine = "in-session only"),
  460-483 (Group SQ) vs brain/shows.py:579 (`angle_similarity`), 596-720 (`ShowEngine`,
  `is_novel`, `propose_show` bounded regenerate), 599-659 (durable per-persona retired-shows
  ledger `load_shows`/`save_show`).
- **Defect**: Two factual problems undermine the boundary analysis. (1) Section 1.1 asserts
  "there is NO durable show RECORD... no permanent memory of what shows existed" (spec.md:93-97).
  False: `ShowEngine` already persists a durable per-persona retired-shows history via
  `load_shows()`/`save_show()` and an in-memory `_ledger: persona_id -> retired shows`
  (brain/shows.py:599-659). (2) LINEUP characterizes ShowEngine as in-session execution only and
  declares it "never owns the novelty check" (spec.md:189, 553-555), but the SQ firewall (reject
  over a tunable threshold + bounded regenerate, spec.md:473-483) is functionally the *same*
  mechanism ShowEngine already ships: `is_novel()` + `angle_similarity()` + the bounded-regenerate
  loop in `propose_show` (brain/shows.py:678-720, REQ-SX-002/SX-004). SQ is a real sibling measure
  (cross-persona, cross-time, name+theme+angle) but the SPEC neither acknowledges the overlap nor
  reuses the existing metric — risking a second, divergent similarity implementation.
- **Remediation**: Correct the 1.1 premise to acknowledge ShowEngine's existing per-persona
  retired-show persistence and novelty check. In Group SQ, explicitly reuse `brain/shows.py:
  angle_similarity` (or justify a distinct metric) and reconcile the SQ threshold with
  ShowEngine's existing `_threshold` (REQ-SX-002) so the station does not run two unrelated
  similarity scales.

### D6. Similarity metric undefined → SQ-002 / AC-SQ-002 not binary-testable — MAJOR
- **Where**: spec.md:473-481 (REQ-SQ-002), 268 (glossary), 422-429 (SY-002 fingerprint) and
  acceptance.md:83-89 (AC-SQ-002) vs brain/shows.py:579 (an existing deterministic metric).
- **Defect**: SQ-002 sets a magic threshold "default 0.6" but leaves "the similarity metric ...
  config" (spec.md:479-481) with no named function, range, or normalization. The fingerprint is
  just "(name, theme, music_angle, persona_id) JSON text" (spec.md:268, 424). "Score ≥ 0.6" is
  meaningless and untestable without a defined metric scale (cosine [0,1]? token Jaccard?
  normalized edit distance?). AC-SQ-002 ("C scores at/above it", acceptance.md:84) therefore is
  not binary-testable as written. A deterministic `angle_similarity()` already exists
  (brain/shows.py:579) and is the natural anchor — but the SPEC never references it.
- **Remediation**: Name the metric (reuse `angle_similarity`), pin its range/normalization, and
  state which fields feed it (the AC compares `name`+`theme`+`music_angle` — confirm the stored
  fingerprint preserves enough to recompute). Then AC-SQ-002 becomes testable against a fixture.

### D7. REQ-SH-004 / Section 1.4 claim that `assign_persona` "already honours the OPS-004 caps" is inaccurate — MAJOR
- **Where**: spec.md:53, 396-397 (REQ-SH-004 "which already honours the OPS-004 caps +
  measured-change budget") vs brain/schedule.py:897-915 (`assign_persona`).
- **Defect**: `assign_persona(slot_id, persona_id, show_or_episode_id, *, caps_ok=None,
  editorial_reason="")` enforces the measured-change budget unconditionally (`_budget_ok`,
  schedule.py:909) but enforces host/territory caps **only if the caller injects a `caps_ok`
  predicate** — it defaults to `None`, i.e. *no cap check* (schedule.py:898, 907-908). So the
  PR-004 anti-convergence cap and any host cap are NOT automatic at the binding seam. If LINEUP
  binds shows through `assign_persona` without passing `caps_ok`, SH-003/PR-004 distinctness is
  silently unenforced at the seam.
- **Remediation**: Correct the wording to "honours the measured-change budget, and honours the
  caps when LINEUP injects the `caps_ok` predicate", and add to REQ-SH-004/AC-SH-004 an explicit
  obligation that the concept→active bind passes a `caps_ok` enforcing SH-003 + the PROGRAMMING-007
  REQ-PR-004 firewall.

### D8. Max-hiatus-exceeded behavior unspecified; two hiatus bounds unrelated — MINOR
- **Where**: spec.md:409 (SY-001 "tunable MAX-HIATUS bound"), 485-494 (SQ-003 "long-hiatus
  bound"), 681 (config delta lists both `max-hiatus bound` and `long-hiatus re-vet bound`).
- **Defect**: SY-001 introduces a `max-hiatus` cap but never says what happens when it is
  exceeded (auto-discontinue? stay forever? force a re-vet?). SQ-003 introduces a *separate*
  `long-hiatus re-vet` bound. The two knobs' relationship (ordering, interaction on a show that is
  both past-max and reactivating) is undefined and has no REQ/AC.
- **Remediation**: Add the exceeded-max-hiatus transition (e.g. auto-`discontinued` past the cap,
  obeying SY-003/OB-014) with an AC, and state the invariant between the two bounds.

### D9. No explicit migration AC for adding `shows` to an existing populated `brain.db` — MINOR
- **Where**: spec.md:568-570 (Exclusions delegate migration to DATASTORE-022), 678 (Delta) and
  acceptance.md:15-22 (AC-SH-001 only asserts "WHEN LINEUP is initialized, THEN a shows table
  exists").
- **Defect**: Migration is delegated by reference but no testable AC covers idempotent addition
  of the table to an *already-populated* brain.db on upgrade (CREATE-IF-NOT-EXISTS, no data loss,
  no `knowledge.db` touch). For a brownfield SPEC adding a durable table this should be explicit.
- **Remediation**: Add an AC: "GIVEN an existing brain.db with `tracks` populated, WHEN LINEUP
  initializes, THEN the new table is created idempotently, existing rows are unchanged, and
  `knowledge.db` is untouched."

### D10. EARS type tags mismatch wording in several requirements — MINOR
- **Where**: spec.md:422 (SY-002 tagged Ubiquitous, but "At retirement... SHALL compute" is
  Event-driven); 485 (SQ-003 tagged State-driven, but "When a show is reactivated... SHALL
  re-run" is Event-driven); 514 (SN-002 tagged Ubiquitous, but "When the director applies... SHALL
  journal" is Event-driven); 389 (SH-004 tagged State-driven, operative clause "on approval...
  SHALL record/bind" is Event-driven); 502 (SN-001 tagged Event-driven, but "SHALL be able to
  propose" is a Ubiquitous/Optional capability). The Section 12 table (spec.md:692-705) inherits
  these mis-tags.
- **Remediation**: Re-tag to match the operative trigger; update the traceability table.

### D11. Invented "library.db" partition name not present in DATASTORE-022 — MINOR
- **Where**: spec.md:196 ("this SPEC names it `library.db`"), 354-356 (REQ-SH-001), AC-SH-001
  (acceptance.md:17) vs DATASTORE-022 which uses `brain.db` (DATASTORE-022:101).
- **Defect**: Introducing a new alias `library.db` for the DATASTORE-022 `brain.db` partition
  adds avoidable terminology drift and compounds the D1 collision confusion.
- **Remediation**: Use `brain.db` consistently; delete the `library.db` alias.

## Chain-of-Verification Pass

Second-look findings (re-read sections after the first pass):
- Re-checked **every** REQ↔AC pair end-to-end: 20 REQ/NFR map 1:1 to 20 ACs (acceptance.md AC ids
  enumerated: SH-001..004, SY-001..004, SQ-001..003, SN-001..003, NFR-LU-1..6). No orphan AC, no
  dangling REQ ref. Traceability is genuinely strong — confirmed, not skimmed.
- Re-verified the four claimed seams in real code, not just the spec's assertions:
  `assign_persona` (schedule.py:897), `remove_slot(discontinue=True)` (schedule.py:863),
  `ProgramDirector` (schedule.py:999), `NoOrphanBootstrap` (schedule.py:961), `program_cycle`/
  `persona_assigned` events (schedule.py:689/694), `show_discontinued`/`show_relaunched`
  (lifecycle.py:71-72). All exist — the seam-reuse claims are real (this is a genuine strength;
  the SPEC is not inventing infrastructure).
- Re-read OB-014 in full (OPS-004:1418-1430) before finalizing D2: confirmed "discontinue" is in
  the trigger list and "a hostless slot is never produced" / "persona STAYS ON AIR" is the
  rejection rule — D2 is not a misreading.
- Re-examined whether the SQ/SY-003 deadlock the prompt feared actually exists: it does **not**
  (escalation routes to the house lane, spec.md:479) — but that same route is what triggers D2.
  Downgraded "deadlock" to a non-finding; the real defect is the OB-014 contradiction.
- Checked the Exclusions section for specificity (spec.md:539-578): 12 concrete, sibling-owned
  exclusions — substantive, not vague. PASS.
- New defect surfaced on second pass: D7 (the `caps_ok` default-None inaccuracy) — only visible by
  reading the actual `assign_persona` signature, not the spec's paraphrase. Added.

## Recommendation (FAIL — actionable fixes for manager-spec)

Resolve all four BLOCKING defects before re-submission:

1. **D1** — Rename the editorial table off the frozen `shows`/`events.db` earmark (e.g.
   `show_registry`) across REQ-SH-001, AC-SH-001, the Delta map, and drop the `library.db` alias
   (D11). Do not add a second `shows` to a different partition file.
2. **D2** — Make the no-replacement discontinuation outcome single-valued and OB-014-consistent:
   reject the transition and keep the incumbent on air (recommended), and remove/qualify the
   "returns to house lane" branch in REQ-SY-003, AC-SY-003, and Scenario B4.
3. **D3** — Reconcile LINEUP's `discontinued` resting-state FSM with the shipped
   `lifecycle.discontinue_show` (atomic discontinue→relaunch-successor) and OB-012; specify which
   SY transition (if any) emits `show_relaunched`, and declare this a behavioral change rather than
   an "extension" if it overrides OB-012's auto-successor.
4. **D4** — Add a pinned/protected-show requirement so PROGRAMMING-007 PT flagship formats
   (Solstice Hour) cannot be auto-retired into permanent, un-recreatable loss.

Then address the MAJORs (D5 ShowEngine duplication + 1.1 factual correction; D6 define/reuse the
similarity metric so AC-SQ-002 is testable; D7 caps_ok injection obligation) and the MINORs
(D8-D11). Re-submit for iteration 2; the regression check will verify each defect by line.
