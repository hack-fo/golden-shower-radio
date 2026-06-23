---
id: SPEC-RADIO-OPS-004
artifact: acceptance
version: 0.9.1
status: draft
created: 2026-06-22
updated: 2026-06-23
author: charlie
---

# SPEC-RADIO-OPS-004 — Acceptance Criteria

> HISTORY — 2026-06-23 (v0.9.1): Audit convergence fixes synced from spec.md (no AC
> added/removed; 1:1 REQ↔AC preserved). AC-OA-010 disambiguated (catalog/DB RECORD only;
> on-file tag/artwork write routed through TAGSTREAM-009 Group TW); AC-OA-011/AC-OA-012
> reworded to CONSUME ANALYSIS-006's produced bpm/camelot/key/energy features (ANALYSIS-006
> owns extraction; OPS-004 owns reconciliation + catalog RECORD).

1:1 REQ ↔ AC mapping: every requirement and NFR in spec.md has exactly one acceptance
entry here (Section A). Detailed Given-When-Then scenarios for the load-bearing
requirements are in Section B. The Definition of Done is in Section C.

All acceptance criteria assume the inherited CORE-001 + VOICE-002 behavior holds: the
stream never depends on any OPS decision to stay audible; no human is in the run loop;
no monetization/appeal-optimization; one shared loudness constant.

---

## Section A — Acceptance criteria (1:1 with requirements)

### Group OA — Program Director & 24h Scheduling

**AC-OA-001 (REQ-OA-001).**
- On daemon start and on the self-scheduled planning cadence, the AI produces a 24h
  programme (talk shows / music blocks / themed hours / imaging across the day) with
  no human prompt.
- The arrangement is AI-authored; no fixed programme/playlist/clock content is
  hardcoded as the creative decision-maker (only the FIXED rails apply).
- Each planning cycle is logged with its trigger.

**AC-OA-002 (REQ-OA-002) [documented compound].**
- (a) Per-daypart format clocks exist as data (typed, ordered slots). (b) On each
  playout pull the current local-clock slot (REQ-OA-009) resolves to exactly one
  concrete item. (Both obligations verified; the AC is intentionally compound, matching
  the compound REQ.)
- Anti-lattice PROPERTY (default guidance, AI-tunable, not a fixed creative rule): the
  number of clock variants per daypart is chosen so it is NOT a divisor or multiple of
  24 (which would land the same song in the same hour every day). The actual variant
  count is AI-authored/tunable; the AC tests only that the count satisfies the
  anti-lattice property by default, not a specific number like "5 or 7."
- Slot order within an active clock, the top-of-hour ID slot, and daypart boundaries
  are fixed; slot contents and which variant is active are AI-chosen.

**AC-OA-003 (REQ-OA-003) — soft separation layer only.**
- Soft separations (tempo/energy/vocalist-gender/era/sound-code) are scored and the AI
  picks the best-scoring legal candidate.
- The AI may weigh/relax soft scores; the soft layer asserts NO hard rail (that is
  AC-OA-003a) and NO empty-set fallback (that is AC-OA-003b).
- Soft-separation decisions are logged for traceability.

**AC-OA-003a (REQ-OA-003a) — sole hard no-repeat / artist rail.**
- [HARD] No song plays again within its configured no-repeat window; artist/title
  separation holds. Repetition within the no-repeat window is rejected (this is the
  ONLY place the hard rail is asserted).
- Selection demonstrably biases toward least-recently-played eligible tracks (verified
  from the play log: a freshly-played title is not re-selected over a long-unplayed
  eligible one absent a logged reason).

**AC-OA-003b (REQ-OA-003b) — empty-legal-set relaxation.**
- [HARD] When no candidate satisfies the soft separations (REQ-OA-003), the soft window
  is widened or an adjacent category is borrowed and the relaxation is logged; the queue
  never stalls.
- [HARD] The hard no-repeat / artist rails (AC-OA-003a) are NEVER relaxed; only the soft
  layer is. Verified by forcing a thin-category condition and confirming no illegal
  repeat occurs and the queue keeps moving (continuity wins, AC-OA-008).

**AC-OA-003c (REQ-OA-003c) — artist-frequency limit.**
- [HARD] The same artist does not play more often than the configured limit: a minimum
  gap between same-artist plays and/or a max plays-per-artist within a rolling window is
  enforced (verified from the play log: no artist exceeds the configured frequency).
- The gap/window values are TUNABLE config; the limit is relaxed only under the
  empty-legal-set degradation (AC-OA-003b) and the relaxation is logged.
- No single artist can dominate the log under normal operation.

**AC-OA-003d (REQ-OA-003d) [SOFT + one HARD sub-clause] [documented compound].**
- (a) GENRE-FAMILY BALANCE [SOFT]: in the unscheduled lane, over a rolling window no single
  genre-family exceeds `target_ceiling` absent a logged relaxation, AND genre families
  demonstrably ROTATE (verified from the play log: families spread rather than clustering).
  The penalty is added to the existing least-recently-played pick score (composite =
  LRP_rank + penalty_lambda * max(0, window_share(family) − target_ceiling); pick min);
  selection is DETERMINISTIC given identical state (no RNG). Tracks map to families via the
  static `genre_family_map` (the only new artifact; families, not raw tags).
- (b) SMOOTH ADJACENCY [SOFT]: in the unscheduled lane, successive picks show BOUNDED
  energy/harmonic distance to the just-aired track (via ANALYSIS-006 `library.adjacency()`,
  which withholds the harmonic filter on low-confidence keys per REQ-AT-007) — jarring jumps
  (funk → black metal) score worse than gradual flow — EXCEPT across a logged deliberate
  BOUNDARY (daypart REQ-OA-005, format-clock song-category slot change REQ-OA-002, or
  top-of-hour), where the adjacency penalty is suspended for that one transition. It is a SOFT
  scoring term, NOT a hard rail (the adjacency/segue DECISION stays the AI's per REQ-OA-006/014).
- (c) [HARD] SCHEDULED-CURATED-SHOW EXEMPTION: when a scheduled show/episode is active
  (REQ-OB-006 association `show_or_episode_id != 'unscheduled'`), NEITHER (a) nor (b) applies;
  a single-genre or consistent-style curated block plays UNMODIFIED with NO taste/coherence/
  anti-drift check (verified), satisfying CORE-001 REQ-D-002 / AC-OA-004. The exemption predicate
  IS the activation predicate: one `is_unscheduled` gate (default True) turns the variety layers
  ON off-schedule and OFF for scheduled. Until the REQ-OB-006 seam is coded, all playout is
  unscheduled so the rule applies unconditionally (self-correcting).
- Both soft layers are STRICTLY SUBORDINATE: they run ONLY on the already-legal candidate set
  REQ-OA-003a/REQ-OA-003c produce (they never re-admit an excluded track), they NEVER ban (only
  down-weight), and on an empty legal-and-balanced subset they relax to the full legal set, play
  one, and LOG it (REQ-OA-003b; continuity wins, AC-OA-008) — the soft layers never stall the
  queue and never override the hard rails.
- All thresholds (`genre_family_map`, `balance_window`, `target_ceiling`, `penalty_lambda`,
  `adjacency_lambda`, `min_distinct_families_per_window`) are TUNABLE config the AI may evolve
  (REQ-OA-004 pattern); every soft-separation/relaxation decision is logged (AC-OA-003). No new
  store (reuses the existing recent deque), no playout/Liquidsoap change (operates at SELECTION,
  one step before the [[dj-mixing]] crossfade/beatmatch transition layer it feeds), and no <1s
  hot-path dependency on the ORCH-005 REQ-RW-006 dedup view (optional slow-tick consumer only).

**AC-OA-004 (REQ-OA-004).**
- Each track carries an AI-assigned rotation category; the AI promotes/demotes/rests
  titles over time.
- Category schema + target frequency bands are config (TUNABLE); the AI may evolve
  them.
- No taste/coherence match is enforced on category membership.

**AC-OA-005 (REQ-OA-005).**
- Crossing a daypart boundary on the LOCAL Faroe clock (REQ-OA-009) switches the active
  clock set + persona register + energy arc.
- Only the daypart MANDATE — its existence and boundary on the local clock (the
  structural rail) — is fixed; the within-daypart energy ordering/tone/register is
  AI-chosen and logged. No fixed energy/creative prescription is enforced per daypart.

**AC-OA-006 (REQ-OA-006).**
- The AI emits a next-song adjacency choice plus transition params (crossfade length,
  cue points) using BPM/key/energy from enrichment.
- The playout layer enforces the no-vocal-over-vocal guard and crossfade mechanics.
- Sample-accurate beat-aligned mixing is not asserted here (later phase, R-O-9).

**AC-OA-007 (REQ-OA-007).**
- An imaging/ID clock slot triggers the imaging production pipeline (Group OE) for an
  AI-chosen element (type/copy/wet-dry/language).
- The top-of-hour ID slot is reserved (REQ-OE-008); other cadence positions are TUNABLE.

**AC-OA-008 (REQ-OA-008).**
- [HARD] Forcing any scheduled item to be unavailable or fail to render results in a
  fallback music track or cached evergreen ID being served; the stream continues.
- No OPS scheduling path can be the single cause of stream silence (verified by
  forcing decision/render failures while the stream continues).
- The fallback and its reason are logged.

**AC-OA-009 (REQ-OA-009).**
- [HARD] The program director resolves the current LOCAL Faroe time and date
  (timezone `Atlantic/Faroe`, default) with correct DST (WET ↔ WEST), not UTC or
  server-local time.
- Dayparts are anchored to local Faroe time (verified: a daypart boundary fires at the
  correct local wall-clock time across a DST transition).
- The AI has access to date, day-of-week, and season/holiday context and may
  differentiate weekday/weekend/seasonal programming (how it uses them is AI-chosen).
- Location is Tórshavn: on-air time/date references (talk + news) use local Faroe time;
  the station presents location awareness (e.g. local greetings). Timezone/location are
  configurable (default `Atlantic/Faroe` / Tórshavn).

**AC-OA-010 (REQ-OA-010).**
- A track with garbled/filename-parsed tags (e.g. "Sly & the Familt Stone") is
  corrected/normalized and reconciled against authoritative metadata.
- Correction runs off the playout path; failures log and leave the track usable with
  best-available tags.
- [Disambiguation] The correction writes the catalog / DB RECORD ONLY; it does NOT write
  corrected tags or artwork back to the audio FILES. Any on-file tag/artwork WRITE is
  routed through SPEC-RADIO-TAGSTREAM-009 (Group TW), referenced not forked — OPS-004
  never mutates the audio files itself.

**AC-OA-011 (REQ-OA-011) [HARD] [documented compound].**
- [HARD] Each track is enriched with genre, mood, BPM, key, energy, and year from any of
  the concrete sources: embedded tags (mutagen/ffprobe) / the audio-analysis features
  PRODUCED BY SPEC-RADIO-ANALYSIS-006 (bpm/camelot/key/energy/cues — CONSUMED here, not
  re-extracted; ANALYSIS-006 [HARD]-OWNS the extraction toolchain) / external metadata
  APIs (MusicBrainz API + TheAudioDB API; Discogs/Last.fm optional) or LLM knowledge /
  and filename `%ARTIST% - %TITLE%` parsing as a reliable fallback (the sources are
  alternatives feeding one enriched record — the AC is intentionally compound, matching
  the compound REQ).
- OPS-004 owns only the tag-correction/reconciliation across sources and the catalog
  RECORD; it does NOT run librosa/aubio/essentia itself (that is ANALYSIS-006).
- Enrichment runs off the playout path and never blocks the stream; partial enrichment
  is still recorded and usable; the filename-parse fallback recovers artist/title when
  tags/APIs are missing.

**AC-OA-012 (REQ-OA-012) [HARD].**
- [HARD] The catalog RECORD is queryable by artist/genre/mood/BPM/key/energy/year/
  category/history and is used by the PD to build genre nights, mood/energy arcs, and
  BPM/key-matched DJ-sets.
- The BPM / key (camelot) / energy fields are populated FROM ANALYSIS-006's produced
  features (consumed, not re-extracted); OPS-004 owns the queryable catalog RECORD and
  the reconciliation of editorial fields, not the audio-feature extraction.
- The catalog stays current as acquisition adds music (new tracks appear enriched).

**AC-OA-013 (REQ-OA-013).**
- Each director planning cycle selects a run mode from the editorial brief (e.g.
  maintenance / responsive / continuity / special / quiet); the mode is logged.
- The mode set is TUNABLE and the per-loop mode choice is AI-authored; no fixed
  per-loop behavior is hardcoded (verified: different cycles can pick different modes,
  including a "quiet" mode that deliberately runs music with minimal talk).

**AC-OA-014 (REQ-OA-014).**
- The AI picks a transition/mixing style by show/daypart context and emits transition
  params for the playout layer.
- For a club/dance show, the emitted style is DJ-style: crossfade + beatmatching
  (BPM/key from REQ-OA-011) + high/low-pass EQ blends (sophistication may phase in with
  the mixing-implementation research; degrades to a crossfade if metadata is missing).
- For a regular show, the style is a clean transition with at minimum a gentle
  crossfade/fade-out — no beatmatch/EQ-mix.
- [HARD] No transition is a sharp hard cut by default (the no-sharp-cutoff floor,
  AC-NFR-O-11, always holds).

**AC-OA-015 (REQ-OA-015).**
- The PD exposes the enumerated grid operations ADD / REMOVE / MOVE slot/show (mapping to
  CORE-001 REQ-B-003 insert/replace/move-show) PLUS a first-class ASSIGN / REASSIGN-persona-
  to-slot operation; all are dispatched through ORCH-005 REQ-RA-001(g) -> REQ-RA-002 ->
  CORE-001 REQ-B-003 (verified: no forked schedule store; the action mutates the CORE-001
  store and persists via REQ-B-010).
- ASSIGN/REASSIGN honors the host caps (REQ-OB-003 / CORE-001 REQ-B-011, Faroese ≤1
  REQ-V-D-005) and the PROGRAMMING-007 REQ-PR-004 firewall (no territory collision on the new
  slot).
- [HARD] Every grid edit preserves the 24h no-gap coverage (CORE-001 REQ-B-002/003) AND the
  always-staffed host-availability invariant (REQ-OB-014), and takes effect for FUTURE blocks
  WITHOUT interrupting the current stream; the website renders the live grid atomically
  (CORE-001 REQ-E-003 / REQ-OB-007) so no listener sees a half-written schedule.
- Edits are recorded as REQ-OD-007 ledger events; grid-edit frequency is bounded by the
  rarity tiering (REQ-OD-010: routine MOVE/REASSIGN Tier 2, discontinue/relaunch Tier 1).

### Group OB — Shows & Host Personas

**AC-OB-001 (REQ-OB-001).**
- The AI invents and schedules themed shows with distinct identity/character using the
  CORE-001 persona/host store; no human-authored show list is required.
- Show creative content is AI-authored, not prescribed.

**AC-OB-002 (REQ-OB-002).**
- An active show carries an AI-chosen persona register (CHR-hype / curatorial /
  continuous-mix) shaping talk frequency/tone/selection.
- The reference patterns drawn from are weighted to KEXP / P3 Dans / P3 Mix / ASOT /
  Rodigan; no reference station's assets or names are copied.

**AC-OB-003 (REQ-OB-003).**
- No show is constructed with more than 2 hosts (CORE-001 REQ-B-011); no Faroese-
  language show exceeds 1 host (VOICE-002 REQ-V-D-005).
- OPS introduces no new host-count authority.

**AC-OB-004 (REQ-OB-004).**
- The AI defines/runs/evolves/retires its own recurring named segments (name + ident +
  selection rule + generated intro).
- Segment names are AI-invented (no trademarked reference-station names).

**AC-OB-005 (REQ-OB-005).**
- A special show's window applies its override clock/pool/persona/imaging and cleanly
  restores the default clock at window end (no orphaned slot).
- The override/restore mechanism is the fixed rail; the show's content is AI-owned.

**AC-OB-006 (REQ-OB-006).**
- Each aired track appends a persisted play-history entry with at least track
  (artist/title), local-time aired_at timestamp, and show/episode id (or 'unscheduled'
  when no show is active).
- The show association is recorded from the start (verified: entries logged before any
  show exists are marked 'unscheduled' and later per-show entries carry the show id).
- The play-history persists across daemon restarts and extends CORE-001's play-log
  (not a forked store).

**AC-OB-007 (REQ-OB-007).**
- The website renders per-show/episode tracklists: each scheduled show/episode lists
  its played tracks with aired-at timestamps, grouped by show/episode.
- The website renders a "songs played" timeline of timestamped unscheduled-block songs
  (entries marked 'unscheduled').
- Both views populate from the persisted play-history (REQ-OB-006) and extend the
  CORE-001 self-served website (not a forked site).

**AC-OB-008 (REQ-OB-008).**
- Each planned/scheduled show has an AI-authored description/blurb (theme/vibe/what
  it's about); no fixed description copy is hardcoded.
- The website's show lineup/schedule displays each show alongside its description.
- Descriptions update when the AI plans or evolves the schedule (verified: editing a
  show's plan refreshes its displayed description); extends the CORE-001 self-served
  website + schedule surface (not a forked site).

**AC-OB-009 (REQ-OB-009).**
- A listener feedback submission POSTs to the brain's feedback endpoint and is ingested
  as a listener signal feeding the existing CORE-001 listener-signals contract
  (REQ-D-008) that OPS-004 consumes (Groups OD/OF).
- The AI may read the feedback and act on it autonomously (curation/show ideas/
  direction) with no human-in-the-loop; nothing forces it to act on any given item.
- [HARD] No code path treats feedback volume/sentiment as an engagement/appeal/
  popularity score to maximize, and no path panders or chases popularity in response to
  feedback (consistent with REQ-OF-004 / NFR-O-7 and CORE-001 REQ-D-008's anti-goal).
- The POST body is validated/sanitized as untrusted input (CORE-001 external-input
  discipline); a malformed/abusive submission is rejected/handled and does not crash
  the daemon or block the stream.

**AC-OB-010 (REQ-OB-010).**
- A persona retirement transitions active -> retiring -> retired, recording
  `persona_retiring` / `persona_retired` events (idempotent IDs) on the REQ-OD-007 ledger,
  decided on the measured-change cadence (Tier 1, REQ-OD-010), never for appeal/reach.
- A documented editorial reason is REQUIRED: a retirement attempt lacking one is REJECTED by
  the REQ-OD-006 canary (verified).
- The persona's charter (REQ-PR-006), PI card (REQ-PI-001), and taste profile (REQ-PL-004) are
  ARCHIVED (status=retired), NEVER deleted (REQ-OD-009 data-only); they remain readable after
  retirement.
- The news anchor (REQ-PI-005) cannot be retired by this path (exempt by construction).

**AC-OB-011 (REQ-OB-011).**
- A persona launch transitions created -> active only AFTER, BEFORE first air: (a) the
  PROGRAMMING-007 REQ-PR-008 growth gate passes; (b) a full REQ-PI-001 identity contract is
  authored; and (c) the REQ-PI-004 distinctness canary passes (verified: a launch missing any
  of the three does not air).
- The launch binds a NEW permanent voice drawn from the UNUSED pool (correct EN/Faroese roster
  per REQ-PR-003), 1:1 and immutable; `persona_launched` is recorded on the ledger; host caps
  (REQ-OB-003 / CORE-001 REQ-B-011) hold.
- Launch is a Tier-1 identity change (REQ-OD-010).

**AC-OB-012 (REQ-OB-012).**
- A show discontinue transitions it live -> discontinued -> relaunched, inventing the successor
  via REQ-OB-001 and restoring the clock cleanly via the REQ-OB-005 override-and-restore
  discipline; `show_discontinued` / `show_relaunched` events are recorded on the ledger.
- The grid mutation that places the successor routes through REQ-OA-015 -> ORCH-005
  REQ-RA-001(g) -> CORE-001 REQ-B-003 (no new store); the transition is subject to the
  always-staffed invariant (AC-OB-014) and is a Tier-1 change (REQ-OD-010).

**AC-OB-013 (REQ-OB-013) [HARD].**
- [HARD] A retired persona's frozen 1:1 voiceID is NEVER re-bound to a different identity
  (verified: a launch cannot select a quarantined voice for a new persona within the cooldown).
- The quarantined voice is re-issuable only as a brand-new persona after the REQ-OD-010 Tier-1
  cooldown; a launch draws a NEW unused voice from the pool.
- [HARD] If the voice pool is EXHAUSTED, the launch is REJECTED (no voice reuse) — continuity
  wins (verified by forcing pool exhaustion). Restates the REQ-PR-003 never-reused invariant.

**AC-OB-014 (REQ-OB-014) [HARD].**
- [HARD] A lifecycle transition (retire/quit/leave/discontinue) does NOT commit unless, at
  commit, every slot the departing persona hosted is already (re)bound to a present eligible
  successor (reassign, REQ-OA-015) OR the successor is pre-staged (relaunch, REQ-OB-012).
- [HARD] No observer — the queue filler (CORE-001 REQ-B-005), the website (CORE-001 REQ-B-002 /
  REQ-OB-007), or playout — ever reads a scheduled block naming a retired/absent persona
  (verified: attempt to retire a persona that owns slots; the published schedule always names a
  valid present persona for EVERY 24h block, extending AC-B-002/AC-B-003 from time-coverage to
  host-availability; no intermediate hostless/retired-named state is observable).
- The transition is a single atomic swap (modeled on CORE-001 REQ-E-003 atomic-publish).
- [HARD] REJECTION RULE: if no eligible successor can be bound (voice pool exhausted, host caps
  would be violated, no distinct territory), the transition is REJECTED, the persona STAYS ON
  AIR, and the rejected transition is logged; a hostless slot is never produced (verified).
- News anchor (REQ-PI-005) is exempt — it is not a curator slot.

### Group OC — Research-Driven Show Prep

**AC-OC-001 (REQ-OC-001).**
- Mode A (minimal prompt, tools OFF, batched) handles the frequent next-track/imaging
  path; Mode B (web tools ON) handles occasional research.
- [HARD] The frequent path uses Mode A; Mode B is reserved for occasional research
  (verified from call logs: tools-off on the hot path).

**AC-OC-002 (REQ-OC-002).**
- A themed-show decision triggers Mode-B research producing a show plan: tracklist
  (classics + deep cuts) + per-segment talking points/history/cultural context.
- The theme and treatment are AI-authored; no theme list is prescribed.

**AC-OC-003 (REQ-OC-003).**
- A show-prep run yields a structured show plan binding the tracklist to per-segment
  talking points/facts, consumed by the talk layer + scheduler.

**AC-OC-004 (REQ-OC-004).**
- Show prep incorporates musical/cultural/historical depth (genre origins, eras,
  artist significance, the role of music in society) drawn from the playbook
  dimension.

**AC-OC-005 (REQ-OC-005).**
- [HARD] Factual claims in show prep/banter are grounded in verified knowledge or
  fetched Mode-B research; uncertain claims are hedged or omitted, not invented.
- Generated copy is logged so fabrication can be detected after the fact.

**AC-OC-006 (REQ-OC-006).**
- [HARD] The system's own recent episodes/segments/scripts are NOT passed to the LLM as
  examples or style references (verified from the generation prompts: no prior-output
  exemplars in context).
- Recent output IS used as a topic/repeat avoid-list (verified: recently played/said
  items are suppressed from re-selection), preventing self-imitation across show-prep,
  talk scripts, and the self-learning loop.

### Group OD — Self-Learning Playbook

**AC-OD-001 (REQ-OD-001).**
- A persistent, queryable playbook exists capturing radio-craft learnings; it survives
  daemon restarts and requires no human authoring.

**AC-OD-002 (REQ-OD-002).**
- On first init, the playbook is seeded from research.md (operations taxonomy +
  reference-station patterns) and is non-empty.
- P3 Dans / P3 Mix are named as references for the runtime loop to study (not covered
  by the plan-time strands).

**AC-OD-003 (REQ-OD-003).**
- On event/self-scheduled cadence, the AI researches radio craft and distills new/
  updated playbook entries 24/7 with no human input.
- Updates are logged.

**AC-OD-004 (REQ-OD-004).**
- The playbook is passed as context to the PD, show-prep, imaging-copy, and newscast
  generation (verified from the prompts/logs).

**AC-OD-005 (REQ-OD-005).**
- The playbook contains first-class music-history/cultural-context and
  newscasting-craft dimensions, both learned (REQ-OD-003) and applied (REQ-OD-004,
  REQ-OC-004, Group OG).

**AC-OD-006 (REQ-OD-006).**
- [HARD] Identity-affecting changes (acted-on playbook rules, format defaults,
  personas, segment roster) are applied under a bounded change rate with a cooldown
  (config-tunable); rapid repeated changes are throttled.
- A proposed change is canary-checked against recent programming and rejected if it
  regresses; contradictions with existing applied rules are reconciled deliberately
  (recorded), never silently churned.
- No human approval is required (human is out of loop); the rails are self-imposed
  stability, verified by forcing many proposed changes and observing throttling.

**AC-OD-007 (REQ-OD-007).**
- [HARD] Playbook memory is an append-only event ledger with event types incl.
  listener_message, decision, listener_reaction, diary_entry, active_threads; each event
  carries an idempotent ID.
- Replaying/retrying an event with the same ID does not create a duplicate (verified by
  re-appending the same event ID); history is never overwritten — corrections are new
  events.

**AC-OD-008 (REQ-OD-008).**
- At the end of a director cycle, a diary entry is appended to the ledger (REQ-OD-007).
- On the next run / after a restart, the director reads its prior diary and continues
  its editorial through-line (verified: a running thread recorded in one cycle is
  referenced in a later cycle); diary content is AI-authored.

**AC-OD-009 (REQ-OD-009) [HARD].**
- [HARD] The autonomous operator's editorial self-expansion (topic banks Group OX,
  ledger/diary threads REQ-OD-007/008, intent cards, voice-card EVOLVABLE layer,
  taste/persona profiles) writes ONLY to persisted DATA stores; no normal-operation code
  path writes to source code, `radio.liq` / the Liquidsoap config, or container/deployment
  config (verified: an inspection/test confirms the autonomous loop's write targets are
  data paths only; an attempted code/config write by the self-expansion path is rejected/
  absent).
- This is the FROZEN-zone discipline (design-system constitution Section 2 + Frozen Guard
  Layer 1) applied to the running station; it references the per-persona Frozen Guard
  (PROGRAMMING-007 Group PI) without re-owning it.
- It complements REQ-OD-006: OD-006 bounds how FAST editorial data changes; OD-009 bounds
  WHAT may be written to (data only, never code/config). The HUMAN developer's tool/code
  changes are out of scope (out-of-loop by design).

**AC-OD-010 (REQ-OD-010) [HARD].**
- [HARD] The measured-change budget is partitioned into ordered tiers: Tier 1 (rarest) =
  identity/existence (persona retire/launch REQ-OB-010/011, show discontinue/relaunch
  REQ-OB-012, voice-bearing swap); Tier 2 = structural (format-clock defaults, dayparting,
  segment-type/segment roster REQ-OB-004 / REQ-OY-002, persona REASSIGN REQ-OA-015); Tier 3 =
  evolvable drift (voice-card EVOLVABLE wording, taste-profile REQ-PL-004, register colour).
- [HARD] A Tier-1 identity transition is throttled HARDER than an evolvable change — its rate
  cap is tighter and its cooldown longer, strictly below the evolvable-drift budget (verified
  by forcing many of each class and observing the identity tier throttle at a lower threshold).
- The REQ-OD-006 canary REJECTS an identity transition lacking a documented editorial gap; the
  rationale "consistency is a listener obligation" is recorded. Tier caps/cooldowns are TUNABLE
  config; that Tier 1 is strictly the rarest is the FIXED rail. It reuses the existing
  rate-limiter/cooldown/canary machinery (no new safety mechanism) and admits no
  appeal/popularity input (REQ-OF-004 / NFR-O-7). Complementary to the PROGRAMMING-007 PI
  two-zone model (who-while-it-exists vs whether-it-exists).

### Group OE — Self-Produced Imaging & Jingles

**AC-OE-001 (REQ-OE-001).**
- An imaging decision yields a structured-JSON brief with the listed fields; the
  taxonomy/length rules are TUNABLE context, not fixed copy.

**AC-OE-002 (REQ-OE-002).**
- [HARD] In a produced wet clip, the VOICE keys the music via sidechaincompress (NOT
  the reverse), with fades and optional stingers, and the voice stays at full level
  after `amix` (verified by a level check on the first produced clip).
- Dry pieces skip the bed.
- This ducking is offline clip-baking and does not touch the live stream.

**AC-OE-003 (REQ-OE-003).**
- Stingers/sweeps/risers/beeps/news-pips are synthesized via sox/ffmpeg with zero
  external assets; output is public-domain-by-construction.

**AC-OE-004 (REQ-OE-004).**
- Musical beds beyond synthesis come from Stable Audio 3 (CPU, config-gated,
  pre-rendered/cached) or first-party CC0; the AI chooses the layer per piece.
- Generation never runs in the playout path.

**AC-OE-005 (REQ-OE-005).**
- [HARD] Every produced imaging clip is two-pass loudnorm'd to -16 LUFS / -1.5 dBTP;
  measured loudness matches the song catalog (verified post-process so imaging does
  not jump out).

**AC-OE-006 (REQ-OE-006).**
- A normalized clip is encoded to the stream codec at the catalog sample-rate/channels
  and registered in CLIPS_DIR with a metadata sidecar.

**AC-OE-007 (REQ-OE-007).**
- A due imaging slot returns `NextItem(kind="imaging")`; `/api/next` serves/commits it
  identically to a song with no Liquidsoap change.

**AC-OE-008 (REQ-OE-008).**
- [HARD] A station-ID slot is reserved at/near every top-of-hour and reliably filled.
- The ID does not claim a real broadcast frequency the station does not hold.

**AC-OE-009 (REQ-OE-009).**
- [HARD] Every served imaging/news/song item is a single clean single-track request;
  no malformed/multi-track item is returned (no post-jingle next-song stall).

**AC-OE-010 (REQ-OE-010).**
- [HARD] Only self-generated (procedural / Stable Audio 3) or strictly first-party CC0
  beds are auto-published as on-air imaging.
- A per-clip license ledger records source/license/attribution/AI-generated/perf-rights
  status; murkier-rights beds are quarantined and not aired unattended.

**AC-OE-011 (REQ-OE-011).**
- Most IDs/liners default to dry; wet/showpiece production is occasional (verified from
  production logs); this is a TUNABLE default the AI may evolve.

**AC-OE-012 (REQ-OE-012).**
- [HARD] A ready buffer of N-ahead pre-rendered talk/imaging clips exists; every
  `/api/next` PULL is served from the buffer and never waits on a synchronous TTS/LLM
  render (verified: forcing slow generation does not delay a pull).
- Heavy generators are serialized — multiple TTS/LLM renders do not run concurrently
  (verified: a single generation worker/queue, bounding RAM).
- Buffer depth N and serialization are TUNABLE config.

### Group OF — Liveliness & Quality

**AC-OF-001 (REQ-OF-001).**
- [HARD] Over a representative observation window the station exhibits character:
  personas, themed shows, talk/commentary/recurring bits, a point of view — it is not
  a character-less shuffle.
- A station with NO programming/character (only an undifferentiated track shuffle) is
  a defect.

**AC-OF-002 (REQ-OF-002).**
- Banter draws on show-prep + playbook material and varies structure (recent-phrase
  memory); shallow/generic/repetitive filler is not produced.

**AC-OF-003 (REQ-OF-003).**
- An AI-scheduled music-only stretch is treated as valid programming; no minimum talk
  density is enforced.
- The absence of talk in an AI-planned music block is NOT a defect; only the absence of
  any character across the station is (AC-OF-001).

**AC-OF-004 (REQ-OF-004).**
- [HARD] No talk/banter/imaging/news content is partisan or political; music's
  cultural/societal significance is the lens, never partisan commentary.
- No code path generates partisan/political content; generated copy/news is logged for
  after-the-fact detection.

**AC-OF-005 (REQ-OF-005).**
- [HARD] Generated host/talk scripts contain none of: "stay tuned" / "up next" /
  "coming up" filler, manufactured morning-DJ enthusiasm, "let's dive in"-style
  openers, emoji or fourth-wall narration, or gratuitous "I am an AI" announcements
  (verified by scanning generated copy against the anti-slop checklist).
- Scripts read as specific, human-curatorial speech, not generic LLM filler.

**AC-OF-006 (REQ-OF-006).**
- [HARD] A script below its word-target minimum or failing the anti-slop discipline
  (REQ-OF-005) is rejected and regenerated; a script that cannot pass within the bounded
  attempt count is dropped (graceful-skip) and never blocks the stream.
- Word targets and the attempt bound are TUNABLE config; rejections/regenerations are
  logged.

### Group OG — News & Newscasting

**AC-OG-001 (REQ-OG-001).**
- The AI decides news cadence/format/segments/length at its own discretion; no fixed
  news schedule/format is hardcoded.
- Regular scheduled newscasting is present.

**AC-OG-002 (REQ-OG-002).**
- The AI maintains its own persistent, evolving trusted-source list with no human
  input; additions/removals are logged.

**AC-OG-003 (REQ-OG-003).**
- Aggregation prefers official feeds/APIs (RSS/Atom, news APIs) over scraping; scraping
  is used only where the source's terms permit. (This feeds/APIs-first preference is the
  testable definition of efficient aggregation — no vague "efficiently" obligation.)
- Aggregation runs off the playout path and never blocks the stream.

**AC-OG-004 (REQ-OG-004).**
- Newscast content reflects what trusted sources report (factual).

**AC-OG-005 (REQ-OG-005).**
- [HARD] Every aired newscast item is grounded in fetched source content and attributed
  to its source(s); ungroundable items are dropped, not invented.
- News stays factual and apolitical (AC-OF-004).

**AC-OG-006 (REQ-OG-006).**
- The AI may prioritize the Faroese angle (kvf.fo/dimma.fo + Sweden SVT/SR-class +
  intl Reuters/AP-class).
- Faroese-language news is voiced in Faroese via teldutala.fo (Hanna/Hanus); other
  languages via Kokoro/Piper; routing per VOICE-002 Group V-D.

**AC-OG-007 (REQ-OG-007).**
- A due news slot produces a newscast via the imaging/TTS pipeline (optional procedural
  pips → TTS read → loudnorm to the shared target) and serves it as
  `NextItem(kind="news")` with no Liquidsoap change.

**AC-OG-008 (REQ-OG-008).**
- When the AI judges an event significant, a breaking-news item may be inserted out of
  cadence at a safe boundary (end of current song, not mid-vocal) and the clock resumes
  cleanly.
- This is optional behavior the AI may choose; it never silences the stream.

**AC-OG-009 (REQ-OG-009).**
- [HARD] Forcing news aggregation/research/production/TTS to fail or time out results
  in the news slot being skipped (or a music fallback) with no stream block/stall/
  silence; the skip is logged.

### Group OH — Library Management & Acquisition Policy

**AC-OH-001 (REQ-OH-001).**
- As the catalog grows, selections increasingly come from the existing library;
  acquisition does not fire on every selection (verified from logs: selections >>
  acquisitions).
- The reuse-vs-acquire balance is the AI's call.

**AC-OH-002 (REQ-OH-002).**
- [HARD] Acquisition tries slskd first; yt-dlp is used only when slskd cannot supply the
  track (verified from acquisition logs: yt-dlp invoked only after slskd fails).

**AC-OH-003 (REQ-OH-003).**
- Imported files are sorted into a clean managed folder structure (e.g. artist/album or
  genre), not left in slskd's raw download dirs.

**AC-OH-004 (REQ-OH-004).**
- [HARD] Free disk is monitored; when low, library size is capped and/or least-valuable
  tracks (least-played, lower-quality duplicates) are evicted; a low-space condition is
  surfaced in health/status. The disk never fills to failure (verified by forcing a
  low-space condition).

**AC-OH-005 (REQ-OH-005).**
- When the AI wants music unobtainable via slskd/yt-dlp but available on Bandcamp, a
  user-facing "buy this" recommendation is emitted via the recommendation channel.
- No autonomous purchase/payment occurs.

**AC-OH-006 (REQ-OH-006).**
- [HARD] Acquisition stats are tracked — current library size and pending-download/
  queued count — and exposed in health/status (NFR-O-6).
- [HARD] The download queue is bounded to a configured maximum; new acquisition is
  throttled/deferred based on library size, free disk, and queue depth (verified: at
  the queue bound or low disk, new acquisition does not pile on).
- The system never amasses a massive uncontrolled queue (verified by forcing many
  acquisition intents and confirming the queue stays bounded); bound/thresholds are
  TUNABLE and tie to REQ-OH-001 / REQ-OH-004.

### Group OX — Topic-Bank Inventory

**AC-OX-001 (REQ-OX-001) [HARD].**
- [HARD] A persisted topic-bank exists recording, per topic, at least: a normalized topic
  identity, a persona/show key (the owning show/host, or `station` for global topics,
  REQ-OX-006), generator-category (PROGRAMMING-007 REQ-PC-006), aired_at (null until
  aired), use-count, freshness/recency, rotation state, discovery source, and editorial
  tags.
- [HARD] It is implemented as a topic-specific VIEW / event-type over the EXISTING
  REQ-OD-007 append-only ledger (`topic_discovered` / `topic_aired` / `topic_refreshed` /
  `topic_skipped`), NOT a forked datastore (verified: a grep confirms no new topic store;
  topic events live in the OPS-004 ledger store).
- Each topic event carries an idempotent ID; replaying the same event ID does not
  duplicate a topic (verified by re-appending); the bank persists across daemon restarts.

**AC-OX-002 (REQ-OX-002).**
- An invented theme (REQ-OC-002) is persisted to the topic-bank as a `topic_discovered`
  event (and `topic_aired` when it airs), tagged with the relevant persona/show key
  (`station` when not show-scoped).
- The topic-bank is consulted as the anti-repetition AVOID-LIST, scoped per-persona/per-show
  (REQ-OX-006), when inventing the next theme (verified: a theme recently aired by a host is
  suppressed from re-selection FOR THAT HOST by own-history recency).
- [HARD] CROSS-PERSONA DEFAULT: a theme recently aired by a DIFFERENT persona is NOT re-airable
  wholesale by another host — it is reference-only (verified: host B cannot re-air host A's exact
  recent topic as a fresh wholesale topic; B may only make an attributed, additive, own-voice
  light reference to it, per the ORCH-005 unified-dedup reference-vs-duplication rule REQ-RW-006
  that OX-006 defers to). This extends the REQ-OC-006 no-self-imitation discipline from
  talk/scripts to themes AND prevents cross-host topic copying.
- A lightweight topic-suitability checklist lint (relevance / respect / ethos-alignment)
  runs at persistence; it is a quick pre-prep guard, not a fork of the post-generation
  script gates (REQ-OF-005/006) or PROGRAMMING-007 Group PG.

**AC-OX-003 (REQ-OX-003) [HARD].**
- [HARD] Theme/segment selection prefers fresh (not-recently-aired) topics and under-used
  generator-categories, ages out recently-aired themes, and rotates across
  generator-categories — within the relevant persona/show scope where one applies
  (REQ-OX-006), else station-globally (verified: a theme aired within its recency window
  for that scope is not re-aired; consecutive selections rotate categories rather than
  looping the same handful).
- The recency window and rotation balance are TUNABLE config; that recently-aired themes
  are not looped is the FIXED rail.
- No appeal/popularity ranking is applied — ranking keys only on freshness/recency/
  use-count/category rotation (consistent with REQ-OF-004 / NFR-O-7).

**AC-OX-004 (REQ-OX-004).**
- A calendar/anniversary/seasonal opportunity or a KNOWLEDGE-008 artist/release fact
  surfaces a candidate theme that is added to the topic-bank by a self-scheduled
  topic-discovery refresh job.
- The refresh job is BOUNDED (like REQ-OH-006) so the bank grows under control; cadence
  and discovery bound are TUNABLE config.
- The job references KNOWLEDGE-008 Group KR (research) + Group KF (freshness) and does NOT
  re-own research or define a new freshness framework (verified: no duplicated research/
  freshness logic in the OX module).

**AC-OX-005 (REQ-OX-005) [HARD].**
- [HARD] The topic-bank is queryable by category/recency/locale/persona-show and is passed
  as context to the program director and show-prep (extending REQ-OD-004) — verified from
  the prompts/logs that the inventory shapes the next plan.
- [HARD] Topic-bank events are surfaced via the EXISTING structured logs / health surface
  (NFR-O-6 / CORE-001 health/status); no new observability subsystem is added.

**AC-OX-006 (REQ-OX-006).**
- Topic entries carry a persona/show key; a show with a host persona has its OWN
  persona-scoped slice of the bank (verified: topics generated under host A are keyed to A;
  station-global topics are keyed `station`).
- Theme invention applies that host's persona + show identity when generating topics into
  its slice (verified: the generation prompt/context carries the persona/show identity).
- The anti-repetition avoid-list (REQ-OX-002) and freshness/rotation (REQ-OX-003) operate
  per-persona/per-show on OWN history (verified: a topic aired by host A is on A's own
  avoid-list by own-history recency).
- [HARD] CROSS-PERSONA DEFAULT (inverted dedup-bug fix): a topic recently aired by a DIFFERENT
  persona is NOT simply "fresh" for another host. Verified: host B may NOT re-air host A's exact
  recent topic as a fresh wholesale topic; B may only make an attributed, additive, own-voice
  LIGHT reference to it (depth director-gated), per the ORCH-005 unified-dedup
  reference-vs-duplication rule (REQ-RW-006) that OX-006 defers to. Distinct hosts thus keep
  distinct topical fingerprints (no convergence AND no wholesale cross-host copying) — via BOTH
  own-history recency and the cross-persona reference-only default.
- [HARD] It remains a VIEW over the one REQ-OD-007 ledger — the persona/show key is a FIELD
  on the topic events, NOT a new store (verified: a grep confirms no per-persona topic
  store). Persona definitions are owned by PROGRAMMING-007 (referenced, not re-owned); the
  cross-surface reference-vs-duplication rule is owned by ORCH-005 (REQ-RW-006, referenced).

### Group OY — Segment-Type Registry & Per-Segment Production Pipeline

**AC-OY-001 (REQ-OY-001) [HARD].**
- [HARD] A persisted segment-type registry exists recording, per AI-defined type, at least: a
  normalized type identity, a kind discriminator (talk-long vs short-form-pointer), daypart/
  persona fit, recipe pointers (research/write/fact-check-level/assemble/schedule),
  input-source bindings, rotation/freshness state, and editorial tags.
- [HARD] It is implemented as a segment-type-specific VIEW / event-type over the EXISTING
  REQ-OD-007 append-only ledger (`segment_type_created` / `_extended` / `_rewritten` /
  `_retired` / `_aired`), NOT a forked datastore (verified: a grep confirms no new segment-type
  store; type events live in the OPS-004 ledger store).
- Each type event carries an idempotent ID; replaying the same event ID does not duplicate a
  type (verified by re-appending); the registry persists across daemon restarts. (Upgrades
  REQ-OB-004's ephemeral authority; structural twin of AC-OX-001.)

**AC-OY-002 (REQ-OY-002) [HARD].**
- The AI can create / extend / rewrite / retire a segment type autonomously (human-out-of-loop),
  each recorded as the matching `segment_type_*` event on the ledger.
- [HARD] Every such operation is BOUNDED by the REQ-OD-006 measured-change rails (rate-limit +
  cooldown + canary + contradiction detection) at the Tier-2 structural cadence (REQ-OD-010)
  (verified: forcing many type-edits throttles them; a contradicting type/recipe is reconciled,
  recorded, never silently churned).
- Extends REQ-OD-006's named "recurring-segment roster" coverage to the persisted registry.

**AC-OY-003 (REQ-OY-003) [HARD].**
- [HARD] A type edit can NEVER weaken or remove a FROZEN invariant: the fact contract
  (REQ-PG-001/002 + KNOWLEDGE-008 REQ-KS-006/KF-003), never-ship-a-FAIL (REQ-PG-005), apolitical
  (REQ-OF-004), fictional-persona ethics (REQ-PT-005/006), no-self-imitation (REQ-OC-006),
  no-pandering (REQ-OF-004/NFR-O-7, CALLIN-003 REQ-CF-003), host caps (REQ-OB-003), and the
  news_analysis type's NEWS-ANCHOR factual stance (fact-check-level + apolitical framing)
  (verified: an attempt to lower a type's fact-check-level, relax consensus/freshness, or make a
  type partisan is rejected).
- EVOLVABLE (allowed within the rails): skeleton shape, length targets, daypart/persona fit
  (except the news-anchor stance), recipe-pointer selection, rotation/freshness windows,
  editorial tags, and the type roster (add/retire). Mirrors the PROGRAMMING-007 Group PI FROZEN
  model (referenced, not re-owned).

**AC-OY-004 (REQ-OY-004).**
- On first init, the registry is SEEDED with the five starter types deep_dive, news_analysis,
  story, listener_mailbag, music_essay, each `segment_type_created` with a skeleton, length
  default, input bindings, fact-check-level, and persona fit; the registry is non-empty.
- news_analysis is bound to the news-anchor stance; the other four to music personas. The seed
  editorial SUBSTANCE lives in PROGRAMMING-007 (REQ-PC-008 seam); the registry stores definitions
  + pointers. The brain may add a sixth type later under the rails (AC-OY-002/003).

**AC-OY-005 (REQ-OY-005) [HARD].**
- A decision to produce a segment instance runs a first-class FLOW keyed to the type's recipe
  pointers: (a) RESEARCH via KNOWLEDGE-008 Group KR + OPS-004 Group OC + Group OX topic-bank
  (+ ORCH-005 Group RN for news_analysis, CALLIN-003 Group CF for listener_mailbag); (b) WRITE
  via PROGRAMMING-007 Group PC/PS/PV under the closed-world fact contract REQ-PG-001; (c)
  FACT-CHECK via REQ-PG-005 backed by KNOWLEDGE-008 REQ-KS-006/KF-003/KI-001; (d) ASSEMBLE via
  VOICE-002 TTS, or IMAGING-010 Group IH/IP when a bed is wanted; (e) SCHEDULE via ORCH-005
  Group RA + OPS-004 Group OA.
- Short-form transitions (station ID / open / close) are NOT produced here — they are
  scheduled-in as existing OPS-004 Group OE + IMAGING-010 Group IL/IS furniture (verified).
- [HARD] The flow is pure composition — no new research engine, gate, playout kind, or store
  (verified: a grep confirms none) — runs off the playout path (REQ-OE-012 buffer), and records
  its stages as ledger events (`segment_type_aired` + ORCH-005 REQ-RA-003 decision/diary) so the
  production is durable and auditable.

**AC-OY-006 (REQ-OY-006) [HARD].**
- [HARD] A produced segment whose script FAILS the fact-check gate (REQ-PG-005) is NOT aired: on
  FAIL it regenerates ONCE, and on a SECOND FAIL it is SKIPPED (talk less, never ship a wrong
  fact); the skip is logged and never blocks/silences the stream (consistent with REQ-OF-006 /
  REQ-OA-008).
- The per-type fact-check-LEVEL selects gate intensity; ALL levels are never-ship-a-FAIL.
- The line is verified: a year/label/producer/personnel token absent from the contract = FAIL;
  perceptual/taste lines grounded in the audible (or ANALYSIS-006 profile) and the persona's POV
  pass through; a listener's quoted text (listener_mailbag) is attributed/sanitized, not adopted
  as the station's fact.

**AC-OY-007 (REQ-OY-007) [HARD].**
- [HARD] The registry is queryable by kind/daypart/persona/category/recency and is passed as
  context to the program director and show-prep (extending REQ-OD-004 / REQ-OX-005) — verified
  from the prompts/logs that the format inventory shapes the next plan.
- A freshness/rotation policy over type use (mirroring REQ-OX-003) makes formats rotate rather
  than loop the same handful (verified).
- [HARD] Registry events are surfaced via the EXISTING structured logs / health surface
  (NFR-O-6 / CORE-001 health/status); no new observability subsystem and NO appeal/popularity
  ranking (selection keys only on freshness/recency/use-count/category rotation).

### Non-Functional

**AC-NFR-O-1 (NFR-O-1).** The brain uses Claude via the MAX subscription through
`claude-agent-sdk`; `ANTHROPIC_API_KEY` is verified UNSET at startup (and a set key is
rejected/flagged because it bills credits and fails); auth uses the mounted `~/.claude`
OAuth with auto-refresh.

**AC-NFR-O-2 (NFR-O-2).** The frequent path uses tools-off Mode A; web-tools Mode B is
occasional; calls are batched; the LLM loop runs async off the playout path; quota
pressure does not stall the stream (deterministic fallback).

**AC-NFR-O-3 (NFR-O-3).** Songs, imaging, talk, and news all measure at -16 LUFS /
-1.5 dBTP, sourced from one shared config constant (shared with CORE-001 ingest +
VOICE-002 talk).

**AC-NFR-O-4 (NFR-O-4).** Forcing any imaging/news/show-prep/playbook/housekeeping
operation to fail logs and is skipped without crashing the director loop or the daemon;
no OPS failure silences the stream.

**AC-NFR-O-5 (NFR-O-5).** The system runs continuously 24/7; a brief interruption on
restart is acceptable; no zero-gap failover machinery is built.

**AC-NFR-O-6 (NFR-O-6).** Structured logs exist for PD decisions, separation
relaxations, imaging production stages, playbook updates, news aggregation/grounding/
attribution, topic-bank events (topic_discovered / topic_aired / topic_refreshed /
topic_skipped, Group OX), segment-type registry events (segment_type_created / _extended /
_rewritten / _retired / _aired, Group OY) and per-segment production stages
(research/write/fact-check/assemble/schedule, REQ-OY-005), persona/show lifecycle
transitions (persona_retiring / persona_retired / persona_launched / show_discontinued /
show_relaunched, incl. rejected transitions, REQ-OB-010..014) and schedule-grid CRUD edits
(REQ-OA-015), library housekeeping/eviction, and fallbacks, surfaced via the CORE-001
health/status surface.

**AC-NFR-O-7 (NFR-O-7).** No code path generates partisan/political content or
fabricated facts/news; generated copy/news is logged for after-the-fact detection.

**AC-NFR-O-8 (NFR-O-8).** Deferred items (Section 13) are not partially built; the
implementation is the smallest design delivering the in-scope groups on the confirmed
stack.

**AC-NFR-O-9 (NFR-O-9).** All scheduling, dayparting, clock-slot resolution, and
time/date references use the configured local timezone (default `Atlantic/Faroe`,
Tórshavn) with correct DST (WET ↔ WEST), not UTC/server-local. Verified: dayparts and
on-air time/date stay correct across a DST transition; a misconfigured/wrong timezone
is detectable and does not silently misalign dayparts.

**AC-NFR-O-10 (NFR-O-10).** Talk/imaging/news generation is decoupled from the playout
pull path: every `/api/next` PULL is served from the pre-stocked ready buffer
(REQ-OE-012) and never waits on a synchronous render. Verified: forcing slow/failed
generation causes no audio under-run/stall; heavy generators are serialized (no
concurrent TTS/LLM renders), bounding RAM.

**AC-NFR-O-11 (NFR-O-11).** No track-to-track transition is a sharp hard cut by default;
the baseline is at minimum a gentle crossfade/fade-out (REQ-OA-014). Verified: sampling
transitions shows no hard cut-offs; DJ-style beatmatch/EQ mixing applies only to
club/dance shows by the AI's context choice while the no-sharp-cutoff floor holds
everywhere.

---

## Section B — Given-When-Then scenarios (load-bearing requirements)

**Scenario 1 — No-repeat / least-recently-played rotation (REQ-OA-003 soft / OA-003a
hard rail / OA-003b relaxation).**
- GIVEN a library with several eligible tracks and a configured no-repeat window
- WHEN the program director selects the next song repeatedly over the window
- THEN (OA-003a hard rail) no track recurs within its no-repeat window and artist
  spacing holds; (OA-003a) a long-unplayed eligible track is preferred over a
  just-played one; (OA-003 soft layer) soft separations score the legal candidates; and
  (OA-003b) if no candidate satisfies the soft rules the soft window widens / an
  adjacent category is borrowed and the relaxation is logged — the hard rail is never
  relaxed and the queue never stalls or repeats illegally.

**Scenario 2 — Never a single point of silence (REQ-OA-008, NFR-O-4/5).**
- GIVEN the stream is live
- WHEN an imaging/news render fails, the clip pool is empty, or the PD decision times
  out
- THEN the brain returns a music track or a cached evergreen ID, the stream stays
  audible, and the failure + fallback are logged; no OPS path is the sole cause of
  silence.

**Scenario 3 — Imaging ducking direction + loudness match (REQ-OE-002/005).**
- GIVEN an AI imaging brief for a wet sweeper with a music bed
- WHEN the pipeline produces the clip
- THEN the voice keys the music (music ducks under voice, not the reverse), the voice
  is at full level after `amix`, and the clip measures -16 LUFS / -1.5 dBTP matching the
  song catalog — it does not jump out on air.

**Scenario 4 — Two LLM modes + quota discipline (REQ-OC-001, NFR-O-1/2).**
- GIVEN the station is running on the MAX subscription with `ANTHROPIC_API_KEY` unset
- WHEN the frequent next-track path runs and, occasionally, a show-prep run fires
- THEN next-track uses tools-off Mode A (batched), show-prep uses web-tools Mode B
  occasionally, calls run async off the playout path, and quota pressure triggers the
  deterministic fallback rather than stalling the stream.

**Scenario 5 — Self-learning playbook + measured self-change (REQ-OD-003/006).**
- GIVEN a seeded playbook
- WHEN the runtime loop produces many proposed identity-affecting changes in a short
  span
- THEN learning continues freely but applied changes are throttled by the rate
  limiter + cooldown, each applied change passes a canary regression check,
  contradictions are reconciled (recorded) not silently churned, and the station's
  identity/format stays consistent — all with no human approval.

**Scenario 6 — Research-driven, grounded, apolitical show prep (REQ-OC-002/005,
REQ-OF-004).**
- GIVEN the AI invents a "soul night" theme
- WHEN it runs Mode-B research
- THEN it produces a tracklist (classics + deep cuts) with per-segment talking points,
  artist/label/song history and cultural/societal context, all grounded in fetched/
  verified facts (uncertain claims hedged or omitted) and free of partisan/political
  commentary.

**Scenario 7 — Factual newscasting with the Faroese angle (REQ-OG-004/005/006/007).**
- GIVEN the AI maintains a trusted-source list including kvf.fo/dimma.fo (FO), Sweden,
  and international outlets
- WHEN a news slot is due
- THEN the newscast is grounded in and attributed to fetched trusted sources, factual
  and apolitical, ungroundable items dropped; Faroese-language items are voiced in
  Faroese via teldutala.fo and others via Kokoro/Piper; the read is loudnorm'd to the
  shared target and served as `kind="news"`.

**Scenario 8 — Liveliness without forcing talk (REQ-OF-001/003).**
- GIVEN the AI plans a long uninterrupted music block in an overnight daypart
- WHEN the block airs
- THEN the music-only stretch is valid programming (no minimum-talk defect), AND across
  the day the station still shows character (personas, themed shows, imaging, talk) so
  REQ-OF-001 holds.

**Scenario 9 — Library enrichment enables DJ-sets (REQ-OA-010/011/012).**
- GIVEN newly acquired tracks with garbled tags and no BPM/key/energy
- WHEN library enrichment runs off the playout path
- THEN tags are corrected/reconciled, genre/mood/BPM/key/energy/year are added, the
  catalog is queryable, and the PD can build a BPM/key-matched DJ-set and a genre night
  from it — without ever blocking the stream.

**Scenario 10 — Acquisition quality preference + disk safety (REQ-OH-002/004).**
- GIVEN free disk is approaching the configured low-space threshold and a track is
  wanted
- WHEN acquisition runs
- THEN slskd is tried first (FLAC/high bitrate) and yt-dlp only as a last resort, AND
  the disk-space manager caps the library / evicts least-valuable tracks and surfaces
  the low-space condition so the disk never fills to failure.

**Scenario 11 — Bandcamp purchase recommendation (REQ-OH-005).**
- GIVEN the AI wants a track it cannot get via slskd or yt-dlp/YouTube but finds it on
  Bandcamp
- WHEN it decides the track is worth having
- THEN it emits a user-facing "buy this" recommendation via the recommendation channel
  and makes no autonomous purchase.

**Scenario 12 — Self-cleared imaging gate (REQ-OE-010).**
- GIVEN a candidate music bed of uncertain license
- WHEN the imaging pipeline tries to use it for unattended on-air imaging
- THEN the self-cleared gate quarantines it (only procedural / Stable Audio 3 /
  first-party CC0 beds are auto-published), the license ledger records the decision,
  and the clip is not aired.

**Scenario 13 — Local Faroe time/date/location awareness (REQ-OA-009, NFR-O-9).**
- GIVEN the station is configured for Tórshavn / `Atlantic/Faroe` and the local clock
  crosses a daypart boundary (and, separately, a DST WET↔WEST transition)
- WHEN the program director resolves the schedule and produces time/date references
- THEN dayparts fire at the correct LOCAL Faroe wall-clock time (DST-correct, not UTC),
  the AI has weekday/weekend + season/holiday context to program from, and on-air
  time/date references (talk + news) and location presentation use local Faroe time /
  Tórshavn — with timezone/location configurable.

**Scenario 14 — Topic-bank as a view: anti-repetition + freshness/rotation
(REQ-OX-001/002/003/005).**
- GIVEN the AI has invented and aired several themes over time, each recorded in the
  topic-bank (normalized identity, generator-category, aired_at, use-count, freshness,
  rotation state) as a VIEW over the OPS-004 REQ-OD-007 ledger — not a forked store
- WHEN the AI invents the next theme and selects a theme/segment to air
- THEN (OX-002) the recently-aired themes are consulted as an anti-repetition avoid-list
  so the AI does not re-run them; (OX-003 hard rail) a theme aired within its recency
  window is not re-aired and generator-categories rotate rather than looping the same
  handful; (OX-001) the chosen theme's `topic_aired` event is appended idempotently to the
  ledger; (OX-005) the queryable bank shaped the plan and its events show in the health
  surface — and no appeal/popularity score was applied (freshness/recency/category only).

**Scenario 15 — Per-persona topic-bank + data-vs-code rail (REQ-OX-006, REQ-OD-009).**
- GIVEN two distinct host personas (A and B), each self-managing its own persona-scoped
  slice of the topic-bank (REQ-OX-006), and the autonomous operator continuously expanding
  its editorial data (topic banks, ledger/diary, intent cards, voice-card EVOLVABLE layer,
  taste/persona profiles)
- WHEN host A airs a theme, then host B plans its own show (and considers A's recent topic),
  and the self-expansion loop writes its updates
- THEN (OX-006) A's aired theme is on A's own avoid-list by own-history recency; AND [HARD]
  (OX-006 cross-persona default — the dedup-bug fix) host B may NOT re-air A's exact recent
  topic wholesale — B may only make an attributed, additive, own-voice LIGHT reference to it
  (per the ORCH-005 unified-dedup reference-vs-duplication rule REQ-RW-006 that OX-006 defers
  to), so the hosts keep distinct topical fingerprints (no convergence AND no wholesale
  cross-host copying) — and the persona/show key is a field on the one OD-007 ledger (no
  per-persona store); AND (OD-009 hard rail) every self-expansion write lands in a persisted
  DATA store, while NO normal-operation write touches source code, `radio.liq`, or critical
  runtime config (the FROZEN-zone discipline holds; verified by inspecting the autonomous
  loop's write targets).

**Scenario 16 — Segment-type registry + per-segment production pipeline with the fact-check
gate (REQ-OY-001/002/003/005/006).**
- GIVEN the registry is seeded with the five starter types as a VIEW over the OPS-004
  REQ-OD-007 ledger (not a forked store), and the AI decides to produce a deep_dive on an
  artist (and, separately, to extend a type's skeleton)
- WHEN the production flow runs and the type-extend is applied
- THEN (OY-005) the flow RESEARCHES (KNOWLEDGE-008 KR + OPS-004 OC + Group OX topic-bank),
  WRITES (PROGRAMMING-007 PC/PS/PV under the closed-world contract REQ-PG-001), FACT-CHECKS as
  an explicit GATE (REQ-PG-005 + KNOWLEDGE-008 KS-006/KF-003), ASSEMBLES (VOICE-002 TTS or
  IMAGING-010 IH/IP), and SCHEDULES (ORCH-005 RA + OPS-004 OA); (OY-006 hard rail) a script
  that fails the gate regenerates once then is SKIPPED — never aired with a wrong fact, never
  silencing the stream; (OY-002) the type-extend is recorded as a `segment_type_extended`
  event bounded by REQ-OD-006; (OY-003 hard rail) the edit cannot lower the type's
  fact-check-level or the news-anchor stance; and (OY-001) no new store, gate, research engine,
  or playout kind was created.

**Scenario 17 — Persona/show lifecycle: always-staffed + voice quarantine + rarity tier
(REQ-OB-010/011/013/014, REQ-OA-015, REQ-OD-010).**
- GIVEN a persona that hosts scheduled slots, a finite unused-voice pool, and the rarity
  tiering active (REQ-OD-010)
- WHEN the director retires that persona (for a documented editorial reason) and, separately,
  attempts a launch when the voice pool is exhausted
- THEN (OB-014 hard rail) the retirement does NOT commit until every orphaned slot is atomically
  (re)bound to a present eligible successor (reassign via REQ-OA-015, or relaunch) — no observer
  ever reads a hostless/retired-named block; if no successor can be bound the retirement is
  REJECTED and the persona stays on air; (OB-013 hard rail) the retired persona's frozen 1:1
  voice is quarantined (never re-bound to a different identity), and the pool-exhausted launch is
  REJECTED (no voice reuse); (OB-010) charter/PI-card/taste-profile are archived not deleted;
  (OD-010 hard rail) the retire/launch draw from the Tier-1 rarest budget, throttled harder than
  evolvable drift, with a reasonless transition rejected by the canary; AND the news anchor
  (REQ-PI-005) is untouched by all of the above.

**Scenario 18 — Off-schedule genre-family balance + smooth adjacency with the scheduled exemption
(REQ-OA-003d; CORE-001 REQ-D-002).**
- GIVEN the station is in the UNSCHEDULED (host-less) lane with a catalog spanning several
  genre-families, `is_unscheduled` = True, and the hard rails (REQ-OA-003a no-repeat/artist,
  REQ-OA-003c artist-frequency) producing the legal candidate set
- WHEN the program director selects successive next songs off-schedule, then later a scheduled
  curated single-genre show (e.g. a soul night, REQ-OB-006 association != 'unscheduled') goes live
- THEN (a) over the rolling window no genre-family exceeds `target_ceiling` absent a logged
  relaxation and families demonstrably rotate (deterministic, no RNG, penalty added to the LRP
  score over `genre_family_map`); (b) successive off-schedule picks show bounded energy/harmonic
  distance to the just-aired track via `library.adjacency` — jarring funk→black-metal jumps score
  worse — EXCEPT across a logged deliberate boundary (daypart / format-clock slot change /
  top-of-hour) where the adjacency penalty is suspended; AND [HARD] (c) once the curated show is
  active, NEITHER soft layer applies — the single-genre block plays unmodified with no
  taste/coherence/anti-drift check, satisfying CORE-001 REQ-D-002 [HARD] / AC-OA-004 (the same
  `is_unscheduled` predicate both activated the layers off-schedule and exempts them now); AND if a
  thin legal-and-balanced subset is ever empty the picker relaxes to the full legal set, plays one,
  and logs it (REQ-OA-003b, continuity wins) — the soft layers never stall the queue, never ban a
  track, and never override the hard rails; no new store and no Liquidsoap change.

The SPEC is implementation-complete when:

- [ ] Every requirement (REQ-OA-*, REQ-OB-*, REQ-OC-*, REQ-OD-*, REQ-OE-*, REQ-OF-*,
      REQ-OG-*, REQ-OH-*, REQ-OX-*, REQ-OY-*) and NFR (NFR-O-*) has its acceptance criteria
      met with evidence (test output, logs, or runtime observation).
- [ ] All 18 Given-When-Then scenarios pass.
- [ ] Editorial self-expansion writes to DATA only; no autonomous-loop path edits code or
      critical runtime config (REQ-OD-009 verified).
- [ ] The segment-type registry (Group OY) is a VIEW over the REQ-OD-007 ledger — no forked
      store, no new gate/research-engine/playout-kind; the per-segment pipeline composes the
      existing fact-check gate and never ships a FAIL (REQ-OY-001/005/006 verified).
- [ ] The always-staffed invariant holds across every lifecycle transition — no observer ever
      reads a hostless/retired-named scheduled block; voice quarantine and the rarity tier hold
      (REQ-OB-013/014, REQ-OD-010 verified); the news anchor is exempt (REQ-PI-005).
- [ ] The off-schedule variety layer (REQ-OA-003d) is SOFT-only and subordinate to the hard rails:
      it down-weights (never bans) over-represented genre-families and jarring adjacency in the
      unscheduled lane via the existing pick score (no new store; only the `genre_family_map`
      artifact; deterministic, no RNG), suspends adjacency at deliberate boundaries, relaxes under
      the empty-legal-set fallback, and is [HARD] EXEMPT inside any scheduled/curated block so a
      single-genre show plays unmodified (CORE-001 REQ-D-002 / AC-OA-004 verified); no Liquidsoap
      change and no <1s hot-path dependency on ORCH-005 REQ-RW-006.
- [ ] Liquidsoap config is unchanged (the seam is brain-only).
- [ ] `/api/next` stays < 1s and never blocks on synthesis; all produced audio is
      pre-rendered/cached.
- [ ] One shared loudness constant verified across songs/imaging/talk/news.
- [ ] No OPS path can be a single point of stream silence (forced-failure tested).
- [ ] No partisan/political or fabricated content path exists; generated copy/news is
      logged.
- [ ] `ANTHROPIC_API_KEY` unset; subscription OAuth auth verified; quota discipline
      (two modes, batching, async) in place.
- [ ] Disk never fills to failure under a forced low-space test.
- [ ] slskd-first / yt-dlp-last acquisition ranking verified.
- [ ] No deferred item (Section 13) is partially built.
- [ ] TRUST 5 gates pass (Tested, Readable, Unified, Secured, Trackable) per the
      project's configured methodology.

### Quality gate criteria

- **Tested:** 85%+ coverage on new brain modules (per CORE-001's testing posture);
  forced-failure tests for never-silence, disk-space, and TTS/news skip paths.
- **Readable:** clear naming; English comments; the imaging filtergraph + loudnorm
  parameters documented.
- **Unified:** consistent with CORE-001/VOICE-002 conventions; no forked stores.
- **Secured:** secrets per CORE-001 discipline; `ANTHROPIC_API_KEY` unset; scraping
  only where ToS permits; no autonomous purchasing.
- **Trackable:** conventional commits referencing SPEC-RADIO-OPS-004; structured logs
  per NFR-O-6.
