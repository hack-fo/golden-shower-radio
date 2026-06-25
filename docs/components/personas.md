# Personas & Host Roster

**SPECs:** SPEC-RADIO-PROGRAMMING-007 (model + roster), SPEC-RADIO-SEEDING-029 (minting),
SPEC-RADIO-OPS-004 Group OB (lifecycle FSM)

The station has a roster of on-air personalities. Each one is autonomous — authored by the AI,
voiced by Kokoro TTS, and grounded in the real music catalog. This page explains how and when
they come to life, what shapes them, and where your influence as the operator lives.

---

## Two kinds of on-air voice

There are exactly two tiers of on-air voice and they are completely separate systems:

### 1. The newscaster (fixed, permanent)

The newscaster is **not a persona**. It is a permanent TTS route with a reserved identity
(`news-anchor`). It reads news in English, then repeats the news in Faroese, with Faroese
sources used for the Faroese segment. It does not curate music. It has no taste charter.
It never retires. The lifecycle system explicitly exempts it (`persona_identity.is_news_anchor`).

### 2. The curator personas (the hosts)

These are the music show hosts. Each has a distinct Kokoro voice, taste charter, and
AI-designed personality. They curate the music, write their own links, and talk about what
they've been listening to, what they've read in music press, what caught their ear recently.
This is the roster this page is about.

---

## How a persona is born

Personas are **minted autonomously** by the AI (`brain/minting.py`). No human writes
their identity — but the human shapes what musical material they are minted from.

The minting pipeline:

```
Real library catalog (data/music/)
         │
         ▼  CLUSTER by genre / era / tags / sub-genre
Distinct taste territories (musical regions in the catalog)
         │
         ▼  FIND a territory not yet occupied by any existing persona
Candidate taste charter (grounded in real catalog, not fabricated)
         │
         ▼  DOCUMENT the editorial gap it fills
Gap record: "no current persona covers <territory>"
         │
         ▼  ASSIGN a free Kokoro voice (strict 1:1 — never shared)
         │
         ▼  DESIGN an identity via LLM: name, age (22–70), short personality
         │  If the LLM is unavailable → deterministic fallback (never crashes)
         │
         ▼  PASS THE SHARED GATE
Anti-convergence check + age bounds + 1:1 voice check. Same gate
the manual operator path uses — never bypassed.
         │
         ▼  PERSIST to brain.db
Persona is live and schedulable.
```

A persona is added only when it fills a **documented editorial gap** — a taste territory no
existing host covers. Minting for "reach", "popularity", or "more listeners" is an explicit
anti-goal, checked at the code level, and refused.

---

## When does minting happen?

Minting is triggered by the **lifecycle engine** (`brain/lifecycle.py`). The lifecycle engine
watches the schedule grid: when a slot has no host, it requests a mint to fill the gap.

The lifecycle engine is currently **off by default** (`BRAIN_LIFECYCLE_ENABLED=0`). When off:

- The station runs with a single "house" curator prompt (the freeform college-radio voice in
  `brain/llm.py`).
- No personas are in the roster. No minting happens. No shows are scheduled by persona.
- Everything on the playout path is byte-identical to before the persona system existed.

Turning it on (`BRAIN_LIFECYCLE_ENABLED=1`) enables the full multi-persona roster.

The number of distinct personas the roster can ever hold is **bounded by the Kokoro voice
palette** — each persona must have a unique voice. Once every voice is claimed, no new
persona can be minted until one retires and its voice is freed (after a quarantine cooldown
window, so a returning voice is never mistaken for the old host mid-cycle).

---

## Your influence: the taste seed → personas connection

You do not write the personas. But you **do** shape who they will be — through the library
you build. The critical insight is:

> **A persona's taste charter is derived from the real library catalog.**

The AI clusters whatever is in `data/music/` to find distinct musical territories. Those
territories become the hosts. So:

```
Your taste seed (Anchor / Compass / WOPR)
          │
          ▼  shapes which music is acquired
Library content in data/music/
          │
          ▼  clustered into distinct taste territories
Musical regions (e.g. "60s soul", "post-punk", "Nordic folk")
          │
          ▼  one minted persona per unoccupied territory
Curator personas with grounded taste charters
```

What this means in practice:

- If your library is 80% soul and 20% electronic, you will get a soul host and an electronic
  host — not two pop hosts.
- Seed with a Spotify export of Scandinavian indie and use **Anchor** mode → the station
  acquires that music → a Scandinavian-indie-flavoured host emerges.
- **Compass** mode → the AI explores outward from your seed → you may get hosts whose taste
  is *adjacent to* but not identical with yours (which is often more interesting radio).
- **WOPR** mode → the AI acquires whatever it editorially judges best → personas reflect
  whatever musical territories accumulate.

The seed is not a direct persona-authoring tool. It is a **library shaping** tool. The
personas emerge from the library.

Additionally, a bootstrap mechanism (`taste.seed_enrichment_bootstrap`) can nudge initial
per-persona taste profile weights using the seed descriptors — distributing them as a small
starting boost to whichever profiles already lean that way. This is soft and optional: after
boot the measured taste-learning loop diverges freely. The seed is never a hard constraint.

---

## The anti-convergence firewall

No two personas can be too similar. Every candidate — autonomously minted or manually created
— must pass a distinctness test against every existing roster member:

1. **Primary territory must be unique** — no two personas can claim the same top-level taste
   region (two "60s soul" hosts cannot coexist).
2. **Descriptor pool overlap must be below the cap** — the Jaccard similarity of genre /
   sub-genre / era / tags sets must be below a configured ceiling. If a candidate overlaps
   too much, the system trims shared tags from its charter and re-measures. If it still
   overlaps after exploration, the mint is rejected cleanly.

This is not a soft guideline. Rejection is clean, logged with a reason, and the catalog is
never left in a half-mutated state.

---

## The lifecycle FSM

When the lifecycle engine is on, each curator persona moves through existence states:

```
minted → active → retiring → retired
```

- **active** — on-air, scheduled, taking show slots.
- **retiring** — given a wind-down period; airs its final sets before removal.
- **retired** — permanently off-air. The record is kept for history. Its voice enters a
  quarantine period before it can be assigned to a new persona.

A retiring persona **never cuts an in-flight break or silences the stream** — the lifecycle
engine only affects future scheduling, not the current playout state. When a slot is left
empty by a retirement, the engine mints a replacement.

---

## Can you author a persona yourself?

Yes. `Roster.create()` is the manual operator path. It runs through the **same gate** as
autonomous minting — same anti-convergence check, same age bound, same 1:1 voice check. The
only difference is that you supply the identity (name, age, personality, taste charter) rather
than having the LLM design it.

There is currently no UI or `run.sh` prompt for this. It is a direct call into the brain's
persona store. A future operator interface could expose it.

---

## Persona model

Each persona record in `brain.db` holds:

| Field | What it is |
|---|---|
| `id` | Stable slug, auto-generated (e.g. `persona-abc123`) |
| `display_name` | AI-designed name (e.g. "Marta") |
| `voice` | Assigned Kokoro speaker ID — permanent, 1:1, never reassigned while active |
| `charter` | Taste charter: primary territory, genres, eras, sub-genres, tags, moods |
| `age` | AI-selected or deterministic, always in [22, 70] |
| `personality` | Short personality / worldview fragment, AI-authored |
| `lifecycle_state` | active / retiring / retired |

All records survive restarts — a minted host does not disappear when the station reboots.

---

## Summary

| Question | Answer |
|---|---|
| When are hosts created? | When the lifecycle engine detects an unstaffed slot and mints one |
| Do they come from nothing? | No — their taste is clustered from the real music catalog |
| Can the operator influence them? | Yes, indirectly — by shaping the library via the taste seed |
| Is there direct operator authoring? | Yes, via `Roster.create()` (no UI yet) |
| Is the roster size limited? | Yes — bounded by the available Kokoro voice palette |
| What is the newscaster? | A fixed permanent TTS route — not a curator persona, exempt from lifecycle |
| Is multi-persona mode on by default? | No — requires `BRAIN_LIFECYCLE_ENABLED=1` |
| Can the AI mint a persona for "reach"? | No — explicitly refused at the code level |
