---
id: SPEC-RADIO-SHOWS-020-acceptance
version: 0.2.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
spec: SPEC-RADIO-SHOWS-020
---

# SPEC-RADIO-SHOWS-020 — Acceptance Criteria

1:1 REQ ↔ AC. Section A is the per-requirement acceptance summary (one entry per REQ/NFR). Section B
carries detailed Given-When-Then scenarios for the load-bearing, anti-repetition, grounding, and
distinctness-critical requirements. Section C is the Definition of Done and the quality gates.

A passing implementation MUST satisfy every Section A entry and every Section B scenario. Where a
criterion is marked [HARD] it is a must-pass gate (no compensation by other criteria).

Group prefixes: LF (Last.fm Research Client) / SG (Show / Program Model) / SX (Editorial Variation
Engine) / SP (Per-Persona Distinctness) / SD (Scheduling / Direction) / SB (Show Wiring).
25 AC + 8 AC-NFR = 33, matching spec.md 25 REQ + 8 NFR (v0.2.0: +AC-LF-006, +AC-SG-005, +AC-SD-005,
+AC-NFR-S-8).

---

## Section A — Per-Requirement Acceptance

### Group LF — Last.fm Research Client

**AC-LF-001 (REQ-LF-001 — key-gated; fully graceful with no key):**
- GIVEN the Last.fm research client, WHEN `lastfm_api_key` is set, THEN it performs research calls; WHEN
  the key is absent, THEN it logs ONCE at INFO and returns EMPTY without constructing a client or raising.
- [HARD] With no key the show engine falls back to taste-only angles and the station is completely
  unaffected (asserted: no key path constructs no client, raises nothing, and the director/talk loops run
  unchanged — mirrors the existing `brain/metadata.py` Last.fm behaviour).

**AC-LF-002 (REQ-LF-002 — rate-limited, timed-out, exception-isolated):**
- GIVEN a research call, WHEN it runs, THEN it has an explicit timeout, is rate-limited (self-throttle),
  and returns EMPTY on ANY error (network/dependency/parse/timeout) without raising.
- [HARD] A research flake never propagates toward the director tick, the talk loop, or the `/api/next`
  pull (asserted: each method is exception-isolated and returns empty on error).

**AC-LF-003 (REQ-LF-003 — complements, never duplicates, the existing providers):**
- GIVEN the research client, WHEN it is built, THEN it exposes `artist.getInfo` / `artist.getSimilar` /
  `artist.getTopTags` / `tag.getTopArtists` / `track.getInfo` and is DISTINCT from the ANALYSIS-006
  `brain/metadata.py` genre-consensus provider.
- [HARD] It does NOT re-derive genre consensus (REQ-AM-003 stays sole owner), does NOT modify `enrich()`,
  and does NOT re-own artist facts (KNOWLEDGE-008 over MBMIRROR-017) (asserted: no consensus logic in the
  research client; `enrich()` is unchanged).

**AC-LF-004 (REQ-LF-004 — per-field research provenance):**
- GIVEN a research item, WHEN it is returned, THEN it carries provenance (which Last.fm method + which
  artist/tag query produced it) so a downstream talking point can be traced and a show's grounding audited.

**AC-LF-005 (REQ-LF-005 — bounded background job, never on the pull path):**
- GIVEN the station running, WHEN research + show-planning runs, THEN it runs as a BOUNDED, THROTTLED
  background job (OPS-004 REQ-OH-006 pattern, adopted by reference) and NEVER on the `/api/next` pull.
- [HARD] At its bound (downloads in flight / throttle engaged) research/planning is deferred, not piled
  on (asserted: planning work runs off the pull path on the director/talk background loops).

**AC-LF-006 (REQ-LF-006 — artist-fact research leads aired only via KNOWLEDGE-008, never raw):**
- GIVEN `artist.getInfo` / `track.getInfo` bio/tag/popularity material, WHEN it is gathered, THEN it is
  treated as an artist-fact research LEAD (something to look up), NOT broadcast text.
- [HARD] A Last.fm fact lead is NEVER voiced directly; an artist fact becomes airable only after it lands
  as a KNOWLEDGE-008 dated/sourced fact and passes the PROGRAMMING-007 grounding gate UNCHANGED (the single
  airable-fact seam, D-S-5); relative popularity may frame loosely but is never quoted as a precise live
  figure (asserted: no raw Last.fm bio/wiki string reaches air without entering KNOWLEDGE-008 first).

### Group SG — Show / Program Model

**AC-SG-001 (REQ-SG-001 — typed Show record):**
- GIVEN a planned show, WHEN it is recorded, THEN a typed record exists with `persona_id`, `theme`/`angle`,
  `selection_lens`, `talking_points`, `provenance`, `created_at`, and `status`.
- [HARD] The record lives in the existing store seam (no new datastore, no library fork).

**AC-SG-002 (REQ-SG-002 — show status lifecycle):**
- GIVEN a show, WHEN it progresses, THEN `status` advances `proposed` → (`rejected` | `active`) →
  `retired`.
- [HARD] A `rejected` show never drives curation or talk; a `retired` show's angle/theme is recorded in
  the per-persona recent-shows ledger for future novelty checks (REQ-SX-002).

**AC-SG-003 (REQ-SG-003 — declarative, catalog-resolvable selection lens):**
- GIVEN a `selection_lens`, WHEN it is resolved, THEN it is a declarative rule (genre / era / mood /
  similar-artist-neighbourhood / tag) resolvable against the LOCAL catalog + ANALYSIS-006 features + the
  Last.fm similar-artist research.
- [HARD] The lens resolves to a BIAS over EXISTING catalog tracks (+ a wishlist hint for gaps); it never
  fabricates a track or force-inserts, and a lens resolving to nothing degrades to ordinary curation
  (NFR-S-5).

**AC-SG-004 (REQ-SG-004 — design research vs airable grounded facts, kept separate):**
- GIVEN a show, WHEN talking points are prepared, THEN INTERNAL show-design research (used to pick the
  theme/lens) is distinguished from AIRABLE talking points (notes the host MAY voice).
- [HARD] A spoken talking point is a GROUNDED fact (a KNOWLEDGE-008 sourced fact in context) validated by
  the PROGRAMMING-007 Group PG gate UNCHANGED — never a raw Last.fm research string voiced directly; design
  research is internal-only and never aired.

**AC-SG-005 (REQ-SG-005 — durable per-persona show HISTORY ("last shows"); our data, not Last.fm events):**
- GIVEN shows that have run, WHEN they retire, THEN a durable per-persona show HISTORY persists (the
  `retired` Show records with theme/angle, lens, provenance, timestamps) in the existing store seam (no new
  datastore) — the same store that feeds the recent-shows novelty ledger (REQ-SX-002).
- [HARD] The show history is OUR OWN data, never sourced from a Last.fm events API (which was retired in
  2016, `research.md` §4/§5c); Last.fm only INFORMED each show's content (asserted: no code path queries a
  Last.fm events/gigs endpoint; "last shows" reads our persisted history).

### Group SX — Editorial Variation Engine

**AC-SX-001 (REQ-SX-001 — LLM proposes a fresh research-grounded, taste-grounded angle):**
- GIVEN a show being planned for a persona, WHEN the engine runs, THEN the LLM proposes an angle/theme +
  selection lens + candidate talking points grounded in the supplied Last.fm research + the persona's
  taste profile + the catalog.
- [HARD] The angle is editorial INVENTION grounded in real research, not an engagement-optimized theme
  (inherited anti-pandering); the LLM call is best-effort and an error falls back to a taste-only angle or
  no show (plain curation), never stalling.

**AC-SX-002 (REQ-SX-002 — per-persona recent-shows ledger + novelty check):**
- GIVEN a per-persona recent-shows ledger (angles/themes + timestamps from `retired` shows), WHEN a new
  angle is proposed, THEN it is checked for NOVELTY against that persona's shows within the configurable
  window; a too-similar angle is `rejected` and the engine regenerates (grounded in fresh research).
- [HARD] No slot's show repeats a recent KIND of show for that persona within the window; a novel angle
  becomes `active` (asserted by the Section B anti-repetition scenario). The threshold + window + max
  retries are tunable config.

**AC-SX-003 (REQ-SX-003 — continuous fresh angles; never a fixed template):**
- GIVEN successive shows, WHEN they are generated, THEN the editorial angle varies continuously (themes,
  lenses, eras/genres/moods within the persona's territory).
- [HARD] No single show template is mechanically reused; SHOWS-020 supplies VARYING editorial content over
  the PROGRAMMING-007 Group PT format skeletons (referenced, not re-owned).

**AC-SX-004 (REQ-SX-004 — novelty-reject loop bounded; graceful fallback):**
- GIVEN repeated novelty rejections, WHEN the engine cannot find a novel angle, THEN after a BOUNDED number
  of regenerate attempts it falls back to a taste-only angle (or no show + ordinary curation) and proceeds.
- [HARD] A novelty-reject storm never loops indefinitely or stalls a director tick, a talk break, or
  playout (asserted by the Section B reject-storm scenario). The retry bound is config.

### Group SP — Per-Persona Distinctness

**AC-SP-001 (REQ-SP-001 — shows generated per-persona in their own taste/voice):**
- GIVEN a show, WHEN it is generated, THEN it is FOR a specific roster persona, IN that persona's
  taste/voice/territory (consuming PROGRAMMING-007 Group PR roster + REQ-PR-005/006 + REQ-PL-004).
- [HARD] The engine consumes the persona model by reference (does not re-own roster/taste). [GREENFIELD]
  Until the roster ships, the engine degrades to a SINGLE DEFAULT persona — shows still vary + stay
  grounded; per-persona distinctness activates when the roster lands with no SHOWS-020 change (asserted by
  the Section B greenfield scenario).

**AC-SP-002 (REQ-SP-002 — roster never converges; angles not shared across personas):**
- GIVEN the roster, WHEN shows are generated, THEN a show angle/lens for one persona is NOT reused for
  another, and the PROGRAMMING-007 REQ-PR-004 anti-convergence firewall applies UNCHANGED.
- [HARD] No homogenizing behaviour (no shared global "show of the week", no copying a successful angle
  across personas); each persona's programme stays its own (asserted by the Section B distinctness
  scenario).

**AC-SP-003 (REQ-SP-003 — shared engine preserves per-persona distinctness):**
- GIVEN the shared variation engine, WHEN it serves multiple personas, THEN the ledger, novelty window,
  and taste grounding are PER-PERSONA and the anti-convergence + disjoint-territory discipline applies
  unchanged.
- [HARD] No single uniform show behaviour across hosts is imposed; the engine being shared is not a
  convergence force.

### Group SD — Scheduling / Direction

**AC-SD-001 (REQ-SD-001 — active show biases curation; non-binding, picker autonomy preserved):**
- GIVEN an `active` show, WHEN the director curation tick runs, THEN the show's `selection_lens` biases the
  curation/wishlist input exactly as the existing `seed_reference` is a non-binding reference.
- [HARD] The lens never force-inserts, overrides rotation/clock/no-repeat, or removes picker autonomy; the
  picker MAY still decline a lens-favoured track (asserted: the lens is a bias input, not a forced queue).

**AC-SD-002 (REQ-SD-002 — active show feeds talk theme + talking points into the existing context):**
- GIVEN a talk break during an `active` show, WHEN `_build_context` runs, THEN the show's `theme` +
  grounded `talking_points` are ADDED into the EXISTING `brain/talk.py` context bundle (alongside the
  HOSTCTX-016 per-song facts + the KNOWLEDGE-008 grounding feed).
- [HARD] This extends the context dict in place (no fork, no second talk loop); a break without an active
  show simply omits the show keys (existing behaviour).

**AC-SD-003 (REQ-SD-003 — spoken show content grounded + gate-validated like any host fact):**
- GIVEN a spoken show talking point, WHEN the break is generated, THEN it is a FACT TOKEN subject to the
  PROGRAMMING-007 grounding rule (REQ-PG-002) + two-tier gate (REQ-PG-005) UNCHANGED.
- [HARD] A talking point not traceable to a supplied grounded fact FAILS the forbidden-fact scan,
  regenerates once, and is skipped on a second FAIL; SHOWS-020 adds no new gate and weakens none; a
  compelling angle never licenses an ungrounded claim.

**AC-SD-004 (REQ-SD-004 — director decides the show when unhosted):**
- GIVEN no scheduled-host persona presenting, WHEN a show is needed, THEN the LLM director (CORE-001
  REQ-D-006/007) decides the show itself under the SAME rails (grounded, novel against the ledger,
  never-blocks).
- [HARD] The director has discretion over WHICH show when unhosted (HOSTCTX-016 director discretion), NOT
  over the grounding/novelty/non-blocking discipline; WHEN a show runs + WHICH persona is on-air remains
  the OPS-004 Group OA / ORCH-005 call (referenced, not re-owned).

**AC-SD-005 (REQ-SD-005 — per-persona forward "planned shows" schedule; our data, distinct from time-grid):**
- GIVEN the engine plans ahead, WHEN it queues upcoming show CONTENT for a persona, THEN a per-persona
  FORWARD "planned shows" schedule persists (novelty-passed `proposed` shows queued ahead) that the director
  consumes when a slot for that persona comes due.
- [HARD] The planned-shows schedule is OUR OWN data (`research.md` §5d, never a Last.fm feed) and DISTINCT
  from the OPS-004 Group OA / ORCH-005 TIME-GRID (which remains sole owner of WHEN a slot occurs + WHICH
  persona is on-air); SHOWS-020 supplies queued CONTENT only and never forks the schedule store.
- [HARD] The queue is bounded + never-blocks: an empty queue falls back to just-in-time angle proposal
  (REQ-SX-001), and a queued show still passes the novelty check at activation (REQ-SX-002).

### Group SB — Show Wiring

**AC-SB-001 (REQ-SB-001 — additive wiring; no fork):**
- GIVEN the engine integrated, WHEN it runs, THEN it attaches to the EXISTING `brain/director.py` tick (the
  lens biases the batch like `seed_reference`), the EXISTING `brain/talk.py` `_build_context` (theme +
  talking points join the bundle), and new `brain/config.py` knobs (enable toggle, anti-repetition window,
  cadence, Last.fm rate/timeout).
- [HARD] No new service, store fork, second director/talk loop, or Liquidsoap change; show records + ledger
  live in the existing store seam; with the engine disabled/empty the loops behave exactly as before this
  SPEC.

**AC-SB-002 (REQ-SB-002 — strictly off the playout pull path):**
- GIVEN slow/erroring/empty show planning, research, or context assembly, WHEN `/api/next` is pulled, THEN
  the pull does NOT wait on it or get affected; all SHOWS-020 work runs on the director tick + the
  talk-context-assembly background paths, never on the sub-1s pull.
- [HARD] A SHOWS-020 error logs and is skipped (the show does not apply this tick / show keys not added),
  preserving the existing curation + break and never crashing the director loop, the talk loop, or the
  daemon.

---

## Section A (cont.) — Non-Functional Acceptance

**AC-NFR-S-1 (NFR-S-1 — never blocks/silences playout; fully graceful):** [HARD] Research is key-gated +
exception-isolated, show planning is best-effort background work off the pull path (REQ-LF-005,
REQ-SB-002), and missing research / an absent show / an absent key / a novelty-reject loop degrades
gracefully (taste-only angle / single default persona / no show + plain curation); the music never silences.

**AC-NFR-S-2 (NFR-S-2 — anti-repetition load-bearing):** [HARD] No slot's show repeats a recent KIND of
show for that persona within the configurable window; the per-persona recent-shows ledger + the novelty
check (REQ-SX-002) structurally defeat show-sameness (ties REQ-SX-001/002/003/004).

**AC-NFR-S-3 (NFR-S-3 — grounded integrity):** [HARD] Every spoken show talking point traces to a supplied
grounded fact and passes the PROGRAMMING-007 REQ-PG-005 forbidden-fact scan + adversarial self-check
unchanged; a compelling angle never licenses an ungrounded claim; a FAIL never airs (ties REQ-SD-003,
REQ-SG-004).

**AC-NFR-S-4 (NFR-S-4 — single-source-of-truth; brain-only + additive):** [HARD] No code path re-owns or
forks the PROGRAMMING-007 roster/taste/firewall/formats/gate, the ANALYSIS-006 genre consensus, the
KNOWLEDGE-008 fact graph, the HOSTCTX-016 per-song facts, the MBMIRROR-017 mirror, the OPS-004/ORCH-005
scheduler, or the CORE-001 picker; each is referenced by id and consumed. SHOWS-020 is brain-only +
additive (no new service, no new datastore).

**AC-NFR-S-5 (NFR-S-5 — show biases, never forces; picker autonomy preserved):** [HARD] No code path lets a
show's selection lens force-insert tracks, override rotation/clock/no-repeat, or remove picker autonomy;
the lens is a non-binding curation/wishlist bias (REQ-SD-001, like `seed_reference`), and a lens resolving
to nothing degrades to ordinary curation.

**AC-NFR-S-6 (NFR-S-6 — per-persona distinctness; roster never converges):** [HARD] The shared engine does
not homogenize the roster: the ledger, novelty window, and taste grounding are per-persona and the
PROGRAMMING-007 REQ-PR-004 firewall applies unchanged; no angle is shared across personas, no uniform
every-host show is imposed (ties REQ-SP-001/002/003).

**AC-NFR-S-7 (NFR-S-7 — bounded/throttled processing):** The Last.fm research + show-planning jobs are
bounded and throttled (OPS-004 REQ-OH-006 pattern, REQ-LF-005) so they do not jointly overload the box
alongside playout, acquisition, analysis, and knowledge research.

**AC-NFR-S-8 (NFR-S-8 — Last.fm ToS compliance):** [HARD] The research client/store complies with the
Last.fm ToS verified in `research.md` §3: (a) caches responses per HTTP cache headers / a sane TTL (ToS
4.3.4, caching is REQUIRED); (b) keeps stored Last.fm-derived data under the 100 MB Reasonable-Usage cap
and prunes; (c) uses Last.fm strictly as private NON-COMMERCIAL research INPUT (ToS 3.1) and re-publishes no
raw Last.fm data / builds no public mirror; (d) sets an identifiable User-Agent on every request; (e)
attaches Last.fm attribution + the `url` back-link IF any Last.fm-derived text/link is ever surfaced to
listeners (4.2.2); (f) observes the polite ≤ 1 req/s default + error-29/16 backoff (REQ-LF-002). A
`partners@last.fm` contact is a user-provisioned prerequisite if the station is monetized or Last.fm data
is surfaced verbatim (asserted: no raw Last.fm data published; caching + cap + User-Agent present).

---

## Section B — Detailed Given-When-Then Scenarios (load-bearing / anti-repetition / grounding / distinctness)

### B1 — Anti-repetition: a persona does not run the same kind of show week after week (REQ-SX-002, REQ-SG-002, NFR-S-2) [HARD]

```
GIVEN persona P with a recent-shows ledger holding angles run within the configurable window
  (e.g. "the producers behind the sound", "1979 in one hour", "label retrospective: Factory Records")
WHEN the engine proposes a new show for P and the LLM returns an angle "the producers behind the sound, vol. 2"
THEN the novelty check finds it too similar to a recent ledger angle and REJECTS it (status `rejected`)
  AND the engine regenerates, grounded in fresh Last.fm research (e.g. artist.getSimilar / tag.getTopArtists)
  AND a sufficiently NOVEL angle (e.g. "mid-tempo b-sides from the catalog's quietest corners") becomes `active`
  AND on slot end the active angle is recorded to P's ledger for future novelty checks
```
Verification: assert a proposed angle within the similarity threshold of a windowed ledger entry is
rejected + regenerated; the eventually-active angle is novel; the retired angle enters the ledger (the
structural defeat of show-sameness, the user's headline ask).

### B2 — Novelty-reject storm degrades gracefully, never blocks (REQ-SX-004, NFR-S-1/S-5) [HARD]

```
GIVEN a persona with a thin catalog and many recent shows (every fresh angle keeps colliding with the ledger)
WHEN the engine proposes + the novelty check rejects angle after angle
THEN after a BOUNDED number of regenerate attempts the engine falls back to a taste-only angle
  (or no show + ordinary curation) and PROCEEDS
  AND it NEVER loops indefinitely, never stalls the director tick, the talk break, or the audio path
```
Verification: assert the regenerate loop is bounded; on exhaustion the engine degrades to plain operation;
the director/talk/playout paths are never blocked (addressing R-S-2).

### B3 — Last.fm graceful with no key; research complements, never duplicates (REQ-LF-001, REQ-LF-003, NFR-S-1/S-4) [HARD]

```
GIVEN no BRAIN_LASTFM_API_KEY is set
WHEN the show engine plans a show
THEN the research client logs once at INFO and returns EMPTY (constructs no client, raises nothing)
  AND the engine falls back to a taste-only angle; the station is completely unaffected
GIVEN a key IS set
WHEN research runs
THEN the research client uses artist.getInfo / getSimilar / getTopTags / tag.getTopArtists / track.getInfo
  AND it is SEPARATE from the ANALYSIS-006 brain/metadata.py genre-consensus provider
  AND it does NOT re-derive genre consensus, does NOT modify enrich(), does NOT re-own artist facts
```
Verification: assert the no-key path matches the existing metadata.py behaviour (log-once, empty, no
client); assert the research client carries no consensus logic and enrich() is unchanged (addressing R-S-4).

### B4 — A show biases curation but never forces the picker (REQ-SD-001, REQ-SG-003, NFR-S-5) [HARD]

```
GIVEN an `active` show whose selection_lens is "tracks by artists similar to Boards of Canada"
WHEN the director curation tick runs
THEN the lens is threaded into the curation batch as a NON-BINDING bias (exactly like seed_reference)
  AND the director researches/wishlists lens-fitting artists and biases the picker toward lens-fitting tracks
  AND the picker MAY still decline a lens-favoured track; rotation/clock/no-repeat are NOT overridden
  AND if the lens resolves to no catalog tracks it degrades to a wishlist hint + ordinary curation (no fabrication)
```
Verification: assert the lens is a bias input not a forced queue; the picker keeps autonomy; an empty lens
degrades to plain curation (addressing R-S-3).

### B5 — Spoken show content is grounded + gate-validated; design research stays internal (REQ-SD-003, REQ-SG-004, NFR-S-3) [HARD]

```
GIVEN an `active` show with internal Last.fm design research (used to pick the theme + lens)
  AND candidate talking points
WHEN a talk break is generated
THEN only talking points that are GROUNDED facts (KNOWLEDGE-008 sourced facts in context) may be spoken
  AND each spoken factual claim passes the PROGRAMMING-007 forbidden-fact scan + two-tier gate UNCHANGED
  AND a talking point not traceable to a supplied grounded fact FAILS, regenerates once, is skipped on a second FAIL
  AND raw Last.fm design-research strings are NEVER voiced directly (internal planning material only)
```
Verification: assert a spoken claim not in the supplied grounded context fails the gate; design research is
never aired without first being a grounded fact (one fact-supply seam, mirrors HOSTCTX-016 REQ-HW-003;
addressing R-S-5).

### B6 — Per-persona distinctness; the roster never converges (REQ-SP-001, REQ-SP-002, REQ-SP-003, NFR-S-6) [HARD]

```
GIVEN two roster personas P1 (its territory) and P2 (a disjoint territory, REQ-PR-004 firewall)
WHEN the engine generates a show for each
THEN each show is generated IN that persona's own taste/voice/territory
  AND a show angle/lens for P1 is NOT reused for P2 (no shared global "show of the week")
  AND the recent-shows ledger, novelty window, and taste grounding are PER-PERSONA
  AND the PROGRAMMING-007 REQ-PR-004 anti-convergence firewall applies unchanged
```
Verification: assert no cross-persona angle reuse; per-persona ledgers; the firewall is referenced not
re-owned (addressing R-S-6).

### B7 — Greenfield roster: variation works against a single default persona (REQ-SP-001, R-S-1)

```
GIVEN the PROGRAMMING-007 persona roster (Group PR) is NOT yet built (the talk layer uses one HOST_PERSONA)
WHEN the engine plans shows
THEN it runs against a SINGLE DEFAULT persona
  AND shows still VARY (the novelty engine runs against that single persona's own recent-shows ledger)
  AND talking points still stay grounded
  AND when the roster ships, the SAME engine generates per-persona distinct shows with NO SHOWS-020 change
```
Verification: assert the engine does not assume a roster surface that does not exist; the degraded mode
preserves variation + grounding; distinctness activates on roster arrival (addressing D-S-1 / R-S-1).

### B8 — Director decides the show when unhosted, under the same rails (REQ-SD-004, REQ-SX-002, NFR-S-1) [HARD]

```
GIVEN no scheduled-host persona is presenting (the OPS-004/ORCH-005 scheduler reports unhosted)
WHEN a show is needed
THEN the LLM director (CORE-001 REQ-D-006/007) decides the show itself
  AND the director's show obeys the SAME rails: grounded, novel against the ledger, never-blocks
  AND the director has discretion over WHICH show, NOT over the grounding/novelty/non-blocking discipline
  AND WHEN a show runs + WHICH persona is on-air remains the scheduler's call (referenced, not re-owned)
```
Verification: assert the unhosted show path applies the same novelty + grounding + non-blocking rails as a
persona's; the scheduler ownership is referenced, not re-owned.

### B9 — All SHOWS-020 work is off the playout pull path (REQ-SB-002, REQ-LF-005, NFR-S-1) [HARD]

```
GIVEN show planning / Last.fm research / show-context assembly is slow, errors, or finds nothing
WHEN /api/next is pulled for the next track
THEN the pull does NOT wait on any SHOWS-020 work and is unaffected
  AND all SHOWS-020 work runs on the director tick + the talk-context-assembly background paths
  AND a SHOWS-020 error logs and is skipped (show not applied this tick / show keys not added)
  AND the existing curation + break are preserved; the director loop, talk loop, and daemon never crash
```
Verification: assert no SHOWS-020 code executes on the sub-1s pull path; every failure mode logs +
degrades (mirrors the existing director/talk best-effort discipline).

### B10 — "Last shows" + "planned shows" are OUR persisted data, never Last.fm events (REQ-SG-005, REQ-SD-005, REQ-LF-006) [HARD]

```
GIVEN the user asks for a persona's recent shows ("last shows") and its upcoming schedule ("planned shows")
WHEN the engine answers
THEN "last shows" reads OUR durable per-persona show HISTORY (retired Show records, REQ-SG-005)
  AND "planned shows" reads OUR per-persona forward CONTENT queue (REQ-SD-005)
  AND NO code path queries a Last.fm events/gigs/radio endpoint (retired 2016, research.md §4)
  AND the OPS-004/ORCH-005 time-grid remains sole owner of WHEN a slot occurs + WHICH persona is on-air
  AND any artist FACT colour for those shows is a KNOWLEDGE-008-grounded fact, never a raw Last.fm string (REQ-LF-006)
```
Verification: assert show history + the forward schedule are our own persisted data (no Last.fm events
dependency); the time-grid ownership is referenced not re-owned; artist facts route through KNOWLEDGE-008
(addressing the broadened use cases + research.md §4/§5c-d/§5b).

---

## Section C — Definition of Done & Quality Gates

A SHOWS-020 implementation is DONE when:

1. [HARD] All 25 REQ + 8 NFR Section A entries pass, and all Section B scenarios pass.
2. [HARD] **Anti-repetition invariant holds (REQ-SX-002, NFR-S-2):** no slot's show repeats a recent kind
   of show for that persona within the configurable window; the per-persona recent-shows ledger + novelty
   check defeat show-sameness (B1); the reject loop is bounded + degrades gracefully (B2).
3. [HARD] **Never blocks/silences playout (NFR-S-1, REQ-SB-002):** all work is best-effort background off
   the pull path; missing research / absent show / absent key / reject storm degrades gracefully; the
   music never silences (B2, B9).
4. [HARD] **Last.fm key-gated + graceful + complementary (REQ-LF-001/002/003):** no key → log-once + empty
   + taste-only fallback; rate-limited + timed-out + exception-isolated; separate from the ANALYSIS-006
   genre-consensus provider, does not modify `enrich()` or re-derive consensus (B3).
5. [HARD] **A show biases, never forces (REQ-SD-001, REQ-SG-003, NFR-S-5):** the selection lens is a
   non-binding curation/wishlist bias (like `seed_reference`); the picker keeps autonomy; an empty lens
   degrades to plain curation; no fabricated/force-inserted tracks (B4).
6. [HARD] **Grounded integrity (REQ-SD-003, REQ-SG-004, NFR-S-3):** spoken talking points are grounded
   facts validated by the unchanged PROGRAMMING-007 gate + forbidden-fact scan; design research stays
   internal; a FAIL never airs (B5).
7. [HARD] **Per-persona distinctness (REQ-SP-001/002/003, NFR-S-6):** shows are per-persona in their own
   taste/voice; no cross-persona angle reuse; the REQ-PR-004 firewall applies unchanged; the shared engine
   never homogenizes the roster (B6); the greenfield-roster mode degrades to a single default persona while
   preserving variation + grounding (B7).
8. [HARD] **Director decides when unhosted (REQ-SD-004):** the LLM director runs the show under the same
   rails; the scheduler ownership is referenced, not re-owned (B8).
9. [HARD] **Single-source-of-truth (NFR-S-4):** the PROGRAMMING-007 roster/taste/firewall/formats/gate,
   the ANALYSIS-006 consensus, the KNOWLEDGE-008 graph, the HOSTCTX-016 per-song facts, the MBMIRROR-017
   mirror, the OPS-004/ORCH-005 scheduler, and the CORE-001 picker are referenced by id, never re-owned;
   brain-only + additive (no new service/datastore).
10. [HARD] **Additive wiring, no fork (REQ-SB-001):** the engine attaches to the existing director + talk
    loops + config; with it disabled/empty the loops behave exactly as before this SPEC.
11. **Bounded/throttled (NFR-S-7, REQ-LF-005):** the research + planning jobs adopt the OPS-004 REQ-OH-006
    bounded-job pattern.
12. **Greenfield roster dependency handled (R-S-1, B7, D-S-1):** SHOWS-020 ships NOW against a single
    default persona until the PROGRAMMING-007 roster lands, preserving variation + grounding (DECIDED D-S-1).
13. [HARD] **Broadened use cases (REQ-LF-006, REQ-SG-005, REQ-SD-005, B10):** artist FACTS are
    KNOWLEDGE-008-grounded research leads never aired raw (DECIDED D-S-5); "last shows" is our durable
    per-persona show history and "planned shows" is our per-persona forward content queue — both OUR data,
    never from a (retired) Last.fm events API, and distinct from the OPS-004/ORCH-005 time-grid.
14. [HARD] **Last.fm ToS compliance (NFR-S-8):** caching required; under the 100 MB cap; non-commercial
    research-input-only; identifiable User-Agent; attribution + back-link if ever surfaced; ≤ 1 req/s with
    error-29/16 backoff; `partners@last.fm` flagged as a user prerequisite for monetization / verbatim
    surfacing.
15. **Decisions reflected (D-S-1…D-S-5):** ship-now single-persona (D-S-1), non-binding lens bias (D-S-2),
    separate `brain/lastfm.py` (D-S-3), deterministic text-similarity novelty for v1 (D-S-4), KNOWLEDGE-008
    single airable-fact home (D-S-5).

Quality gates (TRUST 5, inherited): Tested (the anti-repetition B1, the reject-storm B2, the no-key/
complementary B3, the bias-not-force B4, the grounded-content B5, the distinctness B6, and the
off-pull-path B9 are the must-pass characterization tests); Readable; Unified; Secured (key-gated +
exception-isolated research; no secret in code; the unchanged grounding gate keeps spoken facts honest);
Trackable (the show record + status lifecycle + the recent-shows ledger + per-item research provenance
give an auditable show/variation trail).

Parity check: 25 AC (Section A) + 8 AC-NFR = 33 acceptance entries, matching spec.md 25 REQ + 8 NFR;
1:1 REQ↔AC preserved.
