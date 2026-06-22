# SPEC-RADIO-PROGRAMMING-007 — Research

Research backing the editorial content layer of golden-shower-radio: the persona/
roster model, the radio-craft playbook, script-side TTS naturalization (ear-writing),
and show formats (including the Sommar-style long-form show). Four threads, each with
its sources, the decisions they drove, and the honest limits / ethics constraints they
surfaced. This SPEC formalizes COMPLETED research into requirements; this document is
the evidence trail, not a fresh investigation.

A meta-finding up front: **bhive had NO prior patterns for any of these four threads.**
There were no shared-memory entries for AI-radio persona rostering, radio-craft talk
anatomy, script-side TTS ear-writing for a radio host, or the Sommar-style long-form
format on the Go+Liquidsoap+slskd / Python-brain radio stack. This extends the existing
bhive radio stack-gap memory from an INFRASTRUCTURE gap into an EDITORIAL-CRAFT gap. The
craft seeded here — and refined at runtime via the OPS-004 self-learning loop
(REQ-OD-003) — is the contribution to write back to bhive after the build is validated
(see Section 6).

---

## 1. Thread A — Roster & Persona Model

### 1.1 Question

How many hosts, with what identity structure, and how do we stop autonomous curation
from collapsing every host into the same averaged sound?

### 1.2 Reference stations studied

- **NTS Radio** (nts.live) — the strongest model for the chosen approach: a large roster
  of distinct SOLO selectors, each with a narrow, genuine, deeply personal taste
  territory, presenting a named recurring show in an appointment slot. NTS is the
  archetype of "many single-curator personas, each unmistakably themselves" rather than
  a few generalist presenters. It is the direct inspiration for the multi-persona,
  single-curator, taste-charter model.
- **KEXP** (kexp.org) — curatorial-connoisseur presentation: a host with real knowledge
  and a point of view, talking ABOUT the music with context and genuine reaction, not
  hyping it. Already the emphasized reference in OPS-004 (REQ-OB-002); reinforced here as
  the per-persona POV model.
- **BBC Radio 1Xtra** (and Rodigan's specialist-selector tradition) — the specialist
  who OWNS a genre and presents it with authority; the model for a persona whose taste
  charter is narrow and deep rather than broad and shallow.

### 1.3 Decisions driven (orchestrator-confirmed)

- **Multiple distinct single-curator personas** with a **two-level identity**: a
  station-level editorial "house" (shared ethos/sound) over per-show personas
  (individual hosts). NTS + KEXP both operate this way — a station identity that contains
  many individual voices.
- **Launch ~5 English personas + 2 Faroese** (Hanna ♀, Hanus ♂ as independent SOLO
  personas). Default 1 host/show; 2-host ONLY for a deliberate dialogue/contrast format.
  [HARD] max 2 hosts/show NEVER 3 (inherits CORE-001 REQ-B-011); Faroese exactly 1 (only
  two adult Faroese voices exist — see Thread C and VOICE-002 REQ-V-D-004).
- **Voice↔persona 1:1, NEVER reused** [HARD]. Use only ~5 of the verified Kokoro English
  voices (af_heart, af_bella, am_michael, am_fenrir, bf_emma, bm_george, bm_fable — seven
  verified in VOICE-002) at launch, reserving the rest so the growth gate always has a
  free voice for a genuinely new editorial gap. English and Faroese are SEPARATE rosters;
  no bilingual persona.
- **Per-persona TASTE CHARTER** [HARD]: in/out-of-bounds genres, eras, moods, signature
  artists/labels; hand- or runtime-authored, persisted, system-owned + runtime-extensible.
- **ANTI-CONVERGENCE FIREWALL** [HARD]: no two personas share a primary genre territory;
  cap rotation overlap; enforced as a HARD check at curation time. This is the core
  defense against the failure mode the research kept surfacing: a single underlying model
  curating "autonomously" drifts to a shared statistical average, so five personas end up
  playing the same safe middle — AI slop wearing five name tags. The firewall is PROVEN
  against the ANALYSIS-006 taste feature dimensions (REQ-AD-003), which exist precisely to
  make taste profiles queryable and separable.
- **Persona persistent POV** [HARD]: own intros/sign-offs/recurring bits/pacing signature,
  stable across appearances (the NTS/KEXP "returning person" effect).
- **GROWTH GATE** [HARD]: add a persona ONLY for a documented editorial GAP, never appeal/
  reach; a both-axes (free voice + distinct taste) distinctness test before air.

### 1.4 Why a firewall and not just "give them different prompts"

The research finding is that prompt-level personality differences are cosmetic: under
autonomous curation the underlying selection still gravitates to the catalog's center of
mass, so two differently-prompted personas converge in practice. Separation has to be
enforced on the OUTPUT (the candidate pool), measured over real feature dimensions, not
on the persona's self-description. Hence NFR-P-1 makes plurality a measured property
(pairwise pool overlap under a cap), not a claim.

---

## 2. Thread B — Radio-Craft Playbook

### 2.1 Question

What are the concrete, teachable rules of good radio presentation that a generative host
must follow to sound like real radio instead of an LLM reading liner notes?

### 2.2 Sources studied

- **"The Pips" / programming-director craft writing** — the standard talk-break anatomy:
  backsell as the default move (name what just played), frontsell as spice, the
  Hook→Body→Exit link structure, and the discipline of ONE idea per break.
- **Radio.co and similar broadcaster guides** — link-length discipline (keep it tight,
  ≤~30s), talk cadence (every few songs, not every song), and the "write to one person"
  rule.
- **KEXP** — what to SAY: genuine context and reaction over hype; the connoisseur model.
- **David Rodigan / BBC 1Xtra** — energy and authority in a specialist set; how a host
  carries a genre.
- **NTS** — the connective-tissue style of talk (threading tracks together) and the
  appointment-show shape.
- **DJ set-phase theory** — the warm-up → build → peak → sustain → cool-down → send-off
  arc; cool-downs that slope rather than crash; the weight of the last few tracks in a
  block; avoiding jarring tempo/key jumps (the basis for tempo/key bridges, computed here
  from the ANALYSIS-006 bpm/key/energy dimensions).

### 2.3 Concrete craft rules encoded (Group PC)

- **Talk-break anatomy** (REQ-PC-001): backsell default; frontsell by FEELING not "coming
  up"; periodic re-ID for new tuners; link = Hook (3-6s, lead with the interesting thing)
  → Body (ONE idea) → Exit (clean button). Link ≤30s; talk every 1-3 songs, not every
  song; otherwise segue clean (REQ-PC-002).
- **"Hit the post"** [HARD] (REQ-PC-003): NEVER talk over a vocal — only over instrumental
  intros/outros. **The AI's killer advantage:** a human DJ guesses the intro length and
  often misses; the AI reads the EXACT analyzed instrumental-intro length from the
  ANALYSIS-006 cue/tempo metadata (cue-in, cue-out, true-end, the `annotate:` fields) and
  WRITES the talk break sized to land its last word on the post (automated backtiming). If
  the intro is too short: talk over the prior outro, drop a bed, or segue + backsell. This
  is the single most "real radio" capability in the whole SPEC and the clearest place the
  automation beats a human.
- **What hosts SAY** — rotate categories, never the same twice running (REQ-PC-007):
  artist/track context + history; genuine personal reaction; connective tissue between
  tracks; time/weather/locale (local Faroe); listener shout-outs.
- **What hosts DON'T say** — anti-cheese firewall (REQ-PC-004), the positive expression of
  OPS-004's anti-slop discipline (REQ-OF-005): banned phrases ("stay tuned", "coming up",
  "up next", "don't go anywhere", "back-to-back", "all your favourites"); no forced
  enthusiasm; no clichés / radio-voice; no rambling; write to ONE listener ("you").
- **Energy/mood arc + daypart presets** (REQ-PC-005), Faroe-local time: morning
  bright/frequent → midday steady/sparse → afternoon peak/most-personality → evening
  deeper/longer-links → overnight intimate/sparse. Set-phase arc warm-up → build → peak →
  sustain → cool-down → send-off; cool-downs SLOPE never crash; last 1-3 tracks of a block
  carry extra weight; tempo/key bridges (no 120→135 BPM jump).
- **Theme generators** (REQ-PC-006), rotating: decade/era, place, mood/activity, genre
  deep-dive, artist spotlight, anniversary/calendar, listener-curated hour, connective
  "thread" sets. Recurring shows/segments = same skeleton + NAME + appointment SLOT; first
  ~15s decide retention, so open on the strongest hook/song (REQ-PC-010).

### 2.4 Why the playbook is a self-refining store, not a static ruleset

The craft above is SEED content, not the final word. It lives in the OPS-004 self-learning
playbook store (REQ-OD-001) and is refined 24/7 by the OPS-004 refinement loop (REQ-OD-003)
under the measured-self-change rails (REQ-OD-006). This matches the operating-philosophy
"self-learning playbook" intent: the human seeds the craft, the AI improves it. The
critical guard (inherited OPS-004 REQ-OC-006): the station NEVER feeds its own recent
output back as in-context style exemplars — recent output is only an avoid-list — so the
self-refinement does not collapse into imitating its own template.

---

## 3. Thread C — Script-Side TTS Naturalization (Ear-Writing)

### 3.1 Question

How do we WRITE a talk script so that flat, local, non-expressive TTS reads it as natural
spoken radio rather than as read-aloud prose?

### 3.2 Sources studied

- **Kokoro** (PyPI `kokoro`; hexgrad/Kokoro-82M on Hugging Face) — the primary English
  engine (VOICE-002). Findings: best results come from SHORT inputs chunked to ~100-200
  tokens, with the chunk boundaries placed at sentence-group breaks; the engine has no
  expressive emotion control, so prosody must come from the TEXT (punctuation, sentence
  length) and from inter-chunk silence, not from the voice.
- **Piper** (rhasspy/piper) — the CPU-friendly fallback (VOICE-002). Same finding: pacing
  is controlled by chunking + silence between chunks, not by an emotion API.
- **ffmpeg `anullsrc`** — generating the precise inter-chunk silence beds and pauses
  (engineered pauses) that carry pacing and "breath" in synthesized speech; the offline
  ducked-bed assembly for Solstice Hour.
- **General "writing for the ear" / broadcast-writing guidance** — the standard rules:
  one thought per sentence, keep sentences short (≤~20 words), always use contractions,
  address one listener in the second person, punctuate for breath (commas/em-dash/
  ellipsis), vary sentence length, and spell numbers/dates as spoken.

### 3.3 Rules encoded (Group PS)

- One thought / sentence ≤20 words (REQ-PS-001).
- Always contractions; second person to ONE listener (REQ-PS-002).
- Punctuate for breath; vary sentence length (REQ-PS-003).
- 1-2 sentence blocks separated by blank lines — and **these blocks ARE the TTS
  synthesis-chunk boundaries** (REQ-PS-004). This is the explicit coordination contract
  with VOICE-002: the SCRIPT side writes blocks, the SYNTHESIS side (voice.py) chunks at
  those blank-line boundaries and inserts silence. The boundary discipline is what makes
  pacing natural; getting it wrong (chunking mid-thought) is the main way synthesized
  radio talk sounds robotic.
- Spell numbers/dates as spoken; IPA phoneme override available for mispronounced names
  (REQ-PS-005) — VOICE-002 consumes the override at synthesis.

### 3.4 Boundary with VOICE-002

PROGRAMMING owns the SCRIPT (the text and its block structure). VOICE-002 owns the
SYNTHESIS (the chunk+silence render, speed). REQ-PS-004 is deliberately phrased as a
coordination contract so neither SPEC redefines the other: the script's blank-line blocks
are WRITTEN to align with VOICE-002's chunking.

---

## 4. Thread D — Show Formats (incl. the Sommar-style long-form show)

### 4.1 Question

What recurring show structure builds appointment listening, and can we do a Sommar i
P1-style long-form personal monologue with flat TTS — and ethically, given the show is
built around a "guest's life story"?

### 4.2 Sources studied

- **Sommar i P1** (Sveriges Radio) — Wikipedia overview of the format: a single guest
  speaks for ~90 minutes (we scope to ~60), telling their personal life story interwoven
  with self-chosen music; one of Sweden's most beloved radio institutions. The format's
  power is intimacy + narrative arc + music as emotional punctuation.
- **A representative Sommar transcript (a Bostrom-style episode)** — studied for STRUCTURE
  ONLY: how the monologue moves through a life arc (origins → a turn/struggle → vocation →
  reflection), how tracks are narratively MOTIVATED (a song marks a moment in the story)
  rather than just slotted, and how pauses and a quiet music bed carry emotion. Studied for
  craft, NEVER to reproduce the real person's real story.
- **Press coverage of Sommar** — for the cultural role and the format conventions
  (the annual ritual, the range of guests, the music-as-memory device).
- **RSS episode descriptions** — noted as the practical way to STUDY such formats when the
  audio is region-locked (Sveriges Radio audio is geo-restricted); the public RSS feed +
  press descriptions give the structure and themes without needing the audio.

### 4.3 Decisions encoded (Group PT)

- **Recurring show format spec** (REQ-PT-001): name + fixed slot + stable skeleton +
  open/close ritual; recognizably the same show each time; recurring named segments
  (REQ-PT-003); open on the strongest hook (REQ-PT-002, first ~15s decide retention).
- **The flagship long-form show "Solstice Hour"** (Faroese strand **"Summarrødd"**),
  inspired by Sommar i P1 (REQ-PT-004): ~60 min, weekly flagship slot; a 3-act personal
  life-arc monologue (origins → turn/struggle → vocation → reflection) interwoven with 4-5
  narratively-motivated tracks from the legally-airable library; emotion carried by
  ear-writing + engineered pauses + a ducked music bed.
- **[HARD] fictional-persona ethics guardrail** (REQ-PT-005): the "guest" is an AI-authored
  ORIGINAL FICTIONAL persona — NEVER a real named person, no impersonation, no fabricated
  testimony attributed to a real individual, apolitical.
- **[HARD] mandatory disclaimer at open AND close** (REQ-PT-006): every episode opens and
  closes with a spoken disclaimer that the guest is a fictional persona voiced by the
  station; an episode missing either does NOT air (NFR-P-4).
- **Pre-rendered to one file** (REQ-PT-007): the whole episode is baked to a single
  loudness-normalized file and queued via the OPS-004 ready buffer — zero live-assembly
  risk for a 60-minute emotional piece.
- **Optional 2-voice interview variant + format-study capability** (REQ-PT-008): the
  2-voice variant (fictional host + fictional guest) stays within the max-2 cap and under
  the same guardrail; the format-study capability studies public formats from transcripts/
  press/RSS descriptions to inform craft, never to copy.

### 4.4 Honest TTS limit for emotional long-form

A deliberately honest finding (R-P-2): flat local TTS (Kokoro/Piper/teldutala) achieves
only ~75-85% of the emotional effect a skilled human reader gets. It cannot weep, cannot do
comic timing, and has limited theatrical range. The design response is NOT to pretend
otherwise: the Solstice Hour is DESIGNED for "quiet / measured / reflective" delivery — the
register synthesized speech does best — and carries emotion through WRITING (ear-writing,
Group PS) + engineered pauses + a ducked bed, explicitly AVOIDING scripts that need weeping
or comic timing. This is a design constraint, not a bug to fix.

### 4.5 The ethics finding (why the guardrail is HARD)

A long-form "personal life story" format is exactly where an autonomous LLM could cause
real harm: inventing a biography that resembles a real person, fabricating testimony,
straying into political content, or being mistaken for a real human's genuine account. The
guardrail is therefore HARD and double-locked: (1) the guest is an original fictional
persona only, apolitical, no impersonation, no real testimony (REQ-PT-005); and (2) every
episode says so out loud at both the open and the close, and won't air without both
(REQ-PT-006 / NFR-P-4). The disclaimer + original-only rule are the primary safeguards; the
residual risk (an invented story coincidentally resembling a real person) is flagged as an
ongoing review concern (R-P-3).

---

## 5. Cross-cutting findings

- **The four threads share one enemy: convergence to the average.** Roster convergence
  (Thread A), craft convergence via self-imitation (Thread B), prosody flatness (Thread C),
  and a long-form piece that feels generic (Thread D) are all the same failure — autonomous
  generation collapsing to a safe middle. The defenses are correspondingly specific: the
  anti-convergence firewall (REQ-PR-004), the no-self-imitation rule (inherited REQ-OC-006),
  the ear-writing block discipline (REQ-PS-004), and the narratively-motivated track choice
  + quiet-register design (REQ-PT-004).
- **The AI's structural advantages over a human DJ are real and worth leaning into:**
  perfect knowledge of every track's analyzed intro/outro (hit-the-post backtiming,
  REQ-PC-003), a persisted per-persona taste charter that never drifts on a bad night, and
  the ability to pre-render a flawless 60-minute long-form piece (REQ-PT-007). The SPEC is
  written to exploit these, not to imitate a human's limitations.
- **Everything here is editorial CONTENT over existing ENGINES.** No new service, store, or
  playout seam: personas live in CORE-001's model, craft lives in OPS-004's playbook store,
  scripts synthesize through VOICE-002, taste is queried over ANALYSIS-006's dimensions, and
  episodes air through OPS-004's pull/buffer. The SPEC's discipline is to add the CONTENT
  and REFERENCE the engines (NFR-P-6).

---

## 6. bhive stack-gap note (write-back candidate)

bhive returned NO prior patterns for any of the four threads — no AI-radio persona
rostering, no radio-craft talk-anatomy/hit-the-post, no script-side TTS ear-writing for a
radio host, and no Sommar-style long-form format on this stack. This confirms and EXTENDS
the existing radio stack-gap memory from infrastructure into editorial craft.

After the build is validated, the write-back candidates (per the bhive Close-the-Loop
protocol) are:
- The anti-convergence firewall pattern (enforce roster plurality on the OUTPUT candidate
  pool over real audio-feature dimensions, not on persona prompts) — a non-obvious,
  reusable approach for any multi-persona generative-curation system.
- The hit-the-post automated-backtiming technique (size a generated talk break from
  analyzed instrumental-intro length so it lands on the post; never over a vocal) — a
  concrete, reusable AI-radio capability.
- The ear-writing ↔ TTS-chunk-boundary coordination contract (script blank-line blocks =
  synthesis chunk boundaries) — a reusable pattern for natural-sounding flat-TTS speech.
- The fictional-persona + mandatory-disclaimer ethics guardrail for autonomous long-form
  personal-narrative content — a reusable safety pattern.
- The honest finding that flat local TTS hits only ~75-85% of emotional effect, so
  long-form must be designed for the quiet/measured register — a calibration others will
  want.

Do NOT write back until the build verifies these; write the verified lesson with its
`query_id` per the protocol.

The v0.2.0 addition (Group PL — taste self-learning) ADDS to the write-back candidates:
- The taste-self-learning-on-output pattern: a per-persona taste profile that evolves from
  play/skip/recency/listener-context signals (NEVER appeal metrics) under a measured,
  rate-limited loop, while re-checking the anti-convergence firewall on the EVOLVED
  profiles so refinement never erodes plurality — a reusable pattern for autonomous
  multi-persona curation that improves without homogenizing or pandering.
- The provenance-on-the-track pattern (acquired_for / acquired_context / source, with
  manual drops attributed to "unattributed/house" and still fully curatable) as the
  foundation that makes a curation diary and taste feedback possible.

---

## 8. Thread E — Taste Self-Learning, Provenance & Feedback (v0.2.0; GREENFIELD code audit)

### 8.1 Question

How does each persona's taste GROW over time without converging on the others or sliding
into appeal-optimization — and what does the CURRENT brain already do toward this?

### 8.2 Ground truth: a code audit of the current brain

Unlike Threads A-D (which studied external reference stations), this thread is grounded in
a CODE AUDIT of the brain as it exists today. The finding is that the station has
effectively NO learning loop — Group PL is therefore a GREENFIELD capability, not an
enhancement of an existing one. Audit findings:

- **One global taste, no per-persona model.** Taste lives ONLY in a single global
  LLM-persona prompt. There is no per-persona taste model and no persisted taste structure
  on disk.
- **Stateless curation.** `curate_batch()` selects the next tracks from the LLM prompt plus
  a last-20-played repeat-avoidance window. Each call is effectively stateless — nothing it
  decides is written back into a profile that the next call reads.
- **Acquisition outcomes are recorded but orphaned.** `attempts.json` logs acquisition
  success/fail and the method used (slskd / yt-dlp), but this record is NOT attached to the
  `Track` and is NOT fed back into taste. It is a debugging log, not a learning signal.
- **Play history is repeat-avoidance only.** Play history is consulted solely to avoid
  repeating recent tracks; it is not mined as a play/skip taste signal.
- **No provenance on the track.** `Track` has no `source` or `acquired_for` field. Once a
  file is indexed, a Soulseek download and a human manual drop are indistinguishable.
- **Seed enrichment is a stub.** A `config.SEED_ENRICHMENT_STUBS` config flag and a
  `director._seed_reference()` method exist as STUBS. No real Spotify/YouTube seed
  enrichment is wired. (The build-state ground truth: the seed is the user's Spotify
  `tritnaha` `/me/tracks` + YouTube `@tritnaha1345` liked, enriched via a one-time OAuth,
  and is explicitly non-binding — the LLM bootstraps its own wishlist with full autonomy,
  the seed only enriches it.)

### 8.3 What Group PL specs (the gap)

Group PL builds the whole loop on top of the existing engines, forking nothing:
- **Provenance** (REQ-PL-001/002): extend the ANALYSIS-006 `Track` record in place with
  acquired_for / acquired_context / source; manual drops are valid and attributed to
  "unattributed/house", fully curatable.
- **Acquisition diary** (REQ-PL-003): a per-batch decision-chain VIEW over the OPS-004
  ledger/diary substrate (REQ-OD-007/008) — replacing the orphaned `attempts.json` role
  with a taste-feeding record.
- **Evolving per-persona profile** (REQ-PL-004): one persisted profile per persona, seeded
  from the Group PR charter, expressed over the ANALYSIS-006 dimensions, refining over time
  — closing the "one global taste" gap.
- **Signals + measured loop** (REQ-PL-005/006): learn from play-through / early-skip /
  recency / listener context (never appeal metrics), under the OPS-004 measured-self-change
  rails (rate limit + cooldown + canary + contradiction detection) so identity stays
  stable.
- **Seed enrichment** (REQ-PL-007): wire the stub into a one-time non-binding bootstrap.

### 8.4 The two coupled risks this thread surfaced

1. **Convergence-through-evolution.** As profiles learn, they could drift toward each other
   and quietly defeat the anti-convergence firewall. The design response: re-check the
   firewall against the EVOLVED profiles (NFR-P-7), not just the seed charters.
2. **Appeal creep.** Learning from play/skip/feedback is one short step from optimizing for
   listens. The design response is the [HARD] anti-pandering rule (REQ-PL-005): signals are
   human-curatorial context the AI WEIGHS, never a score to maximize. This is the same
   anti-appeal posture the rest of the station already holds (OPS-004 REQ-OF-004 / NFR-O-7).

### 8.5 bhive note

bhive had NO prior pattern for taste self-learning on this stack either — consistent with
the Threads A-D editorial-craft gap. The taste-self-learning-on-output pattern and the
provenance pattern are recorded above as write-back candidates after the build verifies
them.

---

## 8a. Thread F — Grounded Host Voice & Quality Gate (v0.3.0)

### 8a.1 Question

How does the host talk like a knowledgeable person WITHOUT hallucinating facts or sounding
like AI slop — and how do we MECHANICALLY enforce that on every break, not just hope the
prompt holds?

### 8a.2 The two failures this thread targets

The research thread (agent r-organic; bhive query
`973061e9-2730-4654-94d2-a3a41264c698`) isolated two distinct failure modes that a
"knowledgeable host" LLM falls into, and which a free-recall talk prompt cannot avoid:

1. **Confident wrong facts (hallucination).** Asked to sound knowledgeable, an LLM will
   confidently assert a release year, a label, a producer, a band member, or an anecdote it
   does not actually know — and a wrong fact on air is worse than no fact. The finding:
   free-recall must be removed from the fact path entirely. The host may speak a fact ONLY
   if it was SUPPLIED in a closed-world bundle (REQ-PG-001), and silence about an unknown
   fact beats a guess (REQ-PG-002). PERCEPTUAL description of the audible is safe (it is
   grounded in the signal / the ANALYSIS-006 sonic-character profile, REQ-AE-006); NAMED
   factual attribution is not, unless supplied.
2. **AI-slop register (sounding generated).** Even with correct facts, the default LLM
   register betrays itself: music-slop clichés ("sonic journey", "lush soundscapes",
   "effortlessly blends", "a testament to", "needs no introduction", "ethereal/haunting/
   anthemic", "genre-defying", "must-listen", "banger") and structural LLM tells ("delve/
   leverage/elevate/seamless/captivating/boasts/showcases", negative parallelism "not just
   X but Y", rule-of-three adjective piles, em-dash dramatic reveals, "-ing" significance
   tails, generic closers). The finding: ban the register explicitly (REQ-PG-004, extending
   OPS-004 REQ-OF-005) and replace it with positive rules — specificity over adjectives, a
   genuine POV, show-don't-tell, one idea per break, plain words, and permission to say
   little.

### 8a.3 Why a gate, not just a better prompt

The decisive finding (parallel to Thread A's "firewall not prompt"): prompt instructions to
"only state known facts" and "avoid clichés" are NECESSARY but not SUFFICIENT — an LLM will
still drift. Grounding has to be ENFORCED on the OUTPUT, mechanically, before air. Hence the
two-tier QUALITY GATE (REQ-PG-005, refining OPS-004 REQ-OF-006): a Tier-1 DETERMINISTIC lint
(banned-register scan + banned-construction scan + a FORBIDDEN-FACT scan where every year /
label / producer / personnel token in the script MUST appear in the supplied context — a
year disagreeing with `context.year` is a hard FAIL — + a comparison-grounding check) and a
Tier-2 ADVERSARIAL LLM self-check ("list every factual claim; output any NOT supported by
the context"). On FAIL: regenerate once with the reason; on a second FAIL: gracefully SKIP
the break. NEVER ship a FAIL — "the radio talks less" is correct, "the radio asserts a wrong
fact" is not (NFR-P-8). The graceful-skip rides the OPS-004 pull seam so a skipped break
keeps music playing (inherited never-stops).

### 8a.4 Comparison discipline and the voice card

Two supporting decisions completed the thread:
- **Comparison discipline** (REQ-PG-003): "sounds like X" is the most tempting place to
  hallucinate. The rule grounds every comparison on a `similar_artists` edge with
  `match_score` ≥ ~0.6, a genre/tag both demonstrably carry, or a ShowPrep fact (shared
  label/scene/producer/era), and BANS the fusion formula ("X sounds like A meets B", "the
  lovechild of A and B") regardless of grounding — it is a generative tic, not an
  observation. Max one comparison per break; prefer a concrete grounded observation; force
  none when none is grounded.
- **Persona voice card** (REQ-PG-006): the consistency + restraint mechanism. A per-persona
  card (knowledgeable, dry, understated, mild opinions, never gushing, talks like a person
  not a press release) is injected on EVERY call — the SAME card each time for voice
  consistency (coordinating with the Group PR persistent POV, REQ-PR-005) — with a HARD
  token length cap, because over-explaining is itself a slop tell, and with opinion
  permitted ONLY about the AUDIBLE. Traits live in config so they tune without code.

### 8a.5 Boundary with KNOWLEDGE-008 and ANALYSIS-006

Group PG owns HOW the host speaks; it does NOT produce or date the facts. The TrackContext
features + sonic-character + similar-artist edges come from ANALYSIS-006 (REQ-AD-001 /
REQ-AE-006); the dated, sourced ShowPrep facts (each with a `source_url`) come from the
sibling SPEC-RADIO-KNOWLEDGE-008 grounding feed, which owns freshness and provenance. Group
PG's forbidden-fact scan trusts ONLY what is in the supplied bundle, so KNOWLEDGE-008's
freshness gate and ANALYSIS-006's own grounding rail on the sonic description are the
upstream guarantees PG relies on. Neither SPEC redefines the other.

### 8a.6 bhive note

bhive returned NO prior pattern for a grounded-host / anti-slop / quality-gate layer on this
stack (query `973061e9-2730-4654-94d2-a3a41264c698`) — consistent with the Threads A-E
editorial-craft gap. The write-back candidates after the build verifies them: the
closed-world-fact-contract + forbidden-fact-scan pattern (remove free-recall from the fact
path; lint every factual token against a supplied context), the music-slop + LLM-tell banned
register, and the two-tier (deterministic + adversarial-self-check) gate with
regenerate-once-then-skip — all reusable patterns for any grounded generative-voice system.

---

## 9. Sources

- NTS Radio — nts.live (roster of distinct single-curator solo selectors; appointment
  shows).
- KEXP — kexp.org (curatorial-connoisseur presentation; host POV).
- BBC Radio 1Xtra / David Rodigan (specialist-selector tradition).
- "The Pips" and broadcaster programming-director craft writing (talk-break anatomy:
  backsell/frontsell, Hook→Body→Exit).
- Radio.co broadcaster guides (link length, talk cadence, write-to-one-listener).
- DJ set-phase theory (warm-up → build → peak → sustain → cool-down → send-off arc;
  sloped cool-downs; tempo/key transitions).
- Kokoro — PyPI `kokoro`; hexgrad/Kokoro-82M (Hugging Face) (chunking ~100-200 tokens;
  prosody from text + silence, no emotion API).
- Piper — rhasspy/piper (CPU TTS; pacing via chunk+silence).
- ffmpeg `anullsrc` (inter-chunk silence / engineered pauses; offline ducked-bed assembly).
- "Writing for the ear" / broadcast-writing guidance (one thought per short sentence,
  contractions, second person, breath punctuation, spoken numbers/dates).
- Sommar i P1 — Wikipedia (format overview) + a representative Bostrom-style episode
  transcript (STRUCTURE only) + press coverage (cultural role/conventions) + Sveriges Radio
  public RSS episode descriptions (the practical study path when audio is region-locked).

Note: per the MoAI web-search protocol, the named references above were studied as
background patterns for an editorial design; this SPEC asserts no claims about real
individuals and copies no real episode's content (see REQ-PT-005 / REQ-PT-008). External
metadata/feed integration is owned by OPS-004 / ANALYSIS-006, not this SPEC.
