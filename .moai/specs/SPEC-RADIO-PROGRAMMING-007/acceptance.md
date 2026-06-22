# SPEC-RADIO-PROGRAMMING-007 — Acceptance Criteria

Acceptance criteria for SPEC-RADIO-PROGRAMMING-007 (Hosts, Personas, Radio Craft &
Show Formats). Section A gives one acceptance entry per requirement (1:1 with the
spec's traceability index: 44 REQ + 8 NFR = 52). Section B gives detailed
Given-When-Then scenarios for the load-bearing requirements. Section C is the
Definition of Done.

All acceptance is editorial-content-layer acceptance: it verifies that the persona
model, the radio-craft rules, the ear-writing rules, and the show formats behave as
specified WHEN they flow through the inherited engines (CORE-001 personas, VOICE-002
TTS, OPS-004 playbook store / pull seam / quality gate, ANALYSIS-006 dimensions). It
never re-verifies those engines.

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
appeal/engagement metric as an optimization target.

**AC-NFR-P-8 (NFR-P-8 — grounding integrity).** Verify: (a) every aired host break is
gate-passed (REQ-PG-005 ran); (b) no spoken factual claim lacks a corresponding entry in the
supplied fact contract (forbidden-fact scan + adversarial self-check enforced); (c) a script
failing the gate twice is SKIPPED, never aired ("talks less" > wrong facts), preserving
never-stops; (d) generated scripts + gate verdicts are logged so a grounding violation is
detectable after the fact.

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

7. **Cross-cutting.**
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
   - Every requirement (44 REQ + 8 NFR = 52) has a passing acceptance entry; the 1:1 REQ↔AC
     mapping holds against the spec's traceability index.
