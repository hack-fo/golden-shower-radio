# SPEC-RADIO-DISCO-062 — Research & Design Rationale

Companion to `spec.md`. Records the design reasoning, the exact code seams DISCO-062 attaches to /
consumes, the sibling-SPEC relationships, and the open design questions. This is a DESIGN / PLAN artifact
(no code this pass); the seam map is a build guide for the later `/moai run`.

---

## 1. Problem framing

Golden Shower Radio is autonomous by design: an AI director mints personas, designs shows, schedules, and
decides what airs — with no human in the loop and a stream that never stops. Listener input has, until
now, been indirect (LIKE-015 hearts / drop-off; the OPS-004 feedback form) or unbuilt (REQUEST-011 song
requests). The operator wants a single, expressive, human-facing surface — "Disco Mode" — where a listener
can say what they want ("play some Khruangbin", "more late-night rainy synthwave", "something summery") and
see it influence the music, WITHOUT the listener ever seizing control of the autonomous director.

The tension this SPEC resolves: **maximal listener expressiveness on the front, zero control-surface on the
back.** The resolution is that Disco Mode introduces NO new control lever — it only composes existing SOFT
influence seams (REQUEST-011's advisory request/wishlist, SONICRECO-061's grounded retrieval, taste.py's
bounded nudges) and firewalls every submission behind an LLM review + moderation gate. The front is a
vibrant, playful "influence the music" experience; the back is a boring, bounded, discretionary set of
biases the director may honour or ignore.

## 2. The four settled design decisions (encoded, not re-litigated)

1. **NEW SPEC that COMPOSES REQUEST-011.** REQUEST-011 (draft, unbuilt) OWNS the song-request surface (the
   catalog matcher exact→normalized→fuzzy, the off-catalog wishlist→acquisition crossing with dedup +
   want-count, the moderation floor, the access-gate). DISCO-062 REUSES those for the song/artist input
   path (Group DL) and does NOT re-specify them. Because REQUEST-011 is unbuilt, Group DL degrades to the
   existing `brain/library.py` lookup + a wishlist note until it ships.
2. **Influence semantics = BOTH.** A song/artist submission → a request/wishlist signal (play-if-owned
   bias, else non-binding acquisition wish) via REQUEST-011 (Group DL). A genre/mood/vibe submission → a
   natural-language QUERY that STEERS the director's selection for a bounded window, ideally via
   SONICRECO-061's CLAP text tower → grounded retrieval (REQ-VE-005) (Group DN). Both are soft, bounded,
   time-boxed; neither is a takeover.
3. **Surface = a new `/disco` route on the EXISTING brain HTTP server.** No new container / port / service.
   New handler branches on `brain/server.py`'s stdlib `ThreadingHTTPServer`: `GET /disco` (the page),
   `POST /api/disco` (submit), `GET /api/disco/wall` (accepted feed). Vibrant, self-contained styling on
   the `brain/website.py` render seam (Group DH / DZ).
4. **AI/LLM review + moderation on EVERY submission.** Each submission is vetted by the station LLM
   (`brain/llm.py` subscription / never-raise seam) for safe / on-brand / feasible; on accept it acts and
   records a short reason; spam / abuse / off-brand is rejected. Rate-limited + access-gated; the wall
   shows only accepted, clean, anonymized suggestions (Group DU / DW).

## 3. The seam map (code the build attaches to / consumes)

Verified against the current `brain/` package on `feature/SPEC-RADIO-DISCO-062`.

### 3.1 `brain/server.py` — the HTTP surface (stdlib, no framework)

- `do_GET` dispatch, `:476`-`:506`: an `if path == ... elif ...` ladder over routes (`/api/next`,
  `/api/nowplaying`, `/status`, `/admin`, `/`, ...). **DISCO adds** `elif path == "/disco"` → a new
  `_handle_disco()` (the page) and `elif path == "/api/disco/wall"` → a new `_handle_disco_wall()` (the
  feed).
- `do_POST` dispatch, `:426`-`:451`: the same ladder for POST routes (`/api/airing`, `/api/skip`,
  `/api/like`, ...). **DISCO adds** `elif path == "/api/disco"` → a new `_handle_disco_submit()` (the
  review gate).
- Never-crash discipline, `:507`-`:513`: the `do_GET` `try/except` returns 500 (or an empty 200 for
  `/api/next`) on any handler exception. **DISCO rides this** — a Disco fault degrades without touching the
  daemon (NFR-D-2).
- The hot path, `_handle_next` `:517` / `_pick_refined` `:305` / `NextItemPicker` `:231`: the sub-1s
  Liquidsoap pull. **DISCO never calls these** — the vibe steer influences selection only via the taste /
  retrieval seams the picker already reads, never by intercepting the pull (REQ-DH-003, NFR-D-1).
- The identity + rate-limit precedent, `_handle_like_token` `:744` / `_handle_like` `:766`: mint an HMAC
  token → verify → hash identity → dedup + rate-limit → record. **DISCO reuses this shape** for the DU
  per-listener gate (REQ-DU-004).
- The site render, `_handle_root` `:795` (`self.state.website_html()`). **DISCO's `/disco` page is a
  sibling render**; the site may link to it.

### 3.2 `brain/website.py` — the render idiom + palette tokens

- `render_website(cfg)` `:14`: the whole site is an f-string emitted from the brain (no framework, no build
  step). **DISCO's `/disco` page follows the same idiom** (self-contained, inline scoped styles).
- `:root` CSS custom properties `:26`-`:30`: the existing palette is **gold-on-near-black** —
  `--gold #f5c542`, `--gold-soft #c9a23a`, `--bg #0c0a06`, `--ink #f4eddb`, `--muted #978c70`. **DISCO's
  vibrant palette (orange / peach / flamenco red / cuba libre / summery) is a warm cousin** expressed as
  its own CSS custom properties (Group DZ). See §5 for the palette-conflict flag.

### 3.3 `brain/llm.py` — the LLM review seam (subscription, never-raise)

- The subscription-auth contract: `_build_options` `:99` strips `ANTHROPIC_API_KEY` so the CLI uses the MAX
  subscription (no per-call API cost); `@MX:ANCHOR` at `:113` marks the auth contract.
- The never-raise discipline: `generate_talk_script` `:997` / the `_query_text` path — every LLM call is
  wrapped so an exception falls back to a deterministic result (e.g. `:1019` "talk is best-effort; never
  crash playout"). **DISCO's `review_disco_submission()` mirrors this exactly** — tools-off, one-turn,
  subscription-auth, never-raise; a review exception yields a conservative deterministic verdict
  (defer / reject), never a silent accept and never a crash (REQ-DU-001/005).

### 3.4 `brain/taste.py` — the vibe-steer degradation target

- `TasteProfile` `:366` (per-persona weights `"<dim>::<descriptor>" -> weight`); `relevance(track)` `:464`
  scores a track by summed matching weights (never by play-count / popularity — already anti-appeal).
- The signal machinery: `SIGNAL_LISTENER_CONTEXT = "listener_context"` `:493` (the OPS-004 listener-signal
  input kind); `_SIGNAL_DIRECTION` `:514` maps it to a small `+0.05` delta; `aggregate_delta` `:522`
  aggregates signals into weight deltas. **DISCO's vibe degradation applies a bounded, expiring
  `SIGNAL_LISTENER_CONTEXT`-style delta** over the descriptors the vibe query maps to (REQ-DN-002). This is
  the existing mechanism for "a listener context nudges taste" — DISCO reuses it, bounded + time-boxed.
- `diversity_rerank` `:711` / `related_fn` `:720`: the acquisition-side diversity layer (PROGRAMMING-007
  Group PL); NOT the airplay steer. DISCO's steer is an airplay-selection-side influence — kept distinct.

### 3.5 `brain/like.py` — the anonymized identity + rate-limit pattern

- `hash_identity(cookie_value, salt)` `:65` = `SHA256(salt + cookie)` — a privacy-preserving id, no raw
  cookie. `LikeGate` `:320` enforces per-(identity, key) dedup + rate-limit over a window; `TokenGate.mint`
  `:114` / `verify` `:129` mint + verify HMAC tokens. **DISCO reuses `hash_identity` for the rate-limit key
  and the anonymized wall** (REQ-DU-004, REQ-DW-003, NFR-D-5).

### 3.6 `brain/library.py` — the song/artist degradation target

- `normalize_key(artist, title)` `:43` → the canonical dedup slug; `track_for_key(key)` `:588` resolves an
  owned track; `keys()` `:602` lists the catalog. **DISCO's song/artist degradation** resolves a submission
  via `normalize_key` → `track_for_key` (play-if-owned bias) + a simple wishlist note on a miss
  (REQ-DL-002). `legal_candidates` `:606` / `pick_next` `:636` are the picker's hard-rail-filtered
  candidate source the vibe steer re-weights WITHIN (REQ-DN-004).

### 3.7 The consumed sibling seams (GREENFIELD)

- **REQUEST-011 (draft, unbuilt):** Group RM (tiered catalog matcher + typeahead), Group RWL (off-catalog
  wishlist + acquisition crossing under OPS-004 REQ-OH-007), Group RS (request-endpoint anti-abuse +
  access-gate, reusing the CALLIN-003 moderation floor). DISCO Group DL routes into RM/RWL and reuses RS's
  access-gate. Degrades to §3.6 until built.
- **SONICRECO-061 (draft, unbuilt):** REQ-VE-005 (text→audio KNN via the CLAP text tower — "late-night
  rainy synthwave" → real catalog tracks in the shared embedding space), Group GD (the ID-grounding
  firewall — HARD-reject any out-of-set ID), Group RK (constrained-ID LLM re-rank). SONICRECO REQ-VE-005
  ALREADY names a future "disco mode" surface as its intended consumer — the composition is mutually
  consistent by construction. DISCO Group DN hands its vibe query to REQ-VE-005 to shape the candidate
  pool. Degrades to §3.4 until built.

## 4. Why this shape (design rationale)

- **Compose, don't build a second engine.** A song/artist request is exactly REQUEST-011's problem
  (matching + wishlist + acquisition); a vibe query is exactly SONICRECO-061's problem (text→audio grounded
  retrieval). Re-implementing either in DISCO would fork two future engines and violate single-source-of-
  truth (NFR-D-4). DISCO is a SURFACE + a REVIEW GATE over those seams — nothing more.
- **The review gate is the whole safety story.** Free-text listener input is the highest-risk surface on
  the station (prompt injection, abuse, spam, off-brand). Routing every submission through an LLM review +
  the reused CALLIN-003 fail-closed moderation floor + rate-limit + access-gate, and showing only accepted
  clean items on the wall, means the expressive front never becomes an attack surface. The fail-closed-on-
  safety / fail-open-on-the-stream rule (REQ-DU-005) resolves the review-vs-continuity tension the same way
  the rest of the station does (best-effort LLM, deterministic floor, never silence).
- **Soft + bounded + time-boxed = the control firewall.** The single most important property is that no
  Disco input is a control lever. The song/artist path inherits REQUEST-011's capped/decayed/deduped
  advisory weight; the vibe path is a bounded, auto-expiring re-weight WITHIN the already-legal candidate
  set. A no-repeat-blocked track stays blocked; a popularity signal is never optimized; the director may
  ignore any steer. This mirrors the anti-gaming spine REQUEST-011 and LIKE-015 already established, and
  the within-legal-candidate-set safety argument LIVEMIX-060 uses for its density cap.
- **Brain-only stdlib, off the hot path.** Adding a web framework or a service would contradict the
  station's brain-only posture (NFR-D-3) and risk the sub-1s pull path. New handler branches on the
  existing `ThreadingHTTPServer`, riding the existing never-crash `try/except`, keep the surface additive
  and the stream sacrosanct.
- **Degrade, don't block on unbuilt deps.** Both composed SPECs are drafts. Rather than block DISCO on
  them, each path degrades to an existing brain seam (library lookup / taste nudge) so DISCO is
  independently valuable now and upgrades in place at the sibling seams later (NFR-D-7). This is the same
  "greenfield dependency, degrade until it ships" pattern REQUEST-011 uses for PROGRAMMING-007 REQ-PL-004.

## 5. Brand / palette reconciliation (FLAG for the operator)

The design constitution (`.claude/rules/moai/design/constitution.md` §3.1) makes brand context a
constitutional constraint: the design MUST load and adhere to `.moai/project/brand/` (brand-voice.md,
visual-identity.md, target-audience.md), and brand wins on conflict (§3.3).

**Finding:** at authoring time (2026-07-02) all three brand-context files are UNPOPULATED `_TBD_`
placeholders — the brand interview (`/moai design`) has never been run. There is therefore no populated
visual-identity.md to conflict with, so:

- The operator's Disco palette (orange / peach / flamenco red / cuba libre / summery) is the ONLY concrete
  brand direction available and is adopted as the PROVISIONAL brand direction for this surface (REQ-DZ-001).
- It DIVERGES from the live site's actual palette — gold-on-near-black (`--gold #f5c542` / `--bg #0c0a06`,
  `brain/website.py:26`-`30`). This is an intra-station accent divergence: Disco is a warm, vibrant cousin
  of the gold-on-dark house style, not a contradiction of a populated brand.
- [FLAG] Per REQ-DZ-002, once the brand interview populates visual-identity.md, any conflict between the
  operator palette and the populated brand MUST be reconciled — brand wins on conflict, or the conflict is
  flagged. **Recommended operator action:** either run `/moai design` to ratify a station palette (so Disco
  inherits it), or explicitly accept the operator palette as the surface's brand direction. Recorded as
  R-D-1.

**WCAG note:** a vivid orange/peach/red palette risks failing AA contrast. REQ-DZ-003 makes WCAG 2.1 AA a
HARD gate (>= 4.5:1 normal text, >= 3:1 large text / UI; full keyboard; ARIA on the input + live wall
region). The design phase must pick AA-passing foreground/background pairs; a failing choice is adjusted,
never shipped unreadable (R-D-6).

## 6. Group / prefix collision check

The operator suggested prefixes DS / DV / DW / DX / DZ. A corpus scan (`grep -rhoE "REQ-D[A-Z]-[0-9]+"
.moai/specs/`) found the following D-family prefixes ALREADY IN USE: DC, DE, DF, DG, DI, DK, DM, DO, DP,
DQ, DR, DS, DV, DX (owned by DATASTORE-022 [DR/DX/...], DEDUP-014 [DV], AIDECISION-037 [DS], LIVEMIX-060
[DV], and others). Of the operator's suggestions, DS / DV / DX COLLIDE; only DW / DZ are free.

**Remapped to a collision-free set:** DH (surface & route), DU (submission, review & moderation), DL
(song/artist request path), DN (vibe/mood steer — the bounded nudge), DW (the wall), DZ (design & brand).
All six are absent from the used-prefix set. Verified free at authoring time.

## 7. Open design questions (for the annotation cycle / build)

- **Q1 — Vibe classification boundary.** How to disambiguate "Sade" (artist) vs "smooth" (vibe) vs
  "Khruangbin vibes" (both)? Proposal: a specific title/artist match routes to DL, else DN; the classifier
  is LLM-assisted with a heuristic fast path; it records its choice and never silently miscategorizes
  (REQ-DU-003, R-D-3).
- **Q2 — Steer aggregation.** When many listeners submit vibes at once, how are concurrent steers combined
  without collectively hijacking the director? Proposal: an aggregate cap on total steer magnitude + a
  per-steer window; the director always retains downweight/ignore authority (REQ-DN-003, R-D-4).
- **Q3 — Review budget.** Reviewing every submission consumes subscription quota. Proposal: the
  deterministic moderation floor is the fast first gate; the LLM review is off the hot path, deferrable,
  and possibly batched; set a review budget policy (R-D-5).
- **Q4 — Access-gate default.** Is Disco Mode on by default, and what is the access-gate (open / token /
  config flag)? Deferred to the operator (Section 14 prerequisite).
- **Q5 — Wall freshness vs privacy.** How long do accepted suggestions drift on the wall, and at what
  timestamp granularity (coarse, to avoid correlation with identity)? Config, bounded by REQ-DW-002/003.

## 8. bhive memory seam

bhive (AGENTS.md protocol) has no proven pattern for the LLM-reviewed listener-influence surface, nor for
the vibe-query→bounded-taste-steer / vibe-query→CLAP-text-tower-retrieval→time-boxed-candidate-pool-steer
patterns on this Go + Python + Liquidsoap + slskd stack (recorded gap). Re-run a bhive query during
implementation on: (a) LLM-moderated free-text listener input → soft bounded influence, and (b) natural-
language vibe → embedding-space retrieval → bounded airplay steer; contribute the verified approach back.

## 9. Status

DESIGN / PLAN SPEC, status draft. No code this pass. The actual frontend build + the handler / module
implementation is a later `/moai run` + design-phase concern. This document + `spec.md` + `acceptance.md`
define the requirements and the design brief only.
