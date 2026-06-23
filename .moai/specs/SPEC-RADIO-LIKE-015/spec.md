---
id: SPEC-RADIO-LIKE-015
version: 0.1.0
status: draft
created: 2026-06-23
updated: 2026-06-23
author: charlie
priority: Medium
issue_number: null
---

# SPEC-RADIO-LIKE-015 — Listener Like (Heart) + Implicit Drop-off Negative Signal

## HISTORY

- 2026-06-23 (v0.1.0): Initial draft, occupying the global-incrementing LIKE-015 id. The
  fifteenth authored SPEC in the golden-shower-radio RADIO series and the LISTENER-AFFINITY
  subsystem of the autonomous AI radio station. It delivers the user's feature #3 from the
  2026-06-23 backlog ("Add a heart-icon on the website... An opposite icon would be good
  too, but the risk of abuse is too high") under the LOCKED design decision recorded that
  session: **LIKES-ONLY + IMPLICIT DROP-OFF — NO explicit dislike button.** The heart
  (like) is the ONLY explicit affinity button: rate-limited, cookie-deduped, and bound to a
  SIGNED TOKEN for the CURRENTLY-AIRING track. The negative signal is derived IMPLICITLY
  from listener DROP-OFF (many distinct sessions disconnecting shortly after a track
  starts) — organic, aggregate-only, nothing to abuse. Both the like and the drop-off feed
  the program director as SOFT WEIGHTS, NEVER hard rotation control. Where SPEC-RADIO-CORE-001
  owns the music engine, the program-director loop, the self-controlled website (Group E),
  the typed listener-signal contract (REQ-D-008), and the anti-appeal rail (REQ-OF-004);
  SPEC-RADIO-OPS-004 owns the program director + the bounded-job throttle (REQ-OH-006);
  SPEC-RADIO-ANALYSIS-006 owns the per-track feature substrate + the acquisition-provenance
  fields (Group AD); SPEC-RADIO-REQUEST-011 owns the listener SONG-REQUEST + acquisition-
  growth surface (the advisory-weight prior, the catalog matcher, the public growth viz,
  the internal curation dashboard); and the ENRICH-012 core-tag layer (`brain/enrich.py`)
  owns the CANONICAL RECORDING IDENTITY that de-duplicates a track across copies —
  LIKE-015 owns the LISTENER-AFFINITY surface: the explicit heart button + signed-token-
  bound like endpoint (Group LH), the implicit drop-off engine that polls Icecast listener
  stats and derives a negative signal from early disconnects (Group LD), the soft-signal
  integration that normalizes BOTH into the CORE-001 REQ-D-008 contract as non-binding
  curatorial context (Group LS), the like-endpoint anti-abuse / anti-gaming defense (Group
  LA), the privacy posture (Group LP), and the honest affinity surfaces + observability
  (Group LX). RADIO SPEC-IDs are GLOBAL-INCREMENTING (CORE-001, VOICE-002, CALLIN-003,
  OPS-004, ORCH-005, ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009,
  IMAGING-010, REQUEST-011, ENRICH-012 in progress, STATS-013 / DEDUP-014 planned,
  LIKE-015 = this). It uses a DISTINCT REQ namespace — LH (like heart), LD (implicit
  drop-off), LS (soft-signal integration), LA (anti-abuse / anti-gaming), LP (privacy), LX
  (surfaces & observability) — to avoid collision with CORE (A-E + D), VOICE (V-A…V-F),
  CALLIN (CT/CL/CD/CM/CC/CF/CS/CG), OPS (OA/OB/OC/OD/OE/OF/OG/OH/OX/OY), ORCH
  (RL/RW/RE/RC/RD/RA/RN/RI), ANALYSIS (AE/AT/AM/AD/AP), PROGRAMMING (PR/PC/PS/PT/PL/PG/PV/PI),
  REQUEST (RQ/RM/RA/RWL/RS/RV/RD), KNOWLEDGE (KS/KF/KR/KG/KI), TAGSTREAM (TW/TA/TX), and
  IMAGING (IG/IB/IP/IL/IS/IH/IX). Grounded in a code audit of the current brain: `brain/server.py`
  is stdlib `http.server.ThreadingHTTPServer` / `BaseHTTPRequestHandler` (NO web framework);
  `/api/airing` is the authoritative source of the currently-airing track (`state.set_on_air`);
  Icecast 2.4.0+ exposes a public `/status-json.xsl` listener-count endpoint (and a
  credentialed admin `/admin/stats` for per-mount detail) that the brain does NOT yet poll.
  Total: 21 REQ + 7 NFR = 28, 1:1 REQ↔AC (LH=4, LD=4, LS=4, LA=3, LP=3, LX=3).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "let listeners say they love a track, sense when they flee one, and never give either a lever to game"

The station plays continuously (CORE-001), talks in distinct personas (VOICE-002,
PROGRAMMING-007), programs and presents itself (OPS-004), orchestrates as one operator
(ORCH-005), hears/knows/tags/images its music (ANALYSIS-006, KNOWLEDGE-008, TAGSTREAM-009,
IMAGING-010), takes requests honestly (REQUEST-011), and corrects its core tags
(ENRICH-012). What it cannot yet do is let a listener express AFFINITY for the track on air
right now — a simple "I love this" — and sense, organically, when listeners are turning a
track OFF.

The user asked for a heart icon and wondered aloud about a dislike icon, then ruled the
dislike OUT: "An opposite icon would be good too, but the risk of abuse is too high i
think." The LOCKED answer (2026-06-23 session) is the design this SPEC encodes:

1. **A heart (like) is the ONLY explicit button.** A listener clicks the heart for the
   track on air; it is rate-limited, cookie-deduped, and bound to a SIGNED TOKEN for the
   currently-airing track so a like can only be cast for what is genuinely playing.
2. **The negative signal is IMPLICIT, never a button.** Instead of an abusable dislike
   button, the station infers dissatisfaction from listener DROP-OFF: when many DISTINCT
   sessions disconnect shortly after a track starts, that is an organic negative signal.
   There is nothing to brigade because there is no negative button — the signal is the
   aggregate behaviour of real listeners voting with their players.
3. **Both are SOFT weights, never hard control.** A like and a drop-off are non-binding
   curatorial CONTEXT fed to the director, exactly like the CORE-001 REQ-D-008 listener
   signals. Neither force-plays, force-skips, force-rotates, force-acquires, or force-drops
   a track. The director weighs them with full autonomy and MAY ignore them.

### 1.2 The anti-gaming / anti-pandering spine (the load-bearing idea, inherited from REQUEST-011)

[HARD] LIKE-015 inherits REQUEST-011's load-bearing invariant verbatim and applies it to
affinity: **a like count and a drop-off rate are noisy, identity-deduped, time-decayed weak
PRIORS among editorial signals — NEVER a satisfaction target, never a hard airplay/rotation
driver.** This one rule, plus the deliberate ABSENCE of an explicit dislike button, defeats
the failure modes at once:

- It defeats **like-flooding / brigading**: if likes never BIND to rotation (the director
  always retains discretion, the prior is capped + decayed + deduped per identity, and each
  like must carry a signed token for the genuinely-airing track), then flooding the heart
  buys a flooder nothing. There is no exploitable rotation lever to flood.
- It defeats **dislike-brigading by construction**: there is NO dislike button to brigade.
  The only negative signal is aggregate drop-off, which a single bad actor cannot fake
  without commanding many distinct real listener sessions (LP/LA rails).
- It defeats **pandering**: the same non-binding framing means the station never chases
  likes or avoids drop-off to maximize appeal. Affinity is curatorial CONTEXT, governed by
  the CORE-001 REQ-OF-004 anti-appeal rail.

### 1.3 What this layer is, concretely

- An EXPLICIT LIKE (HEART) on the website (Group LH): a heart control rendered on the
  CORE-001 self-controlled site for the track on air. Clicking it POSTs a like carrying a
  SIGNED TOKEN minted by the brain for the currently-airing track (from `/api/airing` /
  `state.set_on_air`); the brain verifies the token, dedups the click per cookie/identity,
  rate-limits it, and records ONE like against the track's CANONICAL RECORDING (ENRICH-012),
  not the raw file.
- AN IMPLICIT DROP-OFF ENGINE (Group LD): a bounded background poller that samples Icecast
  listener counts per mount (the public `/status-json.xsl`, or the credentialed admin
  endpoint where provisioned), correlates the sampled count against the
  track-start/track-change timeline the brain already knows from `/api/airing`, and derives
  a per-track DROP-OFF signal — a measure of how many DISTINCT listeners left shortly after
  a track started, relative to the audience present at its start. It is AGGREGATE-ONLY: it
  never tracks an individual listener, only the count delta around a track boundary.
- A SOFT-SIGNAL INTEGRATION (Group LS): both the like tally and the drop-off measure
  NORMALIZE into the CORE-001 REQ-D-008 typed listener-signal contract — one human-curatorial
  signal among many — keyed by ENRICH-012 canonical recording, decayed/capped, and exposed to
  the director as a SOFT weight it MAY consider. [HARD] Neither becomes hard rotation control:
  no code path skips, force-plays, force-drops, or auto-acquires a track because of a like or
  a drop-off.
- A LIKE-ENDPOINT ANTI-ABUSE / ANTI-GAMING DEFENSE (Group LA): the signed-token requirement
  (HMAC, short-lived, bound to the airing track + issue time), per-cookie + per-IP dedup,
  rate-limit + cooldown, and the like-never-binds invariant — the structural defeat of
  like-flooding.
- A PRIVACY POSTURE (Group LP): the like identity is a hashed, privacy-preserving cookie id
  (never an account, never raw PII); the drop-off signal is computed from AGGREGATE listener
  counts only and never from per-listener session surveillance; no raw IP or handle is
  stored.
- HONEST AFFINITY SURFACES + OBSERVABILITY (Group LX): an honest, non-gameable way to reflect
  affinity (NO public "most-liked" leaderboard — the same anti-gaming exclusion REQUEST-011
  makes for "top requests"); the full per-track affinity reasoning kept INTERNAL (a redacted
  projection into the REQUEST-011 internal dashboard, one store / two views); and observability
  of the like/drop-off pipeline through the existing health/status surface.

### 1.4 What this SPEC OWNS vs. REFERENCES (boundary discipline)

[HARD] LIKE-015 OWNS the listener-affinity surface: the explicit heart button + signed-token
like endpoint, the implicit drop-off engine, the soft-signal normalization into REQ-D-008,
the like-endpoint anti-abuse, the privacy posture, and the honest affinity surfaces. It MUST
NOT restate, fork, or weaken any CORE-001, VOICE-002, CALLIN-003, OPS-004, ORCH-005,
ANALYSIS-006, PROGRAMMING-007, KNOWLEDGE-008, TAGSTREAM-009, IMAGING-010, or REQUEST-011
requirement, and it MUST NOT re-own the listener-signal contract, the website rendering host,
the program-director loop, the canonical-recording identity, the moderation floor, the
bounded-job throttle, or the internal curation dashboard — it CONSUMES them.

OWNS:
- The EXPLICIT LIKE (HEART): the heart control on the site, the signed per-track like token,
  the like endpoint, the per-cookie/identity dedup + rate-limit, and the like-records-against-
  canonical-recording rule (Group LH).
- The IMPLICIT DROP-OFF ENGINE: the Icecast-stats poller, the per-track listener-count
  sampling, the drop-off derivation (distinct sessions leaving shortly after a track starts,
  relative to the start audience), the aggregate-only discipline, and the tunable thresholds
  (Group LD).
- The SOFT-SIGNAL INTEGRATION: the normalization of both signals into REQ-D-008 as
  non-binding context, keyed by ENRICH-012 canonical recording, decayed + capped, and the
  [HARD] never-hard-control invariant (Group LS).
- The LIKE-ENDPOINT ANTI-ABUSE: the signed-token verification, the per-cookie/per-IP dedup +
  rate-limit + cooldown, and the like-never-binds-to-rotation invariant (Group LA).
- The PRIVACY POSTURE: the hashed cookie identity, the aggregate-only drop-off, and the
  no-raw-PII rule (Group LP).
- The HONEST AFFINITY SURFACES + OBSERVABILITY: the no-public-leaderboard exclusion, the
  internal-only full reasoning (redacted-projection into the REQUEST-011 RD dashboard), and
  the pipeline observability (Group LX).

REFERENCES (consumes / extends; does not restate):
- **CORE-001 REQ-D-008 (the typed listener-signal contract) + REQ-OF-004 (anti-appeal) + the
  curation ethos** — both the like signal and the drop-off signal NORMALIZE INTO REQ-D-008 and
  are treated as human-curatorial CONTEXT, never an appeal-optimization target; LIKE-015
  ingests into the contract, does NOT re-own it or weaken the no-pandering rail.
- **CORE-001 Group E (the self-controlled website) + `brain/server.py` (stdlib
  `http.server.ThreadingHTTPServer` / `BaseHTTPRequestHandler` — NO web framework) +
  `/api/airing` / `state.set_on_air` (the currently-airing track of truth) + `/api/nowplaying`** —
  the heart control renders on the existing site; the like-token mint, the like POST endpoint,
  and the drop-off observability attach as new `BaseHTTPRequestHandler` route branches; the
  signed token binds to the track `/api/airing` reports as on air. No new web service, no web
  framework dependency.
- **ENRICH-012 (`brain/enrich.py`, the canonical-recording core-tag layer)** — likes and
  drop-off are recorded against the CANONICAL RECORDING identity ENRICH-012 establishes, so
  affinity for a track is not split across duplicate copies (live/remaster/different file).
  LIKE-015 reads the canonical identity, does NOT re-own ENRICH-012 or its dedup logic.
  [Cross-cutting: ENRICH-012 is the metadata SPINE; LIKE-015 keys on it.]
- **OPS-004 REQ-OH-006 (the bounded-job throttle)** — the drop-off poller + the like-ingest
  work adopt the bounded/throttled pattern so affinity work does not overload the modest box
  alongside playout, acquisition, and analysis; referenced, not re-owned.
- **REQUEST-011 Group RD (the internal curation dashboard) + REQ-RD-003 (one store, two view
  layers) + Group RA (the advisory-weight prior) + REQ-RA-005 / NFR-R-2 (the anti-gaming /
  anti-pandering invariant)** — LIKE-015's affinity signals are a DISTINCT signal type that
  shares REQUEST-011's anti-gaming invariant and surfaces its full internal reasoning as a
  redacted projection into the SAME internal dashboard; LIKE-015 references the invariant +
  the dashboard, does NOT re-own them or duplicate the advisory-weight prior.
- **OPS-004 program director + ORCH-005 director loop** — the consumers that MAY weigh the
  soft affinity signal; LIKE-015 supplies the signal as REQ-D-008 context, the director owns
  the decision. Neither redefines the other.

### 1.5 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 Section 1.3 and the sibling SPECs' autonomy principle in intent
and does NOT redefine it. The director decides, with full creative freedom, WHETHER and HOW a
like or a drop-off shapes what plays next — sometimes leaning toward a loved track, sometimes
quietly resting a track listeners flee, sometimes ignoring both because the clock, the show,
or the persona's taste says otherwise. What is NOT the AI's call, and what this SPEC fixes as
hard rails, is the never-hard-control invariant, the like-must-carry-a-signed-token rule, the
no-explicit-dislike-button decision, the aggregate-only drop-off rule, the no-public-leaderboard
rule, and the anti-gaming/anti-pandering invariant. The thresholds (decay rate, cap, dedup
window, rate-limit, drop-off window + minimum-audience floor) are TUNABLE config; the
requirement guarantees only that affinity is handled honestly and never becomes a hard lever
or an appeal target.

### 1.6 Fixed engineering rails (the only hard constraints)

- **Likes-only; NO explicit dislike button.** [HARD] The heart is the only explicit affinity
  control. The negative signal is derived implicitly from drop-off (Group LD). No dislike /
  thumbs-down / downvote button is built (the user-ruled abuse vector). (Section 11 exclusion;
  REQ-LH-001, REQ-LD-001.)
- **Every like carries a signed token for the genuinely-airing track.** [HARD] A like POST is
  accepted only with a valid, short-lived, brain-minted signed token bound to the track
  `/api/airing` reported on air at mint time; a like for a track not actually airing (or with a
  forged/expired token) is rejected (REQ-LH-002, REQ-LA-001).
- **Both signals are SOFT weights; never hard rotation control.** [HARD] A like or a drop-off
  is a non-binding bias the director MAY weigh; no code path force-plays, force-skips,
  force-drops, force-rotates, or auto-acquires a track because of a like or a drop-off
  (REQ-LS-002, NFR-L-2).
- **Counts never bind; never an appeal target.** [HARD] The anti-gaming / anti-pandering
  invariant (Section 1.2): a like count and a drop-off rate are noisy, identity-deduped,
  time-decayed weak priors, never a satisfaction target, never a hard airplay driver
  (REQ-LS-003, REQ-LA-003, NFR-L-2). Inherits REQUEST-011 REQ-RA-005 / CORE-001 REQ-OF-004.
- **Drop-off is aggregate-only; never per-listener surveillance.** [HARD] The drop-off signal
  is derived from aggregate Icecast listener COUNTS around a track boundary; the system never
  tracks, profiles, or stores an individual listener's session history (REQ-LD-002, REQ-LP-002,
  NFR-L-7).
- **Affinity is keyed on the ENRICH-012 canonical recording.** [HARD] A like and a drop-off
  attach to the canonical recording identity, so affinity is not split across duplicate copies
  (REQ-LS-001).
- **One backend, ingest into REQ-D-008; never a parallel queue.** [HARD] Both signals
  normalize into the CORE-001 REQ-D-008 listener-signal contract; LIKE-015 does not stand up a
  second listener-signal store (REQ-LS-001, NFR-L-4).
- **No public affinity leaderboard.** [HARD] No public "most-liked / most-hated" ranking is
  rendered (the exact appeal target + brigading lever the anti-gaming invariant forbids); the
  full per-track affinity reasoning is internal-only (REQ-LX-001, REQ-LX-002).
- **Privacy: hashed cookie identity, no account, no raw PII.** [HARD] The like identity is a
  hashed cookie/session id; no user account, no raw IP/handle is stored (REQ-LP-001, NFR-L-7).
- **Brain-only; additive website + store.** [HARD] LIKE-015 adds a like endpoint + a
  signed-token minter + a drop-off poller + a soft-signal normalizer to the existing `brain/`
  package and renders the heart on the existing CORE-001 website; the like tally / drop-off
  records live in the existing store seam. No new service, no new datastore, no web framework
  (NFR-L-4).
- **Resilience: never crash, never silence.** [HARD] A like-endpoint error, a token-verify
  failure, an Icecast-stats-poll failure, a normalizer error, or a surface-render error logs
  and degrades gracefully; it never crashes the daemon, the picker, or the director loop, and
  never silences the stream (NFR-L-5).

---

## 2. Dependencies

This SPEC DEPENDS ON SPEC-RADIO-CORE-001, SPEC-RADIO-OPS-004, SPEC-RADIO-ANALYSIS-006,
SPEC-RADIO-REQUEST-011, and the ENRICH-012 core-tag layer, and is the listener-affinity
subsystem layered on top of them. It references their subsystems by CONCEPT (and, where a
cited requirement is a deliberately stable invariant or seam, by number) rather than
re-specifying them.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any sibling SPEC requirement. Where it
needs a predecessor behavior it consumes it. Where a LIKE decision could conflict with
continuous operation or the no-pandering rail, the inherited behavior WINS — the music keeps
playing and affinity signals never bind to rotation.

Consumed CORE-001 concepts (by number, deliberately):
- **REQ-D-008** — the typed LISTENER-SIGNAL contract. Both the like tally and the drop-off
  measure NORMALIZE INTO this contract; LIKE-015 ingests into it, does not re-own it (Group LS).
- **REQ-OF-004 + the curation ethos** — the anti-appeal / no-pandering rail both signals
  inherit verbatim (REQ-LS-003, NFR-L-2).
- **Group E (self-controlled website) + `brain/server.py`** — the site the heart renders on,
  and the stdlib `http.server.ThreadingHTTPServer` / `BaseHTTPRequestHandler` the like-token
  mint route + the like POST endpoint + the observability route attach to as new handler
  branches; extended additively, no new service, no web framework dependency.
- **`/api/airing` / `state.set_on_air` + `/api/nowplaying`** — the authoritative
  currently-airing track the like token binds to and the track-change timeline the drop-off
  engine correlates against. Consumed, not re-owned.

Consumed ENRICH-012 concept:
- **`brain/enrich.py` canonical-recording identity** — the de-duplicating recording identity a
  like and a drop-off attach to, so affinity is not fragmented across duplicate files. ENRICH-012
  is the metadata SPINE (cross-cutting); LIKE-015 keys on it (REQ-LS-001).

Consumed OPS-004 concepts (by number, deliberately):
- **REQ-OH-006** — the bounded-job throttle the drop-off poller + the like-ingest work adopt
  (REQ-LD-004, NFR-L-6).
- **The program director** — a consumer that MAY weigh the soft affinity signal as REQ-D-008
  context.

Consumed REQUEST-011 concepts (by number where stable):
- **REQ-RA-005 + NFR-R-2 (the anti-gaming / anti-pandering invariant)** — the load-bearing
  invariant LIKE-015 inherits and applies to affinity (REQ-LS-003, REQ-LA-003, NFR-L-2).
- **Group RD (the internal curation dashboard) + REQ-RD-003 (one store, two view layers)** —
  the full per-track affinity reasoning surfaces as a redacted projection into the SAME internal
  dashboard; LIKE-015 references the dashboard + the one-store rule, does not re-own them
  (REQ-LX-002).
- **Group RA (the advisory-weight prior)** — a DISTINCT prior (a song-request bias) from
  LIKE-015's affinity signal; both are non-binding weak priors the director weighs. [HARD]
  LIKE-015 does NOT duplicate or merge into the REQUEST-011 advisory weight; it contributes its
  own affinity signal type to the same REQ-D-008 contract (REQ-LS-002).

Consumed ANALYSIS-006 / ORCH-005 concepts:
- **ANALYSIS-006 per-track feature substrate** — context the director may combine with affinity
  when reasoning; read, not re-owned.
- **ORCH-005 director loop** — a consumer that MAY weigh the soft affinity signal; the signal is
  supplied as REQ-D-008 context, the director owns the decision.

### bhive memory seam

bhive memory (AGENTS.md protocol) has no proven pattern for the heart-as-signed-token-bound-like
+ implicit-drop-off-from-Icecast-listener-stats soft-signal pattern on this Python+Liquidsoap+
Icecast stack (recorded gap). Re-run a bhive query on the HMAC-signed per-track like token +
cookie-dedup, and on deriving an early-disconnect drop-off rate from sampled
Icecast `/status-json.xsl` listener counts, during implementation, and contribute the verified
approach back per the AGENTS.md memory protocol.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Like (heart)** | A listener's explicit "I love this" for the track on air, cast by clicking the heart on the website. The ONLY explicit affinity control; rate-limited, cookie-deduped, and bound to a signed per-track token (Group LH). |
| **Like token** | A short-lived, brain-minted SIGNED token (HMAC over the currently-airing track identity + issue time + a nonce) the heart click must carry. It binds a like to the track genuinely on air at mint time, so a like cannot be cast for a track that is not playing or replayed/forged later (REQ-LH-002, REQ-LA-001). |
| **Currently-airing track** | The track `/api/airing` reports as on air RIGHT NOW (`state.set_on_air`), the authoritative target a like token binds to and the boundary the drop-off engine correlates against. |
| **Canonical recording** | The de-duplicating recording identity established by ENRICH-012 (`brain/enrich.py`). A like and a drop-off attach to it, so affinity is not split across duplicate copies of the same recording (REQ-LS-001). |
| **Implicit drop-off** | The NEGATIVE signal derived WITHOUT a button: a measure of how many DISTINCT listeners disconnected shortly after a track started, relative to the audience present at its start. Computed from aggregate Icecast listener counts, never from individual session tracking (Group LD). |
| **Drop-off window** | The configured short interval after a track starts within which a disconnect is counted toward that track's drop-off (e.g. the first N seconds). A disconnect inside the window is the organic "they turned it off" signal (REQ-LD-001). |
| **Minimum-audience floor** | A configured minimum listener count present at track start below which the drop-off measure is suppressed (too few listeners to be a meaningful aggregate signal — protects against noise + protects privacy) (REQ-LD-003, REQ-LP-002). |
| **Icecast stats poll** | The bounded background sampling of Icecast listener counts per mount via the public `/status-json.xsl` (or the credentialed `/admin/stats` where provisioned), the raw input the drop-off engine derives from (REQ-LD-002). |
| **Soft weight** | A non-binding bias an affinity signal contributes to the director's reasoning. It is decayed, capped, and deduped; the director MAY weigh it and MAY ignore it. It NEVER becomes hard rotation control (REQ-LS-002). |
| **Hard control** | A forbidden outcome: any code path that force-plays, force-skips, force-drops, force-rotates, or auto-acquires a track as a deterministic function of likes or drop-off. [HARD] NOT built (REQ-LS-002, NFR-L-2). |
| **Anti-gaming / anti-pandering invariant** | The inherited REQUEST-011 REQ-RA-005 / CORE-001 REQ-OF-004 rule applied to affinity: a like count and a drop-off rate are a noisy, identity-deduped, time-decayed weak prior, never a satisfaction target or a hard airplay driver (REQ-LS-003, NFR-L-2). |
| **Hashed cookie identity** | The privacy-preserving per-cookie/per-session hash used to dedup likes and rate-limit, never a user account, never raw PII (REQ-LP-001, NFR-L-7). |
| **No-leaderboard rule** | The deliberate exclusion of any public "most-liked / most-hated" ranking — it would create the exact appeal target + brigading lever the anti-gaming invariant forbids (REQ-LX-001). |
| **Redacted projection (into RD)** | The full per-track affinity reasoning is internal-only, surfaced as a redacted projection into the REQUEST-011 Group RD internal dashboard over the same store (REQUEST-011 REQ-RD-003); the public surface shows no raw affinity counts (REQ-LX-002). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group LH — Explicit Like (Heart).** The heart control on the CORE-001 website; the
  signed per-track like-token mint; the like POST endpoint with token verification, per-cookie/
  identity dedup, and rate-limit; the like-records-against-canonical-recording rule; the
  honest opt-in framing.
- **Group LD — Implicit Drop-off.** The bounded Icecast-stats poller (public `/status-json.xsl`
  or credentialed admin endpoint); per-track listener-count sampling correlated against the
  `/api/airing` track timeline; the drop-off derivation (distinct sessions leaving inside the
  drop-off window, relative to the start audience); the minimum-audience floor; the tunable
  thresholds; the throttle.
- **Group LS — Soft-signal Integration.** The normalization of both the like tally and the
  drop-off measure into the CORE-001 REQ-D-008 contract as non-binding context, keyed by the
  ENRICH-012 canonical recording, decayed + capped; the [HARD] never-hard-control invariant;
  the distinct-from-REQUEST-011-advisory-weight rule; the inherited anti-gaming/anti-pandering
  invariant.
- **Group LA — Anti-abuse / Anti-gaming.** The signed-token verification (HMAC, short-lived,
  bound to the airing track + issue time + nonce); the per-cookie/per-IP dedup + rate-limit +
  cooldown; the like-never-binds invariant; the structural defeat of like-flooding.
- **Group LP — Privacy.** The hashed cookie/session identity (no account, no raw PII); the
  aggregate-only drop-off (no per-listener surveillance); the no-raw-PII-in-stores-or-surfaces
  rule.
- **Group LX — Surfaces & Observability.** The no-public-affinity-leaderboard exclusion; the
  honest internal full-reasoning view as a redacted projection into the REQUEST-011 RD
  dashboard (one store, two views); the observability of the like/drop-off pipeline through the
  existing health/status surface.
- Plus **NFRs** (Section 6) and **Risks** (Section 7).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **An explicit DISLIKE / thumbs-down / downvote button** — deliberately EXCLUDED per the
  user-locked decision (abuse vector). The negative signal is implicit drop-off only (Section
  1.6; REQ-LH-001, REQ-LD-001).
- **A public affinity leaderboard / "most-liked" or "most-hated" ranking / vote tally** — a
  public ranking would create the appeal target + brigading lever the anti-gaming invariant
  forbids (REQ-LX-001). Not built.
- **Any HARD rotation control from affinity** — force-play, force-skip, force-drop,
  auto-acquire, or a deterministic rotation function of likes/drop-off; affinity is a soft,
  non-binding bias only (REQ-LS-002, NFR-L-2).
- **Per-listener session tracking / profiling / individual disconnect history** — the drop-off
  is aggregate-count-only; no individual listener is tracked (REQ-LD-002, REQ-LP-002, NFR-L-7).
- **The typed listener-signal CONTRACT (REQ-D-008) + the no-pandering POLICY** — owned by
  CORE-001; LIKE-015 normalizes into the contract and inherits the policy, never re-owns either.
- **The canonical-recording identity + dedup** — owned by ENRICH-012 (`brain/enrich.py`);
  LIKE-015 keys affinity on it, never re-owns it.
- **The website RENDERING host + the runtime self-generation of the site** — owned by CORE-001
  Group E; LIKE-015 adds a heart control + observability route to the existing site, never
  re-owns the rendering pipeline.
- **The next-track PICKER / the program-director DECISION / the playout chain** — owned by
  CORE-001 / OPS-004 / ORCH-005; affinity is a bias INPUT (REQ-D-008 context) to the director,
  never a re-owned picker or a synchronous playout insertion.
- **The internal curation dashboard + the bounded-job throttle + the advisory-weight prior** —
  owned by REQUEST-011 (Group RD / Group RA) and OPS-004 (REQ-OH-006); LIKE-015 projects its
  reasoning into the dashboard, adopts the throttle, and contributes a DISTINCT signal type,
  never re-owns them.
- **Account-based / authenticated listener identity** — out of scope for v1; identity is a
  hashed, privacy-preserving cookie/session id, never a user account (REQ-LP-001, R-L-4).
- **Outbound notification to the listener** ("the host noticed you loved this") — out of scope
  for v1; affinity is internal context + the host's autonomous on-air behaviour, not a
  per-listener push (Section 8 roadmap).
- **A new datastore or a new web service** — brain-only + additive; the like tally / drop-off
  records live in the existing store seam; the heart + observability render on the existing
  CORE-001 website (NFR-L-4).

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Likes-only; NO explicit dislike button.** The heart is the only explicit affinity
  control; the negative signal is implicit drop-off (the user-locked decision).
- [HARD] **Brain-only core + additive website/store.** LIKE-015 adds a like endpoint + a
  signed-token minter + a drop-off poller + a soft-signal normalizer to the existing `brain/`
  package and renders the heart on the existing CORE-001 website; affinity records live in the
  existing store seam. No new service, no new datastore, no web framework.
- [HARD] **Every like carries a signed token for the genuinely-airing track.** A like is
  accepted only with a valid, short-lived, brain-minted signed token bound to the track on air
  at mint time.
- [HARD] **Both signals are SOFT weights; never hard rotation control.** No code path force-plays,
  force-skips, force-drops, force-rotates, or auto-acquires a track because of a like or a
  drop-off.
- [HARD] **Counts never bind to airplay; never an appeal target.** A like count and a drop-off
  rate are a noisy, identity-deduped, time-decayed weak prior among editorial signals — never a
  satisfaction target, never a hard airplay driver (inherits REQUEST-011 REQ-RA-005 / CORE-001
  REQ-OF-004).
- [HARD] **Drop-off is aggregate-only; never per-listener surveillance.** Derived from aggregate
  Icecast listener counts around a track boundary; no individual listener is tracked.
- [HARD] **Affinity is keyed on the ENRICH-012 canonical recording.** A like and a drop-off
  attach to the canonical recording identity, not the raw file.
- [HARD] **Ingest into REQ-D-008; never a parallel queue.** Both signals normalize into the
  CORE-001 REQ-D-008 listener-signal contract; no second listener-signal store.
- [HARD] **No public affinity leaderboard.** No public "most-liked / most-hated" ranking; full
  reasoning is internal-only.
- [HARD] **Privacy: hashed cookie identity, no account, no raw PII.**
- [HARD] **One store, redacted into RD.** The full per-track affinity reasoning surfaces as a
  redacted projection into the REQUEST-011 Group RD internal dashboard over the same store
  (REQUEST-011 REQ-RD-003).
- [HARD] **Reuse, don't re-own.** The listener-signal contract (CORE-001 REQ-D-008), the
  canonical recording (ENRICH-012), the bounded-job throttle (OPS-004 REQ-OH-006), the internal
  dashboard + the anti-gaming invariant (REQUEST-011 Group RD / REQ-RA-005), and the website
  rendering host (CORE-001 Group E) are referenced, never restated.
- [HARD] **No pandering.** Affinity signals are human-curatorial input, never an
  appeal-optimization target (CORE-001 REQ-OF-004).
- [HARD] **Resilience.** A like-endpoint error, a token-verify failure, an Icecast-poll failure,
  a normalizer error, or a surface-render error logs and degrades gracefully; it never crashes
  the daemon and never silences the stream.

---

## 6. Requirement Group LH — Explicit Like (Heart)

Priority: High.

### REQ-LH-001 — A heart (like) is the only explicit affinity control; no dislike button (Ubiquitous) [HARD]

The system SHALL render a HEART (LIKE) control on the CORE-001 self-controlled website for the
track currently on air, and SHALL NOT render any explicit DISLIKE / thumbs-down / downvote /
negative control. [HARD] The heart is the SOLE explicit affinity input; the negative signal is
derived implicitly from drop-off (Group LD), never from a button. The heart is opt-in and
anonymous (no account required); clicking it expresses "I love this track". The control's exact
placement / styling is config/brand-voice; that the only explicit affinity control is a like
(never a dislike) is the rail.

**Acceptance criteria:** see acceptance.md AC-LH-001.

### REQ-LH-002 — A like POST carries a signed token bound to the currently-airing track (Event-driven) [HARD]

When the website serves the heart for the track on air, the system SHALL mint a short-lived
SIGNED LIKE TOKEN bound to the CURRENTLY-AIRING track (the track `/api/airing` /
`state.set_on_air` reports on air), and when a listener clicks the heart, the like POST SHALL
carry that token; the brain SHALL VERIFY the token (signature valid, not expired, bound to a
track that was genuinely on air at mint time) before recording the like. [HARD] A like with a
missing, forged, expired, or wrong-track token is REJECTED and never recorded. The token
scheme (HMAC, TTL, nonce) is owned by Group LA; this requirement fixes that a like is bound to
the genuinely-airing track via a verified signed token. The token TTL is config; that a like
must carry a valid signed token for the genuinely-airing track is the rail.

**Acceptance criteria:** see acceptance.md AC-LH-002.

### REQ-LH-003 — A like is per-cookie/identity deduped and rate-limited (Ubiquitous) [HARD]

The system SHALL record at most ONE like per track per hashed cookie/identity (per-identity
dedup within a window), and SHALL RATE-LIMIT like submissions per cookie + per IP with a
cooldown, so a single listener cannot inflate a track's like tally by re-clicking. [HARD] A
second like for the same track from the same identity within the dedup window is a no-op (not
an increment); like submissions exceeding the rate-limit are rejected. The dedup window / rate
/ cooldown are TUNABLE config; that a like is per-identity-deduped and rate-limited is the rail.

**Acceptance criteria:** see acceptance.md AC-LH-003.

### REQ-LH-004 — A like is recorded against the ENRICH-012 canonical recording, not the raw file (Event-driven) [HARD]

When a verified like is recorded, the system SHALL attach it to the CANONICAL RECORDING
identity established by ENRICH-012 (`brain/enrich.py`), not to the raw file path, so that
affinity for a recording is NOT fragmented across duplicate copies (live/remaster/different
file) of the same recording. [HARD] LIKE-015 reads the canonical identity from ENRICH-012; it
does NOT re-own or fork the canonical-recording dedup logic. Where the canonical identity is
not yet available for a track (ENRICH-012 pending), the like degrades to keying on the existing
`Track.key` dedup slug and reattaches to the canonical recording once available. That a like
keys on the canonical recording is the rail.

**Acceptance criteria:** see acceptance.md AC-LH-004.

---

## 7. Requirement Group LD — Implicit Drop-off

Priority: High.

### REQ-LD-001 — Derive a negative signal from listener drop-off, not from a button (Event-driven) [HARD]

When a track is on air, the system SHALL derive an IMPLICIT DROP-OFF signal — a measure of how
many DISTINCT listeners disconnected shortly after the track STARTED (within a configured
DROP-OFF WINDOW), relative to the audience present at the track's start — as the station's
NEGATIVE affinity signal, in place of an explicit dislike button. [HARD] This is the organic
"listeners turned it off" signal: it requires real listeners voting with their players and
exposes no button to brigade. The drop-off measure is computed per track-airing and attached to
the track's canonical recording (REQ-LS-001). The drop-off window length is config; that the
negative signal is derived from early-disconnect drop-off (not a button) is the rail.

**Acceptance criteria:** see acceptance.md AC-LD-001.

### REQ-LD-002 — Bounded Icecast-stats poll; aggregate listener counts only (State-driven) [HARD]

While running, the system SHALL sample Icecast LISTENER COUNTS per mount on a bounded interval —
reading the public `/status-json.xsl` (or the credentialed admin `/admin/stats` where the user
has provisioned the credential) — and SHALL correlate the sampled counts against the
`/api/airing` track-change timeline to compute per-track drop-off (REQ-LD-001). [HARD] The poll
reads AGGREGATE listener COUNTS only; the system SHALL NOT track, profile, or store an
individual listener's session, IP, or disconnect history (REQ-LP-002, NFR-L-7). The poll is
bounded/throttled (REQ-LD-004) so it does not hammer Icecast or the box. The poll interval +
the stats source are config; that drop-off is computed from aggregate listener counts (never
per-listener surveillance) is the rail.

**Acceptance criteria:** see acceptance.md AC-LD-002.

### REQ-LD-003 — Minimum-audience floor + tunable thresholds suppress noise (State-driven) [HARD]

While computing drop-off, the system SHALL apply a MINIMUM-AUDIENCE FLOOR — when fewer than a
configured number of listeners were present at the track's start, the drop-off measure for that
airing is SUPPRESSED (recorded as not-meaningful rather than as a strong negative) — so a
handful of listeners or normal churn is not read as dissatisfaction. [HARD] The drop-off
threshold (what fraction/count of distinct disconnects inside the window counts as a meaningful
negative), the window length, and the minimum-audience floor are TUNABLE config; the signal is
best-effort and noisy by nature (network churn, player reconnects, schedule changes all add
noise) and SHALL carry a confidence/quality marker so the consumer can weigh it accordingly.
That a minimum-audience floor + tunable thresholds + a confidence marker temper the drop-off
signal is the rail.

**Acceptance criteria:** see acceptance.md AC-LD-003.

### REQ-LD-004 — The drop-off poll adopts the OPS-004 bounded-job throttle; never blocks playout (State-driven) [HARD]

While polling Icecast and computing drop-off, the system SHALL run the work as a BOUNDED,
THROTTLED background job adopting the OPS-004 REQ-OH-006 bounded-job pattern, fully decoupled
from the playout path and the sub-1s `/api/next` pull. [HARD] An Icecast unreachable, a slow
poll, or a stats-parse error SHALL log and be skipped without blocking, stalling, or silencing
the stream — a missing drop-off sample is an expected operating state, not a defect (NFR-L-5).
LIKE-015 ADOPTS the OPS-004 throttle by reference; it does NOT re-own it. The poll
interval/bound is config; that the poll is bounded/throttled and never blocks playout is the
rail.

**Acceptance criteria:** see acceptance.md AC-LD-004.

---

## 8. Requirement Group LS — Soft-signal Integration

Priority: High.

### REQ-LS-001 — Both signals normalize into the CORE-001 REQ-D-008 contract, keyed on the canonical recording (Ubiquitous) [HARD]

The system SHALL NORMALIZE both the like tally and the drop-off measure into the CORE-001
REQ-D-008 typed listener-signal contract — keyed by the ENRICH-012 CANONICAL RECORDING identity
(REQ-LH-004) — as one human-curatorial signal type among many, and SHALL NOT stand up a separate
or parallel listener-signal store. [HARD] LIKE-015 INGESTS INTO the existing REQ-D-008 contract;
it does NOT re-own, fork, or weaken the contract. The per-signal field mapping (like count,
drop-off rate, confidence, canonical recording key, timestamp) is implementation detail; that
both affinity signals normalize into the existing REQ-D-008 contract keyed on the canonical
recording is the rail.

**Acceptance criteria:** see acceptance.md AC-LS-001.

### REQ-LS-002 — Affinity is a SOFT weight to the director; NEVER hard rotation control (Ubiquitous) [HARD]

The system SHALL expose the like and drop-off signals to the program director / director loop
(OPS-004 / ORCH-005) as a SOFT, decaying, capped WEIGHT it MAY weigh among many signals — and
SHALL NOT make either signal HARD rotation control. [HARD] No code path shall force-play,
force-skip, force-drop, force-rotate, or auto-acquire a track as a deterministic function of its
like count or drop-off rate; the director retains full autonomy to lean toward a loved track,
rest a fled one, or ignore both. [HARD] This affinity signal is DISTINCT from the REQUEST-011
Group RA advisory-weight prior (a song-request bias): LIKE-015 contributes its own affinity
signal type to the same REQ-D-008 contract and does NOT duplicate or merge into the advisory
weight. The bias magnitude / decay / cap are config; that affinity is a soft non-binding weight,
never hard control, is the rail.

**Acceptance criteria:** see acceptance.md AC-LS-002.

### REQ-LS-003 — Anti-gaming / anti-pandering invariant inherited: counts never bind, never an appeal target (Ubiquitous) [HARD] [consistency]

The system SHALL treat like counts and drop-off rates as a NOISY, IDENTITY-DEDUPED,
TIME-DECAYED WEAK PRIOR among editorial signals — and SHALL NOT make them a satisfaction /
appeal-optimization TARGET, nor a hard airplay driver. [HARD] [consistency] This is the
REQUEST-011 REQ-RA-005 / CORE-001 REQ-OF-004 anti-appeal rail INHERITED, not a new policy: no
code path shall (a) optimize against a like-count / drop-off / popularity score, (b) make
airplay or removal a deterministic function of affinity counts, or (c) chase likes or avoid
drop-off to maximize listener appeal. [HARD] The deliberate absence of a dislike button plus
the non-binding framing defeats brigading AND pandering together. The director weighs affinity
as one curatorial input among many with full autonomy. That affinity counts are a non-binding
weak prior, never an appeal target or hard airplay/removal driver, is the rail.

**Acceptance criteria:** see acceptance.md AC-LS-003.

### REQ-LS-004 — Affinity decays over time so it is a fresh nudge, not a permanent verdict (Ubiquitous)

The like and drop-off contributions to the soft weight SHALL DECAY over time, so a like or a
drop-off is a fresh, fading nudge reflecting recent listener sentiment — not a permanent
affinity verdict that locks a track in or out of rotation forever. The decay rate is TUNABLE
config; that affinity decays (a fading nudge, not a permanent verdict) is the rail.

**Acceptance criteria:** see acceptance.md AC-LS-004.

---

## 9. Requirement Group LA — Anti-abuse / Anti-gaming

Priority: High.

### REQ-LA-001 — Signed like token: HMAC, short-lived, bound to the airing track + issue time + nonce (Ubiquitous) [HARD]

The system SHALL implement the like token (REQ-LH-002) as a SIGNED token — an HMAC (over the
currently-airing track's canonical identity + issue time + a nonce, with a brain-held secret) —
that is SHORT-LIVED (a configured TTL covering roughly the track's airtime) and VERIFIABLE by
the brain WITHOUT server-side per-token state where possible (stateless HMAC verification),
with the nonce/dedup preventing replay. [HARD] A token whose signature is invalid, whose TTL
has expired, or whose bound track was not genuinely on air at mint time is REJECTED. The HMAC
secret is a user-provisioned config (R-L-2); the TTL + nonce policy are config; that the like
token is a short-lived, HMAC-signed, track-bound, replay-resistant token is the rail.

**Acceptance criteria:** see acceptance.md AC-LA-001.

### REQ-LA-002 — Layered like-endpoint defense: validation + per-cookie/per-IP rate-limit + cooldown + dedup (Ubiquitous) [HARD]

The system SHALL defend the website like endpoint with a LAYERED defense: (a) SERVER-SIDE
VALIDATION (token present + well-formed, body schema); (b) PER-COOKIE and PER-IP RATE-LIMITING;
(c) a COOLDOWN between likes from the same identity; and (d) PER-IDENTITY DEDUP (REQ-LH-003). 
[HARD] A submission failing any layer is rejected and never increments a like tally or reaches
the soft-signal normalizer. The thresholds (rate, cooldown, dedup window) are TUNABLE config;
that the like endpoint carries this layered defense is the rail. [Coordination: this mirrors
the REQUEST-011 Group RS endpoint-defense pattern for the request endpoint; LIKE-015 applies the
analogous defense to the like endpoint and does not re-own REQUEST-011's request-endpoint
defense.]

**Acceptance criteria:** see acceptance.md AC-LA-002.

### REQ-LA-003 — Like-flooding is structurally defeated: cap + dedup + decay + signed token (Ubiquitous) [HARD]

The system SHALL bound the influence of likes so that LIKE-FLOODING cannot meaningfully move
rotation: the per-track like contribution to the soft weight is CAPPED (a ceiling on total
affinity weight from likes), PER-IDENTITY-DEDUPED (REQ-LH-003), DECAYED (REQ-LS-004), and
gated by the signed-token requirement (REQ-LA-001) so each like must correspond to a genuinely-
airing track. [HARD] With cap + dedup + decay + signed token + the never-binds invariant
(REQ-LS-003), flooding the heart cannot dominate the director's decision — there is no airplay
lever worth flooding. The cap ceiling is TUNABLE config; that like-flooding is structurally
defeated (cap + dedup + decay + signed token + never-binds) is the rail.

**Acceptance criteria:** see acceptance.md AC-LA-003.

---

## 10. Requirement Group LP — Privacy

Priority: Medium.

### REQ-LP-001 — Like identity is a hashed cookie/session id; no account, no raw PII (Ubiquitous) [HARD]

The system SHALL identify a liker by a HASHED, privacy-preserving cookie/session id (used only
for dedup + rate-limit), never by a user account, and SHALL NOT store a raw IP, raw cookie
value, or any raw PII in the like record or any surface. [HARD] The stored identity is a hash
suitable for dedup/rate-limit and nothing more; v1 has no authenticated listener identity. The
hash scheme + salt are user-provisioned config (R-L-4); that the like identity is a hashed
cookie id with no account and no raw PII is the rail.

**Acceptance criteria:** see acceptance.md AC-LP-001.

### REQ-LP-002 — Drop-off is aggregate-only; no individual listener is tracked (Ubiquitous) [HARD]

The system SHALL compute the drop-off signal from AGGREGATE Icecast listener COUNTS only
(REQ-LD-002), and SHALL NOT track, profile, store, or correlate an individual listener's
session, IP, or disconnect history. [HARD] Drop-off is a count delta around a track boundary,
never a per-listener behaviour record; combined with the minimum-audience floor (REQ-LD-003) it
reveals nothing about any single listener. That drop-off is aggregate-count-only (no individual
tracking) is the rail.

**Acceptance criteria:** see acceptance.md AC-LP-002.

### REQ-LP-003 — No raw PII in stores or on any surface (Ubiquitous) [HARD]

The system SHALL ensure NO raw PII (raw IP, raw handle, raw cookie value, individual session
identifier) appears in the like record, the drop-off record, the soft-signal normalization, the
internal dashboard projection (REQ-LX-002), or any public surface (REQ-LX-001). [HARD] Only the
hashed identity (for dedup) and aggregate counts are persisted; a surface or projection that
would expose raw PII is redacted. That no raw PII appears in any store or surface is the rail.

**Acceptance criteria:** see acceptance.md AC-LP-003.

---

## 11. Requirement Group LX — Surfaces & Observability

Priority: Medium.

### REQ-LX-001 — No public affinity leaderboard; honest framing only (Ubiquitous) [HARD]

The system SHALL NOT render a PUBLIC affinity LEADERBOARD or ranking — no public "most-liked",
"most-hated", "top tracks by likes", or vote tally — because a public ranking would create the
exact appeal target + brigading lever the anti-gaming invariant forbids (REQ-LS-003). [HARD]
Any public reflection of affinity (if shown at all) MUST be honest and non-rankable (e.g. a
simple per-track heart acknowledgement that the listener's like was received), never a
comparative public ranking and never a raw count that invites gaming. Whether ANY public
affinity figure is shown is an orchestrator decision (R-L-1); that no public affinity
leaderboard/ranking is built is the rail.

**Acceptance criteria:** see acceptance.md AC-LX-001.

### REQ-LX-002 — Full per-track affinity reasoning is internal-only, a redacted projection into the REQUEST-011 RD dashboard (Ubiquitous) [HARD]

The system SHALL surface the FULL per-track affinity reasoning — like count, drop-off
rate/confidence, the soft-weight contribution, and how the director weighed it — INTERNALLY
ONLY, as a REDACTED PROJECTION into the REQUEST-011 Group RD internal curation dashboard over
the SAME store (REQUEST-011 REQ-RD-003, one store / two view layers). [HARD] The public surface
shows no raw affinity counts or reasoning; the internal dashboard carries the full picture.
LIKE-015 PROJECTS into the existing RD dashboard; it does NOT stand up a separate affinity
dashboard or a separate store. That the full affinity reasoning is internal-only as a redacted
projection into the RD dashboard is the rail.

**Acceptance criteria:** see acceptance.md AC-LX-002.

### REQ-LX-003 — Observability of the like/drop-off pipeline (Ubiquitous) — Priority Medium

The system SHALL emit structured logs and surface health/status — likes recorded, rejected
likes (bad token / rate-limited / deduped), Icecast-poll health, drop-off samples computed +
suppressed (below the minimum-audience floor), and the soft-weight contribution — through the
existing CORE-001 health/status surface (OPS-004 NFR-O-6 observability pattern), sufficient to
diagnose an affinity-pipeline problem or a gaming attempt after the fact. The metric set is
config; that the like/drop-off pipeline is observable through the existing surface is the rail.

**Acceptance criteria:** see acceptance.md AC-LX-003.

---

## 12. Open Design Decisions Needing the Orchestrator's Ruling

[HARD] The following are NOT yet locked and are surfaced for an explicit orchestrator ruling
before / during implementation. They do not block authoring; they shape config defaults.

- **D-L-1 — Whether ANY public affinity figure is shown at all.** The no-leaderboard rule
  (REQ-LX-001) is locked. Still open: whether the public site shows a minimal honest
  acknowledgement (e.g. a "your like was received" heart state) or NOTHING public at all
  (affinity purely internal). Recommended: a non-comparative per-listener acknowledgement only,
  no aggregate count. Needs a ruling.
- **D-L-2 — Icecast stats source.** Public `/status-json.xsl` (no credential, coarse per-mount
  counts) vs the credentialed admin `/admin/stats` (richer per-mount detail, requires the
  Icecast admin credential — user-provisioned). Recommended: default to public
  `/status-json.xsl`; enable admin where the credential is provided. Needs a ruling + the
  credential if admin is chosen (R-L-3).
- **D-L-3 — Drop-off window + minimum-audience floor + threshold defaults.** What counts as
  "shortly after start" (window length), the minimum audience for a meaningful signal, and the
  disconnect fraction/count that reads as a negative. These are tunable config (REQ-LD-001/003);
  the SPEC fixes the mechanism, not the numbers. Sane defaults needed (suggest window ≈ first
  30–60s, floor ≈ a small handful of listeners) — confirm.
- **D-L-4 — Per-mount vs station-wide drop-off.** If multiple mounts/qualities exist, whether
  drop-off is computed per-mount and summed, or station-wide. Recommended: per-mount sampled,
  aggregated to a station-wide per-track signal. Needs a ruling.
- **D-L-5 — Like-token TTL + secret provisioning.** The HMAC secret is user-provisioned
  (R-L-2); the TTL should roughly cover a track's airtime. Confirm the TTL policy + that the
  secret lives in the gitignored `secrets/brain.env` seam.
- **D-L-6 — Cookie identity vs session identity for dedup.** Whether dedup keys on a persistent
  hashed cookie (survives reconnects, stronger dedup) or a per-session id (weaker dedup, less
  state). Recommended: a hashed persistent cookie with a privacy-preserving salt. Needs a ruling
  (interacts with R-L-4 retention).

---

## 13. User-Provisioned Prerequisites (the real user must provide / decide)

[HARD] LIKE-015 does NOT provision any external account or hardware. The following are flagged so
the user knows what is required.

- **The HMAC secret for the like token.** A brain-held secret (REQ-LA-001) placed in the
  gitignored `secrets/brain.env` seam (the orchestrator is permission-denied there). The SPEC
  encodes that the token is HMAC-signed, not the secret value.
- **The Icecast admin credential (only if admin stats are chosen).** If D-L-2 selects the
  credentialed `/admin/stats` source, the Icecast admin user/password is user-provisioned config;
  the public `/status-json.xsl` path needs no credential.
- **The cookie hash salt + retention policy.** The salt for the hashed cookie identity
  (REQ-LP-001) and how long hashed like identities are retained for dedup (R-L-4) are user-set
  config with sane defaults.
- **The affinity tuning.** The like dedup window / rate-limit / cooldown / cap, the drop-off
  window / minimum-audience floor / threshold, and the soft-weight decay/cap (REQ-LH-003,
  REQ-LD-001/003, REQ-LS-002/004, REQ-LA-002/003) are config the user/AI may tune; the defaults
  keep affinity a weak, fading, capped, non-binding prior.

---

## 14. Non-Functional Requirements

### NFR-L-1 — Never blocks / silences the music playout (Ubiquitous) — Priority High
The like + drop-off subsystem shall NEVER block or silence the music playout: a like is an
asynchronous record, the drop-off poll is a bounded background job, and affinity is a soft bias
on the next-track decision — never a synchronous insertion into the playout chain (REQ-LS-002,
REQ-LD-004). Inherits CORE-001's continuous-operation identity. See acceptance.md AC-NFR-L-1.

### NFR-L-2 — Anti-gaming / anti-pandering is load-bearing: affinity counts never bind to rotation (Ubiquitous) — Priority High
No code path shall make like counts or drop-off rates a satisfaction / appeal-optimization
target or a hard airplay/removal driver: affinity is a noisy, identity-deduped, time-decayed
weak prior (REQ-LS-003), defeating like-flooding (via cap + dedup + decay + signed token,
REQ-LA-003) and dislike-brigading (by the deliberate absence of a dislike button, REQ-LH-001 /
REQ-LD-001) and pandering (via the inherited CORE-001 REQ-OF-004 anti-appeal rail) together.
This is the load-bearing NFR. See acceptance.md AC-NFR-L-2.

### NFR-L-3 — Drop-off honesty: aggregate-only, floored, confidence-marked (Ubiquitous) — Priority High
The drop-off signal shall be derived from aggregate Icecast listener counts only (REQ-LD-002),
suppressed below the minimum-audience floor (REQ-LD-003), and carry a confidence/quality marker
reflecting its inherent noise; it shall never be presented or weighed as a precise per-listener
verdict. See acceptance.md AC-NFR-L-3.

### NFR-L-4 — Single-source-of-truth: reference siblings, never re-own (Ubiquitous) — Priority High
No code path shall re-own or fork the CORE-001 listener-signal contract / website rendering host,
the ENRICH-012 canonical recording, the OPS-004 bounded-job throttle, or the REQUEST-011 internal
dashboard / anti-gaming invariant; each is referenced by id and consumed. LIKE-015 is brain-only +
additive (a like endpoint + a signed-token minter + a drop-off poller + a soft-signal normalizer
on the existing `brain/` package + the existing website + the existing store; no new service, no
new datastore, no web framework). See acceptance.md AC-NFR-L-4.

### NFR-L-5 — Resilience: never crash, never silence (Ubiquitous) — Priority High
A like-endpoint error, a token-verify failure, an Icecast-poll failure (Icecast unreachable /
stats unparseable), a normalizer error, or a surface-render error shall LOG and degrade
gracefully — without crashing the daemon, the picker, or the director loop, and without silencing
the stream (NFR-L-1). A failed like is rejected/dropped; a missing drop-off sample is skipped;
never a crash. See acceptance.md AC-NFR-L-5.

### NFR-L-6 — Bounded, throttled processing (Ubiquitous) — Priority Medium
The like-ingest + the Icecast-stats poll + the drop-off computation shall be BOUNDED and
THROTTLED (OPS-004 REQ-OH-006 pattern, REQ-LD-004) so affinity processing does not jointly
overload the modest box alongside playout, acquisition, and analysis, and so the poll does not
hammer Icecast. See acceptance.md AC-NFR-L-6.

### NFR-L-7 — Privacy: hashed identity, aggregate drop-off, no raw PII (Ubiquitous) — Priority Medium
The liker identity shall be a hashed, privacy-preserving cookie/session id (REQ-LP-001), the
drop-off shall be aggregate-count-only with no individual tracking (REQ-LP-002), and no raw PII
shall appear in any store, projection, or surface (REQ-LP-003). See acceptance.md AC-NFR-L-7.

---

## 15. Open Questions / Risks

- **R-L-1 — Whether to show any public affinity figure (Low, design).** The no-leaderboard rule
  (REQ-LX-001) is locked; whether a minimal honest acknowledgement is shown publicly is open
  (D-L-1). Mitigated: default to a non-comparative per-listener acknowledgement only; full
  reasoning is internal (REQ-LX-002). Open: orchestrator ruling.
- **R-L-2 — Like-token forgery / replay (Medium, security).** A like must bind to the
  genuinely-airing track; a forged or replayed token would let a bad actor like arbitrary tracks.
  Mitigated: HMAC signature + short TTL + nonce + per-identity dedup (REQ-LA-001/002); the secret
  lives in the gitignored secrets seam. Open: confirm the TTL covers track airtime without
  enabling replay across tracks.
- **R-L-3 — Icecast stats availability / accuracy (Medium, build-time).** `/status-json.xsl`
  exists since Icecast 2.4.0 but gives coarse per-mount counts; admin stats need a credential;
  listener counts include reconnects/churn that add drop-off noise. Mitigated: the
  minimum-audience floor + tunable thresholds + a confidence marker (REQ-LD-003, NFR-L-3) temper
  the noise; the poll is best-effort and a missing sample never breaks anything (REQ-LD-004).
  Open: D-L-2 source choice + threshold tuning against real listener behaviour.
- **R-L-4 — Anonymous-web identity weakens dedup (Medium, policy).** The per-identity dedup +
  rate-limit (REQ-LH-003 / REQ-LA-002) rely on a hashed cookie/session id, which a determined
  abuser can rotate. Mitigated: the like CAP (REQ-LA-003) bounds any single track's like weight
  regardless of identity count, the signed token ties each like to a genuinely-airing track, and
  the never-binds invariant (REQ-LS-003) means there is no rotation lever worth the effort.
  Open: confirm the cookie hash + salt + retention with the user (D-L-6).
- **R-L-5 — Drop-off false negatives/positives (Medium, honesty).** A schedule change, a
  network blip, or a popular track that simply ends can look like drop-off; a beloved track
  during low-audience hours may show none. Mitigated: the minimum-audience floor (REQ-LD-003),
  the correlation against the `/api/airing` track-change timeline (so a track CHANGE is not
  read as drop-off), the confidence marker (NFR-L-3), and the soft non-binding weighting
  (REQ-LS-002). Open: tune the window + floor against observed behaviour.
- **R-L-6 — Overlap with REQUEST-011 (Low/Medium, consistency).** Both add a listener-facing
  signal that biases the picker as a non-binding weak prior, share the anti-gaming invariant,
  and project into the same internal dashboard. Mitigated: LIKE-015 contributes a DISTINCT signal
  TYPE (affinity) to the same REQ-D-008 contract and does NOT duplicate or merge into the
  REQUEST-011 Group RA advisory weight (REQ-LS-002); both inherit REQUEST-011 REQ-RA-005 /
  CORE-001 REQ-OF-004; the RD dashboard is shared by reference (REQ-LX-002). Open: confirm the two
  priors are weighed independently by the director, not double-counted.
- **R-L-7 — ENRICH-012 in-progress dependency (Low/Medium, dependency).** Affinity keys on the
  ENRICH-012 canonical recording, which is in progress. Mitigated: where the canonical identity is
  not yet available a like degrades to the existing `Track.key` dedup slug and reattaches on
  enrichment (REQ-LH-004); LIKE-015 does not block on ENRICH-012 completion. Open: sequence after
  ENRICH-012 lands for full canonical keying.
- **R-L-8 — bhive had no proven pattern for this stack (Low, recorded gap).** No bhive
  instruction exists for the signed-token like + Icecast-drop-off soft-signal pattern. Mitigated:
  grounded in the code audit (stdlib server, `/api/airing` truth, Icecast `/status-json.xsl`) and
  the inherited REQUEST-011 anti-gaming design. Action: re-run a bhive query during implementation
  and contribute back per AGENTS.md.

---

## 16. Out-of-Scope / Future SPEC Roadmap

- **Per-listener outcome notification** — telling a liker the host noticed (an outbound channel);
  deferred, bounded by the no-pandering rail.
- **Authenticated listener accounts** — to strengthen dedup / personalization; deferred (v1 is
  hashed, anonymous).
- **Aggregate (never per-message, never appeal-optimizing) affinity-trend sensing for the
  director** — surfacing decayed like/drop-off trends as one curatorial sensor over time; a future
  enhancement bounded by REQ-LS-003 / NFR-L-2 (counts never bind to rotation). Coordinates with
  the STATS-013 analytics site (the playtime-based insight surface) which may visualize affinity
  trends internally.
- **A richer drop-off model** (correlating drop-off with track features from ANALYSIS-006 to learn
  what listeners flee) — a future learning enhancement, bounded by the same soft / non-binding /
  no-pandering rails and the per-persona anti-convergence firewall (PROGRAMMING-007 REQ-PR-004).
- **A staffed human affinity-review console** — a curator UI over the affinity signals; a future
  enhancement on top of the automated pipeline.

---

## 17. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md;
detailed Given-When-Then scenarios for the load-bearing requirements are in acceptance.md
Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-LH-001 | Explicit Like (Heart) | High | Ubiquitous | AC-LH-001 |
| REQ-LH-002 | Explicit Like (Heart) | High | Event | AC-LH-002 |
| REQ-LH-003 | Explicit Like (Heart) | High | Ubiquitous | AC-LH-003 |
| REQ-LH-004 | Explicit Like (Heart) | High | Event | AC-LH-004 |
| REQ-LD-001 | Implicit Drop-off | High | Event | AC-LD-001 |
| REQ-LD-002 | Implicit Drop-off | High | State | AC-LD-002 |
| REQ-LD-003 | Implicit Drop-off | High | State | AC-LD-003 |
| REQ-LD-004 | Implicit Drop-off | High | State | AC-LD-004 |
| REQ-LS-001 | Soft-signal Integration | High | Ubiquitous | AC-LS-001 |
| REQ-LS-002 | Soft-signal Integration | High | Ubiquitous | AC-LS-002 |
| REQ-LS-003 | Soft-signal Integration | High | Ubiquitous | AC-LS-003 |
| REQ-LS-004 | Soft-signal Integration | Medium | Ubiquitous | AC-LS-004 |
| REQ-LA-001 | Anti-abuse / Anti-gaming | High | Ubiquitous | AC-LA-001 |
| REQ-LA-002 | Anti-abuse / Anti-gaming | High | Ubiquitous | AC-LA-002 |
| REQ-LA-003 | Anti-abuse / Anti-gaming | High | Ubiquitous | AC-LA-003 |
| REQ-LP-001 | Privacy | Medium | Ubiquitous | AC-LP-001 |
| REQ-LP-002 | Privacy | High | Ubiquitous | AC-LP-002 |
| REQ-LP-003 | Privacy | Medium | Ubiquitous | AC-LP-003 |
| REQ-LX-001 | Surfaces & Observability | High | Ubiquitous | AC-LX-001 |
| REQ-LX-002 | Surfaces & Observability | Medium | Ubiquitous | AC-LX-002 |
| REQ-LX-003 | Surfaces & Observability | Medium | Ubiquitous | AC-LX-003 |
| NFR-L-1 | Non-Functional | High | Ubiquitous | AC-NFR-L-1 |
| NFR-L-2 | Non-Functional | High | Ubiquitous | AC-NFR-L-2 |
| NFR-L-3 | Non-Functional | High | Ubiquitous | AC-NFR-L-3 |
| NFR-L-4 | Non-Functional | High | Ubiquitous | AC-NFR-L-4 |
| NFR-L-5 | Non-Functional | High | Ubiquitous | AC-NFR-L-5 |
| NFR-L-6 | Non-Functional | Medium | Ubiquitous | AC-NFR-L-6 |
| NFR-L-7 | Non-Functional | Medium | Ubiquitous | AC-NFR-L-7 |

Parity: 21 REQ + 7 NFR = 28 specified items; 28 acceptance entries (21 AC + 7 AC-NFR); 1:1
REQ↔AC.

REQ-group prefixes + counts: LH (Explicit Like / Heart) = 4, LD (Implicit Drop-off) = 4, LS
(Soft-signal Integration) = 4, LA (Anti-abuse / Anti-gaming) = 3, LP (Privacy) = 3, LX (Surfaces
& Observability) = 3 → 4+4+4+3+3+3 = 21 REQ across 6 groups. NFR-L-1…7 = 7 NFR. Total = 21 + 7 =
28 specified items, 28 acceptance entries, 1:1 REQ↔AC.
