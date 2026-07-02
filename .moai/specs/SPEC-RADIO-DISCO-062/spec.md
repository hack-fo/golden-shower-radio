---
id: SPEC-RADIO-DISCO-062
version: 0.1.1
status: draft
created: 2026-07-02
updated: 2026-07-02
author: charlie
priority: Medium
issue_number: null
---

# SPEC-RADIO-DISCO-062 — "Disco Mode": a vibrant listener-influence surface

## HISTORY

- 2026-07-02 (v0.1.1): **Plan-auditor fixes** (report `.moai/reports/spec-audit-DISCO-062-2026-07-02.md`; verdict NEEDS-FIXES → resolved). **D2** — corrected `brain/like.py` symbol `TokenGate` → `LikeTokener` (the real class at :92; methods mint :114 / verify :129 were right). **D3** — line-number drift fixed (`LikeGate` :320→:319, `_handle_like_token` :744→:743, `_handle_like` :766→:765, `_build_options` :99→:92). **D5** — flagged the vibe-steer degrade as a run-phase [BUILD-GAP]: `SIGNAL_LISTENER_CONTEXT` is a SCALAR nudge, not the per-descriptor mapping REQ-DN-002 needs (with R-D-4 concurrent-steer aggregation + access-gate default). **D1 was a FALSE POSITIVE** — the auditor ran on this branch, where SONICRECO-061's SPEC files are absent (they are committed on `feature/SPEC-RADIO-SONICRECO-061`, not yet merged to main); `REQ-VE-005` + Groups GD/RK are verified real there, and REQ-VE-005 explicitly names a future "disco mode" surface as its consumer — so the cross-refs stand and are now annotated with the branch location. **D4** (cosmetic `## 10X./10Y.` heading artifacts) left as-is to avoid a section-renumber cascade. No REQ/NFR count change (23 + 8 = 31).

- 2026-07-02 (v0.1.0): Initial DESIGN / PLAN draft (no code this pass), occupying the new
  global-incrementing DISCO-062 id (062 is the next free RADIO id; 061 = SONICRECO, 060 = LIVEMIX are
  taken). "Disco Mode" is the human-facing "influence the music" surface of the autonomous AI radio: a
  listener types an artist, song, or genre/vibe into a centered soft input box; the station LLM reviews
  the submission; and, if accepted, the submission INFLUENCES what plays — while the autonomous director
  stays in control (no hijack). A faded / animated background wall drifts other listeners' recently
  ACCEPTED, clean, anonymized suggestions. This SPEC is a NEW subsystem that COMPOSES two sibling SPECs
  rather than re-owning them: SPEC-RADIO-REQUEST-011 (the listener song-request surface — catalog matcher,
  off-catalog wishlist/acquisition crossing, moderation floor, access-gate) OWNS the song/artist request
  path, which DISCO-062 CONSUMES; and SPEC-RADIO-SONICRECO-061 (the grounded sonic recommendation engine —
  the CLAP text tower → grounded retrieval, REQ-VE-005) OWNS the natural-language vibe retrieval, which
  DISCO-062 CONSUMES for the genre/mood/vibe path. BOTH siblings are unbuilt design SPECs, so DISCO-062
  ships with GRACEFUL DEGRADATION for each (a song/artist submission falls back to the existing
  `brain/library.py` `normalize_key` + `track_for_key` lookup plus a simple wishlist note until REQUEST-011
  ships; a vibe submission degrades to a bounded genre/mood nudge on the existing per-persona
  `brain/taste.py` `TasteProfile` weights until SONICRECO ships), so DISCO-062 is independently valuable
  before either lands. The surface is a new `/disco` route + a `POST /api/disco` submission endpoint + a
  `GET /api/disco/wall` feed added as handler branches on the EXISTING stdlib
  `http.server.ThreadingHTTPServer` (`brain/server.py`) — no new container / port / service. Every
  submission is LLM-reviewed + moderated, rate-limited, and access-gated; the wall shows only accepted,
  clean, anonymized suggestions. It uses a DISTINCT REQ namespace — DH (surface & route), DU (submission,
  review & moderation), DL (song/artist request path), DN (vibe/mood steer — the bounded nudge), DW (the
  wall), DZ (design & brand) — chosen to avoid collision with every existing D-family prefix already in
  use across the SPEC corpus (DC, DE, DF, DG, DI, DK, DM, DO, DP, DQ, DR, DS, DV, DX are taken by
  DATASTORE-022 / DEDUP-014 / AIDECISION-037 / LIVEMIX-060 / others; DH, DU, DL, DN, DW, DZ are free). This
  SPEC is a DESIGN / PLAN artifact: the actual frontend build is a later `/moai run` + design-phase
  concern; this document defines the requirements + the design brief only. Total: 23 REQ + 8 NFR = 31, 1:1
  REQ↔AC (DH=4, DU=5, DL=3, DN=4, DW=3, DZ=4).

---

## 1. Overview & Background

### 1.1 Why this SPEC — "let a listener say what they want, let the LLM vet it, let it colour the music — but never let it grab the wheel"

The station already plays continuously and autonomously (CORE-001), talks in distinct personas
(VOICE-002, PROGRAMMING-007), programs and presents itself (OPS-004), orchestrates as one operator
(ORCH-005), and — on the drawing board — will let a listener request a specific song (REQUEST-011) and
retrieve tracks by natural-language vibe (SONICRECO-061). What it does not yet have is a single,
human-facing, VIBRANT surface where a listener can point at the music — "play some Khruangbin", "more
late-night rainy synthwave", "give me something summery" — and see their influence reflected, in a way
that is safe, moderated, anonymized, and that NEVER lets the listener seize control of the autonomous
director.

Disco Mode is that surface. It is the station's public "influence the music" face:

1. **A soft, centered input box.** A listener types an artist, a song, or a genre/mood/vibe.
2. **The station LLM reviews it.** Every submission is vetted for safe / on-brand / feasible before it
   influences anything. Spam, abuse, and off-brand submissions are rejected with a short recorded reason.
3. **On accept, it influences the music — softly.** A song/artist submission becomes a request/wishlist
   signal (play-if-owned bias, else a non-binding acquisition wish) via REQUEST-011's path. A genre / mood
   / vibe submission becomes a natural-language QUERY that STEERS the director's selection for a bounded
   time window via SONICRECO-061's grounded retrieval. Either way the influence is a soft, bounded,
   time-boxed nudge; the director stays in control.
4. **A living wall.** A faded / animated background wall drifts other listeners' recently ACCEPTED, clean,
   anonymized suggestions — a vibrant, flavorful sense that the room is influencing the music together,
   with no listener identity ever shown.

### 1.2 The load-bearing idea — influence is composed, soft, and firewalled from control

[HARD] The single design decision that makes Disco Mode safe is that **it never introduces a new control
lever — it only composes existing SOFT influence seams and firewalls them from the autonomous director.**
Concretely:

- The song/artist path REUSES REQUEST-011's advisory-weight semantics (a decaying, capped, deduped weak
  prior that biases but never force-inserts; the AI may decline). DISCO-062 adds no airplay-binding lever;
  it inherits REQUEST-011's anti-gaming / anti-pandering rail verbatim (REQ-DL-003).
- The vibe path REUSES SONICRECO-061's grounded retrieval to shape the candidate POOL for a bounded
  window. The steer only re-weights WITHIN the already-legal candidate set (which already passes the
  PROGRAMMING-007 / OPS-004 HARD no-repeat / LRP rail); it can never resurrect a no-repeat-blocked track
  and can never become a popularity / engagement maximizer (REQ-DN-003/004).
- Every submission passes an LLM review + a reused moderation floor before it touches either seam, is
  rate-limited + access-gated, and — on any fault — degrades (queued / deferred / rejected) rather than
  silencing the stream or crashing the daemon (Group DU, NFR-D-2/6).

This means a flood of Disco submissions buys a flooder nothing (there is no forced-airplay lever to
flood), and a hostile submission cannot escape the moderation + LLM review gate. The surface is
expressive and fun on the front, firewalled and boring on the back — by construction.

### 1.3 What this layer is, concretely

- A NEW `/disco` PAGE + TWO API ENDPOINTS (Group DH) on the EXISTING brain HTTP server: `GET /disco`
  (the vibrant page), `POST /api/disco` (submit an influence), `GET /api/disco/wall` (the
  accepted-suggestions feed). All three are new handler branches on the existing stdlib
  `http.server.ThreadingHTTPServer` — no new container, port, service, or web framework.
- A SUBMISSION → REVIEW → MODERATION GATE (Group DU): every submission is LLM-reviewed (safe / on-brand /
  feasible) via the `brain/llm.py` subscription / never-raise seam, classified as song/artist vs vibe,
  rate-limited per listener, access-gated, and — on accept — acts (routes to the request/wishlist path or
  issues the vibe-steer) with a SHORT recorded reason; on reject, it influences nothing.
- A SONG/ARTIST REQUEST PATH (Group DL): an accepted song/artist submission becomes a request/wishlist
  signal via REQUEST-011 (play-if-owned bias, else a non-binding acquisition wish). DISCO-062 CONSUMES
  REQUEST-011's matcher + wishlist + acquisition crossing; it does NOT re-specify them. Until REQUEST-011
  ships, the path degrades to a `brain/library.py` lookup + a simple wishlist note.
- A VIBE/MOOD STEER (Group DN): an accepted genre/mood/vibe submission becomes a natural-language query
  that STEERS the director's selection for a bounded window — ideally via SONICRECO-061's CLAP text-tower
  grounded retrieval (REQ-VE-005). The steer is SOFT, TIME-BOXED, and never a takeover. Until SONICRECO
  ships, it degrades to a bounded genre/mood nudge on the per-persona `brain/taste.py` `TasteProfile`
  weights.
- A LIVING WALL (Group DW): a faded / animated background wall + the `GET /api/disco/wall` feed showing
  ONLY accepted, clean, anonymized suggestions (titles / artists / genres) with a drifting / fading
  effect. No rejected / pending items, no moderation verdicts, no listener identity.
- A DESIGN & BRAND BRIEF (Group DZ): a centered soft input box, a vibrant POP palette (orange, peach,
  flamenco red, cuba libre, summery), a drifting background wall, brand-context adherence per the design
  constitution, and WCAG 2.1 AA conformance.

### 1.4 What this SPEC OWNS vs. CONSUMES (boundary discipline)

[HARD] DISCO-062 OWNS the vibrant listener-influence SURFACE and the SUBMISSION-REVIEW spine: the
`/disco` page + endpoints, the LLM-review-every-submission gate, the song/artist-vs-vibe classifier, the
per-listener rate-limit + access-gate wiring, the vibe-steer's bounded/time-boxed SOFT semantics + its
editorial-rail firewall, the wall's accepted-only/anonymized projection, and the design/brand brief. It
MUST NOT restate, fork, or weaken any REQUEST-011, SONICRECO-061, CALLIN-003, CORE-001, OPS-004, or
PROGRAMMING-007 requirement — it CONSUMES them.

OWNS:
- The `/disco` surface + the `POST /api/disco` + `GET /api/disco/wall` endpoints as new handler branches
  on the existing brain HTTP server (Group DH).
- The submission → LLM-review → moderation → accept/reject → act gate, the short recorded reason, the
  song/artist-vs-vibe classifier, and the per-listener rate-limit + access-gate wiring (Group DU).
- The COMPOSITION of the song/artist path onto REQUEST-011 (route the request/wishlist signal) and its
  degradation to the `brain/library.py` lookup until REQUEST-011 ships (Group DL).
- The COMPOSITION of the vibe path onto SONICRECO-061 (issue the text-tower steer) and its degradation to
  the `brain/taste.py` bounded nudge until SONICRECO ships; the SOFT + TIME-BOXED + never-takeover
  semantics; and the editorial-rail firewall (Group DN).
- The wall's accepted-only, clean, anonymized projection + the drift/fade presentation (Group DW).
- The design/brand brief: centered soft input, vibrant palette, drifting wall, brand adherence, WCAG AA
  (Group DZ).

CONSUMES (references / composes; does not restate):
- **REQUEST-011 Group RM (catalog matcher + typeahead) + Group RWL (off-catalog wishlist + acquisition
  crossing) + Group RS (moderation floor + access-gate)** — the song/artist path routes into these; the
  matcher / wishlist / acquisition-crossing / access-gate are OWNED by REQUEST-011 and consumed by
  DISCO-062, never re-specified (Groups DL, DU). [REQUEST-011 is a DRAFT, unbuilt SPEC — see Section 2.]
- **SONICRECO-061 REQ-VE-005 (text→audio KNN via the CLAP text tower) + Group GD (the ID-grounding
  firewall) + Group RK (constrained-ID selection)** — the vibe path hands its natural-language query to
  SONICRECO's grounded retrieval, which shapes the candidate pool; DISCO-062 consumes it, never re-owns
  the embedding / retrieval / selection (Group DN). [SONICRECO-061 is a DRAFT, unbuilt SPEC — see
  Section 2.]
- **CORE-001 Group E (the self-controlled website) + `brain/server.py` (stdlib
  `http.server.ThreadingHTTPServer` — NO web framework) + `brain/website.py` (`render_website`)** — the
  `/disco` page + endpoints attach as new handler branches on the existing server and render as a sibling
  of the existing site; DISCO-062 adds no new service (Groups DH, DZ).
- **CALLIN-003 fail-closed moderation floor (Groups CM/CC)** — reused (via REQUEST-011 Group RS, which
  itself reuses it) for the submission text; DISCO-062 does not re-own moderation (Group DU).
- **LIKE-015 `brain/like.py` `hash_identity` + `LikeGate` (dedup + rate-limit)** — the anonymized
  identity-hash + per-identity rate-limit precedent DISCO-062 reuses for its per-listener rate-limit key
  and its anonymized wall (Groups DU, DW).
- **PROGRAMMING-007 anti-convergence + anti-appeal rail (inherited from CORE-001 REQ-OF-004) + the HARD
  no-repeat / LRP rail (OPS-004 SelectionRefiner over `library.legal_candidates`)** — the editorial rails
  the vibe-steer must respect and can never override (Group DN, NFR-D-8).

### 1.5 The Creative Autonomy Principle (inherited, cross-cutting)

This SPEC inherits CORE-001 Section 1.3 and the sibling SPECs' autonomy principle and does NOT redefine
it. The director decides, with full creative freedom, which accepted influences to honour, when, and how
strongly — exactly as a smart human DJ folds a room's requests and a shifting mood into a set they still
own. What is NOT the listener's call, and what this SPEC fixes as hard rails, is: every submission is
LLM-reviewed + moderated; influence is always SOFT (a bias / a bounded steer, never a forced insert or a
hard filter); the vibe steer is TIME-BOXED and can never override the no-repeat / LRP or anti-appeal
rails; the wall shows only accepted / clean / anonymized items; and no path silences the stream. The
thresholds (rate-limit, steer magnitude, steer window, wall size) are TUNABLE config; the requirement
guarantees only that influence is reviewed, soft, bounded, and firewalled from control.

### 1.6 Fixed engineering rails (the only hard constraints)

- **Off the sub-1s playout pull path; never blocks / silences.** [HARD] The `/disco` surface, submission
  processing, LLM review, and the steer are ALL off the `GET /api/next` hot path (`brain/server.py`
  `_handle_next`); a fault degrades (submission queued / deferred / rejected), never silences the stream
  (REQ-DH-003, NFR-D-1/2).
- **The director stays in control (no hijack).** [HARD] No Disco path grants listener-controlled forced
  airplay; the song/artist path is an advisory bias (REQUEST-011 semantics), the vibe path is a bounded
  time-boxed soft steer — both discretionary, both auto-expiring (REQ-DN-003, NFR-D-8).
- **Every submission is LLM-reviewed + moderated.** [HARD] Each submission is vetted for safe / on-brand
  / feasible via the `brain/llm.py` never-raise seam and passes the reused moderation floor before it
  influences anything; spam / abuse / off-brand is rejected (Group DU).
- **Fail-closed on safety, fail-open on the stream.** [HARD] An LLM-review outage degrades to the
  deterministic moderation floor + defer; it NEVER auto-accepts unsafe content (fail-closed on safety) and
  NEVER blocks playout (fail-open on the stream) (REQ-DU-005).
- **The vibe steer respects the editorial rails.** [HARD] The steer re-weights only WITHIN the already-
  legal candidate set; it never overrides the PROGRAMMING-007 / OPS-004 HARD no-repeat / LRP rail and is
  never an appeal / popularity maximizer (REQ-DN-004).
- **Rate-limited + access-gated + anonymized.** [HARD] Submissions are rate-limited per (anonymized)
  listener and access-gated (reusing REQUEST-011's access-gate + LIKE-015's `hash_identity`); the wall
  shows only accepted, clean, anonymized items — no listener identity (Groups DU, DW, NFR-D-5/6).
- **Compose, don't re-own.** [HARD] The song/artist path consumes REQUEST-011's matcher / wishlist /
  acquisition-crossing; the vibe path consumes SONICRECO-061's grounded retrieval; moderation is reused
  from CALLIN-003 (via REQUEST-011). DISCO-062 re-specifies none of them (NFR-D-4).
- **Graceful degradation for BOTH unbuilt dependencies.** [HARD] Until REQUEST-011 ships, the song/artist
  path degrades to a `brain/library.py` lookup + wishlist note; until SONICRECO-061 ships, the vibe path
  degrades to a bounded `brain/taste.py` nudge. DISCO-062 is independently valuable before either lands
  (REQ-DL-002, REQ-DN-002, NFR-D-7).
- **Brain-only Python + stdlib http.server; additive; no new service.** [HARD] DISCO-062 adds a `/disco`
  handler set + a submission module + a wall projection to the existing `brain/` package and the existing
  website; submissions / accepted-suggestions live in the existing store seam. No web framework, no new
  datastore, no new service or port (NFR-D-3).
- **Brand + accessibility are constitutional.** [HARD] The design adheres to the brand context in
  `.moai/project/brand/` (design constitution §3.1) and meets WCAG 2.1 AA; the vibrant palette never
  sacrifices contrast / keyboard / ARIA (Group DZ, REQ-DZ-002/003).

---

## 2. Dependencies

This SPEC COMPOSES SPEC-RADIO-REQUEST-011 and SPEC-RADIO-SONICRECO-061, and is layered on SPEC-RADIO-
CORE-001, SPEC-RADIO-CALLIN-003, SPEC-RADIO-OPS-004, SPEC-RADIO-PROGRAMMING-007, and SPEC-RADIO-LIKE-015.
It references their subsystems by CONCEPT (and, where a cited requirement is a deliberately stable
invariant or seam, by number) rather than re-specifying them.

[HARD] This SPEC MUST NOT re-specify, fork, or weaken any sibling SPEC requirement. Where it needs a
predecessor behavior it consumes it. Where a Disco decision could conflict with continuous operation, the
inherited behavior WINS — the music keeps playing, the director keeps control, and influence stays soft.

Composed / consumed concepts:
- **REQUEST-011 (DRAFT, unbuilt) — Groups RM / RWL / RS.** The song/artist path (Group DL) routes an
  accepted song/artist submission into REQUEST-011's tiered catalog matcher (RM) and off-catalog wishlist
  + acquisition crossing (RWL), and reuses its request-endpoint access-gate + the CALLIN-003 moderation
  floor it wraps (RS). [HARD][GREENFIELD] REQUEST-011 is a DRAFT SPEC that is NOT yet built; until it
  ships, Group DL degrades to the existing `brain/library.py` `normalize_key` + `track_for_key` lookup
  (play-if-owned bias) + a simple wishlist note (REQ-DL-002). The dependency is recorded so DISCO-062 is
  not built assuming a matcher / wishlist surface that does not yet exist.
- **SONICRECO-061 (DRAFT, unbuilt; committed on branch `feature/SPEC-RADIO-SONICRECO-061`, not yet merged to main — `REQ-VE-005` + Groups GD/RK verified present there).** The vibe path (Group DN) hands its
  natural-language query to SONICRECO's text→audio KNN via the CLAP text tower (REQ-VE-005), whose
  grounded retrieval + constrained-ID selection (Groups GD / RK) shape the candidate pool for a bounded
  window. SONICRECO-061 REQ-VE-005 already names a future conversational "disco mode" surface as its
  intended consumer — the composition is mutually consistent by design. [HARD][GREENFIELD] SONICRECO-061
  is a DRAFT SPEC that is NOT yet built; until it ships, Group DN degrades to a bounded genre/mood nudge
  on the `brain/taste.py` `TasteProfile` weights via a `SIGNAL_LISTENER_CONTEXT`-style bounded delta
  (REQ-DN-002).
- **CORE-001 Group E + `brain/server.py` + `brain/website.py`.** The `/disco` page + the two endpoints
  attach as new handler branches on the existing stdlib `http.server.ThreadingHTTPServer` (`do_GET` /
  `do_POST` dispatch) and render as a sibling of the `render_website` site; extended additively, no new
  service, no web framework.
- **CALLIN-003 fail-closed moderation floor (Groups CM/CC).** The submission text passes the SAME
  deterministic slur/PII regex + LLM classifier (reached via REQUEST-011 Group RS, which reuses it);
  DISCO-062 reuses it by reference, never re-owns it.
- **LIKE-015 `brain/like.py` `hash_identity` + `LikeGate`.** The anonymized identity-hash
  (`SHA256(cookie + salt)`) + the per-identity dedup / rate-limit precedent DISCO-062 reuses for its
  per-listener rate-limit key and its anonymized wall.
- **PROGRAMMING-007 anti-appeal / anti-convergence + the HARD no-repeat / LRP rail (OPS-004
  SelectionRefiner over `library.legal_candidates`).** The editorial rails the vibe-steer must respect;
  the steer re-weights only within the already-legal candidate set and is never a popularity maximizer.

### bhive memory seam

bhive memory (AGENTS.md protocol) has no proven pattern for the LLM-reviewed listener-influence surface +
vibe-query-to-bounded-taste-steer pattern on this Go/Python + Liquidsoap stack (recorded gap). Re-run a
bhive query on the "LLM-moderated free-text listener input → soft bounded influence" + the "natural-
language vibe → CLAP text-tower retrieval → time-boxed candidate-pool steer" patterns during
implementation, and contribute the verified approach back per the AGENTS.md memory protocol.

---

## 3. Glossary

| Term | Definition |
|------|-----------|
| **Disco Mode** | The vibrant, human-facing "influence the music" surface: a centered soft input box + a drifting wall of accepted suggestions, on a new `/disco` route (Group DH). |
| **Submission** | A listener's free-text influence: an artist, a song, or a genre / mood / vibe, typed into the Disco input box and POSTed to `/api/disco` (Group DU). |
| **LLM review** | The station-LLM vet applied to EVERY submission — safe / on-brand / feasible — via the `brain/llm.py` subscription / never-raise seam, before the submission influences anything (REQ-DU-001). |
| **Classifier (song/artist vs vibe)** | The step that routes an accepted submission to the song/artist request path (Group DL) or the vibe/mood steer (Group DN); ambiguity is resolved without silent miscategorization (REQ-DU-003). |
| **Song/artist request path** | The influence path for a specific song/artist submission: a request/wishlist signal via REQUEST-011 (play-if-owned bias, else a non-binding acquisition wish). CONSUMES REQUEST-011; degrades to a `brain/library.py` lookup until it ships (Group DL). |
| **Vibe/mood steer** | The influence path for a genre / mood / vibe submission: a natural-language query that STEERS the director's selection for a bounded window via SONICRECO-061's grounded retrieval. SOFT, TIME-BOXED, never a takeover; degrades to a `brain/taste.py` nudge until SONICRECO ships (Group DN). |
| **Bounded / time-boxed** | The vibe steer has a bounded magnitude and an auto-expiring window; when the window elapses, the steer's influence is removed and selection returns to the director's default (REQ-DN-003). |
| **Editorial-rail firewall** | [HARD] The rule that the vibe steer re-weights ONLY within the already-legal candidate set (post no-repeat / LRP) and is never an appeal / popularity maximizer — it can never override a HARD rail or hijack the director (REQ-DN-004, NFR-D-8). |
| **The wall** | The faded / animated background wall (and its `GET /api/disco/wall` feed) drifting other listeners' recently ACCEPTED, clean, anonymized suggestions. No rejected / pending items, no verdicts, no identity (Group DW). |
| **Accepted-only projection** | [HARD] The wall is a redacted projection over the submission store: it shows only submissions that passed review + moderation, stripped to the clean suggestion text + timestamp, with the identity anonymized (REQ-DW-001/002). |
| **Anonymized identity** | A hashed, privacy-preserving requester id (`SHA256(cookie + salt)` per LIKE-015 `hash_identity`) used only for per-listener rate-limiting / dedup; never a raw cookie / IP / account, never shown on the wall (REQ-DU-004, REQ-DW-003, NFR-D-5). |
| **Access-gate** | The reused REQUEST-011 request-endpoint access-gate concept (a config-gated allow condition for submitting), plus the anti-abuse rate-limit / cooldown; DISCO-062 wires it, does not re-own it (REQ-DU-004). |
| **Moderation floor (reused)** | The CALLIN-003 fail-closed deterministic slur/PII regex + LLM classifier the submission text passes (reached via REQUEST-011 Group RS). Reused by reference, not re-owned (REQ-DU-001/005). |
| **Fail-closed on safety / fail-open on the stream** | [HARD] On an LLM-review outage, DISCO-062 degrades to the deterministic moderation floor + defer (never auto-accepting unsafe content — fail-closed on safety) and never blocks the audio path (fail-open on the stream) (REQ-DU-005). |
| **Graceful degradation** | The fallback behavior when a composed dependency is unbuilt: song/artist → `brain/library.py` lookup + wishlist note (until REQUEST-011); vibe → `brain/taste.py` bounded nudge (until SONICRECO-061). DISCO-062 works either way (REQ-DL-002, REQ-DN-002, NFR-D-7). |
| **CLAP text tower (SONICRECO REQ-VE-005)** | The SONICRECO-061 text encoder that maps a natural-language vibe query into the shared audio-text embedding space to retrieve real catalog tracks; the seam the vibe path consumes when SONICRECO ships (Group DN). |
| **`TasteProfile` nudge (degradation)** | The bounded genre/mood delta the vibe path applies to `brain/taste.py` `TasteProfile` weights when SONICRECO is unavailable — a `SIGNAL_LISTENER_CONTEXT`-style soft, bounded, expiring bias (REQ-DN-002). |

---

## 4. Scope

### 4.1 In scope (requirement groups)

- **Group DH — Surface & Route.** The `/disco` page + `POST /api/disco` + `GET /api/disco/wall` as new
  handler branches on the existing brain HTTP server; off the sub-1s pull path; brain-only additive, no
  new service.
- **Group DU — Submission, Review & Moderation.** The LLM-review-every-submission gate; the accept → act
  (+ short reason) / reject → no-influence lifecycle; the song/artist-vs-vibe classifier; the per-listener
  rate-limit + access-gate + anonymized identity; the fail-closed-on-safety / fail-open-on-the-stream
  degradation.
- **Group DL — Song/Artist Request Path.** The composition onto REQUEST-011 (request/wishlist signal);
  the graceful degradation to the `brain/library.py` lookup + wishlist note; the inherited anti-gaming /
  anti-pandering rail.
- **Group DN — Vibe/Mood Steer.** The composition onto SONICRECO-061 REQ-VE-005 (text-tower grounded
  retrieval steer); the graceful degradation to the `brain/taste.py` bounded nudge; the SOFT + TIME-BOXED
  + never-takeover semantics; the editorial-rail firewall.
- **Group DW — The Wall.** The accepted-only, clean, anonymized drifting wall + its `GET /api/disco/wall`
  feed as a redacted projection; the no-identity privacy rule.
- **Group DZ — Design & Brand.** The centered soft input box; the vibrant POP palette + drifting wall
  effect; brand-context adherence per the design constitution; WCAG 2.1 AA; self-contained styling on the
  existing render seam.
- Plus **NFRs** (Section 8) and **Risks** (Section 9).

### 4.2 Out of scope (explicitly deferred / owned elsewhere)

- **The tiered catalog matcher + typeahead + off-catalog wishlist + acquisition crossing** — owned by
  REQUEST-011 (Groups RM / RWL); DISCO-062 routes into them, never re-owns them.
- **The grounded sonic recommendation engine (CLAP embedding, brute-force retrieval, constrained-ID
  selection, ID-grounding firewall)** — owned by SONICRECO-061 (Groups GD / VE / RK); the vibe path
  consumes REQ-VE-005, never re-owns the engine.
- **The moderation floor (deterministic slur/PII regex + LLM classifier)** — owned by CALLIN-003 (Groups
  CM/CC); reused via REQUEST-011 Group RS, never re-owned.
- **The listener-signal contract + the no-pandering policy** — owned by CORE-001 (REQ-D-008 / REQ-OF-004);
  Disco influence normalizes through the existing seams and inherits the policy, never re-owns it.
- **The website rendering host + the runtime self-generation of the site** — owned by CORE-001 Group E /
  `brain/website.py`; DISCO-062 adds a `/disco` page + endpoints on the existing server, never re-owns the
  render pipeline.
- **The next-track picker + the playout chain + the no-repeat / LRP rail** — owned by CORE-001 / OPS-004 /
  PROGRAMMING-007; the vibe steer is a bounded bias INPUT within the already-legal candidate set, never a
  re-owned picker, a hard filter, or a synchronous playout insertion.
- **A listener leaderboard / "top requests" / vote tally / most-popular-vibe ranking** — deliberately
  EXCLUDED: a public ranking would create the exact appeal target + flooding lever the anti-gaming rail
  forbids (REQ-DL-003, NFR-D-8). No public ranking is built.
- **A coin-op jukebox / listener-controlled forced airplay** — explicitly NOT built: all influence is
  soft, bounded, discretionary; the director stays in control (REQ-DN-003, NFR-D-8).
- **Authenticated / account-based listener identity** — out of scope for v1; identity is a hashed,
  privacy-preserving id (LIKE-015 `hash_identity`), never a user account (REQ-DU-004, NFR-D-5).
- **Outbound per-listener outcome notification** ("your influence was applied / declined") — out of scope
  for v1; the disposition is internal + reflected in the host's autonomous behavior + the wall (Section 10
  roadmap).
- **A new datastore or a new web service / port / container** — brain-only + additive; submissions +
  accepted-suggestions live in the existing store seam; the surface renders on the existing website
  (NFR-D-3).

---

## 5. Constraints (confirmed, fixed)

- [HARD] **Brain-only Python + stdlib http.server; additive; no new service.** New handler branches on
  the existing `ThreadingHTTPServer`, a submission module, and a wall projection on the existing `brain/`
  package + website + store. No web framework, no new datastore, no new port / container.
- [HARD] **Off the sub-1s pull path; never blocks / silences.** The `/disco` surface + submission
  processing + LLM review + steer are off the `GET /api/next` hot path; a fault degrades, never silences.
- [HARD] **The director stays in control (no hijack).** No Disco path grants listener-controlled forced
  airplay; influence is a soft advisory bias (song/artist) or a bounded time-boxed soft steer (vibe).
- [HARD] **Every submission is LLM-reviewed + moderated** before it influences anything; spam / abuse /
  off-brand is rejected with a short recorded reason.
- [HARD] **Fail-closed on safety, fail-open on the stream.** An LLM-review outage degrades to the
  deterministic moderation floor + defer; never auto-accepts unsafe content; never blocks playout.
- [HARD] **The vibe steer respects the editorial rails.** It re-weights only within the already-legal
  candidate set; it never overrides the HARD no-repeat / LRP rail and is never an appeal / popularity
  maximizer.
- [HARD] **Rate-limited per (anonymized) listener + access-gated.** Reuses REQUEST-011's access-gate + the
  LIKE-015 `hash_identity` pattern; no raw PII.
- [HARD] **The wall shows only accepted, clean, anonymized suggestions** — no rejected / pending items, no
  verdicts, no listener identity.
- [HARD] **Compose, don't re-own.** REQUEST-011 (matcher / wishlist / acquisition / access-gate),
  SONICRECO-061 (grounded retrieval), CALLIN-003 (moderation), CORE-001 (website / listener-signal), and
  PROGRAMMING-007 / OPS-004 (editorial rails) are referenced, never restated.
- [HARD] **Graceful degradation for BOTH unbuilt dependencies.** Song/artist → `brain/library.py` lookup
  + wishlist note (until REQUEST-011); vibe → `brain/taste.py` bounded nudge (until SONICRECO-061).
  DISCO-062 is independently valuable before either lands.
- [HARD] **Brand + accessibility are constitutional.** The design adheres to the brand context in
  `.moai/project/brand/` (design constitution §3.1) and meets WCAG 2.1 AA.
- [HARD] **Resilience.** A `/disco` route error, a submission-store error, an LLM-review error, a
  classifier error, a steer-apply error, or a wall-render error logs and degrades gracefully; it never
  crashes the daemon and never silences the stream.
- [HARD][GREENFIELD] **REQUEST-011 + SONICRECO-061 dependencies.** Both are DRAFT, unbuilt SPECs; DISCO-062
  is built against their seams with graceful degradation on each (Groups DL / DN).

---

## 6. Delta / Brownfield Impact Map

All targets are additive extensions to the existing brain package. No file is rewritten; no new service,
port, datastore, or web framework is introduced. `[MODIFY]` = add a branch / sibling to an existing file;
`[NEW]` = a new brain module; `[CONSUME]` = a sibling SPEC's seam consumed by reference; `[REUSE]` = an
existing function reused as-is.

| File / Seam | Change | Detail |
|-------------|--------|--------|
| `brain/server.py` `do_GET` dispatch (`:476`-`:506`) | **[MODIFY]** | Add a `/disco` branch → a new `_handle_disco()` serving the vibrant page, and a `/api/disco/wall` branch → a new `_handle_disco_wall()` serving the accepted-suggestions feed. Rides the existing never-crash `try/except` (`:507`-`:513`) so a Disco fault returns 500 without touching the daemon. New routes; no new dependency (REQ-DH-001/002, NFR-D-2). |
| `brain/server.py` `do_POST` dispatch (`:426`-`:451`) | **[MODIFY]** | Add a `/api/disco` branch → a new `_handle_disco_submit()` accepting a submission body, invoking the DU review gate, and returning an accept/reject verdict (REQ-DH-002, Group DU). |
| `brain/server.py` `_handle_next` (`:517`) / `_pick_refined` (`:305`) | **[UNTOUCHED — rail]** | [HARD] The sub-1s pull path stays byte-identical; Disco routes never call `_handle_next`. The vibe steer influences selection only via the taste/retrieval seams read by the picker, never by intercepting the pull (REQ-DH-003, NFR-D-1). |
| `brain/server.py` `_handle_like_token` (`:743`) / `_handle_like` (`:765`) | **[REUSE — precedent]** | The mint → verify → identity-hash → rate-limit → dedup pattern is the precedent for the DU submission gate's per-listener rate-limit + anonymized identity (REQ-DU-004). |
| `brain/server.py` `_handle_root` / `state.website_html()` (`:795`) | **[REFERENCE]** | The existing site render; the `/disco` page is a sibling render, and may link from the site (Group DZ). |
| `brain/website.py` `render_website(cfg)` (`:14`) + `:root` tokens (`:26`-`:30`) | **[MODIFY / REFERENCE]** | The `/disco` page reuses the render idiom and the CSS-custom-property token pattern; the vibrant Disco palette (orange / peach / flamenco red / cuba libre / summery) is a warm cousin of the existing `--gold #f5c542` / `--bg #0c0a06` tokens. [HARD] Reconcile with brand context (Group DZ, REQ-DZ-002). |
| `brain/llm.py` `generate_talk_script` (`:997`) / `_query_text` subscription-auth never-raise seam (`:1019` fallback) / `_build_options` (`:92`) | **[REUSE / NEW sibling]** | A new `review_disco_submission()`-style call mirrors the tools-off, one-turn, subscription-auth, never-raise contract (never crashes; degrades to a deterministic verdict on any exception) for the LLM review (REQ-DU-001/005). |
| `brain/taste.py` `TasteProfile` (`:366`) / `relevance` (`:464`) / `SIGNAL_LISTENER_CONTEXT` (`:493`) / `_SIGNAL_DIRECTION` (`:514`) / `aggregate_delta` (`:522`) | **[REUSE — vibe degradation]** | The vibe-steer degradation applies a bounded, expiring `SIGNAL_LISTENER_CONTEXT`-style delta to the per-persona `TasteProfile` weights when SONICRECO is unavailable (REQ-DN-002). [BUILD-GAP] `SIGNAL_LISTENER_CONTEXT` is today a SCALAR global nudge (`+0.05`), NOT the per-descriptor genre/mood mapping REQ-DN-002 needs → the degrade path requires NEW per-descriptor mapping logic designed at implementation; concurrent-steer aggregation (R-D-4) + the access-gate default remain run-phase items. |
| `brain/like.py` `hash_identity` (`:65`) / `LikeGate` (`:319`) / `LikeTokener.mint`/`verify` (`:114`/`:129`) | **[REUSE]** | Anonymized identity hash (`SHA256(cookie + salt)`) + dedup / rate-limit for the DU per-listener gate and the DW anonymized wall (REQ-DU-004, REQ-DW-003, NFR-D-5). |
| `brain/library.py` `normalize_key` (`:43`) / `track_for_key` (`:588`) / `keys` (`:602`) | **[REUSE — song/artist degradation]** | The song/artist degradation resolves a submission via `normalize_key(artist, title)` → `track_for_key` (play-if-owned bias) + a simple wishlist note when REQUEST-011 is unavailable (REQ-DL-002). |
| REQUEST-011 Group RM (matcher) / RWL (wishlist + acquisition) / RS (access-gate + moderation) | **[CONSUME — GREENFIELD]** | The song/artist path routes an accepted submission into REQUEST-011's matcher + wishlist; DISCO-062 does not re-specify them. Unbuilt → Group DL degrades (REQ-DL-001/002). |
| SONICRECO-061 REQ-VE-005 (text→audio CLAP KNN) / Group GD (ID-grounding firewall) / Group RK (constrained-ID selection) | **[CONSUME — GREENFIELD]** | The vibe path hands its query to SONICRECO's grounded retrieval to shape the candidate pool; DISCO-062 does not re-own the engine. Unbuilt → Group DN degrades (REQ-DN-001/002). |
| CALLIN-003 moderation floor (Groups CM/CC) | **[CONSUME]** | The submission text passes the reused fail-closed moderation floor (via REQUEST-011 Group RS) before it influences anything (REQ-DU-001/005). |
| PROGRAMMING-007 anti-appeal + OPS-004 `SelectionRefiner` over `library.legal_candidates` (HARD no-repeat / LRP) | **[CONSUME — rail]** | [HARD] The editorial rails the vibe steer must respect; the steer re-weights only within the already-legal candidate set (REQ-DN-004, NFR-D-8). |
| Existing store seam (SQLite, per DATASTORE-022) | **[MODIFY — additive]** | Submissions + accepted-suggestions live in the existing store; no new datastore (NFR-D-3). |

---

## 7. Relationships to sibling SPECs

- **SPEC-RADIO-REQUEST-011 — COMPOSES (song/artist path).** REQUEST-011 OWNS the listener song-request
  surface (catalog matcher + typeahead, off-catalog wishlist + acquisition crossing, request-endpoint
  anti-abuse + access-gate, the moderation-floor reuse). DISCO-062 Group DL routes an accepted song/artist
  submission into that surface and reuses its access-gate; it never re-specifies the matcher / wishlist /
  acquisition. Because REQUEST-011 is unbuilt, Group DL degrades to a `brain/library.py` lookup + wishlist
  note (REQ-DL-002).
- **SPEC-RADIO-SONICRECO-061 — CONSUMES (vibe path).** SONICRECO-061 OWNS the grounded sonic recommendation
  engine; its REQ-VE-005 text→audio CLAP KNN is the natural-language vibe retrieval, and REQ-VE-005 already
  names a future "disco mode" surface as its intended consumer. DISCO-062 Group DN hands its vibe query to
  that retrieval to steer the candidate pool for a bounded window; it never re-owns the embedding /
  retrieval / selection. Because SONICRECO-061 is unbuilt, Group DN degrades to a `brain/taste.py` bounded
  nudge (REQ-DN-002).
- **SPEC-RADIO-LIKE-015 — REUSES (identity-hash + rate-limit pattern).** DISCO-062 reuses `hash_identity`
  (`SHA256(cookie + salt)`) + the `LikeGate` dedup / rate-limit precedent for its per-listener rate-limit
  key and its anonymized wall — the same privacy posture (no raw cookie / IP / account).
- **SPEC-RADIO-PROGRAMMING-007 / OPS-004 — RESPECTS (editorial rails).** DISCO-062 Group DN's vibe steer
  re-weights only within the already-legal candidate set (post no-repeat / LRP, produced by the OPS-004
  `SelectionRefiner` over `library.legal_candidates`), and is never an appeal / popularity maximizer
  (inherits CORE-001 REQ-OF-004). It can never override a HARD rail or hijack the director.
- **SPEC-RADIO-CALLIN-003 — REUSES (moderation floor).** The submission text passes the CALLIN-003
  fail-closed moderation floor (reached via REQUEST-011 Group RS); DISCO-062 reuses it by reference.
- **SPEC-RADIO-CORE-001 — EXTENDS (website + server).** The `/disco` surface + endpoints attach to the
  existing CORE-001 self-controlled website + stdlib HTTP server as additive handler branches.

---

## 8. Requirement Group DH — Surface & Route

Priority: High.

### REQ-DH-001 — A `/disco` page on the existing brain HTTP server (Ubiquitous) [HARD]

The system SHALL serve a `/disco` PAGE — the vibrant Disco Mode surface — as a NEW handler branch on the
EXISTING stdlib `http.server.ThreadingHTTPServer` (`brain/server.py` `do_GET` dispatch), rendered as a
self-contained sibling of the existing station website (`brain/website.py` `render_website`). [HARD] No
new container, port, service, or web framework is introduced; the page is emitted from the brain at render
time exactly as the existing site is. The exact page markup / styling is a design-phase concern (Group
DZ); that the `/disco` page is a new route on the existing server is the rail.

**Acceptance criteria:** see acceptance.md AC-DH-001.

### REQ-DH-002 — `POST /api/disco` submission + `GET /api/disco/wall` feed endpoints (Ubiquitous) [HARD]

The system SHALL provide a `POST /api/disco` endpoint (accepting a listener submission body and returning
an accept/reject verdict) and a `GET /api/disco/wall` endpoint (serving the accepted-suggestions feed) as
NEW handler branches on the existing server (`do_POST` / `do_GET` dispatch). [HARD] Both are brain-only,
stdlib-only handler branches; no web framework, no new service. The request/response schema is
implementation detail; that the two endpoints exist as additive handler branches is the rail.

**Acceptance criteria:** see acceptance.md AC-DH-002.

### REQ-DH-003 — Off the sub-1s playout pull path; never blocks / silences (Ubiquitous) [HARD]

The `/disco` surface, `POST /api/disco` processing, the LLM review, and the vibe steer SHALL be OFF the
`GET /api/next` sub-1s playout pull path (`brain/server.py` `_handle_next`), and SHALL NEVER block or
silence the audio path. [HARD] A Disco request is handled asynchronously to the picker; a fault on any
Disco route degrades (the submission is queued / deferred / rejected, the wall omits the item) and returns
a graceful error — it NEVER touches `_handle_next` / `_pick_refined`, the picker, or the stream. That the
Disco surface is off the hot path and never blocks / silences is the rail.

**Acceptance criteria:** see acceptance.md AC-DH-003.

### REQ-DH-004 — Brain-only, additive; no new service / datastore / framework (Ubiquitous) [HARD]

The system SHALL implement DISCO-062 as an ADDITIVE extension to the existing `brain/` package: new
handler branches + a submission module + a wall projection, with submissions + accepted-suggestions living
in the EXISTING store seam. [HARD] DISCO-062 SHALL NOT add a new web service, a new port / container, a
new datastore, or a web framework; it is stdlib-only, consistent with the existing server / site. The
storage layout is config; that DISCO-062 is brain-only + additive with no new service is the rail.

**Acceptance criteria:** see acceptance.md AC-DH-004.

---

## 9. Requirement Group DU — Submission, Review & Moderation

Priority: High.

### REQ-DU-001 — Every submission is LLM-reviewed (safe / on-brand / feasible) + moderated before it influences anything (Event-driven) [HARD]

When a submission is received at `POST /api/disco`, the system SHALL REVIEW it with the station LLM (via
the `brain/llm.py` subscription / never-raise seam) for SAFE / ON-BRAND / FEASIBLE, AND pass its text
through the reused CALLIN-003 fail-closed moderation floor (via REQUEST-011 Group RS), BEFORE the
submission influences the request/wishlist path (Group DL) or the vibe steer (Group DN). [HARD] A
submission that fails review or the moderation floor influences NOTHING (it is rejected, REQ-DU-002) and
never reaches the request/wishlist seam, the steer, or the wall. The review prompt / model is config; that
every submission is LLM-reviewed + moderated before any influence is the rail.

**Acceptance criteria:** see acceptance.md AC-DU-001.

### REQ-DU-002 — On accept: act + record a short reason; on reject: no influence (Event-driven) [HARD]

When the review + moderation ACCEPTS a submission, the system SHALL ACT on it — routing it to the
song/artist request path (Group DL) or issuing the vibe steer (Group DN) — and SHALL record a SHORT reason
(one clean sentence, e.g. "on-brand vibe request"); when the review REJECTS a submission (spam / abusive /
off-brand / infeasible), the system SHALL record the rejection reason and apply NO influence. [HARD] The
short reason is internal / wall-safe (grounded, never fabricated); a rejected submission never reaches the
request/wishlist seam, the steer, or the wall. The reason wording is config/brand-voice; that accept →
act + short reason and reject → no influence is the rail.

**Acceptance criteria:** see acceptance.md AC-DU-002.

### REQ-DU-003 — Classify each accepted submission as song/artist vs genre/mood/vibe (Event-driven)

When a submission is accepted, the system SHALL CLASSIFY it as a SONG/ARTIST request (→ Group DL) or a
GENRE/MOOD/VIBE steer (→ Group DN), and SHALL route it accordingly. [HARD] An ambiguous submission SHALL
be resolved without SILENT miscategorization — it is routed to the best-fit path (or handled as a
song/artist request when it names a specific title/artist, else as a vibe), and the chosen classification
is recorded. The classifier (LLM-assisted or heuristic) is config; that each accepted submission is
classified and routed without silent miscategorization is the rail.

**Acceptance criteria:** see acceptance.md AC-DU-003.

### REQ-DU-004 — Rate-limited per (anonymized) listener + access-gated (Ubiquitous) [HARD]

The system SHALL RATE-LIMIT submissions PER (anonymized) LISTENER and ACCESS-GATE the submission endpoint,
reusing the REQUEST-011 request-endpoint access-gate concept and the LIKE-015 `hash_identity`
(`SHA256(cookie + salt)`) anonymized-identity pattern for the rate-limit key. [HARD] The identity is a
hashed, privacy-preserving id (per-cookie / per-session), never a raw cookie / IP / user account; a
submission over the rate-limit or failing the access-gate is rejected (REQ-DU-002) without influence. The
rate / cooldown / gate mechanism are TUNABLE config; that submissions are rate-limited per anonymized
listener + access-gated is the rail.

**Acceptance criteria:** see acceptance.md AC-DU-004.

### REQ-DU-005 — Fail-closed on safety, fail-open on the stream: an LLM-review outage degrades safely (Unwanted) [HARD]

If the LLM review is UNAVAILABLE, erroring, or over quota, then the system SHALL DEGRADE to the
deterministic moderation floor + DEFER (queue the submission or reject it), and SHALL NOT (a) auto-accept
an unsafe / unmoderated submission (FAIL-CLOSED on safety), nor (b) block or silence the playout
(FAIL-OPEN on the stream), nor (c) crash the daemon. [HARD] The `brain/llm.py` never-raise discipline
applies: a review exception yields a deterministic conservative verdict (defer / reject), never a silent
accept and never a crash. That an LLM-review outage fails closed on safety + open on the stream is the
rail.

**Acceptance criteria:** see acceptance.md AC-DU-005.

---

## 10X. Requirement Group DL — Song/Artist Request Path

Priority: High. [Composes REQUEST-011 — GREENFIELD; see Section 2.]

### REQ-DL-001 — An accepted song/artist submission becomes a request/wishlist signal via REQUEST-011 (Event-driven) [HARD]

When an accepted submission is classified as a SONG/ARTIST request (REQ-DU-003), the system SHALL route it
into the REQUEST-011 path — a play-if-owned advisory REQUEST (biasing the picker, never force-inserting)
when the track is in the catalog, or a NON-BINDING off-catalog WISHLIST / acquisition wish when it is not.
[HARD] DISCO-062 CONSUMES REQUEST-011's tiered catalog matcher (Group RM) + off-catalog wishlist +
acquisition crossing (Group RWL); it does NOT re-specify the matcher, the wishlist, or the
acquisition-crossing policy. That a song/artist submission routes into REQUEST-011's request/wishlist path
(consumed, not re-owned) is the rail.

**Acceptance criteria:** see acceptance.md AC-DL-001.

### REQ-DL-002 — Graceful degradation until REQUEST-011 ships: `brain/library.py` lookup + wishlist note (State-driven) [HARD]

While REQUEST-011 is NOT yet built, the system SHALL DEGRADE the song/artist path to the EXISTING
`brain/library.py` seam: resolve the submission via `normalize_key(artist, title)` → `track_for_key` and,
on a hit, apply a bounded play-if-owned advisory bias; on a miss, record a SIMPLE WISHLIST NOTE (a
non-binding acquisition wish). [HARD] The degraded path is still NON-BINDING (a bias, never a forced
insert) and never a jukebox; it is a strict subset of REQUEST-011's eventual behavior, so DISCO-062 is
independently valuable before REQUEST-011 lands. That the song/artist path degrades to a library lookup +
wishlist note (still non-binding) until REQUEST-011 ships is the rail.

**Acceptance criteria:** see acceptance.md AC-DL-002.

### REQ-DL-003 — Inherit the anti-gaming / anti-pandering rail; add no airplay-binding lever (Ubiquitous) [HARD] [consistency]

The song/artist path SHALL INHERIT the REQUEST-011 / CORE-001 anti-gaming / anti-pandering rail: a request
count is a noisy, identity-deduped, time-decayed weak PRIOR, never a satisfaction target or the sole
airplay driver — and DISCO-062 SHALL ADD NO new airplay-binding lever. [HARD] [consistency] No Disco code
path shall (a) force-insert a requested track, (b) make airplay a deterministic function of Disco request
count, or (c) chase Disco submissions to maximize appeal. Flooding the Disco box buys a flooder nothing
because there is no forced-airplay lever to flood. That the song/artist path inherits the anti-gaming /
anti-pandering rail and adds no binding lever is the rail.

**Acceptance criteria:** see acceptance.md AC-DL-003.

---

## 10Y. Requirement Group DN — Vibe/Mood Steer

Priority: High. [Composes SONICRECO-061 REQ-VE-005 — GREENFIELD; see Section 2.]

### REQ-DN-001 — An accepted vibe submission steers selection via SONICRECO-061's grounded retrieval (Event-driven) [HARD]

When an accepted submission is classified as a GENRE/MOOD/VIBE steer (REQ-DU-003), the system SHALL treat
its text as a NATURAL-LANGUAGE QUERY and route it to SONICRECO-061's text→audio retrieval (REQ-VE-005 — the
CLAP text tower into the shared embedding space), whose grounded result (Groups GD / RK) shapes the
candidate POOL the director selects from for a bounded window. [HARD] DISCO-062 CONSUMES SONICRECO-061's
grounded retrieval + constrained-ID selection; it does NOT re-own the embedding, the retrieval, or the
ID-grounding firewall. That an accepted vibe submission steers selection via SONICRECO's grounded retrieval
(consumed, not re-owned) is the rail.

**Acceptance criteria:** see acceptance.md AC-DN-001.

### REQ-DN-002 — Graceful degradation until SONICRECO-061 ships: a bounded `brain/taste.py` nudge (State-driven) [HARD]

While SONICRECO-061 is NOT yet built, the system SHALL DEGRADE the vibe steer to a BOUNDED genre/mood
NUDGE on the EXISTING per-persona `brain/taste.py` `TasteProfile` weights — a `SIGNAL_LISTENER_CONTEXT`-
style soft, bounded, expiring delta over the descriptors the vibe query maps to (mapped by the LLM review
or a heuristic to ANALYSIS-006 genre/tag descriptors). [HARD] The degraded nudge is SOFT (a weight bias,
never a hard filter), BOUNDED (a capped magnitude), and TIME-BOXED (auto-expiring, REQ-DN-003); it is a
strict subset of SONICRECO's eventual grounded steer, so DISCO-062 is independently valuable before
SONICRECO lands. That the vibe steer degrades to a bounded, expiring `TasteProfile` nudge until SONICRECO
ships is the rail.

**Acceptance criteria:** see acceptance.md AC-DN-002.

### REQ-DN-003 — The steer is SOFT + TIME-BOXED + never a takeover; the director stays in control (Ubiquitous) [HARD]

The vibe steer SHALL be a SOFT, BOUNDED, TIME-BOXED influence — a bounded bias applied for a configured
window, after which it AUTO-EXPIRES and selection returns to the director's default. [HARD] The steer SHALL
NEVER become a takeover: it does not pin the director to a genre, does not force a fixed playlist, does not
persist past its window, and the director MAY downweight or ignore it. Multiple concurrent vibe steers are
bounded in aggregate so the room cannot collectively seize control. The window / magnitude / aggregate cap
are TUNABLE config; that the steer is soft, bounded, time-boxed, and never a takeover (director in control)
is the rail.

**Acceptance criteria:** see acceptance.md AC-DN-003.

### REQ-DN-004 — The steer respects the editorial rails: within the legal candidate set; never an appeal maximizer (Ubiquitous) [HARD] [consistency]

The vibe steer SHALL re-weight ONLY WITHIN the already-legal candidate set (the tracks that already pass
the PROGRAMMING-007 / OPS-004 HARD no-repeat / LRP rail produced by the `SelectionRefiner` over
`library.legal_candidates`), and SHALL NOT (a) override or bypass a HARD rail (no-repeat / LRP / palette
caps), nor (b) become an appeal / popularity / engagement maximizer (it inherits the CORE-001 REQ-OF-004
anti-appeal rail). [HARD] [consistency] A vibe steer that would resurrect a no-repeat-blocked track is
inert on that track by construction; a steer is curatorial CONTEXT, never an optimization target. That the
steer re-weights only within the legal candidate set and is never an appeal maximizer is the rail.

**Acceptance criteria:** see acceptance.md AC-DN-004.

---

## 11. Requirement Group DW — The Wall

Priority: Medium (the surface works without the wall; the wall is its living flavor).

### REQ-DW-001 — The wall shows ONLY accepted, clean, anonymized suggestions (Ubiquitous) [HARD]

The background wall SHALL show ONLY submissions that passed review + moderation (accepted), rendered as
CLEAN suggestion text (title / artist / genre), with a drifting / fading animated effect — and SHALL NOT
show rejected or pending submissions, moderation verdicts, internal reasoning, or any listener identity.
[HARD] The wall is accepted-only + clean + anonymized by construction; a rejected / pending / unsafe
submission never appears. The wall size / rotation / animation are config; that the wall shows only
accepted, clean, anonymized suggestions is the rail.

**Acceptance criteria:** see acceptance.md AC-DW-001.

### REQ-DW-002 — `GET /api/disco/wall` is a redacted projection of the submission store (Ubiquitous) [HARD]

The `GET /api/disco/wall` feed SHALL be a REDACTED PROJECTION over the SAME submission store: it emits only
the clean suggestion text + a coarse timestamp for accepted submissions, STRIPPING the raw text (where it
differs from the clean suggestion), the moderation verdict, the LLM-review reasoning, and the identity.
[HARD] There is ONE submission store and the wall is a redacted view of it — no separate public store, no
duplication, no identity, no verdicts. The projected field-set is config; that the wall feed is a redacted
projection (accepted + clean + anonymized only) is the rail.

**Acceptance criteria:** see acceptance.md AC-DW-002.

### REQ-DW-003 — Privacy: hashed identity only; the wall never exposes who submitted what (Ubiquitous) [HARD]

Any stored requester identity SHALL be a HASHED, privacy-preserving id (LIKE-015 `hash_identity`,
`SHA256(cookie + salt)`), used only for rate-limiting / dedup, and the wall (and its feed) SHALL NEVER
expose the identity or associate a suggestion with a listener. [HARD] No raw cookie / IP / account appears
in the submission store or the wall; the wall shows WHAT was suggested, never WHO suggested it. That the
identity is hashed and the wall never exposes who submitted what is the rail.

**Acceptance criteria:** see acceptance.md AC-DW-003.

---

## 12. Requirement Group DZ — Design & Brand

Priority: Medium.

### REQ-DZ-001 — Centered soft input box + drifting animated wall + vibrant POP palette (Ubiquitous)

The `/disco` page SHALL present a CENTERED SOFT INPUT BOX (prompting "type an artist, song, or vibe") over
a FADED / ANIMATED background WALL of drifting accepted suggestions, in a VIBRANT, flavorful, POP visual
register — the operator palette direction being orange, peach, flamenco red, cuba libre, and summery
tones. [HARD] The design MUST be self-contained and consistent with the existing server-rendered site (no
heavy client framework); the exact drift / fade effect + layout are a design-phase concern. That the page
is a centered soft input over a drifting animated wall in a vibrant POP palette is the rail.

**Acceptance criteria:** see acceptance.md AC-DZ-001.

### REQ-DZ-002 — Adhere to the brand context; reconcile the operator palette; brand wins on conflict (Ubiquitous) [HARD]

The design SHALL ADHERE to the brand context in `.moai/project/brand/` (brand-voice.md,
visual-identity.md, target-audience.md) per the design constitution (§3.1 — brand is a constitutional
constraint), and SHALL RECONCILE the operator's Disco palette (orange / peach / flamenco red / cuba libre
/ summery) with visual-identity.md. [HARD] Where the operator palette conflicts with a populated
visual-identity.md, BRAND WINS on conflict (design constitution §3.3), OR the conflict is FLAGGED for the
operator. [HARD][FLAG] At authoring time the brand-context files are unpopulated placeholders (`_TBD_`) —
see Section 9 R-D-1; the operator palette is therefore the de-facto brand direction for this surface,
PROVISIONAL and subject to reconciliation once the brand interview (`/moai design`) populates
visual-identity.md. That the design adheres to brand context (brand wins on conflict, else flag) is the
rail.

**Acceptance criteria:** see acceptance.md AC-DZ-002.

### REQ-DZ-003 — WCAG 2.1 AA: contrast, keyboard, ARIA (Ubiquitous) [HARD]

The `/disco` surface SHALL meet WCAG 2.1 AA: text / interactive contrast ratios at or above the AA
thresholds (>= 4.5:1 for normal text, >= 3:1 for large text / UI components) against the vibrant palette,
FULL keyboard operability (the input, the submit action, and any wall controls reachable + operable by
keyboard with visible focus), and appropriate ARIA labelling for the input and the live wall region.
[HARD] The vibrant palette SHALL NOT sacrifice accessibility — a palette choice that fails AA contrast is
adjusted (or the text/background is), never shipped unreadable. That the surface meets WCAG 2.1 AA
(contrast + keyboard + ARIA) is the rail.

**Acceptance criteria:** see acceptance.md AC-DZ-003.

### REQ-DZ-004 — Self-contained styling on the existing render seam (Ubiquitous)

The `/disco` page SHALL be styled SELF-CONTAINED on the EXISTING render seam — reusing the
`brain/website.py` `render_website` idiom and the `:root` CSS-custom-property token pattern (`:26`-`:30`),
emitting its own scoped styles inline, with NO heavy client framework and no new build step. The Disco
palette is expressed as CSS custom properties (a warm cousin of the existing `--gold` / `--bg` tokens).
The exact token set is a design-phase concern; that the page is self-contained on the existing render seam
(no framework, no build step) is the rail.

**Acceptance criteria:** see acceptance.md AC-DZ-004.

---

## 13. Exclusions (What NOT to Build)

[HARD] This SPEC explicitly excludes the following (a consolidated restatement of Section 4.2 + the
Section 10 roadmap, as the mandatory exclusions list):

- **A coin-op jukebox / listener-controlled forced airplay** — all influence is soft, bounded,
  discretionary; the director stays in control (REQ-DN-003, NFR-D-8).
- **A public leaderboard / "top requests" / "most-popular-vibe" ranking / vote tally** — a public ranking
  would create the exact appeal target + flooding lever the anti-gaming rail forbids (REQ-DL-003,
  NFR-D-8). Not built.
- **Re-specifying REQUEST-011's matcher / typeahead / off-catalog wishlist / acquisition crossing** —
  owned by REQUEST-011 (Groups RM / RWL); consumed, never re-owned (REQ-DL-001).
- **Re-owning SONICRECO-061's embedding / grounded retrieval / constrained-ID selection / ID-grounding
  firewall** — owned by SONICRECO-061 (Groups GD / VE / RK); consumed via REQ-VE-005, never re-owned
  (REQ-DN-001).
- **The moderation floor (slur/PII regex + classifier)** — owned by CALLIN-003; reused via REQUEST-011
  Group RS, never re-owned (REQ-DU-001/005).
- **The next-track picker + the playout chain + the no-repeat / LRP rail** — owned by CORE-001 / OPS-004 /
  PROGRAMMING-007; the vibe steer is a bounded bias INPUT within the already-legal candidate set, never a
  re-owned picker, a hard filter, or a synchronous playout insertion (REQ-DN-004, NFR-D-1).
- **The website rendering host + the runtime self-generation of the site** — owned by CORE-001 Group E /
  `brain/website.py`; DISCO-062 adds a `/disco` page + endpoints, never re-owns the render pipeline
  (REQ-DH-001).
- **Authenticated / account-based listener identity** — v1 uses a hashed, privacy-preserving id (LIKE-015
  `hash_identity`), not a user account (REQ-DU-004, NFR-D-5).
- **Outbound per-listener outcome notification** ("your influence was applied / declined") — deferred
  (Section 10); the disposition is internal + reflected in the host's autonomous behavior + the wall.
- **A new datastore, web service, port, container, or web framework** — brain-only + additive; the
  surface renders on the existing server / site; submissions live in the existing store (NFR-D-3).
- **Exposing listener identity on the wall** — the wall shows WHAT was suggested, never WHO (REQ-DW-003).

---

## 14. User-Provisioned Prerequisites (the real user must provide / decide)

[HARD] DISCO-062 does NOT provision any external account or hardware. The following are flagged so the user
knows what is required / decided.

- **The brand context.** The design (Group DZ) adheres to `.moai/project/brand/`, which is currently
  UNPOPULATED (`_TBD_` placeholders). The operator either runs the brand interview (`/moai design`) to
  populate visual-identity.md — after which brand wins on conflict with the operator palette — or accepts
  the operator palette as the provisional brand direction for this surface (REQ-DZ-002, R-D-1).
- **The access-gate mechanism.** The submission access-gate (REQ-DU-004) reuses REQUEST-011's access-gate
  concept; the concrete gate (open / token / config flag) is a user decision, as is whether Disco Mode is
  on by default.
- **The anti-abuse thresholds.** The per-listener rate-limit / cooldown / dedup window (REQ-DU-004) have
  sane defaults; the user may tune them for their traffic.
- **The steer tuning.** The vibe-steer magnitude / window / aggregate cap (REQ-DN-002/003) are config the
  user/AI may tune; the defaults keep the steer soft, bounded, and time-boxed.
- **The LLM review model.** The review runs on the existing subscription seam (`brain/llm.py`); no new key
  is required, but the user decides the model / prompt for the review (REQ-DU-001).

---

## 15. Non-Functional Requirements

### NFR-D-1 — Never blocks / silences the music playout (Ubiquitous) — Priority High
The Disco surface + submission processing + LLM review + steer shall NEVER block or silence the music
playout: they are OFF the `GET /api/next` sub-1s pull path (REQ-DH-003); the picker and audio path are
unaffected by Disco load. Inherits CORE-001's continuous-operation identity. See acceptance.md AC-NFR-D-1.

### NFR-D-2 — Resilience: never crash, never silence (Ubiquitous) — Priority High
A `/disco` route error, a submission-store error, an LLM-review error, a classifier error, a steer-apply
error, or a wall-render error shall LOG and degrade gracefully — riding the existing `do_GET` / `do_POST`
never-crash `try/except` — without crashing the daemon, the picker, or the director loop, and without
silencing the stream. A failed submission is rejected / deferred / dropped, never a crash. See
acceptance.md AC-NFR-D-2.

### NFR-D-3 — Brain-only + additive: no new service / datastore / framework (Ubiquitous) — Priority High
DISCO-062 shall be a brain-only, additive extension: new handler branches + a submission module + a wall
projection on the existing `brain/` package + website + store; no web framework, no new datastore, no new
port / container / service (REQ-DH-004). See acceptance.md AC-NFR-D-3.

### NFR-D-4 — Single-source-of-truth: compose siblings, never re-own (Ubiquitous) — Priority High
No Disco code path shall re-own or fork REQUEST-011's matcher / wishlist / acquisition / access-gate,
SONICRECO-061's retrieval / selection, CALLIN-003's moderation floor, CORE-001's website / listener-signal
seams, or the PROGRAMMING-007 / OPS-004 editorial rails; each is referenced by id and consumed. See
acceptance.md AC-NFR-D-4.

### NFR-D-5 — Privacy: hashed / anonymized identity, no PII (Ubiquitous) — Priority Medium
The requester identity shall be a HASHED, privacy-preserving id (LIKE-015 `hash_identity`,
`SHA256(cookie + salt)`), used only for rate-limiting / dedup, never a raw cookie / IP / account; no raw
PII appears in the submission store or on the wall / feed (REQ-DU-004, REQ-DW-003). See acceptance.md
AC-NFR-D-5.

### NFR-D-6 — Abuse-resistance: layered gate; fail-closed on safety (Ubiquitous) — Priority High
The submission endpoint shall carry a LAYERED defense — LLM review + reused moderation floor + per-listener
rate-limit + access-gate + accepted-only wall — and shall FAIL CLOSED on safety: an LLM-review outage
degrades to the deterministic moderation floor + defer, never an auto-accept of unsafe content (REQ-DU-005,
REQ-DW-001). See acceptance.md AC-NFR-D-6.

### NFR-D-7 — Independent value: graceful degradation for BOTH unbuilt dependencies (Ubiquitous) — Priority Medium
DISCO-062 shall be independently valuable BEFORE REQUEST-011 and SONICRECO-061 land: the song/artist path
degrades to a `brain/library.py` lookup + wishlist note (REQ-DL-002) and the vibe path degrades to a
bounded `brain/taste.py` nudge (REQ-DN-002); neither degraded path is a jukebox or a takeover. See
acceptance.md AC-NFR-D-7.

### NFR-D-8 — The director stays in control: no listener-controlled forced airplay (Ubiquitous) — Priority High
No Disco path shall grant listener-controlled forced airplay: the song/artist path is an advisory bias
(REQUEST-011 semantics), the vibe path is a bounded, time-boxed soft steer within the legal candidate set
(REQ-DN-003/004); both are discretionary and auto-expiring, and no Disco input can override a HARD rail or
hijack the director. This is the load-bearing control-firewall NFR. See acceptance.md AC-NFR-D-8.

---

## 16. Open Questions / Risks

- **R-D-1 — Brand context is unpopulated (Medium, flag).** `.moai/project/brand/` (brand-voice.md,
  visual-identity.md, target-audience.md) is all `_TBD_` placeholders at authoring time. The operator
  palette (orange / peach / flamenco red / cuba libre / summery) is the only concrete brand direction, and
  it diverges from the live site's gold-on-near-black tokens (`--gold #f5c542` / `--bg #0c0a06`,
  `brain/website.py:26`-`30`). Mitigated: REQ-DZ-002 makes the operator palette PROVISIONAL — brand wins on
  conflict once visual-identity.md is populated. Open: run the brand interview (`/moai design`) before or
  during the design build, OR ratify the operator palette as the surface's brand direction. [FLAGGED for
  the operator.]
- **R-D-2 — Both composed dependencies are unbuilt (Medium, dependency).** REQUEST-011 and SONICRECO-061
  are DRAFT SPECs. Mitigated: graceful degradation on both paths (REQ-DL-002, REQ-DN-002) makes DISCO-062
  independently valuable (NFR-D-7). Open: sequence the full-fidelity paths after the siblings ship, or
  ship the degraded paths first and upgrade in place at their seams.
- **R-D-3 — Vibe classification ambiguity (Medium, build-time).** A submission like "Sade" (artist) vs
  "smooth" (vibe) vs "Khruangbin vibes" (both) can be miscategorized. Mitigated: the classifier records
  its choice and never silently miscategorizes (REQ-DU-003); a specific title/artist routes to the request
  path, else to the vibe steer. Open: tune the classifier against real submission text once observed.
- **R-D-4 — Anonymous-web identity weakens rate-limiting (Medium, policy).** The per-listener rate-limit
  relies on a per-cookie / per-session hash a determined abuser can rotate. Mitigated: the LLM review +
  moderation floor + the aggregate steer cap (REQ-DN-003) + the no-forced-airplay firewall (NFR-D-8) mean
  even rotated identities cannot seize control or bypass moderation. Open: confirm the identity key + the
  aggregate cap.
- **R-D-5 — LLM-review latency / quota (Medium, cost).** Reviewing every submission consumes subscription
  quota and adds latency off the hot path. Mitigated: the review is off the sub-1s pull path (NFR-D-1),
  fail-closed-on-safety / fail-open-on-the-stream (REQ-DU-005), and deferrable under load. Open: set a
  review budget / batching policy (cf. the deterministic moderation floor as the fast first gate).
- **R-D-6 — WCAG AA vs a vibrant palette (Low/Medium, design).** A vivid orange/peach/red palette can
  fail AA contrast. Mitigated: REQ-DZ-003 makes AA a hard gate — a failing palette choice is adjusted,
  never shipped unreadable. Open: pick AA-passing foreground/background pairs during the design phase.
- **R-D-7 — bhive had no proven pattern for this stack (Low, recorded gap).** No bhive instruction exists
  for the LLM-reviewed listener-influence + vibe-to-bounded-steer pattern. Mitigated: grounded in the
  research dossier. Action: re-run a bhive query during implementation and contribute back per AGENTS.md.

---

## 17. Out-of-Scope / Future SPEC Roadmap

- **Per-listener outcome notification** — telling a listener "your influence was applied / declined"; an
  outbound channel deferred and bounded by the no-pandering rail.
- **A staffed / human submission-screening console** — a curator UI over the submission queue; a future
  enhancement on top of the automated LLM review + moderation.
- **Authenticated listener accounts** — to strengthen rate-limiting / personalization; deferred (v1 is
  hashed, anonymous).
- **A conversational "disco mode" (multi-turn dialogue with the station)** — a richer chat surface over
  the same influence seams; the SONICRECO-061 text tower already anticipates it; deferred.
- **Aggregate (never per-submission, never appeal-optimizing) vibe-trend sensing for the director** —
  surfacing deduped accepted-vibe trends as one curatorial sensor; a future enhancement bounded by
  REQ-DL-003 / NFR-D-8 (no input binds airplay).

---

## 18. Traceability Index

1:1 REQ ↔ AC mapping (each requirement has exactly one acceptance entry in acceptance.md; detailed
Given-When-Then scenarios for the load-bearing requirements are in acceptance.md Section B).

| REQ ID | Group | Priority | EARS type | Acceptance ref |
|--------|-------|----------|-----------|----------------|
| REQ-DH-001 | Surface & Route | High | Ubiquitous | AC-DH-001 |
| REQ-DH-002 | Surface & Route | High | Ubiquitous | AC-DH-002 |
| REQ-DH-003 | Surface & Route | High | Ubiquitous | AC-DH-003 |
| REQ-DH-004 | Surface & Route | High | Ubiquitous | AC-DH-004 |
| REQ-DU-001 | Submission, Review & Moderation | High | Event | AC-DU-001 |
| REQ-DU-002 | Submission, Review & Moderation | High | Event | AC-DU-002 |
| REQ-DU-003 | Submission, Review & Moderation | Medium | Event | AC-DU-003 |
| REQ-DU-004 | Submission, Review & Moderation | High | Ubiquitous | AC-DU-004 |
| REQ-DU-005 | Submission, Review & Moderation | High | Unwanted | AC-DU-005 |
| REQ-DL-001 | Song/Artist Request Path | High | Event | AC-DL-001 |
| REQ-DL-002 | Song/Artist Request Path | High | State | AC-DL-002 |
| REQ-DL-003 | Song/Artist Request Path | High | Ubiquitous | AC-DL-003 |
| REQ-DN-001 | Vibe/Mood Steer | High | Event | AC-DN-001 |
| REQ-DN-002 | Vibe/Mood Steer | High | State | AC-DN-002 |
| REQ-DN-003 | Vibe/Mood Steer | High | Ubiquitous | AC-DN-003 |
| REQ-DN-004 | Vibe/Mood Steer | High | Ubiquitous | AC-DN-004 |
| REQ-DW-001 | The Wall | Medium | Ubiquitous | AC-DW-001 |
| REQ-DW-002 | The Wall | Medium | Ubiquitous | AC-DW-002 |
| REQ-DW-003 | The Wall | High | Ubiquitous | AC-DW-003 |
| REQ-DZ-001 | Design & Brand | Medium | Ubiquitous | AC-DZ-001 |
| REQ-DZ-002 | Design & Brand | High | Ubiquitous | AC-DZ-002 |
| REQ-DZ-003 | Design & Brand | High | Ubiquitous | AC-DZ-003 |
| REQ-DZ-004 | Design & Brand | Medium | Ubiquitous | AC-DZ-004 |
| NFR-D-1 | Non-Functional | High | Ubiquitous | AC-NFR-D-1 |
| NFR-D-2 | Non-Functional | High | Ubiquitous | AC-NFR-D-2 |
| NFR-D-3 | Non-Functional | High | Ubiquitous | AC-NFR-D-3 |
| NFR-D-4 | Non-Functional | High | Ubiquitous | AC-NFR-D-4 |
| NFR-D-5 | Non-Functional | Medium | Ubiquitous | AC-NFR-D-5 |
| NFR-D-6 | Non-Functional | High | Ubiquitous | AC-NFR-D-6 |
| NFR-D-7 | Non-Functional | Medium | Ubiquitous | AC-NFR-D-7 |
| NFR-D-8 | Non-Functional | High | Ubiquitous | AC-NFR-D-8 |

Parity: 23 REQ + 8 NFR = 31 specified items; 31 acceptance entries (23 AC + 8 AC-NFR); 1:1 REQ↔AC.

REQ-group prefixes + counts: DH (Surface & Route) = 4, DU (Submission, Review & Moderation) = 5, DL
(Song/Artist Request Path) = 3, DN (Vibe/Mood Steer) = 4, DW (The Wall) = 3, DZ (Design & Brand) = 4 →
4+5+3+4+3+4 = 23 REQ across 6 groups. NFR-D-1…8 = 8 NFR. Total = 23 + 8 = 31 specified items, 31
acceptance entries, 1:1 REQ↔AC.
