# SPEC-RADIO-INTERVIEW-CRAFT-034 — Research

Learning Music-Journalist Talk & Interview CRAFT from Transcribed Human Interviews (Style Corpus, Never a
Fact Source). PLAN-phase research artifact. This document records the gap, the mechanic, the integration map,
the load-bearing style-not-fact discipline, the sibling relationship to DJ-craft learning, and — critically —
the exhaustive REQ-prefix collision verification.

---

## 1. The problem this SPEC names (the gap)

The station's hosts already have deep, persistent identities — a per-persona taste charter (PROGRAMMING-007
REQ-PR-006), a frozen anchor (REQ-PI-001), an evolving taste profile (REQ-PL-004), a persistent POV
(REQ-PR-005), a grounded host voice with a named MUSIC-JOURNALIST banter thread (Group PV), richer grounded
talk (HOSTCTX-016), and a lived life between shows (HOSTLIFE-032). They are even learning HOW TO MIX from real
human DJs (PROGRAMMING-007 Group CL, v0.9.0, consuming the SHOWS-020 Group SK human-DJ session feed).

What they do NOT yet have is the learned CRAFT of TALK and INTERVIEW. A great music host talks like someone
who has listened to thousands of interviews — Audiotree, KEXP, Nardwuar — and absorbed the technique: the
question TYPES, the openings, the segues, the rapport/banter, the pacing, the way a journalist frames an
artist or a record. Today the hosts' talk is grounded and anti-slop, but the TECHNIQUE of journalism is not
learned from real practitioners; it is whatever the talk-script prompt produces.

The gap is precise: there is no pipeline that (a) ingests a bounded, curated set of human interviews, (b)
transcribes them, (c) extracts GENERALIZED interviewing/talk technique into a style corpus, and (d) applies
that craft to the host talk so the hosts ask better questions and talk with an authentic journalist register —
WITHOUT importing the un-grounded facts heard in those interviews.

INTERVIEW-CRAFT-034 closes this gap by INTEGRATING layers that already exist or are specced: the HOSTCTX-016
talk seam (the apply target), host-voice-grounding + tts-naturalization (the register + delivery),
INTEGRITY-033 (the trust governance that keeps style separate from fact), MEMORY-031 (the corpus substrate),
PROGRAMMING-007 PR/PI/PV/PG (the persona/voice/gate) + Group CL (the sibling DJ-craft loop), KNOWLEDGE-008
(the SOLE airable-fact seam), and the GPU Whisper-STT substrate (the transcription). It OWNS the talk-craft
pipeline; it re-owns NONE of those layers.

---

## 2. The mechanic — learning talk craft from transcribed human interviews

The pipeline, bounded and off the air path:

```
   [curated source roster: Audiotree / KEXP / Nardwuar — capped, not a bulk scrape]
        |
        |  (1) INGEST + TRANSCRIBE (Group IN) ────────────────────────────────┐
        |       download a capped set per source per batch (dedup against      │
        |       already-transcribed) → Whisper-STT on the RTX 2000 Ada GPU     │
        |       (DETERMINISTIC, not an LLM) → store transcript w/ provenance,   │
        |       tagged TIER-4 HUMAN CONTENT FOR STYLE ONLY                      │
        |                                                                       │
        |  (2) EXTRACT CRAFT (Group IC) ─────────────────────────────────────┤
        |       ONE bounded LLM distillation pass → GENERALIZED technique:     │
        |       question types / openings / segues / rapport / pacing /        │
        |       artist-framing → PATTERNS + anonymized EXEMPLARS.              │
        |       DROP every fact + every verbatim line. Tag each pattern with   │
        |       its STYLE FAMILY. Write THROUGH the INTEGRITY-033 single        │
        |       governance write-path (cardinal rule + auto-promotion ban).    │
        |                                                                       ▼
        |                                                         technique corpus (PROCEDURAL/STYLE memory)
        |                                                                       │
        |  (3) APPLY TO HOST VOICE (Group IV) ───────────────────────────────┤
        |       feed relevant patterns INTO the existing HOSTCTX-016           │
        |       `_build_context` seam → the talk-script LLM composes           │
        |       questions/openings/segues with LEARNED technique in the        │
        |       persona's register; per-persona STYLE LEAN under the           │
        |       unchanged anti-convergence firewall; route through the         │
        |       UNCHANGED PG grounding gate.                                    │
        |                                                                       ▼
        |  (4) STYLE-NOT-FACT GUARD (Group ID) — across all stages ───────────►  every external fact still
        |       a transcript teaches HOW, never WHAT is true; a transcript        grounded; no transcript fact
        |       fact airs ONLY via independent KNOWLEDGE-008 grounding             aired without independent
        |                                                                          KNOWLEDGE-008 grounding
```

**Worked example (the north star).** The station ingests a small, curated set of Audiotree / KEXP / Nardwuar
interviews and transcribes them on the GPU. The distillation extracts patterns like "opens with a specific,
researched detail about the artist's early work" (Nardwuar deep-research family) and "warm, open-ended
follow-up that invites a story" (KEXP conversational family) — TECHNIQUE only, no facts, no copied lines. A
deep-research-leaning persona's talk is enriched with those patterns: it now opens a break with a researched
detail and asks an open-ended follow-up, in ITS OWN register. But when it states an external fact (a year, an
album, a credit), that fact still passes the UNCHANGED PG grounding gate and traces to a grounded source — and
a "fact" it merely heard in a transcript is NOT aired unless independently corroborated through KNOWLEDGE-008.
The host talks like a journalist; nothing un-grounded is aired.

---

## 3. The integration map — what INTERVIEW-CRAFT consumes (and never re-owns)

Each seam below is REFERENCED by number; INTERVIEW-CRAFT owns only the pipeline that strings them together.

| Need | Owned by (referenced, not re-owned) | INTERVIEW-CRAFT's contribution |
|------|--------------------------------------|--------------------------------|
| The talk seam the craft feeds INTO | **HOSTCTX-016** (`brain/talk.py` `_build_context`, Group HW) | Feeds technique patterns INTO `_build_context` (Group IV); does not fork the talk generator or add a talk gate. |
| The register + the boundary on WHAT is said | **host-voice-grounding** (fact contract / anti-slop / never-confidently-wrong) | Enriches HOW the host talks (register); grounding stays the boundary on WHAT it says (Group ID/IV). |
| The delivery / pacing | **tts-naturalization** (chunk + ffmpeg-silence pacing, ear-writing rails) + **VOICE-002** | The learned PACING informs the ear-written script (REQ-IV-004); the TTS engine is unchanged. |
| The trust governance (style ≠ fact) | **INTEGRITY-033** (Group TT six trust tiers; REQ-AL-001 cardinal anti-loop; REQ-KP-002 auto-promotion ban; REQ-KV-005 demote/promote asymmetry; REQ-IT-006 single write-path; Group SU source-admission) | A transcript = tier-4 style-only; the corpus is written THROUGH the single write-path; new sources earn their place (Group ID). |
| The corpus substrate | **MEMORY-031** (four-layer memory — Procedural / Knowledge layers) | Writes the technique corpus as governed procedural/style memory (REQ-IC-003); the substrate/keying/cascade are MEMORY-031's. |
| The persona / voice / firewall / gate | **PROGRAMMING-007** Groups PR (firewall REQ-PR-004, POV REQ-PR-005, charter REQ-PR-006), PI (anchor REQ-PI-001, guard/canary REQ-PI-003/004, news-anchor-excluded REQ-PI-005), PV (REQ-PV-001 identity-awareness, REQ-PV-005 register spine, REQ-PV-006 anti-slop bans, REQ-PV-009 voice card, the MUSIC-JOURNALIST banter thread), PG (REQ-PG-005 gate, REQ-PG-008 quote-sourcing) | Feeds craft into the voice under the unchanged firewall + gate; a per-persona style lean; re-owns none. |
| The SIBLING learning loop | **PROGRAMMING-007 Group CL** (per-persona DJ-craft: observe → extract → distill → apply → measure → bounded-update, consuming SHOWS-020 Group SK human-DJ clusters) | INTERVIEW-CRAFT is the TALK/INTERVIEW sibling of the mixing-craft loop; same shape, different subject; referenced, not re-owned. |
| The SOLE airable-fact seam | **KNOWLEDGE-008** (REQ-KS-006 airable-fact contract + consensus/freshness gates + REQ-KS-009 reliability tiers) | A transcript fact reaches air ONLY via independent KNOWLEDGE-008 grounding (REQ-ID-002); never bypassed. |
| The transcription substrate | **GPU Whisper-STT (RTX 2000 Ada)** — shared inference resource (also TTS / analysis) | Deterministic transcription (REQ-IN-003); does not own GPU/Docker plumbing or the STT model lifecycle. |

**A note on the unbuilt/in-flight seams.** INTEGRITY-033 (the governance write-path REQ-IT-006, the SU
source-admission lane) and the GPU/STT plumbing (the RTX 2000 Ada is not yet plumbed into Docker, per project
memory) are SPEC'd / pending. INTERVIEW-CRAFT is their CONSUMER: it specifies the contracts it needs (a corpus
write through the governance write-path; a deterministic transcription on the GPU; a source admitted through
SU) and degrades gracefully — with no GPU/STT, transcription is skipped, the corpus does not grow, and the
hosts use the existing talk model (the golden rule). It builds against the contracts and improves as they land.

---

## 4. The load-bearing discipline — style corpus, not a fact source

A host that has "listened to a thousand interviews" is the single highest-risk place for fact contamination: a
transcribed interview is rich human SPEECH (great for STYLE) but it is unverified — full of claims, anecdotes,
and approximate "facts" the speaker may have gotten wrong. The whole feature is only acceptable if the host
absorbs the CRAFT without absorbing the un-grounded claims. The discipline is exactly INTEGRITY-033's contract
applied to transcripts:

1. **Tier-4 style-only admission.** A transcript is INTEGRITY-033 tier-4 human content (REQ-IN-004), admitted
   for STYLE; its factual content is hypothesis-grade at most and carries no authority (REQ-ID-001). This is
   the project's own trust-tier scale, not a new invention.

2. **Drop all facts + all verbatim lines at extraction.** The distillation captures TECHNIQUE (structure,
   register, question shape) and drops, at extraction time, every factual claim and every verbatim line
   (REQ-IC-002). A pattern reads "opens with a researched early-career detail" — NOT the actual sentence a
   named host said, and NOT the fact that sentence asserted.

3. **No fact-import without grounding (cardinal anti-loop + auto-promotion ban).** A style-derived memory
   whose evidence chain does not trace to a non-AI grounding tier within the cardinal K-hop budget is
   QUARANTINED (INTEGRITY-033 REQ-AL-001 — the CARDINAL trap), and a transcript-sourced fact is NEVER
   auto-promoted (REQ-KP-002). The corpus write rides the single governance write-path (REQ-IT-006), which
   enforces both at the chokepoint. The demote/promote ASYMMETRY (REQ-KV-005) holds: distilling/critiquing a
   transcript may only DEMOTE/flag; only independent non-AI grounding may PROMOTE a fact.

4. **Air only via independent KNOWLEDGE-008 grounding.** A claim present only in a transcript reaches air as
   fact ONLY if independently grounded via the KNOWLEDGE-008 consensus seam (REQ-KS-006 the SOLE airable-fact
   contract + its consensus/freshness gates) — never on the transcript's word alone (REQ-ID-002). The enriched
   talk routes through the UNCHANGED PG gate (REQ-IV-006), so any external fact is gated exactly as any other
   talk's fact is.

This is INTEGRITY-033's central insight (AI/unverified output is a HYPOTHESIS, never its own evidence) applied
to a specific contamination vector — transcribed human interviews — and it is the reason the feature is safe.
It is the SPEC's load-bearing property (NFR-IC-2). Note the parallel to the sibling Group CL DJ-craft loop:
there too, a human-DJ session is "PURELY research input (no source sequence is ever air-played)"; here, a human
interview is purely STYLE input (no source fact is ever aired un-grounded).

---

## 5. The copyright / ethics discipline — no verbatim mimicry, no impersonation

Two further boundaries, distinct from the fact guard:

- **No verbatim mimicry.** The corpus learns GENERALIZED technique; it never stores a specific human's verbatim
  lines, and the host never reproduces a human's lines on air (REQ-IC-005, REQ-ID-007). The corpus is internal
  and distilled into patterns + anonymized structure-describing exemplars, never a republished transcript.
- **No impersonation.** The host learns the CRAFT of music journalism and speaks in ITS OWN persona voice
  (REQ-PV-009 / REQ-PI-001); it never claims to be (or is presented as) a named journalist (REQ-ID-004). This
  rides PROGRAMMING-007 REQ-PV-001 (the host is honest about being itself, never breaking the fourth wall).

These are a copyright + ethics NFR (NFR-IC-5), enforced at the corpus write (anonymized patterns) and at the
surface (transcripts + corpus are internal-only, REQ-ID-007).

---

## 6. House-rule alignment

- **Golden rule (never-stop).** The whole pipeline runs in the BACKGROUND, off the `<1s /api/next` path,
  exception-isolated; a failure (download, GPU/STT unavailable, distillation, write) logs and skips; the hosts
  fall back to the existing talk model; an empty corpus is valid. (NFR-IC-1/8; inherits CORE-001.)
- **Style corpus, not a fact source (LOAD-BEARING).** Section 4. A transcript teaches HOW, never WHAT is true;
  no transcript fact airs without independent KNOWLEDGE-008 grounding. (NFR-IC-2.)
- **Deterministic-first / quota-aware.** Transcription is deterministic Whisper-STT on the GPU (no LLM); the
  LLM runs only for the bounded per-batch distillation + the existing talk pass; per-source/per-batch caps;
  dedup. Finite `~/.claude` quota respected. (NFR-IC-3.)
- **Anti-slop enrichment; grounding stays the boundary.** The learned craft enriches the anti-slop register
  (host-voice-grounding + REQ-PV-006 + tts-naturalization) and never weakens grounding (the unchanged PG gate
  still gates every external fact). (NFR-IC-4.)
- **Copyright / no-verbatim / no-impersonation.** Section 5. Generalized patterns + anonymized exemplars;
  internal-only corpus; never republished; no named-journalist impersonation. (NFR-IC-5.)
- **Anti-convergence preserved.** A per-persona style lean develops talk WITHIN its identity through the
  unchanged firewall + distinctness canary; styles never converge. (NFR-IC-6.)
- **Reference, don't re-own; brain-only, additive.** Section 3. Every seam referenced by number; a `brain/`
  ingest+extract+apply pipeline; no new service, no Liquidsoap change, no listener surface. (NFR-IC-7.)
- **GPU dependency degrade-safe; full autonomy.** No human input in the loop (operator provides hardware +
  caps + roster); GPU/STT unavailable → degrade-safe. (NFR-IC-8.)

---

## 7. REQ-prefix collision verification (exhaustive — house [HARD] requirement)

Per the SPEC-builder collision discipline, every chosen REQ-group prefix MUST resolve to zero other specs. The
verification was exhaustive across every `spec.md` in `.moai/specs/`.

### 7.1 The full taken-prefix enumeration (extracted, not assumed)

Extracted via `grep -rhoE 'REQ-[A-Z]{2,3}-[0-9]'` across all specs, deduplicated:

```
AC AD AE AF AG AK AL AM AP AS AT AW CC CD CF CG CL CM CN CS CT DC DE DF DG DK DM DO DP DR DV DX EC EG EI EX
FC FD FF FM FR FS FX HC HD HE HF HG HL HN HT HW HY IB IG IH IL IP IS IT IX KF KG KI KP KR KS KV LA LB LC LD
LE LF LG LH LK LL LM LN LP LQ LR LS LT LX MA MB MC MD ME MF MK ML MM MP MR MS MT MV MX OA OB OC OD OE OF OG
OH OX OY PC PG PI PL PR PS PT PV QC QO QP QR QT QW RA RC RD RE RF RH RI RL RM RN RQ RS RV RW RWL SA SB SC SD
SE SF SG SI SK SL SM SO SP SR SS SU SV SW SX TA TT TW TX VB VC VG VK VR WA WP WS WV
```

NFR prefixes taken (via `grep -rhoE 'NFR-[A-Z]{1,3}-[0-9]'`):

```
A AA C D E F H HL I IT K L M O P Q R RF S T V W
```

### 7.2 The chosen prefixes and why each is collision-free

| Group | Prefix | Mnemonic | In taken REQ set? | Verification |
|-------|--------|----------|-------------------|--------------|
| Ingest + Transcription | **IN** | INgest | NO | `grep -rohE 'REQ-IN-[0-9]'` → 0 hits |
| Craft Extraction | **IC** | Interview Craft | NO | `grep -rohE 'REQ-IC-[0-9]'` → 0 hits |
| Apply-to-Host-Voice | **IV** | Interview Voice (apply) | NO (only IB/IG/IH/IL/IP/IS/IT/IX of the I-family are taken — all IMAGING-010 / INTEGRITY-033) | `grep -rohE 'REQ-IV-[0-9]'` → 0 hits |
| Interview Discipline (style-not-fact guard) | **ID** | Interview Discipline | NO | `grep -rohE 'REQ-ID-[0-9]'` → 0 hits |

NFR family: **NFR-IC** (reusing the IC group letter — the house pattern, exactly as HOSTLIFE reused NFR-HL and
INTEGRITY reused NFR-IT). `grep -rohE 'NFR-IC-[0-9]'` → 0 hits. The taken NFR set has the single-letter `I`
(IMAGING-010 NFR-I-n) but NOT the two-letter `IC`, so NFR-IC is collision-free.

### 7.3 Remaps / collisions considered and rejected

- **`IT`** (a natural "InTerview" mnemonic) is TAKEN — it is INTEGRITY-033's primary REQ group + its NFR
  family (NFR-IT). Rejected; would collide head-on with the very SPEC this one most depends on. Remapped the
  interview-discipline group to **ID** (Interview Discipline) instead.
- **`IS` / `IG` / `IL` / `IP` / `IB` / `IH` / `IX`** (other I-family ideas) are all TAKEN by IMAGING-010.
  Rejected.
- **`TT`** (a "Talk Technique" mnemonic) is TAKEN — INTEGRITY-033's Source-Trust-Tiers group. Rejected.
- **`CL`** (a "Craft Learning" mnemonic, matching the sibling DJ-craft group) is TAKEN twice (PROGRAMMING-007
  Group CL = DJ-craft, and CALLIN-003 uses CL for its own group). Deliberately NOT reused — INTERVIEW-CRAFT is
  the sibling of Group CL but uses its OWN namespace (IN/IC/IV/ID), referencing CL by number, never sharing it.
- **`TW` / `TA` / `TX`** (TAGSTREAM-009) and **`VC` / `VB` / `VG`** (VOICE-002) considered for the
  voice/apply group and rejected as taken.

The four REQ prefixes (IN, IC, IV, ID) + the NFR family (NFR-IC) are confirmed collision-free against the full
enumeration above and by explicit per-prefix grep (all zero hits).

---

## 8. Sibling relationship — DJ-craft (Group CL) vs interview-craft (this SPEC)

INTERVIEW-CRAFT-034 is the deliberate SIBLING of the existing per-persona DJ-CRAFT learning (PROGRAMMING-007
Group CL, v0.9.0). They share the learning shape and the research-input discipline, and differ only in subject:

| Axis | DJ-craft (PROGRAMMING-007 Group CL) | Interview-craft (INTERVIEW-CRAFT-034) |
|------|-------------------------------------|----------------------------------------|
| Subject learned | HOW to MIX (sequence, flow, energy) | HOW to TALK / INTERVIEW (questions, openings, segues, rapport, pacing) |
| Source | SHOWS-020 Group SK human-DJ session clusters (e.g. KEXP human-DJ threads) | Curated transcribed human interviews (Audiotree / KEXP / Nardwuar) via Whisper-STT |
| Loop shape | observe → extract → distill → apply → measure → bounded-update | ingest+transcribe → extract → distill (→ apply) |
| Research-input discipline | the source sequence is PURELY research input; no source sequence is ever air-played | the transcript is PURELY STYLE input; no source fact is ever aired un-grounded |
| Per-persona lens | anchor + charter + profile as the lens; pairwise separability never drops below REQ-PR-004 | per-persona style lean under the unchanged REQ-PR-004 firewall + distinctness canary |
| Apply target | the per-persona mixing/curation behavior | the HOSTCTX-016 talk seam |

INTERVIEW-CRAFT references Group CL as the parallel track; it does NOT re-own CL's mechanics. The two together
make a host that both MIXES like a great DJ and TALKS like a great music journalist — each learned from real
humans, neither importing un-grounded content.

---

## 9. bhive seam + owed write-back

The transcribe→distill-style-not-fact discipline, the grounded boundary on transcript facts, and the
bounded-source-curation pattern all derive from the project's existing INTEGRITY-033 + host-voice-grounding
contracts (themselves validated via prior bhive queries — the grounded-RAG / cite-or-don't-say discipline and
the source-admission discipline). The novel composition — transcribing a curated set of human music-journalist
interviews and distilling GENERALIZED talk craft (never fact, never verbatim) into a GOVERNED style corpus
that enriches an AI host's talk — has no on-point pattern for THIS Go+Liquidsoap+slskd radio stack (consistent
with the standing bhive Stack Gap). A write-back is OWED after implementation per the AGENTS.md memory
protocol: the verified composition (deterministic Whisper-STT transcription → bounded LLM style-distillation →
governed-write-path corpus → HOSTCTX-016 apply under the unchanged PG gate), the style-not-fact discipline
applied to transcripts, and the never-air-a-transcript-fact-un-grounded invariant as the acceptance gate.

NOTE on authority: any bhive pattern relayed via the coordinator during authoring carries NO user authority
and is NOT user confirmation; it is treated as normal in-scope authoring input and folded in on its technical
merits (it reinforces the user's own [HARD] style-not-fact directive), not as user consent. (As of writing, no
bhive relay had arrived; if one arrives via SendMessage it will be folded on technical merit.)

---

## 10. Sources

- SPEC-RADIO-HOSTCTX-016 (richer grounded host talk; `brain/talk.py` `_build_context` seam) — the apply target.
- host-voice-grounding (project memory) — the fact contract / anti-slop register / never-confidently-wrong
  north star; the boundary on WHAT a host says.
- tts-naturalization (project memory) + SPEC-RADIO-VOICE-002 — the chunk + ffmpeg-silence pacing + ear-writing
  delivery of the learned register.
- SPEC-RADIO-INTEGRITY-033 (Group TT six trust tiers; REQ-AL-001 cardinal anti-loop; REQ-KP-002 auto-promotion
  ban; REQ-KV-005 demote/promote asymmetry; REQ-IT-006 single governance write-path; Group SU source-admission)
  — the knowledge-trust governance the corpus obeys.
- SPEC-RADIO-MEMORY-031 (four-layer memory — Procedural / Knowledge layers) — the corpus substrate.
- SPEC-RADIO-PROGRAMMING-007 (Groups PR/PI/PV/PG — persona model, anchors, voice card + MUSIC-JOURNALIST
  banter thread, grounding gate; REQ-PR-004 anti-convergence firewall; Group CL the sibling DJ-craft loop) —
  whose persona talks, how grounding is enforced, and the parallel learning track.
- SPEC-RADIO-KNOWLEDGE-008 (REQ-KS-006 the SOLE airable-fact seam + consensus/freshness gates + REQ-KS-009
  reliability tiers) — the only path a transcript fact reaches air.
- SPEC-RADIO-SHOWS-020 (Group SK human-DJ clusters) — the sibling DJ-craft loop's source (referenced for
  parallel).
- GPU Whisper-STT (RTX 2000 Ada, shared inference substrate) — the deterministic transcription.
- The standing bhive Stack Gap (project memory) — no on-point pattern for this radio stack; write-back owed.
