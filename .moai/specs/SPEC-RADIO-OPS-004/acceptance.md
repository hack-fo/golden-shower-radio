# SPEC-RADIO-OPS-004 — Acceptance Criteria

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

**AC-OA-011 (REQ-OA-011) [HARD] [documented compound].**
- [HARD] Each track is enriched with genre, mood, BPM, key, energy, and year from any of
  the concrete sources: embedded tags (mutagen/ffprobe) / audio analysis (BPM/key/
  energy via librosa-aubio-essentia-class) / external metadata APIs (MusicBrainz API +
  TheAudioDB API; Discogs/Last.fm optional) or LLM knowledge / and filename
  `%ARTIST% - %TITLE%` parsing as a reliable fallback (the sources are alternatives
  feeding one enriched record — the AC is intentionally compound, matching the
  compound REQ).
- Enrichment runs off the playout path and never blocks the stream; partial enrichment
  is still recorded and usable; the filename-parse fallback recovers artist/title when
  tags/APIs are missing.

**AC-OA-012 (REQ-OA-012) [HARD].**
- [HARD] The catalog is queryable by artist/genre/mood/BPM/key/energy/year/category/
  history and is used by the PD to build genre nights, mood/energy arcs, and
  BPM/key-matched DJ-sets.
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
attribution, library housekeeping/eviction, and fallbacks, surfaced via the CORE-001
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

The SPEC is implementation-complete when:

- [ ] Every requirement (REQ-OA-*, REQ-OB-*, REQ-OC-*, REQ-OD-*, REQ-OE-*, REQ-OF-*,
      REQ-OG-*, REQ-OH-*) and NFR (NFR-O-*) has its acceptance criteria met with
      evidence (test output, logs, or runtime observation).
- [ ] All 12 Given-When-Then scenarios pass.
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
