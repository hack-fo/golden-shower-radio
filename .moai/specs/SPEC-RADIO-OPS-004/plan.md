# SPEC-RADIO-OPS-004 — Implementation Plan

Implementation plan for the autonomous program director, self-produced imaging,
self-learning playbook, newscasting, and library management. This is the HOW; spec.md
is the WHAT/WHY; research.md is the evidence.

[HARD] Per the MoAI time-estimation rule, this plan uses priority labels and phase
ordering only — no time estimates.

---

## 1. Guiding architecture

OPS-004 sits on top of CORE-001 + VOICE-002 and changes the BRAIN only — Liquidsoap
needs ZERO change. The single most important architectural fact:

- The brain's `Picker.pick()` already returns `NextItem(kind="music"|"talk", ...)` and
  the documented seam anticipates new kinds. OPS adds `kind="imaging"` and
  `kind="news"`. `/api/next` serves/commits them identically. `request.dynamic.list` +
  `mksafe` in `radio.liq` plays whatever path it gets.
- `/api/next` MUST stay < 1s and never block on synthesis. ALL produced audio
  (imaging, news, talk) is PRE-RENDERED by the async director loop and cached to
  `CLIPS_DIR`; the request path only reads the library/clip pool and commits.
- The director loop (`brain/director.py`) — already async, crash-isolated per tick,
  and quota-batched — is the home for program-director planning, show-prep, imaging/
  news production, playbook refinement, and library housekeeping.

The only FIXED rails (everything else is the AI's call): never a single point of
silence; one shared loudness constant; hard no-repeat/artist separation; top-of-hour
ID; self-cleared-imaging gate; single clean served items; apolitical + factual;
subscription auth + quota; disk never runs out.

---

## 2. Technical approach by group

### Group OA — Program Director & 24h Scheduling

- **Format clock engine.** Per-daypart hour skeletons as data (JSON/YAML): ordered,
  typed slots. 5 or 7 clock variants per daypart (never multiples of 24) to break the
  daily lattice. A wall-clock-aware slot resolver becomes the core of `Picker.pick()`:
  current daypart → active clock variant → current slot type → concrete item.
- **Separation solver (REQ-OA-003 + REQ-OA-003a).** Candidate scoring over the slot's
  category pool: hard filters (same-title no-repeat window, artist spacing) + soft
  scores (tempo/energy/gender/era/sound-code) + least-recently-played bias. On empty
  legal set: widen window / borrow adjacent category / LOG — never stall, never repeat
  illegally. Supersedes CORE-001 REQ-B-006's minimal window; preserves its hard rails.
- **Rotation categories (REQ-OA-004).** Per-track category field + promotion/demotion/
  resting moves on the director's planning cadence. Uneven category sizes.
- **Dayparting + energy flow (REQ-OA-005).** Wall-clock → daypart → active clock pool +
  persona register + energy arc ("now, now, then").
- **Adjacency (REQ-OA-006).** Adjacency scoring using the BPM/key/energy from
  enrichment (REQ-OA-011); emit crossfade length + cue points; the no-vocal-over-vocal
  guard + crossfade mechanics live in the playout layer.
- **Library metadata (REQ-OA-010/011/012).** Extends `brain/library.py`: tag
  correction/normalization (mutagen/ffprobe + reconcile against MusicBrainz/Discogs/
  Last.fm), audio analysis for BPM/key/energy (librosa/aubio/essentia-class), a
  queryable catalog the PD reads. Runs off the playout path; partial metadata is still
  usable.
- **Never-silence (REQ-OA-008).** Any decision/render failure → fall back to a music
  track or cached evergreen ID; the inherited CORE-001 failover sits below.

### Group OB — Shows & Host Personas

- Reuse CORE-001's runtime-extensible, system-owned persona/show store. OPS adds
  persona-register tags, themed-show construction, recurring named-segment definitions
  (name + ident clip + selection rule + generated intro), and special-show clock
  override/restore. Host caps consumed (CORE REQ-B-011 max-2; VOICE REQ-V-D-005
  Faroese-1). Reference patterns weighted to KEXP / P3 Dans / P3 Mix / ASOT / Rodigan.

### Group OC — Research-Driven Show Prep (two LLM modes)

- **Mode A (cheap quick-curation).** Minimal system prompt, tools OFF, batched. The
  frequent next-track/next-imaging path. Reuses the existing brain LLM call pattern.
- **Mode B (richer research).** Claude Agent SDK web tools ON. Occasional show-prep:
  invent a theme → research tracklist (classics + deep cuts) + per-segment talking
  points/facts/history/cultural context. Produces a structured show plan bound to the
  tracklist. Grounded, not fabricated (hedge uncertain claims).

### Group OD — Self-Learning Playbook + measured self-change

- A persistent, queryable knowledge base (its own store, e.g. a structured doc/db).
  Dimensions: radio craft, music history + cultural/societal context, newscasting
  craft. Seeded at plan time from research.md; refined 24/7 via Mode B on a
  self-scheduled cadence; injected as context into the PD, show-prep, imaging-copy,
  and newscast generation.
- **Measured self-change (REQ-OD-006).** Identity-affecting changes (playbook rules
  acted on, format defaults, personas, segment roster) go through a self-imposed
  stability gate modeled on `.claude/rules/moai/design/constitution.md` Section 5:
  rate limiter (bounded changes/period + cooldown), canary (shadow-evaluate against
  recent programming, reject regressions), contradiction detection (reconcile, never
  silently churn). Human-optional (human is out of loop). Learning is unbounded; only
  the CHANGE velocity is bounded.

### Group OE — Self-Produced Imaging & Jingles (the 6-stage pipeline)

1. **Concept (Mode A/B).** Claude emits the structured-JSON brief.
2. **Voice.** Calls the VOICE-002 TTS layer (Kokoro/Piper EN; teldutala.fo FO,
   pre-rendered + cached, gentle concurrency).
3. **Mix (ffmpeg + sox).** Dry IDs skip the bed; wet pieces: sox bed prep → `afade` →
   optional `adelay` stinger → `sidechaincompress` with VOICE as the sidechain KEY
   compressing the MUSIC → `amix=...:normalize=0` (verify voice full-level). OFFLINE
   clip-baking, distinct from VOICE-002's live ducking.
4. **Normalize.** Two-pass `loudnorm` to -16 LUFS / -1.5 dBTP (shared constant).
5. **Encode + library.** ffmpeg to the stream codec at the catalog's
   sample-rate/channels → `CLIPS_DIR` + metadata sidecar.
6. **Serve.** `Picker.pick()` returns `NextItem(kind="imaging")`.
- **Beds:** procedural sox/ffmpeg synthesis (default, zero-risk) → Stable Audio 3
  Small on CPU (config-gated, pre-rendered pool) → first-party CC0. License ledger +
  self-generated-or-CC0-only gate. Anti-overproduction: default dry, wet occasional.
- **Containers:** add `CLIPS_DIR` mount to brain + liquidsoap; add `sox` to
  `Dockerfile.brain`.

### Group OF — Liveliness & Quality

- Liveliness is a checkable property of the running station (presence of personas,
  themed shows, imaging, talk over time) — NOT a per-block talk mandate. Music-only
  blocks are valid. Anti-shallow banter draws on show-prep + playbook + recent-phrase
  memory. Apolitical + factual filter on all generated copy (logged for after-the-fact
  detection).

### Group OG — News & Newscasting

- AI-owned cadence/format. A self-evolved trusted-source list (RSS/Atom/news APIs,
  permitted scraping). Aggregation off the playout path. Mode B fetches/grounds
  headlines; every item attributed; ungroundable items dropped. Faroese angle
  (kvf.fo/dimma.fo FO via teldutala; Sweden SVT/SR-class; intl Reuters/AP-class), lang
  routing per VOICE-002. Newscast produced via the imaging/TTS pipeline (optional
  procedural pips → TTS read → loudnorm) and served as `kind="news"`. Optional
  breaking-news interrupt at a safe boundary. Never blocks the stream.

### Group OH — Library Management & Acquisition Policy

- **Play-from-library balance (REQ-OH-001).** As the catalog grows, lean on it; don't
  acquire on every selection; the balance is the AI's call.
- **Quality preference (REQ-OH-002).** Acquisition ranking: slskd primary (FLAC/high
  bitrate); yt-dlp last resort only.
- **Folder structure (REQ-OH-003).** Sort imports into a managed structure (artist/
  album or genre) out of slskd's raw dirs.
- **Disk management (REQ-OH-004).** Monitor free disk; cap library size and/or evict
  least-valuable (least-played, lower-quality dup) tracks; low-space alert in
  health/status. Hard rail — never run out.
- **Bandcamp hook (REQ-OH-005).** When the AI wants music it can't get via slskd/
  yt-dlp but it's on Bandcamp, emit a user-facing "buy this" recommendation
  (notification/webhook/log/push, TBD). Recommend-only; no autonomous purchase.

---

## 3. Milestones (priority-ordered, no time estimates)

**Milestone M1 — Foundations (Priority High, build first).**
- `CLIPS_DIR` mount + `kind="imaging"`/`kind="news"` in `Picker.pick()`/`NextItem`.
- Add `sox`; one shared loudness constant in config.
- Library metadata enrichment + queryable catalog (REQ-OA-010/011/012) — unblocks
  curation, DJ-sets, and disk eviction value.
- Disk-space management (REQ-OH-004) and acquisition quality preference (REQ-OH-002) —
  operational safety + quality, cheap to add.

**Milestone M2 — Program director core (Priority High).**
- Format clock engine + separation solver + no-repeat/LRP (REQ-OA-001/002/003/003a).
- Rotation categories + dayparting + adjacency (REQ-OA-004/005/006).
- Never-silence fallback wiring (REQ-OA-008).
- Play-from-library balance + library folder structure (REQ-OH-001/003).

**Milestone M3 — Imaging pipeline (Priority High).**
- 6-stage pipeline: procedural FX first (REQ-OE-003), then dry IDs/liners, then wet
  sweepers with offline ducking (REQ-OE-001/002/005/006/007/011).
- License ledger + self-cleared gate (REQ-OE-010); top-of-hour ID (REQ-OE-008);
  single-clean-track (REQ-OE-009).
- Generative/CC0 beds (REQ-OE-004) — config-gated, after procedural.

**Milestone M4 — Shows, show-prep, two LLM modes (Priority High).**
- Two LLM modes (REQ-OC-001); themed shows + register switching + named segments +
  special-show override (Group OB); show-prep + grounding (REQ-OC-002/003/004/005).

**Milestone M5 — Self-learning playbook (Priority High).**
- Persistent playbook + plan-time seed + runtime refinement + apply (REQ-OD-001..005);
  measured self-change stability gate (REQ-OD-006).

**Milestone M6 — Newscasting (Priority High).**
- Source list + aggregation + grounded factual reads + Faroese angle + production +
  pull insertion + never-block (Group OG); optional breaking-news interrupt last.

**Milestone M7 — Liveliness, quality, Bandcamp hook, observability (Priority Medium/High).**
- Liveliness checkable property + anti-shallow + music-blocks-valid + apolitical
  (Group OF). Bandcamp hook (REQ-OH-005). Observability + health/status (NFR-O-6).

Cross-cutting throughout: subscription auth (NFR-O-1), quota discipline (NFR-O-2),
loudness consistency (NFR-O-3), resilience (NFR-O-4), continuous operation (NFR-O-5),
apolitical/factual integrity (NFR-O-7), simplicity (NFR-O-8).

---

## 4. Key technical decisions / parameters

- **ffmpeg ducking filtergraph (REQ-OE-002):**
  `[0:a]asplit=2[v][key];[1:a][key]sidechaincompress=threshold=0.02:ratio=10:attack=50:release=400:makeup=1[ducked];[v][ducked]amix=inputs=2:duration=first:normalize=0`.
  VOICE is the sidechain key; verify voice stays full-level (the #1 wiring bug).
- **Two-pass loudnorm (REQ-OE-005):** pass 1 `print_format=json` → parse measured_* →
  pass 2 with `linear=true`. Target `I=-16:TP=-1.5:LRA=11`.
- **Procedural synthesis (REQ-OE-003):** sox `synth` + ffmpeg `aevalsrc`/`anoisesrc`;
  public-domain by construction.
- **Stable Audio 3 (REQ-OE-004):** config-gated; pre-render a reusable bed pool on CPU;
  never in the playout path; registration + <$1M revenue check.
- **Measured self-change (REQ-OD-006):** rate limiter + cooldown + canary +
  contradiction detection, values in config; modeled on design constitution Section 5.
- **Acquisition ranking (REQ-OH-002):** slskd → (gap) → yt-dlp last resort.
- **Disk eviction (REQ-OH-004):** value = f(play count, recency, quality, duplicate
  status); evict least-valuable when below the free-space threshold.

---

## 5. Risks to manage during implementation

See spec.md Section 16 (R-O-1 .. R-O-18). The highest build-time attention items:
sidechaincompress wiring + amix voice level (R-O-7); disk-space exhaustion (R-O-17,
operational, deployment hit it before); loudness consistency across content types
(R-O-4); subscription quota for Mode B (R-O-2); news/show-prep factual grounding
(R-O-5); enrichment accuracy/cost + external API rate limits (R-O-15).

Out of scope but flagged: public-stream music-rights licensing for the main rotation
(R-O-10) — keep the build private/experimental.
