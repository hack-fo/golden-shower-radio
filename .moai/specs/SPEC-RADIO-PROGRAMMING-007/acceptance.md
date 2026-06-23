# SPEC-RADIO-PROGRAMMING-007 — Acceptance Criteria

Acceptance criteria for SPEC-RADIO-PROGRAMMING-007 (Hosts, Personas, Radio Craft &
Show Formats). Section A gives one acceptance entry per requirement (1:1 with the
spec's traceability index: 78 REQ + 10 NFR = 88). Section B gives detailed
Given-When-Then scenarios for the load-bearing requirements. Section C is the
Definition of Done.

All acceptance is editorial-content-layer acceptance: it verifies that the persona
model, the radio-craft rules, the ear-writing rules, and the show formats behave as
specified WHEN they flow through the inherited engines (CORE-001 personas, VOICE-002
TTS, OPS-004 playbook store / pull seam / quality gate, ANALYSIS-006 dimensions). It
never re-verifies those engines.

(2026-06-23, v0.7.1 — audit convergence fixes:) Section 14 EARS-type relabel in spec.md only
(PC-004, PG-002, PG-004, PT-005, PV-006, PV-017: "Unwanted" → "Ubiquitous"; PV-008 kept "Event").
No acceptance text changed; the 1:1 REQ ↔ AC mapping is unaffected.

(2026-06-23, v0.7.2 — acquisition-loop integrity:) Added four Group PL acceptance entries
(AC-PL-008 grab-reason capture, AC-PL-009 exclusion-feedback, AC-PL-010 diary outcome taxonomy,
AC-PL-011 catalog-diversity re-rank), two Section B GWT blocks (B-7a exclusion-feedback +
grab-reason-never-aired, B-7b catalog-diversity re-rank relaxes on a thin catalog), and amended
AC-NFR-P-7 with axis (e). 1:1 REQ ↔ AC preserved (71 REQ + 9 NFR = 80).

(2026-06-23, v0.7.3 — audit fix pass, matches spec.md v0.7.3:) AC-PL-008 clause (c) + the B-7a GWT
updated in lockstep with the canonical REQ-PL-008 change — the grab reason now POPULATES the
ANALYSIS-006 REQ-AD-006 `grab_reason` field (ANALYSIS owns the field; Group PL owns the populating
logic), replacing the prior "threaded into REQ-PL-001 `acquired_context` / no new field schema"
wording; semantics unchanged. The six spec.md EARS-header relabels ("Unwanted" → "Ubiquitous":
PC-004, PT-005, PG-002, PG-004, PV-006, PV-017) are header-only and do not affect any AC. 1:1
REQ ↔ AC preserved (71 REQ + 9 NFR = 80).

(2026-06-23, v0.8.0 — long-form episode-craft extension, matches spec.md v0.8.0:) Added eight
acceptance entries — AC-PT-009 (long-form format instances inherit the rails), AC-PG-007 (episode-level
Tier-3 coherence gate), AC-PG-008 (quote-sourcing lint), AC-PC-011 (extended-monologue + track-interleave
craft), AC-PV-018 (long-form delivery voice model), AC-PV-019 (episode-persona-state threading),
AC-PI-006 (frozen-anchor audit across episodes), AC-NFR-P-10 (long-form episode integrity) — plus one
Section B GWT block (B-24 long-form episode integrity) and a Section C item 9 (long-form episode craft).
All ADDITIVE; the FROZEN invariants are inherited unchanged (fictional-persona guardrail REQ-PT-005,
open/close disclaimer REQ-PT-006, fact contract REQ-PG-001, grounding REQ-PG-002, per-break two-tier
gate REQ-PG-005, anti-convergence REQ-PR-004, anchor freeze REQ-PI-002). PIVOT-CONSISTENT: REQ-PG-008
gates ATTRIBUTED-SPEECH quotes for TRUTH, never lyric usage (lyrics ungated). 1:1 REQ ↔ AC preserved
(78 REQ + 10 NFR = 88).

---

## Section A — Acceptance Criteria (1:1 with requirements)

### Group PR — Roster & Persona Model

**AC-PR-001 (REQ-PR-001 — two-level identity).** The persona model represents a
STATION-LEVEL house identity (shared ethos/sound) and PER-SHOW PERSONA identities that
inherit it. Verify: (a) a station-house identity record exists with the apolitical/
curatorial ethos; (b) each persona record references/inherits the house ethos; (c) a
persona's expressed taste/POV is its own while its ethos matches the house;
(d) station IDs use the house identity, shows use the persona identity. Both levels'
content is AI-authored (no fixed copy asserted).

**AC-PR-002 (REQ-PR-002 — multi-persona, default 1, max 2, never 3).** Verify:
(a) the roster contains multiple distinct personas (~5 EN + 2 FO at launch); (b) a
show is assigned exactly 1 host by default; (c) a 2-host show is only created for a
deliberate dialogue/contrast format; (d) [HARD] no show is ever assigned 3+ hosts — an
attempt to do so is rejected. The launch roster size is tunable; the caps are fixed.

**AC-PR-003 (REQ-PR-003 — voice↔persona 1:1, no reuse, separate rosters).** Verify:
(a) each persona has exactly one voice and each voice maps to exactly one persona
(strict 1:1); (b) [HARD] no voice is assigned to two personas — an attempt is rejected;
(c) English personas use Kokoro/Piper voices, Faroese personas use the two adult
teldutala voices; (d) [HARD] no persona is bilingual and English/Faroese rosters are
disjoint.

**AC-PR-004 (REQ-PR-004 — anti-convergence firewall).** Verify: (a) at curation time
a HARD check enforces that no two personas share a PRIMARY genre territory; (b) the
rotation overlap between any two personas stays under the configured cap; (c) the check
is computed over the ANALYSIS-006 feature dimensions (REQ-AD-003); (d) two personas'
taste charters yield MATERIALLY DISTINCT candidate pools (low overlap); (e) the check
is hard (a convergent pairing is blocked), not advisory. See Section B for the GWT.

**AC-PR-005 (REQ-PR-005 — persistent POV).** Verify: (a) each persona has persisted
POV elements (intros, sign-offs, recurring bits, pacing signature); (b) the same
persona's POV is consistent across appearances (not regenerated from scratch each
time); (c) POV content is AI-authored and evolves only under the OPS-004
measured-self-change rails; (d) the persona's recent scripts are used as an avoid-list,
never as in-context exemplars (REQ-OC-006).

**AC-PR-006 (REQ-PR-006 — taste charter).** Verify: (a) every persona has a persisted
taste charter with in/out-of-bounds genres, eras, moods, and signature artists/labels;
(b) the charter is hand- or runtime-authored, system-owned, and runtime-extensible;
(c) the charter is expressed in terms the ANALYSIS-006 dimensions can query;
(d) querying the catalog with the charter returns a distinct candidate pool (feeds the
firewall AC-PR-004).

**AC-PR-007 (REQ-PR-007 — Faroese roster = exactly two solo personas).** Verify:
(a) the Faroese roster contains exactly two personas, one on `Hanna22k_NT` and one on
`Hanus22k_NT`; (b) each has its own taste charter + POV; (c) [HARD] the two never
co-host one show (Faroese shows are single-host); (d) the Faroese roster is separate
from the English one and is not grown beyond two while only two adult Faroese voices
exist.

**AC-PR-008 (REQ-PR-008 — growth gate).** Verify: (a) a new persona is added ONLY with
a documented editorial GAP (a taste territory no current persona covers); (b) a persona
proposed for appeal/reach is rejected; (c) [HARD] before air it passes the BOTH-AXES
test — a free unused voice is available AND its charter passes the anti-convergence
firewall against every existing persona; (d) a candidate failing either axis is not
added. See Section B for the GWT.

**AC-PR-009 (REQ-PR-009 — track-level anti-convergence: per-track cross-show rotation
exclusivity).** Verify: (a) at SELECTION time a HARD predicate prevents an individual track
already adopted into one show's regular rotation from being selected into a DIFFERENT show's
regular rotation; (b) the exclusivity is measured over concrete TRACK IDs (keyed on the
OPS-004 REQ-OB-006 play-history `show_or_episode_id` + the per-track `adopted_by_show` field
extending ANALYSIS-006 `Track`/REQ-AD-001 in place, defaulting empty so pre-adoption tracks
stay valid), NOT over the ANALYSIS-006 feature pools REQ-PR-004 measures — so thematic/genre
adjacency (Layer 1) is still PERMITTED while identical-track airplay (Layer 2) is forbidden;
(c) the runtime check is the ORCH-005 unified dedup view (REQ-RW-006) `any_persona`
track-surface scope (PROGRAMMING-007 owns the RULE, ORCH-005 performs the cross-persona check;
referenced, not re-owned); (d) a director-DECLARED, TIME-BOXED program/theme MAY reference a
specific track cross-show (inheriting ORCH-005 REQ-RW-007 override-and-restore + auto-revert),
but this is NEVER a shared regular rotation; (e) [HARD] on an EMPTY LEGAL SET the rail
gracefully RELAXES to a bounded, LOGGED shared-track exception rather than stall the queue
(continuity wins, mirrors OPS-004 REQ-OA-003b); (f) exclusion operates on TRACK IDs only,
never on taste FEATURE sets, so REQ-PL-004 separability is preserved; (g) the news anchor
(REQ-PI-005) is exempt by construction (no rotation, no anti-convergence slot). See Section B
for the GWT.

### Group PC — Radio-Craft Playbook & Talk Rules

**AC-PC-001 (REQ-PC-001 — talk-break anatomy).** Verify a generated link: (a) backsell
(naming the just-played artist+title) is the default; (b) frontsell, when present,
teases by FEELING and uses NO banned "coming up/up next" phrasing; (c) a periodic re-ID
(artist+track) appears; (d) the link is structured Hook (lead with the interesting
thing) → Body (one idea) → Exit (clean button). Copy is AI-authored.

**AC-PC-002 (REQ-PC-002 — link length + cadence).** Verify: (a) a regular-show link is
≤ ~30s (tunable); (b) talk occurs every 1-3 songs, not over every song; (c) when not
talking, the transition is a clean segue; (d) AI-planned music-only stretches are valid
(consistent with OPS-004 REQ-OF-003). Cadence/ceiling are tunable defaults.

**AC-PC-003 (REQ-PC-003 — hit the post).** Verify: (a) the talk-break length is sized
from the analyzed INSTRUMENTAL intro length (ANALYSIS-006 cue/tempo, REQ-AT-001/002/
003/005); (b) the break lands its last word as the vocal begins (or the outro ends);
(c) [HARD] no talk is ever written/scheduled over a VOCAL; (d) when the instrumental
intro is too short, the system uses talk-over-outro / bed / clean-segue instead, never
a vocal talk-over and never overrunning the post. See Section B for the GWT.

**AC-PC-004 (REQ-PC-004 — anti-cheese firewall).** Verify generated talk: (a) contains
NONE of the banned phrases ("stay tuned", "coming up", "up next", "don't go anywhere",
"back-to-back", "all your favourites"); (b) has no forced/manufactured enthusiasm,
radio-voice cliché, or rambling; (c) writes to ONE listener ("you"), not a crowd;
(d) is enforced by the OPS-004 quality gate (REQ-OF-006) and references — does not fork
— the OPS-004 anti-slop discipline (REQ-OF-005).

**AC-PC-005 (REQ-PC-005 — energy arcs / daypart presets / bridges).** Verify: (a) a
daypart applies an energy/personality preset (morning bright/frequent → … → overnight
intimate/sparse), anchored to local Faroe time (REQ-OA-009); (b) a block follows a
set-phase arc (warm-up → … → send-off) where cool-downs SLOPE (no crash) and the last
1-3 tracks carry extra weight; (c) successive tracks avoid jarring tempo/key jumps
(ordered on ANALYSIS-006 bpm/key/energy, REQ-AD-004); (d) presets/arcs are
AI-authored/tunable.

**AC-PC-006 (REQ-PC-006 — theme generators).** Verify: (a) themed shows/segments are
drawn from the rotating generator set (decade/era, place, mood/activity, genre
deep-dive, artist spotlight, anniversary/calendar, listener-curated hour, connective
thread); (b) the generator used rotates so themes stay varied; (c) themes are
AI-authored (consuming OPS-004 show-prep REQ-OC-002); (d) the category set is
extensible.

**AC-PC-007 (REQ-PC-007 — rotate what-hosts-say categories).** Verify across
successive talk breaks: (a) the say-category rotates among artist/track context,
personal reaction, connective tissue, time/weather/locale, listener shout-outs; (b) the
SAME category is not used twice in a row; (c) shout-outs come from the listener-signals
contract (CORE-001 REQ-D-008); (d) the category set is tunable.

**AC-PC-008 (REQ-PC-008 — craft lives in the self-learning store).** Verify: (a) the
PC-001…PC-007 content/rules are stored as editorial knowledge in the OPS-004 playbook
store (REQ-OD-001); (b) the store is available as context to talk generation, show-prep,
and the program director (REQ-OD-004); (c) the content is refined over time by the
OPS-004 refinement loop (REQ-OD-003) under the measured-self-change rails (REQ-OD-006);
(d) [HARD] the craft is seed content the station self-improves (not static hardcode) and
is NEVER fed back as in-context style exemplars (REQ-OC-006). PROGRAMMING owns the
content; OPS-004 owns the store.

**AC-PC-009 (REQ-PC-009 — periodic re-ID for new tuners).** Verify: (a) at the
configured interval / natural boundaries, a re-ID names the station (house identity) and,
where relevant, the current/just-played artist+track; (b) the cadence is tunable and may
vary by daypart; (c) this is distinct from the top-of-hour station-ID slot (OPS-004
REQ-OE-008) — it is in-link re-ID content.

**AC-PC-010 (REQ-PC-010 — open on the strongest hook).** Verify: (a) a show/segment/
block opens on its strongest hook (song or line) within ~15s; (b) the "strongest"
judgment is AI-made (informed by taste charter + energy arc); (c) the open front-loads
the hook rather than easing in; (d) applies to recurring shows (REQ-PT-002) and the
Solstice Hour open (REQ-PT-004).

**AC-PC-011 (REQ-PC-011 — extended-monologue + track-interleave craft).** Verify a long-form
episode (REQ-PT-004 / REQ-PT-009): (a) is written as ~5-15-minute (tunable) ducked-music-bed
monologue BLOCKS, each with its own block-scale Hook→Body→Exit, NOT a string of 30s links;
(b) [HARD] long-form BACKTIMES each interwoven track entry — the lead-in is sized to hand off
into the track's cue-in/instrumental intro (ANALYSIS-006 REQ-AT-*), the ducked bed RAMPS up to
the track, and the track is BACKSOLD when narration resumes; (c) [HARD] never talks over a vocal
at any interleave (REQ-PC-003 rail holds; safe fallback ladder per transition); (d) the block
size + interleave count are tunable; this owns the long-form CRAFT (VOICE-002 owns ducking,
ANALYSIS-006 owns cues, REQ-PV-018 owns the delivery voice). See Section B for the GWT.

### Group PS — Script-Side Ear-Writing

**AC-PS-001 (REQ-PS-001 — one thought, ≤20 words).** Verify: (a) generated script
sentences carry one thought each and are ≤ ~20 words (tunable); (b) over-long sentences
are rejected/regenerated by the quality gate (OPS-004 REQ-OF-006); (c) this is a script
rule, synthesis is VOICE-002's.

**AC-PS-002 (REQ-PS-002 — contractions, singular second person).** Verify: (a) scripts
always use contractions; (b) scripts address ONE listener in the second person ("you"),
never a crowd; (c) the rule is enforced, the copy is AI-authored.

**AC-PS-003 (REQ-PS-003 — punctuate for breath, vary length).** Verify: (a) scripts use
commas/em-dashes/ellipses to mark natural pauses; (b) sentence length varies (not
monotone); (c) punctuation serves the ear (prosody), not the page.

**AC-PS-004 (REQ-PS-004 — blank-line blocks = synthesis chunks).** Verify: (a) scripts
are structured as 1-2 sentence blocks separated by blank lines; (b) [HARD coordination]
those blank-line boundaries are the boundaries at which VOICE-002 chunks the script for
synthesis with inter-chunk silence; (c) the alignment produces speakable pacing;
(d) VOICE-002 owns the chunk+silence render, this SPEC owns writing the block boundaries
to match. See Section B for the GWT.

**AC-PS-005 (REQ-PS-005 — spoken numbers/dates, IPA override).** Verify: (a) numbers
and dates are spelled as spoken ("twenty twenty-six", "nineteen seventy-three"), not as
raw digits; (b) a hard name can carry an IPA/phoneme-spelling override; (c) VOICE-002
consumes the override at synthesis; (d) which names get overrides is the AI's call.

### Group PT — Show Formats incl. Solstice Hour

**AC-PT-001 (REQ-PT-001 — recurring show format spec).** Verify a recurring show has:
(a) an AI-invented name (no reference-station trademark, OPS-004 REQ-OB-004); (b) a fixed
appointment slot; (c) a stable skeleton; (d) an open/close ritual; and (e) [HARD] it is
recognizably the same show each time (name/slot/skeleton/ritual consistent). Slot
placement is OPS/ORCH's; the format content is this SPEC's.

**AC-PT-002 (REQ-PT-002 — recurring shows open on strongest hook).** Verify a recurring
show opens on its strongest hook within ~15s (REQ-PC-010); the hook choice is AI-made
from the show theme + presenting persona's charter.

**AC-PT-003 (REQ-PT-003 — recurring named segments).** Verify a show can define/run/
evolve/retire its own recurring named segments (over OPS-004 REQ-OB-004), each with an
AI-invented name + selection rule; no reference-station trademarked segment names are
used.

**AC-PT-004 (REQ-PT-004 — Solstice Hour long-form).** Verify a Solstice Hour /
Summarrødd episode: (a) is ~60 min in the weekly flagship slot; (b) is a 3-act life-arc
monologue (origins → turn/struggle → vocation → reflection) by a single fictional
persona; (c) interweaves 4-5 narratively-motivated legally-airable library tracks;
(d) [HARD] is single-narrator long-form (2-voice is the optional variant REQ-PT-008);
(e) carries emotion via ear-writing + engineered pauses + a ducked bed (not vocal
performance). Length/track-count are tunable. See Section B for the GWT.

**AC-PT-005 (REQ-PT-005 — original fictional persona only).** Verify: (a) the guest is
an AI-authored ORIGINAL FICTIONAL persona; (b) [HARD] the episode never impersonates,
presents as, or attributes fabricated testimony to a REAL named person; (c) the story is
apolitical (OPS-004 REQ-OF-004); (d) the story carries no real-world factual claims about
a living or identifiable person. See Section B for the GWT.

**AC-PT-006 (REQ-PT-006 — mandatory open+close disclaimer).** Verify: (a) every episode
includes a spoken disclaimer at the OPEN stating the guest is a fictional persona voiced
by the station; (b) every episode includes the same disclaimer at the CLOSE; (c) [HARD]
an episode missing EITHER disclaimer does NOT air; (d) the wording is AI-authored in the
episode's language (EN/FO). See Section B for the GWT.

**AC-PT-007 (REQ-PT-007 — pre-rendered to one file).** Verify: (a) the whole episode
(monologue TTS + tracks + ducked bed + pauses) is pre-rendered to ONE self-contained
file; (b) the file is loudness-normalized to the shared target (-16 LUFS / -1.5 dBTP,
OPS-004 REQ-OE-005); (c) [HARD] the file airs as one pre-rendered item via the OPS-004
ready buffer (REQ-OE-012) / pull seam — nothing is assembled live; (d) it consumes the
OPS-004 pre-render machinery (no fork).

**AC-PT-008 (REQ-PT-008 — optional 2-voice variant + format-study).** Verify: (a) the
optional 2-voice interview variant uses a fictional host + fictional guest STRICTLY
within the max-2 cap and under the same guardrail + disclaimers (PT-005/006); (b) a
Faroese long-form stays single-host (REQ-PR-007); (c) the format-study capability studies
public formats from transcripts/press/RSS descriptions to inform craft, NEVER to copy a
real episode's content; (d) both are optional/advanced and respect source terms.

**AC-PT-009 (REQ-PT-009 — long-form format instances inherit the long-form rails).** Verify a
LONGFORM-025-conceived long-form instance (album-doc / artist-retrospective / era-spotlight):
(a) is single-narrator (or the optional 2-voice variant strictly within the max-2 cap,
REQ-PT-008/REQ-PR-002), interweaves narratively-motivated library tracks, and is carried by
ear-writing (Group PS) + pauses + a ducked bed (REQ-PV-018); (b) [HARD] is pre-rendered to ONE
loudness-normalized file and queued via the OPS-004 ready buffer (REQ-PT-007), zero live assembly;
(c) [HARD] passes the episode-level grounding gate (REQ-PG-007 Tier-3 coherence + REQ-PG-008
quote-sourcing); (d) [HARD] when it voices an INVENTED character it carries the fictional-persona
guardrail (REQ-PT-005) + the mandatory open-AND-close disclaimer (REQ-PT-006) and never
impersonates / attributes fabricated testimony to a real person and never carries politics;
(e) [HARD] for a REAL-SUBJECT episode the truth load is carried by the grounding rule (REQ-PG-002)
+ quote-sourcing (REQ-PG-008), never by fabricating the real subject's biography/testimony;
(f) LONGFORM-025 Group LB owns the instance conception (topic/segment-plan/sourcing), referenced
not re-owned. See Section B for the GWT.

### Group PL — Taste Self-Learning, Provenance & Feedback (added v0.2.0)

**AC-PL-001 (REQ-PL-001 — track provenance).** Verify: (a) every track record carries
`acquired_for` (persona/show or "unattributed/house"), `acquired_context` (why / which
curation decision), and `source` (slskd / yt-dlp / manual-drop); (b) the fields EXTEND the
ANALYSIS-006 `Track` record in place (no fork); (c) a curation-acquired track records the
acquiring persona + reason; (d) the gap is closed — the audited brain had no such fields
(downloads and manual drops were indistinguishable once indexed).

**AC-PL-002 (REQ-PL-002 — manual-drop attribution).** Verify: (a) a file ingested with no
acquiring persona (manual drop via ANALYSIS-006 REQ-AP-007, or house acquisition) gets
`acquired_for = "unattributed/house"`; (b) it is a fully VALID, curatable catalog member
once analyzed; (c) it becomes curatable by whichever persona's taste it fits (features
matched against profiles); (d) [HARD] the manual drop is a NON-BINDING signal, never a
constraint and never a pandering target. See Section B for the GWT.

**AC-PL-003 (REQ-PL-003 — acquisition diary).** Verify: (a) each curation/acquisition
batch writes a structured diary entry capturing "persona wanted X for reason R → acquired
from Y → outcome Z"; (b) the entry is a VIEW written into the OPS-004 ledger/diary substrate
(REQ-OD-007/008), not a new store; (c) it is distinct from the orphaned `attempts.json`
(which records only success/fail+method, not fed into taste); (d) the diary feeds the
taste-evolution signals (REQ-PL-005).

**AC-PL-004 (REQ-PL-004 — evolving per-persona profile).** Verify: (a) each persona has a
PERSISTED taste profile seeded from its Group PR charter (REQ-PR-006); (b) [HARD] it is
per-persona (no global single taste — closes the audited gap), persists across restarts, and
is expressed over the ANALYSIS-006 dimensions; (c) the profile refines over time;
(d) [HARD] an EVOLVED profile still passes the anti-convergence firewall (REQ-PR-004) against
every other persona — refinement never erodes plurality. See Section B for the GWT.

**AC-PL-005 (REQ-PL-005 — taste-evolution signals).** Verify: (a) the profile learns from
play-through vs early-skip/replace, recency, and the OPS-004 listener-signal/contact-form
input (CORE-001 REQ-D-008); (b) [HARD consistency] no path uses play count, skip rate, or
feedback volume/sentiment as a score to MAXIMIZE — signals are human-curatorial context,
never an appeal target (anti-pandering, OPS-004 REQ-OF-004 / NFR-O-7); (c) the signal set is
tunable. See Section B for the GWT.

**AC-PL-006 (REQ-PL-006 — measured taste-evolution loop).** Verify: (a) taste-profile
changes are GRADUAL — bounded change rate, cooldown honored between applied changes, no
thrashing; (b) [HARD] the mechanism is the OPS-004 measured-self-change framework (REQ-OD-006:
rate limiter + cooldown + canary + contradiction detection) applied to taste; (c) the loop
bounds how FAST taste changes, not how much the AI may LEARN; (d) it is not
engagement-maximization (anti-goal). See Section B for the GWT.

**AC-PL-007 (REQ-PL-007 — seed enrichment bootstrap).** Verify: (a) initial per-persona
profiles can be enriched from the non-binding seed (Spotify `tritnaha` `/me/tracks` +
YouTube `@tritnaha1345` liked) via a ONE-TIME OAuth, wiring the existing
`config.SEED_ENRICHMENT_STUBS` + `director._seed_reference()` stubs; (b) [HARD consistency]
the seed is a REFERENCE, never a constraint — it bootstraps then is free to be diverged from,
never pins/gates ongoing taste, never an appeal target; (c) the OAuth is one-time, the
enrichment is optional/config-gated, and an unavailable seed never blocks operation.

**AC-PL-008 (REQ-PL-008 — grab-reason capture; unverified director claim).** Verify: (a) when
the director proposes an acquisition, the reason is captured as STRUCTURED per-item output
`{artist, title, reason}` AT GRAB TIME, criterion-guided by + citing the prompt's seed/recent/
exclusion context (REQ-PL-007/009/004); (b) it is NOT a free-form retrospective narrative (the
hallucination failure mode); (c) it POPULATES the ANALYSIS-006 REQ-AD-006 `grab_reason` field
(ANALYSIS owns the field + write-discipline on the `Track` record REQ-AD-001 in place, no fork;
Group PL owns the populating logic) and is threaded into the REQ-PL-001 `acquired_context`
provenance and the diary (REQ-PL-003);
(d) [HARD] it is stored/used as an UNVERIFIED director CLAIM — it never enters the closed-world
fact contract (REQ-PG-001) and no aired host break states it as a certainty (grounding REQ-PG-002,
consensus KNOWLEDGE-008 REQ-KS-006). See Section B for the GWT.

**AC-PL-009 (REQ-PL-009 — exclusion-feedback into the curator prompt).** Verify: (a) the curator/
acquisition prompt (driven by the REQ-PL-004 profile) carries explicit `already_have` (recently-
ACQUIRED, from catalog + REQ-PL-001 provenance) + `recently_rejected` (recently-ATTEMPTED/FAILED/
no-candidate, from the REQ-PL-003/010 diary outcomes + OPS-004 Group OH attempts) exclusion sets;
(b) [HARD] these are ADDITIVE to the recently-played `recent` exclusion the director already passes
— `recent` is the EPHEMERAL playout window, `already_have`/`recently_rejected` are the PERSISTENT
acquisition history (the two-no-repeat separation); (c) with the exclusion context, a batch proposes
genuinely NEW candidates rather than re-proposing items the gate silently drops (the verified
near-zero-new-acquisition / wasted-quota gap is closed); (d) the window sizes + prompt format are
tunable. See Section B for the GWT.

**AC-PL-010 (REQ-PL-010 — acquisition diary outcome taxonomy).** Verify: (a) each proposed item's
OUTCOME is recorded in the diary (REQ-PL-003) as exactly one of `success` / `failed` /
`no-candidate`; (b) the diary now covers ATTEMPTED-BUT-NOT-ACQUIRED items (closing the audited gap
where the orphaned `attempts.json` dropped `no-candidate` items, Section 1.7); (c) it is written
into the OPS-004 ledger/diary substrate (REQ-OD-007/008) as part of the same VIEW — no new store;
(d) the outcome feeds the REQ-PL-009 `recently_rejected` set + the REQ-PL-005 taste signals (an
outcome is human-curatorial context, never an appeal target, OPS-004 REQ-OF-004).

**AC-PL-011 (REQ-PL-011 — catalog-diversity re-rank; relaxes on a thin catalog).** Verify:
(a) acquisition candidates are re-ranked by an MMR-style relevance+diversity score that biases
AGAINST re-grabbing the same artist / same sonic cluster, using the ANALYSIS-006 features
(REQ-AD-003) + the KNOWLEDGE-008 similar-artist graph (REQ-KG-001/003); (b) [HARD] it is
ACQUISITION-TIME anti-repetition, DISTINCT from the playout no-repeat (it re-ranks what to ACQUIRE,
never what to PLAY — OPS-004 REQ-OA-003a + ORCH-005 REQ-RW-006 + PROGRAMMING REQ-PR-009 own playout
rotation); (c) [HARD] the diversity pressure is GATED on catalog size and RELAXES below the wishlist
low-watermark so a small/new catalog is never STARVED (mirrors OPS-004 REQ-OA-003b continuity-wins;
ties to REQ-OH-001 acquisition balance); (d) the MMR weights + watermark value are tunable. See
Section B for the GWT.

### Group PG — Grounded Host Voice & Quality Gate (added v0.3.0)

**AC-PG-001 (REQ-PG-001 — closed-world fact contract).** Verify: (a) the talk LLM receives
exactly ONE fact bundle = a verified TrackContext (artist/title/album, year|null, genres[],
folksonomy_tags[], mood/energy/bpm/key, sonic-character REQ-AE-006, similar_artists[{name,
match_score}], prior_track, next-as-MOOD-not-name) + optional ShowPrep facts each with a
`source_url`; (b) [HARD] the bundle is the ONLY allowed source of fact — the LLM does not
draw facts from free-recall; (c) the next item is supplied as a MOOD hint, not a name;
(d) bundle values come from ANALYSIS-006 + KNOWLEDGE-008 (this SPEC contracts supply, does
not produce facts). See Section B for the GWT.

**AC-PG-002 (REQ-PG-002 — grounding rule).** Verify: (a) [HARD] a fact absent from context
(year/label/producer/members/chart/award/location/anecdote) is NOT spoken — no guessing/
approximating; (b) PERCEPTUAL audio description (e.g. "a slow, heavy groove") IS allowed,
grounded in the audible/sonic-character profile; (c) NAMED factual attribution (specific
instrument/gear/personnel) only if in context; (d) silence about a fact beats a confident
wrong fact (host-voice expression of OPS-004 REQ-OC-005). See Section B for the GWT.

**AC-PG-003 (REQ-PG-003 — comparison discipline).** Verify: (a) an artist comparison appears
ONLY when grounded — similar_artists match_score ≥ ~0.6, a shared genre/tag, or a ShowPrep
fact (shared label/scene/producer/era); (b) [HARD] fusion formulas ("X sounds like A meets
B", "lovechild of") are banned; (c) at most ONE comparison per break; (d) a concrete grounded
observation is preferred and no comparison is forced when none is grounded. See Section B for
the GWT.

**AC-PG-004 (REQ-PG-004 — anti-slop register).** Verify generated host copy: (a) contains
NONE of the banned music-slop phrases ("sonic journey", "lush soundscapes", "effortlessly
blends", "a testament to", "needs no introduction") or LLM tells ("delve/leverage/elevate",
negative-parallelism, rule-of-three adjective piles); (b) follows the positive rules
(specificity over adjectives, genuine POV, show-don't-tell, one idea/break, plain words, OK
to say little); (c) [HARD] EXTENDS OPS-004 REQ-OF-005 (references, does not fork it); (d) the
list + positive rules are tunable config.

**AC-PG-005 (REQ-PG-005 — two-tier quality gate).** Verify: (a) Tier-1 deterministic lint
runs banned-register + banned-construction scan, a FORBIDDEN-FACT scan (every year/label/
producer/personnel token must appear in context; a year disagreeing with context = FAIL),
and a comparison-grounding check; (b) Tier-2 adversarial self-check lists every factual claim
and flags any NOT supported by context (unsupported = FAIL); (c) on FAIL the script
regenerates ONCE, on a second FAIL the break is SKIPPED; (d) [HARD] a FAIL never ships;
refines OPS-004 REQ-OF-006; graceful-skip preserves never-stops. See Section B for the GWT.

**AC-PG-006 (REQ-PG-006 — persona voice card).** Verify: (a) a per-persona voice card is
injected into EVERY talk-generation call; (b) the SAME card is used each call for that
persona (consistency); (c) [HARD] the card has a hard length cap and confines opinion to the
AUDIBLE; (d) traits are tunable config and coordinate with the Group PR persistent POV
(REQ-PR-005) + Group PC craft.

**AC-PG-007 (REQ-PG-007 — episode-level Tier-3 coherence gate).** Verify a whole long-form
episode script (REQ-PT-004 / REQ-PT-009) before pre-render: (a) [HARD] runs an ARC-BEATS-IN-ORDER
check (beats appear in the planned order, none missing/duplicated); (b) [HARD] runs a CROSS-SEGMENT
NON-CONTRADICTION check (no segment contradicts another segment or the fact contract REQ-PG-001);
(c) [HARD] runs a PERSONA-CHARTER CONSISTENCY check (the narrator stays consistent with its frozen
anchor REQ-PI-001 + persistent POV REQ-PR-005 across segments, coordinating with REQ-PV-019);
(d) [HARD] on FAIL the failing segment regenerates once, on a second FAIL the WHOLE episode is
DEFERRED (falls back to regular programming) and NEVER airs incoherent; (e) the Tier-3 gate is
ABOVE the UNCHANGED per-break Tier-1/Tier-2 gate (REQ-PG-005), which still runs on every segment;
(f) the deferral preserves never-stops (NFR-P-5/P-10). See Section B for the GWT.

**AC-PG-008 (REQ-PG-008 — quote-sourcing lint).** Verify: (a) [HARD] a quoted INTERVIEW or
LINER/PRESS phrase attributed to a person/source ("X said …") requires `source_url` + `speaker`
+ `date` in the fact contract or it is a FAIL; (b) [HARD] on FAIL the quote is DROPPED (or the
break/segment regenerated-once-then-skipped per REQ-PG-005 / deferred per REQ-PG-007), so an
unsourced attributed quote NEVER airs (a fabricated "X said Y" never airs); (c) it EXTENDS the
REQ-PG-005 Tier-1 forbidden-fact scan to quotes (a quote = a fact-with-attribution, governed like
REQ-PG-002); (d) [HARD] PIVOT-CONSISTENT — verbatim song LYRICS are NOT gated (no lyric source/
legal gate; the lyric is the on-air song, not an external attributed claim); a contested single-
source READING is HEDGED, not banned (KNOWLEDGE-008 REQ-KS-006). See Section B for the GWT.

### Group PV — Host-Voice Persona-Awareness, Delivery Craft & Continual Improvement (added v0.4.0)

**AC-PV-001 (REQ-PV-001 — live-human persona-awareness).** Verify: (a) the shared
HOST_PERSONA is a POSITIVE live-human identity (one person, one mic, talking to one listener),
NOT the negation-based "not a corporate announcer / not a chirpy AI" form; (b) "live human
host" shapes DELIVERY (present tense, second person, one-to-one intimacy) and is NEVER stated
as a claim — generated copy never says it is live/real/an AI/a script and never breaks the
fourth wall; (c) the persona-awareness is the station-house parent onto which the voice card
(REQ-PV-009) layers; (d) grounding (KNOWLEDGE-008/REQ-PG-002) is unchanged — no new
claim-making latitude. (Amended v0.5.0:) (e) the positive identity carries a concrete
MUSIC-JOURNALIST register lineage (6 Music / NTS / KEXP) + the "text one smart, slightly-impatient
friend" addressee frame (a delivery stance, never a spoken claim); (f) any persona self-disclosure
draws ONLY from the persona's OWN frozen fictional life/temperament (REQ-PI-001), never a shared
cross-persona template and never an "I'm an AI"/fourth-wall break. See Section B for the GWT.

**AC-PV-002 (REQ-PV-002 — calibrated delivery DO-set).** Verify a generated break: (a) is
punctuated for breath (commas/em-dash/ellipsis) with varied sentence length; (b) always uses
contractions and one thought ≤~20 words; (c) includes at most ONE vivid, concrete, GROUNDED
detail (theater-of-the-mind), never adjective piles, drawn only from the fact contract/
sonic-character; (d) addresses ONE listener ("you"), never a crowd; (e) follows Hook→Body→Exit
at ≤30s. (Amended v0.5.0:) (f) the break LEADS with one plain, OWNED reaction THEN one concrete
grounded/audible detail (subject-verb-early; a flat true sentence over an impressive one),
countering the diagnosed pink-elephant retreat. The DO-set references the PS/PC/PG rules; copy is
AI-authored.

**AC-PV-003 (REQ-PV-003 — delivery-energy vs hype split).** Verify: (a) energy is carried by
rhythm, specificity, and block length calibrated to the persona's daypart energy band (morning
bright → overnight intimate); (b) energy is NEVER carried by exclamation marks, manufactured
excitement, or hype words (REQ-PC-004 ban holds); (c) energy is treated as a WRITING property
(degrades to a writing effect even where flat TTS does not move, R-P-2); (d) the band wording
is tunable.

**AC-PV-004 (REQ-PV-004 — ear-writing rails in the live prompt).** Verify: (a) the live
talk-generation prompt explicitly carries the ear-writing rails (REQ-PS-001..005): always
contractions, one thought ≤~20 words, punctuate for breath, vary length, 1-2-sentence
blank-line blocks, spoken numbers/dates; (b) [HARD coordination] the blank-line block rail is
present and aligns with the VOICE-002 synthesis chunk boundaries (REQ-PS-004) — it is not
removed or broken; (c) the audited gap (these rails absent from `_build_talk_prompt`) is
closed. See Section B for the GWT.

**AC-PV-005 (REQ-PV-005 — unifying principle).** Verify: (a) the governing rule "warmth and
energy in delivery, restraint in content" is encoded as the spine of the PV calibration;
(b) [HARD] turning delivery up never relaxes the grounding rule (REQ-PG-002), the anti-slop
register (REQ-PG-004/REQ-PV-006), or the comparison discipline (REQ-PG-003); (c) the principle
reconciles the warmth/energy/teasing wishlist with every existing ban. (Amended v0.5.0:) (d) the
DELIVERY axis explicitly includes the banter band — blunt phrasing, dry humour, profanity (per the
per-persona policy REQ-PV-013), and grounded self-disclosure (REQ-PV-014) — each on DELIVERY only,
relaxing no content ban; (e) both the banter recalibration (Group PV) and the persona-identity model
(Group PI) compose on this spine (PV tunes DELIVERY on the EVOLVABLE layer; PI freezes WHO the
persona is).

**AC-PV-006 (REQ-PV-006 — extended banned list).** Verify generated host copy: (a) contains
NONE of the preserved existing bans (cliché filler incl. "coming up/up next/stay tuned", forced
enthusiasm, music-slop + LLM-tell register, fusion-comparison formulas, ungrounded facts,
emoji/markdown/stage-directions/fourth-wall); (b) [HARD] does NOT over-use a warmth-transition
(≤1 per break, never the same tic two breaks running — filler-as-crutch banned); (c) [HARD]
draws warmth-transitions ONLY from the persona's OWN disjoint tic bank — no global shared filler
set, and no two personas share a tic (anti-convergence REQ-PR-004); (d) the bans extend, and
reference — do not fork — the PC/PG bans. (Amended v0.5.0:) (e) every ban is PAIRED IN THE PROMPT
with a positive "say this instead" twin (the ban stays the Tier-1 firewall; the twin is carried in
the prompt to fill the vacuum), and (f) the twins steer FORM only — the fact contract (REQ-PG-001)
still supplies all CONTENT, so a warm prompt cannot reopen the slop the gate catches. See Section B
for the GWT.

**AC-PV-007 (REQ-PV-007 — tease-by-feeling frontsell).** Verify: (a) a frontsell, when present,
teases ONLY the next track's mood/energy shift; (b) [HARD] it never names the next artist/title
and never uses the banned "coming up/up next/stay tuned"; (c) the next track is supplied to the
LLM as a MOOD hint, not a name (TrackContext "next = MOOD hint", REQ-PG-001); (d) the
artist+title name is reserved for the following break's backsell (REQ-PC-001). See Section B for
the GWT.

**AC-PV-008 (REQ-PV-008 — mandatory frontsell code-fix / live regression).** Verify: (a) the
talk-context assembly NO LONGER passes the next track's artist/title NAME (`brain/talk.py`
`_build_context` no longer sets `next_artist`/`next_title`); (b) the talk prompt
(`brain/llm.py` `_build_talk_prompt`) NO LONGER contains the banned `Coming up next: "{title}"
by {artist}` block or the "name the artist and title" upcoming-track instruction; (c) the
context instead carries a `next_mood`/energy hint DERIVED from the ANALYSIS-006 features (never
the name), and the prompt offers an OPTIONAL feeling-tease that forbids naming and forbids the
banned filler; (d) [HARD] this clears the currently-airing banned-phrase regression on the live
path (no aired break emits "coming up next"). See Section B for the GWT.

**AC-PV-009 (REQ-PV-009 — extended voice card).** Verify: (a) the per-persona voice card
(REQ-PG-006, injected every call, identical each call) carries a per-daypart ENERGY BAND, a
PACING SIGNATURE, a REGISTER, and a 3-5-entry VERBAL-TIC BANK; (b) [HARD] the tic bank is
DISJOINT across personas (REQ-PR-004) and used sparingly (≤1/break, never the same tic two
breaks running, REQ-PV-006); (c) the card is persisted and EVOLVABLE (self-refines under
REQ-PV-011 within the distinctness rails); (d) it threads into HOST_PERSONA (REQ-PV-001) +
`_build_talk_prompt` WITHOUT breaking grounding (delivery shape + opinion-about-the-audible
only, never facts). (Amended v0.5.0:) (e) the card ALSO carries four new EVOLVABLE delivery fields —
`profanity_tier` {none|mild|salty}, `humour_mode` {dry|warm|deadpan|none}, `self_disclosure`
{frequency, register-slice}, and a 2-3-entry blunt-praise starter set — all DISJOINT across personas
(REQ-PV-010); (f) [HARD] the card's fields are split explicitly into a FROZEN CORE (anchor focuses +
core temperament + voice signature + pacing — the REQ-PI-001 anchor block, never loop-writable) vs
an EVOLVABLE LAYER (tic-bank wording, energy/register/bluntness/humour/self-disclosure tone, surface
tastes, new card fields — the loop's only write-set). See Section B for the GWT.

**AC-PV-010 (REQ-PV-010 — distinctness + crutch lints).** Verify the Tier-1 deterministic lint
(extending REQ-PG-005): (a) FAILS a script exceeding the warmth-transition frequency cap (≤1/
break) or repeating the persona's previous-break tic; (b) FLAGS a cross-persona tic COLLISION
(no two personas share a tic), enforcing REQ-PV-006/009 + REQ-PR-004 at the talk layer; (c) the
lints ride the existing two-tier gate and its regenerate-once-then-skip behavior; (d) the cap
is tunable. (Amended v0.5.0:) (e) the cross-persona collision check ALSO covers the new REQ-PV-009
card fields — no two personas share the {profanity_tier + humour_mode + self-disclosure
register-slice + blunt-praise starter set} combination — the same machinery the REQ-PI-004
distinctness canary uses on an evolvable change. See Section B for the GWT.

**AC-PV-011 (REQ-PV-011 — bounded continual-improvement loop).** Verify: (a) the loop refines
prompts/rules/voice-cards/playbook content in the OPS-004 store (REQ-OD-001/003), promoting
learnings observation→heuristic→rule→graduated from the per-break gate signal + ledger/diary;
(b) [HARD] it is iterative REFINEMENT, NOT model fine-tuning (no training path); (c) [HARD] it
is bounded by the OPS-004 measured-self-change rails (REQ-OD-006: rate limiter + canary +
contradiction detection); (d) [HARD] it NEVER self-imitates (REQ-OC-006), NEVER optimizes an
engagement/appeal/popularity metric (curation bright line), and NEVER evolves the FROZEN
invariant set (never-ship-a-FAIL REQ-PG-005, grounding REQ-PG-001/002 + KNOWLEDGE-008,
anti-convergence REQ-PR-004, banned-phrase firewall REQ-PC-004/REQ-PV-006, fictional-persona
ethics REQ-PT-005/006, no-self-imitation REQ-OC-006, host caps REQ-PR-002); the human is out
of the run loop. See Section B for the GWT.

**AC-PV-012 (REQ-PV-012 — blunt-praise license).** Verify: (a) blunt, plain, OWNED praise is
licensed as first-class delivery (if it rules, say it rules; a flat true sentence beats an
impressive one); (b) [HARD] a praise/reaction line is VALID only if it is BOTH first-person/owned
AND specific (points at one audible element, a grounded fact, or a true persona self-reaction) — a
borrowed-PR-vocabulary line floating free FAILS ("This fucking rules — wait for the drum fill at 90
seconds" PASSES; "a captivating sonic journey" FAILS); (c) [HARD] it relaxes NOTHING on the CONTENT
axis (grounding REQ-PG-002 + anti-slop REQ-PG-004/REQ-PV-006 unchanged); (d) it is enforced as a
Tier-1 lint check (REQ-PV-016) and the validity test is the rail while the phrasing is the AI's. See
Section B for the GWT.

**AC-PV-013 (REQ-PV-013 — per-persona/daypart profanity + humour).** Verify: (a) profanity is
governed by the persona's `profanity_tier` {none|mild|salty} CAPPED DOWN by a daypart gradient
(none morning/family → freest overnight; card tier is a ceiling the daypart only lowers, bound to
the REQ-PV-003/REQ-PC-005 daypart band); (b) humour is governed by `humour_mode`
{dry|warm|deadpan|none} as a GROUNDED aside about the audible/the live moment, never an invented
anecdote-as-fact; (c) [HARD] profanity is delivery colour on an owned+specific reaction (REQ-PV-012),
never on an ungrounded fact or a banned cliché (lazy "banger" stays banned even sworn at), NO quota,
never aimed at a person/artist/group, slurs Tier-1-banned (coordinated with CALLIN-003); (d) these
fields make personas DIVERGE and are DISJOINT across personas (REQ-PV-009/010); the tier/mode +
gradient thresholds are tunable. See Section B for the GWT.

**AC-PV-014 (REQ-PV-014 — three-class content taxonomy + fenced self-disclosure).** Verify: (a)
every clause is classified music-fact | audible-opinion | persona-self-disclosure; (b) [HARD]
music-fact clauses route to the UNCHANGED fact contract (REQ-PG-001/002) + Tier-1 forbidden-fact
scan; (c) audible-opinion is licensed, UNGATED for grounding, uncapped in intensity (the blunt-praise
license), and persona-self-disclosure is licensed as FENCED FICTION; (d) [HARD] self-disclosure is
fenced per REQ-PT-005 — no real-person claim, no autobiographical-truth/fourth-wall claim, apolitical
(the one opinion class that does NOT open up, REQ-OF-004), and no embedded music-fact token; a
class-(b)/(c) clause embedding a music-fact token is RECLASSIFIED to class-(a) and gated, and a
negative claim implying a checkable fact ("this flopped") stays class-(a). The grounding contract
governs ONLY class-(a); "warmth/opinion UP, claim-making restrained" (REQ-PV-005) is preserved. See
Section B for the GWT.

**AC-PV-015 (REQ-PV-015 — positive-register wiring + live-regression fix).** Verify: (a) the live
talk prompt injects the positive-identity HOST_PERSONA with the music-journalist lineage + addressee
frame (REQ-PV-001), the ban→positive-twin pairings (REQ-PV-006), and 2-4 ROTATED GOOD-vs-BAD
exemplar pairs using GENERIC tracks (never the real upcoming track) labelled "VOICE to hit, NOT lines
to reuse"; (b) [HARD] this closes the wiring gap — the deployed `brain/llm.py` HOST_PERSONA
(L261-269) is no longer the OLD negation-only form; (c) [HARD] the exemplars are HAND-AUTHORED
anchors (no-self-imitation REQ-OC-006 holds — never fed-back station scripts) and the fact contract
(REQ-PG-001) supplies CONTENT while exemplars steer FORM; (d) [HARD] RE-AFFIRMS the REQ-PV-008
regression fix still live in code — the prompt no longer passes the next track's NAME nor emits the
"Coming up next" block (`brain/llm.py` L300-303, `brain/talk.py` `_build_context` L135-138). See
Section B for the GWT.

**AC-PV-016 (REQ-PV-016 — specificity + ownership praise lint).** Verify the extended REQ-PG-005
gate: (a) [HARD] Tier-1 FAILS a praise/reaction clause of borrowed critic/PR vocabulary pointing at
no locatable thing (the blunt-praise validity test) — the lazy USE of a hype noun as a floating
verdict ("an infectious banger") FAILS while owned DELIVERY emphasis ("this one just goes") PASSES;
(b) [HARD] Tier-2 ALSO scans audible-opinion + persona-self-disclosure clauses for SMUGGLED
MUSIC-FACT TOKENS (a label/date token in a self-disclosure), reclassifying + gating the clause
(REQ-PV-014) and FAILing an unsupported token; (c) the checks ride the existing two-tier gate +
regenerate-once-then-skip; (d) the borrowed-vocabulary list is tunable, the praise-validity +
smuggled-token enforcement is the rail. See Section B for the GWT.

**AC-PV-017 (REQ-PV-017 — dated / try-hard-slang ban; register currency + authenticity).** Verify
generated host copy: (a) [HARD] contains NONE of the banned dated/try-hard slang ("hip", "swagger",
"groovy", "rad", "far out", "with it", "fly" as a compliment, "the kids", and the "how do you do,
fellow kids" register); (b) follows the POSITIVE RULE — contemporary, natural, REGISTER-TRUE
vocabulary in the persona's OWN voice per its voice card (REQ-PV-009 register / REQ-PI-001 anchor
temperament), never borrowing faux-cool/dated slang to sound young or to dress up a track; (c) [HARD]
this is a DISTINCT axis from the music-slop ban (REQ-PV-006/REQ-PG-004) and the blunt-praise license
(REQ-PV-012/016) — a line that is slop-free AND owned/specific still FAILS if the words are stale or
try-hard ("this track's got real swagger" FAILS even though owned), and blunt praise must be
owned+specific AND register-true to pass; (d) [HARD] it is enforced as a checkable Tier-1 lint
term-class on the REQ-PG-005 gate (riding the REQ-PV-010/REQ-PV-016 lint + regenerate-once-then-skip),
not advisory; (e) the banned-term list is tunable (slang dates), each persona's register-true
vocabulary is its own (disjoint REQ-PV-009/010), and the news anchor is unaffected (excluded by
construction REQ-PI-005). See Section B for the GWT.

**AC-PV-018 (REQ-PV-018 — long-form delivery voice model).** Verify a long-form episode
(REQ-PT-004 / REQ-PT-009) delivery: (a) each monologue block is delivered over a DUCKED MUSIC BED in
the persona's voice-card register (REQ-PV-009), warmth/energy carried by ear-writing + pauses + bed
(designed quiet/measured/reflective per the honest TTS limit R-P-2, never weeping/comic timing);
(b) [HARD] the delivery RAMPS into and out of each interwoven track (measured wind-down / pick-up,
coordinating with REQ-PC-011 backtiming/ramp/backsell); (c) the daypart-calibrated energy band
(REQ-PV-003) is sustained as a WRITING property across the episode, never via exclamation/hype (the
REQ-PC-004/REQ-PV-006 bans hold); (d) [HARD] the warmth-in-delivery / restraint-in-content spine
(REQ-PV-005) is PRESERVED at long-form scale — no new claim-making latitude, grounding (REQ-PG-002)
unchanged; this owns the delivery voice (VOICE-002 owns the render, REQ-PC-011 owns the craft).

**AC-PV-019 (REQ-PV-019 — episode-persona-state threading).** Verify each segment of a multi-segment
long-form episode: (a) [HARD] carries the persona's FROZEN temperament + voice signature (the
REQ-PI-001 anchor block) UNCHANGED into every per-segment voice-card call (the same frozen identity
start to finish, never re-rolled); (b) [HARD] has the current ARC-PHASE context (origins/turn/
vocation/reflection for Solstice, or the conceived segment role for a LONGFORM-025 instance) injected
into that voice-card call so delivery is phase-aware WITHOUT changing WHO the persona is; (c) [HARD]
the frozen anchor (REQ-PI-002) is never mutated by arc-phase threading — only evolvable delivery
colour responds; (d) the per-segment calls stay ONE persona (enforced at assembly by the REQ-PG-007
persona-charter-consistency check); this extends the REQ-PG-006/REQ-PV-009 per-call card to the
episode axis. See Section B for the GWT.

### Group PI — Persona Identity (Anchors) (added v0.5.0)

**AC-PI-001 (REQ-PI-001 — per-persona frozen-anchor identity contract).** Verify: (a) every curator
persona has a persisted two-block voice card — a FROZEN CORE (≥2 permanent ANCHOR FOCUSES incl. the
primary genre territory = the REQ-PR-004 firewall key + ≥1 charter pillar; CORE TEMPERAMENT,
REQ-PG-006; VOICE SIGNATURE = 1:1 voice REQ-PR-003 + pacing + POV structure REQ-PR-005) and an
EVOLVABLE LAYER (secondary territories, taste-profile state, tic/register/energy/self-disclosure
wording, tunable targets); (b) the anchor block is assembled from existing HARD rails, nothing
re-derived; (c) the per-persona FOCUS TABLE (5 EN + 2 FO, anchors marked, primaries pairwise-distinct)
is illustrative seed content; (d) the STRUCTURE (≥2 anchors + temperament + voice + distinct
secondaries) is the fixed rail while the focus content is AI/user-authored.

**AC-PI-002 (REQ-PI-002 — anchors are frozen).** Verify: (a) [HARD] no path of the
continual-improvement loop (REQ-PV-011) or the taste loop (REQ-PL-006) writes any anchor field (the
≥2 anchor focuses, core temperament, voice signature); (b) [HARD] the per-persona anchor block is in
the FROZEN invariant set; (c) the loop may change wording/surface-taste/secondary-interests/delivery
register but never WHO the persona is; (d) an anchor change is human-only and out-of-band.

**AC-PI-003 (REQ-PI-003 — per-persona frozen guard).** Verify: (a) [HARD] a graduation proposal is
zone-classified at the FRONT of the protocol (before canary); (b) [HARD] an anchor-targeting proposal
is BLOCKED, logged, and never applied (models design-constitution Layer 1); (c) only evolvable-layer
targets proceed observation→heuristic→rule→graduated; (d) the human is out of the run loop (the guard
is self-imposed stability). See Section B for the GWT.

**AC-PI-004 (REQ-PI-004 — distinctness canary on evolvable change).** Verify: (a) [HARD] before
applying ANY evolvable change the system shadow-evaluates it against the anti-convergence firewall
(REQ-PR-004) + the cross-persona collision lint (REQ-PV-010, incl. the new banter fields); (b) [HARD]
a change reducing pairwise separability below the cap or drifting toward another persona's PRIMARY
territory is REJECTED; (c) a change colliding a verbal-tic or banter field with another persona's is
REJECTED; (d) this makes AC-PL-004(d) + NFR-P-9(b) testable at evolution time (no persona's evolvable
secondaries grow into another's primary anchor). See Section B for the GWT.

**AC-PI-005 (REQ-PI-005 — news anchor excluded by construction + implication carve-out).** Verify:
(a) [HARD] the news anchor is NOT a Group-PR curator persona — no charter (REQ-PR-006), POV
(REQ-PR-005), taste profile (REQ-PL-004), firewall slot (REQ-PR-004), evolvable card, or
anchor/evolvable contract (REQ-PI-001), so the evolution machinery (REQ-PV-011/REQ-PL-006/REQ-PI-002/
003/004) structurally does not reach it; (b) [HARD] it is wholly frozen (factual/sourced/attributed/
never-fabricated/apolitical), OWNED by OPS-004 Group OG + ORCH-005 Group RN; its voicing is a TTS
route, not a persona; PROGRAMMING-007 states the exclusion and re-owns nothing; (c) [HARD] its ONE
frozen carve-out (implication-analysis) is permitted ONLY when ATTRIBUTED-to-a-source OR a logically
NECESSARY consequence of cited facts, grounded+attributed exactly like a fact, DROPPED if
ungroundable, and NEVER opinion/advocacy/viewpoint/normative judgment — it TIGHTENS, never relaxes,
OPS-004 REQ-OF-004; (d) the banter recalibration (bluntness/humour/self-disclosure) applies ONLY to
curator personas and never reaches the news anchor; the carve-out + its forbidden-normative-token
lint + its rubric are OPS-004/ORCH-005 amendments referenced not re-owned here. See Section B for the
GWT.

**AC-PI-006 (REQ-PI-006 — frozen-anchor audit across episodes).** Verify: (a) [HARD] a cross-episode
audit compares a persona's persisted ANCHOR BLOCK (REQ-PI-001: ≥2 anchor focuses + core temperament +
voice signature) at each episode boundary against its baseline anchor; (b) [HARD] a drifted anchor
field is REVERTED to the baseline (the anchor is human-only / out-of-band, REQ-PI-002/003) and the
attempt is logged; (c) the continual-improvement loop (REQ-PV-011) + taste loop (REQ-PL-006) may
evolve only the EVOLVABLE layer between episodes, never the anchor; (d) this is the TIME-AXIS net under
the per-persona frozen guard (REQ-PI-003 intake block) — together PV-019 keeps one episode coherent and
PI-006 keeps the persona coherent ACROSS episodes; the audit cadence is tunable. See Section B for the
GWT.

### Non-Functional Acceptance

**AC-NFR-P-1 (NFR-P-1 — measurable plurality).** A test computes the candidate-pool
overlap between every pair of personas over the ANALYSIS-006 dimensions and asserts every
pair is under the anti-convergence cap; plurality is a checkable property, not a name
difference.

**AC-NFR-P-2 (NFR-P-2 — anti-slop + gate).** All Group PC/PS talk content passes the
OPS-004 anti-slop discipline (REQ-OF-005) + script quality gate (REQ-OF-006), is never
fed back as in-context exemplars (REQ-OC-006), and a gate-failing script is dropped
(graceful-skip) without blocking the stream.

**AC-NFR-P-3 (NFR-P-3 — hit-the-post degrades safely).** Backtiming uses analysis when
present; on unanalyzed/too-short-intro tracks it falls back to talk-over-outro / bed /
clean-segue and NEVER talks over a vocal or overruns the post; analysis lag never forces
a vocal talk-over or silences the stream.

**AC-NFR-P-4 (NFR-P-4 — fictional-persona ethics enforced).** No code path airs a
Solstice Hour episode that impersonates a real person, attributes fabricated testimony to
a real person, contains political content, or is missing either disclaimer; episode
scripts are logged for after-the-fact audit.

**AC-NFR-P-5 (NFR-P-5 — never silences the stream).** No editorial decision (talk gen,
show assembly, Solstice Hour pre-render) is a single point of silence; generation is
decoupled via the OPS-004 ready buffer (REQ-OE-012); a failing/late script or episode is
dropped/deferred, never stalling the stream.

**AC-NFR-P-6 (NFR-P-6 — simplicity).** The implementation adds no new service, no new
store (uses CORE-001 persona model + OPS-004 playbook store/ledger + ANALYSIS-006 Track
extended in place), and no new playout seam; deferred items (spec Section 10) are not
partially built.

**AC-NFR-P-7 (NFR-P-7 — measured taste-evolution + provenance integrity).** Verify:
(a) the applied identity-affecting taste-change rate stays under the configured limit with
the cooldown honored (no thrashing); (b) an evolved profile still passes the anti-convergence
firewall against every other persona (refinement never erodes plurality, NFR-P-1);
(c) provenance never blocks/stalls ingest, and a manual-drop "unattributed/house" track is
always a curatable catalog member (never an orphan); (d) no taste-evolution path uses an
appeal/engagement metric as an optimization target; (e) (added v0.7.2) the acquisition-loop
additions are safe — (i) the structured grab reason (REQ-PL-008) is an UNVERIFIED claim that never
enters the fact contract and is never aired-as-certain; (ii) the two no-repeat systems stay SEPARATE
(persistent acquisition anti-re-fetch REQ-PL-009/011 vs ephemeral playout rotation OPS-004
REQ-OA-003a + ORCH-005 REQ-RW-006 + PROGRAMMING REQ-PR-009 — never merged); and (iii) the
catalog-diversity re-rank (REQ-PL-011) RELAXES below the wishlist low-watermark so a thin catalog is
grown, never starved.

**AC-NFR-P-8 (NFR-P-8 — grounding integrity).** Verify: (a) every aired host break is
gate-passed (REQ-PG-005 ran); (b) no spoken factual claim lacks a corresponding entry in the
supplied fact contract (forbidden-fact scan + adversarial self-check enforced); (c) a script
failing the gate twice is SKIPPED, never aired ("talks less" > wrong facts), preserving
never-stops; (d) generated scripts + gate verdicts are logged so a grounding violation is
detectable after the fact.

**AC-NFR-P-9 (NFR-P-9 — delivery-vs-content integrity).** Verify the three encoded
non-refuted-verdict guarantees: (a) warmth/energy turned UP never reintroduces a banned
phrase/construction — the extended banned list (REQ-PV-006), grounding (REQ-PG-002), and
anti-slop (REQ-PG-004) still pass on every break, and the frontsell regression (REQ-PV-008) is
removed so no aired break emits "coming up/up next"; (b) the personas stay DISTINCT after shared
craft is applied — every verbal-tic bank is disjoint (REQ-PV-006/009) and the cross-persona
tic-collision lint (REQ-PV-010) passes, so shared DELIVERY craft never collapses per-persona
DELIVERY/TASTE distinctness (REQ-PR-004/005); (c) the continual-improvement loop (REQ-PV-011)
stays bounded — the applied change rate honors the OPS-004 rate-limit/cooldown (REQ-OD-006), no
path optimizes an engagement/appeal metric, the loop never self-imitates (REQ-OC-006), and the
FROZEN invariant set is never evolved; and (d) (added v0.5.0) the per-persona ANCHOR BLOCK is never
evolved (REQ-PI-002/003 — a loop attempt is blocked at intake before canary and logged) and the
banter recalibration (blunt-praise license REQ-PV-012, per-persona/daypart profanity+humour
REQ-PV-013, fenced three-class taxonomy REQ-PV-014) lands ENTIRELY on the EVOLVABLE DELIVERY axis
(REQ-PV-005) — it never drifts a frozen temperament anchor and never collapses distinctness
(REQ-PI-004; profanity/humour/self-disclosure/praise fields disjoint REQ-PV-009/010; blunt praise
never reintroduces a banned phrase REQ-PV-012/016). Axis (d) encodes the two non-refuted v0.5.0
verdicts.

**AC-NFR-P-10 (NFR-P-10 — long-form episode integrity).** Verify every long-form episode (REQ-PT-004
/ REQ-PT-009) before it airs, on four axes: (a) the episode-level Tier-3 coherence gate (REQ-PG-007:
arc-beats-in-order + cross-segment non-contradiction + persona-charter consistency) runs on the whole
assembled script before pre-render, and an episode failing it twice is DEFERRED, never aired; (b) the
quote-sourcing lint (REQ-PG-008) runs on every attributed interview/liner quote and a quote missing
`source_url` + `speaker` + `date` is DROPPED, never aired (a fabricated "X said Y" never airs), while
verbatim song lyrics are unaffected (PIVOT: lyrics need no source gate); (c) the per-persona ANCHOR
BLOCK is provably stable BOTH within an episode (REQ-PV-019 threading) and ACROSS episodes (REQ-PI-006
audit reverts + logs any drift); and (d) long-form NEVER silences the stream — the episode is
pre-rendered to one loudness-normalized file (REQ-PT-007) and a coherence-deferred / quote-failed
episode falls back to regular programming (inherits NFR-P-5). The per-break two-tier gate (REQ-PG-005)
is UNCHANGED and still runs on every segment; this NFR adds the episode-scale guarantees on top.
Generated episode scripts + gate verdicts are logged so a long-form integrity violation is detectable
after the fact (inherits NFR-P-4 / OPS-004 NFR-O-7).

---

## Section B — Detailed Given-When-Then (load-bearing requirements)

### B-1 — Anti-convergence firewall (REQ-PR-004 / AC-PR-004)

```gherkin
Scenario: Two personas cannot share a primary genre territory
  Given a roster persona "Ember" whose taste charter has primary genre "deep house"
    And a candidate persona "Pulse" whose taste charter also has primary genre "deep house"
  When the system evaluates the pair at curation time
  Then the anti-convergence firewall flags a primary-territory collision
    And the pairing is BLOCKED (Pulse is not admitted with that charter)
    And the block is logged with both personas' overlapping dimensions

Scenario: Distinct charters yield materially distinct candidate pools
  Given persona "Ember" (charter: deep house / electronic / 2010s / warm)
    And persona "Hald" (charter: 1970s soul & funk / vintage / mid-tempo)
  When each charter queries the catalog over the ANALYSIS-006 dimensions
       (genre, sub_genre, bpm, energy, era, tags)
  Then the two returned candidate pools overlap below the configured cap
    And NFR-P-1's pairwise-overlap test passes for the pair

Scenario: Overlap cap is a hard rail, not advisory
  Given two personas whose pools overlap just above the configured cap
  When curation runs
  Then the firewall treats the overlap as a violation (hard), not a soft penalty
    And curation does not proceed with the convergent pairing
```

### B-1a — Track-level anti-convergence: per-track cross-show exclusivity (REQ-PR-009 / AC-PR-009)

```gherkin
Scenario: The same individual track cannot be in two shows' regular rotation
  Given track T ("artist X — title Y") is adopted into show "Deep Currents" regular rotation
    And its play-history / adopted_by_show records "Deep Currents" (OPS-004 REQ-OB-006)
  When show "Night Drive" runs its selector and track T matches its taste pool
  Then the per-track exclusivity predicate EXCLUDES track T from "Night Drive" rotation
    And the exclusion is performed by the ORCH-005 unified dedup view (REQ-RW-006)
        any_persona track-surface scope at selection time
    And "Night Drive" still draws OTHER taste-matching tracks (REQ-PL-004 separability holds)

Scenario: Thematic adjacency is still allowed (Layer 1 vs Layer 2 are non-contradictory)
  Given "Deep Currents" and "Night Drive" share an adjacent genre/era pool within the
        REQ-PR-004 Layer-1 overlap cap (slight thematic crossover)
  When both shows curate
  Then the Layer-1 pool-overlap cap is satisfied (adjacency permitted)
    But no SINGLE concrete track ID appears in BOTH shows' regular rotation (Layer-2 exclusivity)

Scenario: Director-declared time-boxed crossover references a track cross-show
  Given the director DECLARES a time-boxed theme that names track T and the personas in scope
  When the declared window is active
  Then track T may be referenced cross-show for that theme (REQ-RW-007 override-and-restore)
    And the exception is recorded to the ledger and AUTO-REVERTS at window end
    And outside the window track T returns to single-show rotation exclusivity
    And this is never a shared REGULAR rotation

Scenario: Empty legal set -> graceful relaxation, never stall the queue
  Given the catalog is too thin for "Night Drive" to fill rotation without a shared track
  When the selector exhausts its exclusive legal set
  Then the rail RELAXES to a bounded, LOGGED shared-track exception (mirrors OPS-004 REQ-OA-003b)
    And the queue continues (continuity wins, REQ-OA-008)
    And the relaxation is logged as a degradation, not a silent override
```

### B-2 — Growth gate, both-axes distinctness (REQ-PR-008 / AC-PR-008)

```gherkin
Scenario: New persona admitted only for a documented editorial gap with a free voice
  Given the roster covers soul, deep house, reggae, indie, and ambient
    And the AI documents an editorial GAP: "no one covers vintage Brazilian / tropicália"
    And at least one verified Kokoro voice is still unused
  When the AI proposes a new persona for that gap
  Then the growth gate checks axis (a): a free unused voice is available -> pass
    And checks axis (b): the new charter passes the anti-convergence firewall
        against every existing persona -> pass
    And the persona is admitted and assigned the free voice 1:1

Scenario: Reject a persona proposed for appeal, not a gap
  Given the AI proposes a persona "because a pop show would attract more listeners"
  When the growth gate evaluates it
  Then it is rejected: no documented editorial gap, and appeal is an anti-goal

Scenario: Reject when no free voice exists (voice-blocked growth)
  Given a genuine editorial gap is documented
    But every verified voice is already bound 1:1 to a persona
  When the growth gate evaluates axis (a)
  Then it fails (no free voice) and the persona is not added until VOICE-002 adds a voice
```

### B-3 — Hit the post, never over a vocal (REQ-PC-003 / AC-PC-003)

```gherkin
Scenario: Backtime a talk break onto a long instrumental intro
  Given the next track has an analyzed instrumental intro of 11.0s (ANALYSIS-006 cue-in)
  When the system writes the talk break to air over the intro
  Then the break is sized so its spoken duration lands its last word at ~11.0s
    And no spoken word overlaps the vocal onset
    And the annotate: transition metadata aligns the talk to the intro window

Scenario: Intro too short -> fall back, never talk over the vocal
  Given the next track's analyzed instrumental intro is 2.0s (too short for the break)
  When the system plans the talk
  Then it does NOT talk over the vocal
    And it chooses one of: talk over the previous track's outro, drop a music bed under
        the talk, or segue clean and backsell after
    And the chosen option keeps all speech off the vocal

Scenario: Unanalyzed track -> safe fallback (NFR-P-3)
  Given the next track has no analysis feature record yet
  When the system plans a talk break
  Then it does not assume an intro length, does not talk over a vocal,
       and falls back to bed/outro/clean-segue, never overrunning the post
```

### B-4 — Ear-writing block boundaries = synthesis chunks (REQ-PS-004 / AC-PS-004)

```gherkin
Scenario: Script blocks align with VOICE-002 synthesis chunks
  Given the talk-script generator produces a link as 1-2 sentence blocks
       separated by blank lines
  When VOICE-002 splits the script for synthesis
  Then it chunks at the blank-line block boundaries
    And inserts natural inter-chunk silence between blocks
    And the resulting audio has speakable pacing (no run-on, no unnatural mid-thought cut)

Scenario: Block sizing respects the synthesis chunk budget
  Given a block of 1-2 short sentences (within VOICE-002's ~100-200 token chunk budget)
  When synthesized
  Then the block synthesizes as a single clean chunk
    And the SPEC owns the block boundaries while VOICE-002 owns the chunk+silence render
```

### B-5 — Fictional-persona guardrail + mandatory disclaimer (REQ-PT-005, REQ-PT-006 / AC-PT-005, AC-PT-006)

```gherkin
Scenario: Solstice Hour guest is an original fictional persona
  Given the AI authors a Solstice Hour episode
  When it creates the "guest"
  Then the guest is a wholly invented, original fictional persona
    And the episode does not impersonate, name, or attribute fabricated testimony to
        any real person
    And the story contains no political content and no real-world factual claims about
        a living or identifiable person

Scenario: Both disclaimers present -> episode may air
  Given a produced episode with a spoken disclaimer at the open AND at the close
       stating the guest is a fictional persona voiced by the station
  When the episode is checked before airing
  Then both disclaimers are detected and the episode is cleared to air

Scenario: Missing a disclaimer -> episode does NOT air
  Given a produced episode missing the closing disclaimer
  When the episode is checked before airing
  Then it is rejected and does NOT air (NFR-P-4)
    And the rejection is logged for after-the-fact audit

Scenario: Quiet/measured register only (honest TTS limit, R-P-2)
  Given the episode script
  Then it is written for quiet/measured/reflective delivery
    And it does not require weeping, comic timing, or high theatrical range
    And emotion is carried by ear-writing + engineered pauses + the ducked bed
```

### B-6 — Voice↔persona 1:1 and max-2 host cap (REQ-PR-003, REQ-PR-002 / AC-PR-003, AC-PR-002)

```gherkin
Scenario: A voice is never reused across personas
  Given persona "Ember" is bound to Kokoro voice "af_bella"
  When the AI tries to bind "af_bella" to a second persona
  Then the binding is rejected (voice↔persona is strict 1:1, no reuse)

Scenario: A show may have at most two hosts, never three
  Given a deliberate dialogue/contrast format with two English personas
  When the show is assembled
  Then two hosts are allowed
    But any attempt to add a third host is rejected (CORE-001 REQ-B-011)

Scenario: Faroese show is single-host
  Given a Faroese-language show
  When hosts are assigned
  Then exactly one Faroese persona is assigned (Hanna OR Hanus, never both)
```

### B-7 — Manual drop attributed and curatable (REQ-PL-002 / AC-PL-002)

```gherkin
Scenario: A human-dropped file is ingested, attributed to house, and becomes curatable
  Given a human drops "unknown_artist - dub_track.flac" into the music directory
  When the ANALYSIS-006 stat-scan (REQ-AP-007) picks it up and analyzes it
  Then its provenance is set to acquired_for = "unattributed/house",
       source = "manual-drop"
    And it is a valid, curatable catalog member (not an orphan)
    And whichever persona's taste profile its features fit may curate it
    And the drop is a non-binding signal — the station is not forced to play it
       and does not pander to it
```

### B-7a — Exclusion-feedback yields new acquisitions; grab reason is never aired (REQ-PL-008, REQ-PL-009, REQ-PL-010 / AC-PL-008, AC-PL-009, AC-PL-010)

```gherkin
Scenario: Without exclusion context a big batch re-proposes items the gate drops (the gap)
  Given a curator prompt that passes only the recently-played `recent` exclusion
    And the catalog already holds many of the persona's favourite tracks
  When the LLM proposes a big batch of acquisitions
  Then it re-proposes items already in the catalog or already-failed
    And the OPS-004 acquisition gate (Group OH) silently drops them as duplicates/known-failures
    And the batch yields near-zero NEW acquisitions while burning subscription quota

Scenario: Exclusion-feedback makes the batch propose genuinely new candidates
  Given the curator prompt is fed `already_have` (recently-acquired, from REQ-PL-001 provenance)
    And `recently_rejected` (recently failed / no-candidate, from the REQ-PL-010 diary outcomes)
    And these are ADDITIVE to the recently-played `recent` (the two-no-repeat separation)
  When the LLM proposes a batch
  Then it excludes the already-have and recently-rejected items
    And it proposes genuinely NEW candidates the gate can actually acquire

Scenario: Each grabbed item carries a structured at-grab-time reason, stored as an unverified claim
  Given the director decides to grab "Artist X - Title Y"
  When the acquisition is proposed
  Then a structured `{artist, title, reason}` is captured AT GRAB TIME citing the prompt context
    And it is NOT a free-form retrospective narrative (the hallucination failure mode)
    And it POPULATES the ANALYSIS-006 REQ-AD-006 `grab_reason` field (ANALYSIS owns it; PL populates)
    And it is threaded into the REQ-PL-001 `acquired_context` provenance + the diary
    And it is stored as an UNVERIFIED director CLAIM — it never enters the fact contract (REQ-PG-001)
       and no host break states it as a certainty (grounding REQ-PG-002, consensus REQ-KS-006)

Scenario: Every proposed item records a diary outcome, including no-candidate
  Given a batch where one item is acquired, one attempt fails, and one has no source at all
  When the batch resolves
  Then the diary records outcome = success / failed / no-candidate respectively
    And the no-candidate item is captured (not dropped, unlike the orphaned attempts.json)
    And the failed + no-candidate items feed `recently_rejected` so they are not endlessly re-proposed
```

### B-7b — Catalog-diversity re-rank biases against repetition but relaxes on a thin catalog (REQ-PL-011 / AC-PL-011)

```gherkin
Scenario: On a healthy catalog the re-rank biases against re-grabbing the same artist/cluster
  Given the catalog is above the wishlist low-watermark
    And it is already dense in one artist / one sonic cluster
    And a batch of profile-relevant candidates is proposed
  When the MMR-style relevance+diversity re-rank runs (using ANALYSIS-006 features + the
       KNOWLEDGE-008 similar-artist graph REQ-KG-001/003)
  Then candidates that add same-artist / same-cluster density are down-ranked
    And the acquired set broadens the catalog rather than deepening an existing cluster

Scenario: On a thin/new catalog the diversity pressure relaxes so it is not starved
  Given the catalog/backlog is BELOW the wishlist low-watermark
  When the re-rank runs
  Then the diversity penalty relaxes toward pure profile-relevance
    And profile-fitting candidates are acquired to GROW the catalog (never refused for resembling
        the few tracks already present) — mirroring OPS-004 REQ-OA-003b continuity-wins

Scenario: The acquisition re-rank is separate from the playout no-repeat
  Given the acquisition-time catalog-diversity re-rank (REQ-PL-011)
  Then it re-ranks what to ACQUIRE, never what to PLAY
    And the playout rotation no-repeat (OPS-004 REQ-OA-003a + ORCH-005 REQ-RW-006 +
        PROGRAMMING REQ-PR-009) is a separate system over different state
    And the two are never merged (the two-no-repeat separation)
```

### B-8 — Per-persona profile evolves but stays separable (REQ-PL-004, REQ-PL-006 / AC-PL-004, AC-PL-006)

```gherkin
Scenario: A profile refines from its charter seed under measured change
  Given persona "Ember" has a taste profile seeded from its charter (deep house / warm)
    And recent signals show consistent play-through of dub-techno and early-skips of
        vocal house
  When the measured taste-evolution loop runs (REQ-PL-006)
  Then the profile shifts gradually toward dub-techno within the bounded change rate
    And the cooldown between applied changes is honored (no thrashing)
    And the shift is applied as a small increment, not a wholesale rewrite

Scenario: An evolved profile still passes the anti-convergence firewall
  Given "Ember" and "Hald" have each evolved over several cycles
  When the firewall (REQ-PR-004) re-checks the pair over the ANALYSIS-006 dimensions
  Then their candidate-pool overlap is still under the cap (NFR-P-7)
    And refinement has not eroded roster plurality

Scenario: Change velocity is bounded even under strong signals
  Given a burst of signals all pushing "Ember" toward one territory
  When the loop evaluates the change
  Then the applied change rate stays under the configured limit (anti-thrash)
    And the loop bounds how FAST taste changes, not how much is learned
```

### B-9 — Signals are context, never an appeal target (REQ-PL-005 / AC-PL-005)

```gherkin
Scenario: Play/skip/feedback inform taste but are never maximized
  Given play-through, early-skip, recency, and listener-contact-form signals
  When the taste profile learns from them
  Then they are weighed as human-curatorial CONTEXT
    And no path computes a play-count / skip-rate / feedback-volume / sentiment score
        to MAXIMIZE
    And the station does not pander or chase popularity in response (anti-appeal,
        OPS-004 REQ-OF-004 / NFR-O-7)

Scenario: Seed enrichment bootstraps then is free to diverge (REQ-PL-007)
  Given the one-time Spotify/YouTube seed enrichment has populated initial profiles
  When taste evolves over subsequent cycles
  Then the seed acts only as the initial reference
    And it never pins, gates, or constrains the evolving profiles
    And an unavailable seed never blocks operation
```

### B-10 — Grounding rule: speak only from context (REQ-PG-001, REQ-PG-002 / AC-PG-001, AC-PG-002)

```gherkin
Scenario: A fact not in context is not spoken
  Given a TrackContext with year=null and no producer fact, and no ShowPrep facts
  When the host writes a break about the track
  Then it does NOT state a year, label, producer, or personnel
    And it does NOT guess or approximate ("probably late 80s")
    And it may still speak from what IS present (genre, mood, the just-played title)

Scenario: Perceptual description allowed, named attribution gated
  Given a TrackContext with a sonic-character profile (slow, heavy, bass-forward) but no
        named-personnel fact
  When the host describes the track
  Then a PERCEPTUAL line ("a slow, heavy groove that sits right in your chest") is allowed
    But a NAMED claim ("that's a Moog bass played by ...") is NOT made (not in context)

Scenario: Silence beats a wrong fact
  Given the host is unsure of a release year and it is not in context
  Then the host says nothing about the year rather than risk a wrong one
```

### B-11 — Comparison discipline (REQ-PG-003 / AC-PG-003)

```gherkin
Scenario: A grounded comparison is allowed; a fusion formula is banned
  Given the TrackContext lists similar_artists [{name: "Artist Y", match_score: 0.71}]
  When the host writes a comparison
  Then it MAY say a grounded, single comparison referencing Artist Y
    But it MUST NOT use a fusion formula ("sounds like Y meets Z", "lovechild of Y and Z")
    And it makes at most one comparison in the break

Scenario: No grounded comparison -> none is forced
  Given no similar_artist >= 0.6, no shared tag, and no ShowPrep relation fact
  When the host writes the break
  Then it makes NO artist comparison
    And it leads with a concrete grounded observation instead
```

### B-12 — Two-tier quality gate, regenerate-once-then-skip (REQ-PG-005, REQ-PG-004 / AC-PG-005, AC-PG-004)

```gherkin
Scenario: Forbidden-fact scan fails a year not in context
  Given a generated script claims "released in 1979"
    And the TrackContext year is null (or 1981)
  When Tier-1 deterministic lint runs the forbidden-fact scan
  Then the script FAILS (the year token is not supported by context)
    And the system regenerates the script once

Scenario: Banned register is rejected
  Given a generated script contains "a sonic journey that effortlessly blends"
  When Tier-1 scans the banned register
  Then the script FAILS and is regenerated

Scenario: Adversarial self-check catches an unsupported claim
  Given a script passes Tier-1 but asserts "their third album"
    And no album-ordinal fact is in context
  When Tier-2 lists factual claims and flags unsupported ones
  Then "third album" is flagged as unsupported and the script FAILS

Scenario: Second failure skips the break, never ships a FAIL
  Given a script has failed and been regenerated once
    And the regenerated script still FAILS the gate
  Then the break is SKIPPED (no talk this time)
    And music continues (never-stops preserved, NFR-P-8)
    And no failed/ungated script is ever aired
```

### B-13 — Live-human persona-awareness is a stance, never a claim (REQ-PV-001 / AC-PV-001)

```gherkin
Scenario: The host is framed as a live human via delivery, not via a claim
  Given the positive-identity HOST_PERSONA frames the host as a live human radio host
       talking to one listener
  When the host writes a break
  Then the copy reads as a present, in-the-moment person (present tense, second person,
       one-to-one intimacy)
    And it does NOT say "I'm live", "I'm a real person", "as an AI", or "this script"
    And it does NOT break the fourth wall or read stage directions/punctuation aloud

Scenario: Persona-awareness adds delivery warmth, never new claim-making latitude
  Given a TrackContext with year=null and no producer fact
  When the live-human host writes the break
  Then it still states NO fact absent from context (grounding REQ-PG-002 unchanged)
    And the live-human framing only changes HOW it talks, not WHAT it may claim
```

### B-14 — Tease-by-feeling frontsell + the mandatory code-fix (REQ-PV-007, REQ-PV-008 / AC-PV-007, AC-PV-008)

```gherkin
Scenario: The next track is teased by feeling, never named
  Given the next track has ANALYSIS-006 features (lower energy, slower bpm, late-night mood)
  When the talk context is assembled
  Then context carries a next_mood/energy hint (e.g. "lower, slower, late-night")
       derived from those features
    And context does NOT carry next_artist or next_title (no name)
  When the host writes a frontsell
  Then it teases only the FEEL/mood shift ("the next one sits lower, slower")
    And it does NOT name the artist or title
    And it does NOT use "coming up", "up next", or "stay tuned"

Scenario: The live "Coming up next" regression is removed (the single most important fix)
  Given the pre-fix code: brain/talk.py _build_context sets context["next_artist"] /
       context["next_title"], and brain/llm.py _build_talk_prompt emits
       'Coming up next: "{title}" by {artist}.' + "name the artist and title"
  When the fix is applied
  Then _build_context no longer passes the next track's name (passes next_mood instead)
    And _build_talk_prompt no longer contains the "Coming up next" block or the
       "name the artist and title" upcoming-track instruction
    And the prompt offers an OPTIONAL feeling-tease that forbids naming and forbids
       the banned filler
    And no aired break can emit "coming up next" (the banned-phrase regression is cleared)

Scenario: The name reappears as the backsell on the following break
  Given the track that was teased by feeling has now finished playing
  When the host writes the next break
  Then it back-announces that track by artist + title (the name is saved for the backsell)
```

### B-15 — Disjoint verbal-tic banks + crutch/collision lints (REQ-PV-006, REQ-PV-009, REQ-PV-010 / AC-PV-006, AC-PV-009, AC-PV-010)

```gherkin
Scenario: Each persona draws warmth-transitions only from its own disjoint bank
  Given persona "Ember" has tic bank {"Funny thing is", "So here's where it gets good",
       "I keep coming back to"}
    And persona "Hald" has tic bank {"Now", "Truth be told", "What gets me"}
  When each writes a break
  Then Ember uses at most one tic, drawn only from Ember's bank
    And Hald uses at most one tic, drawn only from Hald's bank
    And no tic is shared between the two banks (disjoint)

Scenario: Filler-as-crutch is caught by the Tier-1 lint
  Given a generated break uses two warmth-transitions (over the ≤1/break cap)
  When the Tier-1 distinctness/crutch lint runs
  Then the script FAILS (frequency cap exceeded) and is regenerated

Scenario: Repeating the previous break's tic is caught
  Given persona "Ember" used "Funny thing is" in its previous break
    And the new break uses "Funny thing is" again
  When the lint runs
  Then the script FAILS (same tic two breaks running) and is regenerated

Scenario: A cross-persona tic collision is flagged
  Given a playbook self-refinement would add "What gets me" to Ember's bank
    And "What gets me" already exists in Hald's bank
  When the cross-persona tic-collision lint runs
  Then the collision is flagged (the disjointness rail REQ-PR-004 is enforced at the talk layer)
    And the shared-filler-set failure mode does not silently reopen
```

### B-16 — Daypart-calibrated delivery energy is a writing property, not hype (REQ-PV-003, REQ-PV-005 / AC-PV-003, AC-PV-005)

```gherkin
Scenario: Energy is carried by writing, not by exclamation/hype
  Given it is afternoon (peak daypart) in the Faroes and the persona's energy band is "warm,
       leaning in"
  When the host writes a high-energy break
  Then energy is carried by short punchy blocks, specifics, and rhythm
    And the break contains NO exclamation marks, manufactured excitement, or hype words
    And turning delivery energy UP does not relax grounding or the anti-slop register
       (warmth in delivery, restraint in content)

Scenario: Overnight intimacy is the same persona, calibrated down
  Given the same persona at overnight (energy band "intimate, near-whisper close")
  When it writes a break
  Then the delivery is quieter and more spacious (longer beats, fewer words)
    And it is still recognizably the same persona (consistent register + pacing signature)
```

### B-17 — Bounded continual-improvement loop, not fine-tuning (REQ-PV-011 / AC-PV-011)

```gherkin
Scenario: The loop refines craft as bounded refinement, never trains a model
  Given the per-break quality gate has logged repeated FAILs on a stale craft rule
  When the continual-improvement loop runs
  Then it refines the PROMPT / RULE / VOICE CARD content in the OPS-004 playbook store
       (observation -> heuristic -> rule -> graduated)
    And it does NOT fine-tune or train any model (no training path exists)
    And the applied change rate honors the OPS-004 rate-limit + cooldown (REQ-OD-006)
    And a canary check rejects a change that would degrade recent programming
    And a contradiction with an applied rule is reconciled deliberately, never silently churned

Scenario: The loop never self-imitates and never chases appeal
  Given recent host scripts exist
  When the loop refines craft
  Then recent scripts are used as an AVOID-LIST only, never as in-context style exemplars
       (REQ-OC-006)
    And no play-count / skip-rate / feedback-volume / sentiment score is made an
       optimization target (curation bright line)

Scenario: The loop may never evolve a FROZEN invariant
  Given a proposed learning would relax never-ship-a-FAIL, the grounding/fact-contract,
       the anti-convergence firewall, the banned-phrase firewall, the fictional-persona
       ethics, no-self-imitation, or the host caps
  When the loop evaluates the proposal
  Then it is rejected — the FROZEN invariant set is never evolved (NFR-P-9)
```

### B-18 — Blunt-praise license: owned+specific passes, floating PR-label fails (REQ-PV-012, REQ-PV-016 / AC-PV-012, AC-PV-016)

```gherkin
Scenario: An owned, specific blunt verdict passes
  Given a TrackContext with an audible drum fill the host can locate
  When the host writes a reaction line "This one just rules — wait for the drum fill at ninety seconds"
  Then the Tier-1 praise-validity lint PASSES it
       (first-person/owned AND specific: points at the locatable drum fill)
    And it relaxes nothing on the CONTENT axis (no fact is asserted)

Scenario: A borrowed-PR-vocabulary line floating free fails
  Given a generated line "a captivating sonic journey that effortlessly transports you"
  When the Tier-1 praise-validity lint runs
  Then it FAILS (borrowed critic/PR vocabulary pointing at no locatable thing)
    And the script regenerates

Scenario: Heat as delivery passes; the lazy floating label fails
  Given two candidate lines about the same track
  When "this one just goes; stick around" and "an infectious banger that transports you" are linted
  Then "this one just goes" PASSES (owned DELIVERY emphasis)
    And "an infectious banger that transports you" FAILS (floating PR label)
```

### B-19 — Three-class taxonomy: a smuggled music-fact token is reclassified + gated (REQ-PV-014, REQ-PV-016 / AC-PV-014, AC-PV-016)

```gherkin
Scenario: A self-disclosure with a smuggled label token is reclassified and gated
  Given a persona self-disclosure clause "I keep coming back to this, back when they were on Sub Pop"
    And the TrackContext has no label fact
  When the Tier-2 self-disclosure/opinion scan runs (REQ-PV-016)
  Then "Sub Pop" is detected as a smuggled MUSIC-FACT token
    And the clause is RECLASSIFIED from persona-self-disclosure to music-fact (REQ-PV-014)
    And it is gated by the fact contract; the unsupported label is a FAIL
    And the script regenerates (and on a second FAIL the break is skipped)

Scenario: A fenced self-disclosure with no checkable claim is licensed
  Given a self-disclosure clause "this one got me through a rough week — anyway, gorgeous"
  When the taxonomy classifies it
  Then it is persona-self-disclosure (fenced fiction), ungated for grounding
    And it makes no real-person claim, no fourth-wall break, no political content,
       and embeds no music-fact token (REQ-PT-005 fence holds)
```

### B-20 — Per-persona frozen guard blocks an anchor-targeting proposal (REQ-PI-002, REQ-PI-003 / AC-PI-002, AC-PI-003)

```gherkin
Scenario: A loop proposal to change a persona's PRIMARY anchor is blocked at intake
  Given persona "The Crate" has FROZEN primary anchor "deep funk / soul / rare-groove"
    And the continual-improvement loop proposes shifting its primary territory toward "boogie"
  When the proposal is zone-classified at the FRONT of the protocol (before canary)
  Then the per-persona Frozen Guard BLOCKS it (it targets an anchor field)
    And the attempt is logged and never applied (REQ-PI-002)
    And the loop is told the anchor is human-only / out-of-band

Scenario: An evolvable-layer proposal proceeds normally
  Given the same loop proposes refining "The Crate"'s evolvable secondary "Afro-funk reissues"
  When the proposal is zone-classified
  Then it is an EVOLVABLE target and proceeds observation -> heuristic -> rule -> graduated
    And it is still subject to the distinctness canary (REQ-PI-004) before applying
```

### B-21 — Distinctness canary rejects drift toward another persona (REQ-PI-004 / AC-PI-004)

```gherkin
Scenario: An evolvable change drifting toward another persona's primary territory is rejected
  Given persona "Off-Kilter" (primary anchor "post-punk / art-rock / no-wave")
    And persona "After Hours" (primary anchor "late-night ambient / dub-techno")
    And an evolvable-layer change would grow "Off-Kilter"'s secondaries deep into ambient/dub-techno
  When the distinctness canary shadow-evaluates the change (REQ-PR-004 + REQ-PV-010)
  Then it REJECTS the change (it reduces pairwise separability toward another persona's primary)
    And "Off-Kilter" stays distinct from "After Hours" (refinement never erodes plurality)

Scenario: A banter-field collision is rejected
  Given a self-refinement would set "Off-Kilter"'s humour_mode + profanity_tier + praise-starter
       to a combination another persona already uses
  When the canary runs the cross-persona collision check (REQ-PV-010)
  Then the collision is flagged and the change is rejected (disjointness preserved)
```

### B-22 — News anchor: permitted attributed implication vs forbidden normative opinion (REQ-PI-005 / AC-PI-005)

```gherkin
Scenario: The news anchor is excluded from the persona model by construction
  Given the news anchor
  Then it has no taste charter, no POV, no evolving taste profile, no anti-convergence slot,
       and no anchor/evolvable voice card
    And the persona-evolution machinery (REQ-PV-011/REQ-PL-006/REQ-PI-002/003/004) never touches it
    And the banter recalibration (bluntness/humour/self-disclosure) never reaches it
    And it is owned by OPS-004 Group OG + ORCH-005 Group RN (referenced, not re-owned here)

Scenario: An attributed implication is permitted
  Given a sourced item "the central bank raised rates by 0.5 points"
    And a source analysis "according to Reuters, mortgage costs are expected to rise"
  When the news anchor states the implication
  Then it is PERMITTED (attributed to a source, grounded, no stance)

Scenario: A necessary implication is permitted
  Given the cited facts "two of three listed bidders have withdrawn"
  When the anchor states "so the tender has one remaining bidder"
  Then it is PERMITTED (logically necessary, no normative load)

Scenario: An unattributed forecast is dropped or must be attributed
  Given a candidate line "this will probably hurt the economy" with no source attribution
  When the implication-analysis check runs
  Then the line is DROPPED (unattributed forecast) or rewritten as an attributed source projection

Scenario: A normative/advocacy line is forbidden
  Given a candidate line "this is a reckless decision that voters should reject"
  When the forbidden-normative-token lint runs
  Then it FAILS (normative predicate + advocacy) and is graceful-skipped — never aired
    And the carve-out TIGHTENS, never relaxes, the apolitical rail (OPS-004 REQ-OF-004)
```

### B-23 — Dated / try-hard-slang ban: distinct from slop and from blunt praise (REQ-PV-017 / AC-PV-017)

```gherkin
Scenario: An owned but dated-slang praise line fails the register-currency lint
  Given a generated reaction line "this track's got real swagger"
  When the Tier-1 dated/try-hard-slang lint runs (REQ-PV-017)
  Then it FAILS (the word "swagger" is dated/try-hard) even though the line is owned
    And the script regenerates (and on a second FAIL the break is skipped)

Scenario: A faux-cool "fellow kids" reach fails
  Given a generated line "this one's seriously hip, the kids are gonna love it"
  When the lint runs
  Then it FAILS ("hip", "the kids" — the bot-reaching-for-cool register)
    And it FAILS independently of the music-slop ban (it is slop-free) and the blunt-praise license

Scenario: A contemporary, register-true blunt line passes both axes
  Given a generated line "this one just rules — that bassline does not let up"
  When both the blunt-praise lint (REQ-PV-012/016) and the dated-slang lint (REQ-PV-017) run
  Then it PASSES the blunt-praise validity test (owned + specific)
    And it PASSES the register-currency test (contemporary, register-true, no faux-cool slang)

Scenario: The dated-slang term-class is per-persona register-true and tunable
  Given two personas with different register-true vocabularies on their voice cards
  When each writes a break
  Then each draws contemporary vocabulary from its OWN voice card register (REQ-PV-009/REQ-PI-001)
    And the banned dated-slang list is tunable config (refined as slang dates, REQ-PV-011)
    And the news anchor is unaffected (excluded by construction, REQ-PI-005)
```

---

### B-24 — Long-form episode integrity: Tier-3 coherence, quote-sourcing, real-vs-fictional, cross-episode anchor (REQ-PT-009, REQ-PG-007, REQ-PG-008, REQ-PI-006 / AC-PT-009, AC-PG-007, AC-PG-008, AC-PI-006)

```gherkin
Scenario: A self-contradicting long-form episode is deferred, not aired
  Given a LONGFORM-025-conceived artist-retrospective episode assembled from 5 segments
    And segment 2 states the debut album year as "1991" and segment 4 states it as "1989"
  When the episode-level Tier-3 coherence gate runs before pre-render (REQ-PG-007)
  Then the cross-segment non-contradiction check FAILS (the year tokens disagree)
    And the failing segment regenerates once
    And on a second FAIL the WHOLE episode is DEFERRED (held back from the slot)
    And regular programming keeps playing (never a silence, NFR-P-5/P-10)
    And the per-break Tier-1/Tier-2 gate (REQ-PG-005) is unchanged and still ran on each segment

Scenario: An out-of-order arc fails the beat-order check
  Given a Solstice Hour episode whose planned 3-act arc is origins -> turn -> vocation -> reflection
    And the assembled script places "reflection" before "vocation"
  When the Tier-3 gate runs (REQ-PG-007)
  Then the arc-beats-in-order check FAILS
    And the episode is regenerated/deferred, never aired out of arc order

Scenario: An unsourced attributed interview quote is dropped; verbatim lyrics are not gated
  Given a documentary segment containing the line: the producer said "we cut it live in one take"
    And the fact contract carries NO source_url/speaker/date for that quote
  When the quote-sourcing lint runs (REQ-PG-008)
  Then the attributed quote FAILS and is DROPPED (a fabricated "X said Y" never airs)
  Given the same segment quotes two verbatim lines of the song's own lyrics
  When the lint runs
  Then the lyric quote is NOT gated (PIVOT: lyrics need no source; the lyric is the on-air song itself)

Scenario: A real-subject retrospective speaks only grounded sourced facts, never fabricates a biography
  Given an artist-retrospective about a real artist
  When the host narrates the artist's history
  Then every named fact (year/label/personnel/chart) is present in the fact contract or is unspoken (REQ-PG-002)
    And every attributed quote carries source_url + speaker + date (REQ-PG-008)
    And the host never fabricates the real artist's biography or testimony
    And the fictional-persona guardrail (REQ-PT-005) + disclaimer (REQ-PT-006) apply only where an INVENTED character is voiced

Scenario: A persona's frozen anchor never drifts across episodes
  Given a curator persona whose baseline anchor primary genre is "ambient/drone" (the REQ-PR-004 firewall key)
    And the persona has narrated 6 episodes over several weeks with evolvable-layer refinement between them
  When the cross-episode frozen-anchor audit runs at each episode boundary (REQ-PI-006)
  Then the persisted anchor block is identical to baseline every episode
    And IF a loop change ever drifted an anchor field, that field is REVERTED to baseline and the attempt is logged
    And only the evolvable layer (secondary tastes, tic wording, register colour) changed between episodes
```

---

## Section C — Definition of Done

The SPEC-RADIO-PROGRAMMING-007 editorial layer is DONE when:

1. **Roster & persona model (Group PR).**
   - Two-level identity (house + persona) exists; personas inherit the house ethos.
   - The roster holds multiple distinct single-curator personas (~5 EN + 2 FO at launch).
   - Per-show host caps hold: default 1, max 2 (dialogue/contrast only), never 3;
     Faroese exactly 1.
   - Voice↔persona is strict 1:1, no reuse; English/Faroese rosters are disjoint; no
     bilingual persona.
   - Every persona has a persisted, queryable taste charter and a persistent POV.
   - The anti-convergence firewall passes: every persona pair is under the overlap cap
     over the ANALYSIS-006 dimensions (NFR-P-1).
   - The growth gate enforces documented-editorial-gap + both-axes distinctness; appeal-
     and voice-blocked growth are rejected.

2. **Radio-craft playbook content + talk rules (Group PC).**
   - Talk-break anatomy (backsell default, frontsell-by-feeling, re-ID, Hook→Body→Exit),
     link ≤30s, talk every 1-3 songs.
   - Hit-the-post backtiming reads ANALYSIS-006 intro/outro lengths and lands on the
     post; NEVER talks over a vocal; safe fallback ladder works on short/unanalyzed
     intros.
   - Anti-cheese firewall: banned phrases absent, no forced enthusiasm, write to one
     listener; enforced by the OPS-004 quality gate; references (not forks) OPS-004
     anti-slop.
   - Energy/mood arcs + daypart presets + set-phase arc (sloped cool-downs) + tempo/key
     bridges; what-hosts-say categories rotate (no same twice running).
   - All craft content lives in the OPS-004 self-learning store, informs all programming,
     self-refines under the measured-change rails, and is never an in-context exemplar.
   - Periodic re-ID for new tuners; opens lead on the strongest hook.

3. **Script-side ear-writing (Group PS).**
   - Scripts: one thought ≤20 words, always contractions, singular second person,
     punctuated for breath, varied length.
   - Blank-line 1-2 sentence blocks align with VOICE-002 synthesis chunk boundaries.
   - Numbers/dates spelled as spoken; IPA phoneme override available for hard names.

4. **Show formats incl. Solstice Hour (Group PT).**
   - Recurring shows have name + fixed slot + stable skeleton + open/close ritual + own
     recurring named segments; recognizably the same show each time; open on the strongest
     hook.
   - Solstice Hour / Summarrødd: ~60-min weekly flagship, 3-act fictional-persona life-arc
     monologue, 4-5 interwoven legally-airable tracks, single-narrator (optional 2-voice
     within max-2), emotion via ear-writing + pauses + ducked bed.
   - [HARD] guest is an original fictional persona (no impersonation, no fabricated real
     testimony, apolitical); mandatory open AND close disclaimer; an episode missing either
     does NOT air (NFR-P-4).
   - The whole episode is pre-rendered to one loudness-normalized file and queued via the
     OPS-004 ready buffer — zero live assembly.
   - The 2-voice variant and the format-study capability (transcripts/press/RSS, craft not
     copy) work and respect source terms.

5. **Taste self-learning, provenance & feedback (Group PL, added v0.2.0).**
   - Every track carries provenance (acquired_for / acquired_context / source), extending
     the ANALYSIS-006 `Track` record in place; the audited no-provenance gap is closed.
   - A manual drop is attributed to "unattributed/house", analyzed, and becomes a fully
     curatable catalog member curatable by whichever persona's taste fits (non-binding).
   - A per-batch acquisition diary records the decision chain as a VIEW over the OPS-004
     ledger/diary (not a new store, not the orphaned attempts.json).
   - Each persona has a persisted taste profile seeded from its charter that EVOLVES from
     play/skip/recency/listener-signal context — never from an appeal/engagement metric.
   - The taste-evolution loop is MEASURED (bounded rate + cooldown + canary + contradiction
     detection, via OPS-004 REQ-OD-006); an evolved profile still passes the anti-convergence
     firewall (NFR-P-7) — refinement never erodes plurality.
   - The one-time Spotify/YouTube seed enrichment bootstraps initial profiles (wiring the
     existing stubs) as a non-binding reference, never a constraint; it never blocks
     operation.
   - (Added v0.7.2:) Each acquisition carries a STRUCTURED at-grab-time grab reason
     `{artist, title, reason}` threaded into provenance, stored as an UNVERIFIED director claim
     that never enters the fact contract and is never aired-as-certain.
   - The curator prompt carries `already_have` + `recently_rejected` EXCLUSION context (additive to
     the recently-played `recent`), so a batch proposes genuinely NEW candidates instead of
     re-deciding duplicates the gate drops.
   - The acquisition diary records an OUTCOME taxonomy (success / failed / no-candidate) covering
     attempted-but-not-acquired items, feeding `recently_rejected` + the taste signals.
   - An acquisition-time CATALOG-DIVERSITY MMR re-rank biases against re-grabbing same-artist/
     same-cluster, GATED on catalog size and RELAXED below the wishlist low-watermark (never starves
     a thin catalog); it is DISTINCT from the playout no-repeat (the two-no-repeat separation).

6. **Grounded host voice & quality gate (Group PG, added v0.3.0).**
   - The talk LLM receives ONE closed-world fact contract (TrackContext from ANALYSIS-006 +
     sourced ShowPrep facts from KNOWLEDGE-008); it speaks no fact from free-recall.
   - The grounding rule holds: a fact absent from context is never spoken; perceptual
     description is allowed, named factual attribution only if in context; silence beats a
     wrong fact.
   - Comparison discipline holds: grounded comparisons only (match_score / shared tag /
     ShowPrep fact), fusion formulas banned, at most one per break.
   - The anti-slop register (banned music-slop + LLM-tells + positive rules) extends OPS-004
     REQ-OF-005; the two-tier quality gate (deterministic lint incl. forbidden-fact scan +
     adversarial self-check) refines REQ-OF-006; on FAIL it regenerates once then SKIPS — a
     FAIL never airs (NFR-P-8).
   - A per-persona voice card is injected every call, consistent + length-capped, opinion
     only about the audible.

7. **Host-voice persona-awareness, delivery craft & continual improvement (Group PV, added v0.4.0).**
   - Every persona is framed as a LIVE HUMAN RADIO HOST via a positive-identity HOST_PERSONA
     (replacing the negation-based one); "live human host" is a DELIVERY stance, never a spoken
     claim, never a fourth-wall break; grounding (KNOWLEDGE-008) is untouched.
   - The calibrated delivery DO-set is carried in the live prompt: pacing punctuation,
     contractions, ONE grounded theater-of-the-mind detail, one-to-one "you", daypart-calibrated
     GENUINE energy (a WRITING property, not hype), Hook→Body→Exit ≤30s.
   - The ear-writing rails (REQ-PS-001..005) are present IN the live talk prompt, preserving the
     REQ-PS-004 blank-line-block ↔ VOICE-002 chunk-silence pacing contract.
   - The governing principle holds: warmth and energy in DELIVERY, restraint in CONTENT —
     turning delivery up never relaxes grounding, the anti-slop register, or comparison discipline.
   - The extended banned list holds: every existing ban PLUS filler-as-crutch (≤1 warmth-
     transition/break, never the same tic two breaks running) and no shared cross-persona filler
     set (each persona's verbal-tic bank is DISJOINT).
   - The frontsell teases by FEELING (mood/energy), never the next track's name and never "coming
     up"; the name is saved for the backsell.
   - [HARD] The live "Coming up next" frontsell REGRESSION is fixed in code: `brain/talk.py`
     `_build_context` no longer passes next_artist/next_title names, and `brain/llm.py`
     `_build_talk_prompt` no longer emits the banned "Coming up next" block — replaced with a
     mood-hint frontsell derived from ANALYSIS-006 features.
   - The per-persona voice card is extended with an energy band, pacing signature, register, and
     a disjoint verbal-tic bank, injected every call without breaking grounding.
   - The quality gate is extended with distinctness + crutch lints (warmth-transition over-use +
     cross-persona tic-collision), riding the REQ-PG-005 two-tier gate.
   - The continual-improvement loop is BOUNDED, MEASURED refinement of prompts/rules/voice-cards
     in the OPS-004 store — NOT model fine-tuning — with no self-imitation, NO engagement/appeal
     target, the OPS-004 rate-limit/canary/contradiction rails, and a FROZEN invariant set the
     loop may never evolve (NFR-P-9).
   - (Added v0.5.0 — banter authenticity:) the positive-identity HOST_PERSONA carries the
     music-journalist register lineage (6 Music / NTS / KEXP) + the "text one smart, slightly-
     impatient friend" addressee frame and is WIRED into `brain/llm.py` (closing the diagnosed
     sterility gap); each ban is paired with a positive "say this instead" twin in the prompt; the
     BLUNT-PRAISE LICENSE holds (owned + specific praise passes, borrowed PR vocabulary floating
     free fails); the per-persona/daypart PROFANITY + HUMOUR policy holds (card tier capped down by
     daypart, no quota, never at a person, slur-banned, grounded humour); the THREE-CLASS CONTENT
     TAXONOMY routes every clause (music-fact gated; audible-opinion + fenced self-disclosure
     licensed; a smuggled music-fact token reclassified + gated); and the specificity+ownership
     praise lint + Tier-2 smuggled-token scan ride the gate — all on the DELIVERY axis, no ban
     weakened, grounding untouched.
   - (Added v0.7.0 — register currency:) the DATED / TRY-HARD-SLANG ban holds — no "hip / swagger /
     groovy / the kids / fellow-kids" faux-cool slang; the host uses contemporary, register-true
     vocabulary in its OWN voice (REQ-PV-009/REQ-PI-001), enforced as a distinct Tier-1 lint
     term-class (REQ-PV-017) that fails an owned-but-dated line and composes with the blunt-praise
     license (owned+specific AND register-true).

8. **Persona identity / anchors (Group PI, added v0.5.0).**
   - Every curator persona has a two-block voice card: a FROZEN CORE (≥2 permanent anchor focuses
     incl. the REQ-PR-004 primary territory + core temperament + voice signature) over an EVOLVABLE
     LAYER (the only loop-writable surface).
   - Anchors are FROZEN — added to the FROZEN invariant set; no continual-improvement/taste loop
     writes an anchor field; anchor changes are human-only and out-of-band.
   - The per-persona Frozen Guard blocks an anchor-targeting graduation proposal at intake (before
     canary), logs it, and never applies it; only evolvable-layer targets proceed.
   - The distinctness canary shadow-evaluates every evolvable change against the anti-convergence
     firewall + the cross-persona collision lint (incl. the new banter fields) and rejects drift
     toward another persona's primary territory or a shared-field collision — develop-plus-shared-
     craft provably cannot homogenize the 5+2 roster.
   - The per-persona FOCUS TABLE (5 EN + 2 FO, anchors marked, primaries pairwise-distinct) is
     authored as illustrative seed content; the STRUCTURE (≥2 anchors + temperament + voice +
     distinct secondaries) is the fixed rail.
   - [HARD] The NEWS ANCHOR is excluded by construction — not a curator persona (no charter/POV/
     taste/firewall-slot/evolvable-card/anchor contract), wholly frozen (factual/sourced/attributed/
     apolitical), owned by OPS-004 Group OG + ORCH-005 Group RN; its one frozen carve-out (bounded
     impartial implication-analysis: attributed-OR-necessary, grounded+attributed, dropped-if-
     ungroundable, never opinion/advocacy/normative) TIGHTENS the apolitical rail and is referenced,
     not re-owned (R-P-20 records the contested checkability).

9. **Long-form episode craft (added v0.8.0).**
   - A LONGFORM-025-conceived long-form instance (album-doc / artist-retrospective / era-spotlight)
     inherits the long-form rails UNCHANGED (REQ-PT-009): single-narrator-or-max-2, ear-writing +
     pauses + ducked bed, pre-rendered to one loudness-normalized file via the OPS-004 ready buffer.
   - The fictional-persona guardrail (REQ-PT-005) + mandatory open/close disclaimer (REQ-PT-006) apply
     wherever an invented character is voiced; a real-subject episode carries the truth load via
     grounding (REQ-PG-002) + quote-sourcing (REQ-PG-008), never by fabricating a real biography.
   - Long-form is written as 5-15-minute ducked-bed monologue blocks with long-form backtiming / ramp /
     backsell (REQ-PC-011), delivered in the persona's register on the warmth-in-delivery /
     restraint-in-content spine at long-form scale (REQ-PV-018), never talking over a vocal.
   - An EPISODE-LEVEL Tier-3 coherence gate (REQ-PG-007: arc-beats-in-order + cross-segment
     non-contradiction + persona-charter consistency) runs on the whole script before pre-render, ABOVE
     the UNCHANGED per-break Tier-1/Tier-2 gate; a twice-failing episode is DEFERRED, never aired.
   - A quote-sourcing lint (REQ-PG-008) drops any attributed interview/liner quote missing source_url +
     speaker + date so a fabricated "X said Y" never airs; verbatim song lyrics are NOT gated (PIVOT).
   - Episode-persona-state threading (REQ-PV-019) carries the frozen temperament/signature + injects the
     arc-phase into every segment voice-card call (one coherent persona within an episode); the
     cross-episode frozen-anchor audit (REQ-PI-006) reverts + logs any anchor drift episode-to-episode.
   - Every long-form episode is integrity-checked before air on four axes and never silences the stream
     (NFR-P-10); LONGFORM-025 Group LB owns the instance conception, referenced not re-owned.

10. **Cross-cutting.**
   - No editorial decision silences the stream (NFR-P-5); a failing script is dropped
     (graceful-skip) via the OPS-004 buffer/gate.
   - The layer adds no new service/store/playout seam (NFR-P-6); it consumes CORE-001's
     persona model, VOICE-002's TTS, OPS-004's playbook store / ledger-diary / pull seam /
     quality gate, ANALYSIS-006's dimensions / cue metadata / sonic-character / Track record
     (extended in place), and KNOWLEDGE-008's grounding feed, and forks none of them.
   - All talk obeys the inherited anti-slop (OPS-004 REQ-OF-005), the script gate
     (REQ-OF-006), the no-self-imitation rule (REQ-OC-006), and the apolitical rail
     (REQ-OF-004); taste evolution obeys the anti-appeal rule (NFR-O-7); host facts obey the
     grounded-never-fabricated rail (REQ-OC-005) via the Group PG fact contract + gate.
   - Every requirement (78 REQ + 10 NFR = 88) has a passing acceptance entry; the 1:1 REQ↔AC
     mapping holds against the spec's traceability index.
