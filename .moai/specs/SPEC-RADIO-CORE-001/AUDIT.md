# AUDIT — SPEC-RADIO-CORE-001 (Autonomous AI Radio Station, v1 Core)

Auditor: plan-auditor (adversarial, independent). Reasoning context from the
SPEC author ignored per M1 Context Isolation. Audited: spec.md (v0.4.0),
acceptance.md (v0.3.0). No AUDIT.md pre-existed.

## Verdict: SHIP-WITH-FIXES

Strong SPEC: EARS compliance is clean (no hard violations across 52 REQs + 6
NFRs) and REQ→AC parity is a clean 1:1 (52 REQ : 52 AC). However there are real
internal contradictions (stale Exclusions/Roadmap vs the now-in-scope concrete
ingestion reqs) and one significant consistency/feasibility red flag (the
`[HARD]` Go mandate vs the actually-live Python brain). These need resolution
before/at Run, but none is a catastrophic blocker.

## Resolution Status (all must-fixes APPLIED)

- 2026-06-23 (DDD characterization slice): All four must-fixes are RESOLVED in
  spec.md v0.4.1 + acceptance.md v0.4.1. Verified against the current text:
  - MF-1 — §12 stale "concrete Spotify/YouTube OAuth ingestion EXCLUDED" bullet
    removed; §12 now excludes ONLY YouTube watch history (impossible via Data API
    v3), matching §3.2. DONE.
  - MF-2 — §14 SPEC-RADIO-INGEST narrowed to "future expansion of ingestion
    sources beyond Spotify saved + YouTube liked." DONE.
  - MF-3 — §4 + §1.4 reconciled to the live PYTHON brain (`brain/`,
    `Dockerfile.brain`, `radio.liq → brain:8080/api/next`); the `internal/` +
    `cmd/radiod/` Go tree is marked DEPRECATED/SUPERSEDED; the `[HARD]` Go
    language mandate is removed (implementation language is no longer a [HARD]
    constraint). DONE.
  - MF-4 — acceptance.md bumped to v0.4.1 with a Changelog entry recording the
    AC-B-012 sync; AC-B-012 present and 1:1 with REQ-B-012. DONE.
  No further spec edits required by this slice. Nits (NFR→AC references, personal
  default identifiers) left as-is — out of scope for the characterization slice.

---

## Must-Fixes (with REQ IDs + concrete fix)

### MF-1 (major) — Exclusions §12 contradicts in-scope REQ-A-004a/REQ-A-004b
spec.md §12 (lines 1298–1299) still lists as EXCLUDED:
> "Concrete Spotify/YouTube OAuth+API wishlist ingestion (v1 consumes an
> abstract provided wishlist source; the concrete integration is a future SPEC)."

But v0.3.0 added REQ-A-004a (Spotify `/v1/me/tracks` OAuth ingestion),
REQ-A-004b (YouTube `myRating=like` OAuth ingestion), REQ-A-011, and REQ-F-008
(guided one-time OAuth) — concrete Spotify/YouTube OAuth+API ingestion IS now
v1 scope. §3.2 (lines 381–383) was correctly updated ("v1 DOES include concrete
Spotify + YouTube seed ingestion") but §12 was not. Direct in-scope/out-of-scope
contradiction.
**Fix:** Delete or rewrite the §12 bullet so it excludes ONLY YouTube watch
history (impossible via Data API v3), matching §3.2. Concrete liked/saved-track
OAuth ingestion is in scope.

### MF-2 (major) — Roadmap §14 "SPEC-RADIO-INGEST" is stale (same root cause)
spec.md §14 (line 1372): "SPEC-RADIO-INGEST — concrete Spotify/YouTube wishlist
ingestion." That work is now delivered in v1 (REQ-A-004a/b, REQ-A-011,
REQ-F-008), not deferred.
**Fix:** Remove the SPEC-RADIO-INGEST roadmap line (or narrow it to "future
expansion of ingestion sources beyond Spotify saved + YouTube liked"). Fold with
MF-1; both stem from §3.2 being updated at v0.3.0 while §12/§14 were not.

### MF-3 (major) — `[HARD]` Go daemon mandate contradicts the live Python brain
spec.md §4 (line 389) `[HARD] Language/runtime: Go, implemented as a long-lived
daemon` and §1.4 ("Go daemon (the brain)") mandate Go. The actually-live stack is
Python: `deploy/config/radio.liq` calls `http://brain:8080/api/next`,
`deploy/Dockerfile.brain` builds the Python brain, and `brain/*.py`
(main.py, director.py, llm.py, library.py, …) is the implemented system. A Go
tree exists under `internal/` + `cmd/radiod/` but is not wired into the live
Liquidsoap config and appears superseded.
**Fix:** Reconcile the constraint with reality — change §4/§1.4 to "Python
long-lived daemon" (matching `brain/`), or explicitly document that `internal/`
Go is deprecated and removed. Leaving a `[HARD]` Go mandate while shipping a
Python brain will mislead Run-phase implementers and any future auditor.

### MF-4 (minor) — acceptance.md version header drifts from its content
acceptance.md frontmatter `version: 0.3.0`, but it already contains AC-B-012
(lines 208–225), which corresponds to REQ-B-012 added in spec.md v0.4.0.
acceptance.md has no HISTORY/changelog recording the AC-B-012 addition.
**Fix:** Bump acceptance.md to `version: 0.4.0` and add a one-line changelog
note for AC-B-012, keeping it lock-stepped with spec.md.

---

## EARS Findings

EARS compliance is GOOD. All 52 REQs and 6 NFRs map to a valid EARS pattern; no
hard violations. Minor stylistic nits only:

- REQ-E-005 (line 1106): "The **site** shall display…" uses "the site" as the
  subject rather than "the system". Acceptable entity phrasing; nit.
- REQ-D-007 (line 1014, Unwanted): compound — first sentence is Ubiquitous
  ("The LLM decision loop shall run asynchronously…") then Unwanted ("If … slow,
  errored…, then the system shall fall back…"). Traceability labels it Unwanted
  only. The testable safety clause is well-formed Unwanted; nit.
- REQ-A-003 (line 450, Ubiquitous): embeds a conditional "…and shall refuse to
  start acquisition if it is unset, empty, or not writable." Compound
  Ubiquitous+Unwanted; acceptable, nit.
- REQ-A-008 / REQ-F-005: negative-ubiquitous "The system shall not … if …"
  phrasing for Unwanted. Acceptable inverted Unwanted; nit.

No EARS must-fix.

---

## Parity Findings (REQ ↔ AC)

**1:1 clean — no genuine coverage gap.** Counts:
- REQs: A=14, B=12, C=4, D=8, E=6, F=8 → **52 functional REQs**; plus NFR-1..6.
- ACs (acceptance.md): A=14, B=12, C=4, D=8, E=6, F=8 → **52 ACs**. Every REQ-x
  has exactly one AC-x with the same id.

The "raw grep showed REQ far exceeds distinct AC-id count" alarm is a FALSE
POSITIVE: spec.md embeds inline "Acceptance criteria:" bullets under each REQ and
cross-references many REQ IDs in HISTORY/§15, inflating a naive `REQ-` grep over
spec.md, while AC ids live only in acceptance.md. Distinct AC ids (52) == REQ
count (52). No REQ has zero acceptance coverage.

NFR coverage note (minor): NFR-1..6 have no dedicated AC-NFR-* ids; they are
covered indirectly via the Quality Gate section (NFR-3 cited explicitly) and the
Definition of Done (NFR-1/2/6) plus AC-C-003/AC-F-002/AC-F-004/AC-F-005. Testable,
but consider adding explicit NFR→AC references for traceability.

---

## Boundary / Single-Source-of-Truth Notes

Largely clean against siblings (ANALYSIS-006, KNOWLEDGE-008, TAGSTREAM-009,
VOICE-002):

- **ANALYSIS-006 (BPM/key/energy/cues):** REQ-A-007 extracts only container/ID3
  metadata (artist/title/album/duration); REQ-B-006 rotation uses artist/title
  spacing. No computed-audio-feature claim. No overlap. Clean.
- **KNOWLEDGE-008 (editorial facts/consensus):** CORE-001 deliberately
  under-constrains curation (Creative Autonomy §1.3) and has no fact/knowledge
  requirement. No overlap. Clean.
- **VOICE-002 (TTS):** TTS explicitly out of scope (§3.2/§12). REQ-F-007/REQ-F-008
  + AC-F-007 forward-reference "the TTS runtime once the deferred VOICE SPEC
  lands" — a guarded seam, not a duplication. Acceptable.
- **TAGSTREAM-009 (tag/artwork WRITES + stream/site exposure):** SEAM TO WATCH.
  CORE-001 REQ-E-005/REQ-C-001 own a foundational now-playing/site display and
  the Icecast stream. CORE-001 does NOT claim writing ICY/stream-title metadata
  or artwork, so there is no hard duplication — but ownership of "now-playing
  exposure on the stream/site" should be confirmed so TAGSTREAM-009 EXTENDS
  rather than re-owns it. Note, not a must-fix.

---

## DATA-vs-CODE Rail

Respected. All CORE-001 self-modification targets DATA stores, not source
code/critical runtime config:
- REQ-B-003 (schedule), REQ-B-009 (persona creation), REQ-B-010 (persist),
  REQ-B-012 (assign/reassign) → system-owned roster/schedule STORE (data). OK.
- REQ-E-001..004 self-controlled website edits GENERATED HTML/CSS content (an
  output artifact, not the brain's source code or runtime config) and is heavily
  guarded (sandbox → validation → atomic publish → auto-rollback). Rail holds.
- REQ-F-007 "validate and auto-create configuration where possible" is
  bootstrap-time provisioning, not editing critical runtime config during normal
  ops. Borderline but acceptable; keep it bootstrap-scoped.

---

## Feasibility / Over-Engineering

- **LLM cost/latency (acknowledged):** REQ-D-006 continuous self-initiated
  curation across multiple personas 24/7 on a Claude Max subscription (no paid
  streaming API) is a real cost/rate-limit risk. Mitigated by async loop +
  deterministic fallback (REQ-D-007) and flagged in R4. The "LLM provider"
  abstraction (REQ-F-003) should encode the real constraint (Claude Max, no paid
  API) so Run does not assume a metered API budget. Nit.
- **GPU:** CORE-001 has no TTS/Whisper/analysis in scope, so the un-plumbed RTX
  2000 Ada is irrelevant to v1 core — correctly NOT a dependency. Good.
- **slskd:** config-gated off by default (REQ-A-001a), consistent with the
  current "slskd disabled" operating state. Good.
- No zero-gap-failover gold-plating: §1.2 + NFR-6 explicitly forbid
  over-engineering HA; brief restart silence is accepted (R7). Good.

---

## Nits

- REQ-A-011 hardcodes personal defaults (`tritnaha`, `@tritnaha1345`) in the SPEC
  body; fine as overridable config reference, minor privacy/cleanliness nit.
- acceptance.md DoD (line 451) references "Milestones M1–M7 (plan.md)" — verify
  plan.md still defines exactly M1–M7.
- Consider explicit NFR→AC references (see Parity Findings).

---

## Self-Verification (Chain-of-Verification)

Re-read all 52 REQ entries end-to-end (not sampled); confirmed EARS pattern per
REQ and 1:1 AC presence per REQ. Re-checked §3.2 vs §12 vs §14 for the
ingestion-scope contradiction (confirmed §12/§14 stale). Verified live stack via
`deploy/config/radio.liq` (calls Python `brain:8080`), `deploy/Dockerfile.brain`,
and `brain/*.py` vs the unused `internal/` Go tree — confirming MF-3. No
additional defects surfaced on second pass.
