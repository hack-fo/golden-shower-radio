# Host Personas

SPEC-RADIO-PROGRAMMING-007. A multi-persona host system: autonomous minting, lifecycle management, per-persona taste seeding, voice assignment, and anti-convergence rules. Each host is a single, independent editorial curator with a distinct voice, taste envelope, and on-air identity.

---

## Persona model

Each persona is a `PersonaIdentity` record with:

- **id** — stable slug (`en-host-1`, `fo-host-2`, etc.)
- **name** — display name (e.g. "Astrid")
- **language** — `en` or `fo`; determines which TTS voice pool is eligible
- **charter** — editorial charter: seed genres, eras, moods, topic interests; the fingerprint of what this host cares about
- **voice_id** — assigned Kokoro voice (1:1 binding, never shared between personas)
- **lifecycle_state** — FSM state: `seed → active → dormant → retired`
- **taste_envelope** — live probability distribution over genres/eras/moods, updated by the taste loop

All persona records live in `personas.db` (SQLite). The brain reads them at startup and keeps them in memory for the session.

---

## Autonomous minting

The brain can propose minting a new persona without human instruction when:

1. The host roster drops below `BRAIN_PERSONA_MIN_COUNT` (default: 2 active per language).
2. An active editorial gap is detected: the taste-coverage heatmap has a cold zone (genre × era combination with no host whose charter covers it).
3. The director tick fires a `MINT_PERSONA` intent, which goes to ActionSurface.

Minting uses a single LLM call with the current roster and gap analysis as context. It generates: name, charter, seed tastes, and a bio fragment. The new persona is inserted in `seed` lifecycle state and transitions to `active` after a first-show warm-up cycle.

**Anti-convergence** — minting is gated on editorial gap distance: a proposed persona must differ from every existing active persona by at least `BRAIN_PERSONA_MIN_DIVERGENCE` (default 0.4 on a 0-1 charter distance metric). This prevents the roster from filling up with near-identical hosts.

---

## Lifecycle FSM

```
seed ──(warm-up complete)──▶ active ──(dormancy threshold)──▶ dormant ──(reactivation)──▶ active
                                                                              │
                                                                         (retirement)──▶ retired
```

- **seed** — persona exists but has not aired. Taste envelope is the charter defaults.
- **active** — persona airs shows. Taste envelope evolves with each play event.
- **dormant** — persona has not aired above `BRAIN_PERSONA_DORMANCY_THRESHOLD` shows per week for `BRAIN_PERSONA_DORMANCY_WINDOW_DAYS`. Keeps its taste state but does not take show slots.
- **retired** — manually retired or roster pruned. Records are kept (for history) but the persona is permanently inactive.

Transitions are written to `personas.db` with a timestamp and reason for audit.

---

## Voice assignment

Each persona is assigned a voice from the configured Kokoro voice pool at mint time. The assignment is **permanent** — switching voices mid-persona would break listener identity. Voices are assigned in a round-robin order from the pool filtered by persona language (`en` voices for English personas, Faroese voices for `fo` personas). No two active personas share a voice.

Voice pool is configured in `config.py` as `kokoro_voice_pool` (list of Kokoro speaker IDs).

---

## Per-persona taste seeding and evolution

The taste envelope is a probability distribution over the station's genre/era/mood taxonomy. At mint time, it is initialized from the charter. It evolves through three signals:

1. **Play feedback** — the OD-007 ledger records whether a track aired successfully, was skipped, or triggered a listener drop-off. Tracks that perform well in their slot pull their genre/era/mood weights up slightly.
2. **Hostlife engagement** — when a persona engages positively with a news item about an artist or genre (HOSTLIFE-032 TASTE phase), that genre's weight gets a small bump.
3. **Anti-drift clamp** — taste drift is bounded. No single genre can rise above `BRAIN_PERSONA_TASTE_MAX_WEIGHT` or fall below `BRAIN_PERSONA_TASTE_MIN_WEIGHT`. This keeps personas recognizable over time.

Taste state is persisted to `personas.db` after each director tick.

---

## Anti-convergence at the roster level

The taste distance check runs on every tick: if two active personas' taste envelopes drift within `BRAIN_PERSONA_CONVERGENCE_ALERT_DISTANCE` of each other, the director logs a warning and can nudge the lower-priority persona's charter away from the overlap zone on its next minting review.

---

## Configuration

| Variable | Default | Effect |
|---|---|---|
| `BRAIN_PERSONA_MIN_COUNT` | `2` | Minimum active personas per language before auto-mint |
| `BRAIN_PERSONA_MIN_DIVERGENCE` | `0.4` | Minimum charter distance when minting a new persona |
| `BRAIN_PERSONA_DORMANCY_THRESHOLD` | `1` | Shows per week below which persona goes dormant |
| `BRAIN_PERSONA_DORMANCY_WINDOW_DAYS` | `14` | Window to measure show count for dormancy |
| `BRAIN_PERSONA_TASTE_MAX_WEIGHT` | `0.6` | Maximum weight any single genre can reach |
| `BRAIN_PERSONA_TASTE_MIN_WEIGHT` | `0.02` | Minimum weight floor per genre |

---

## Host roster (launch configuration)

Seven hosts configured at project launch: 5 English-language, 2 Faroese-language. Each has a distinct voice from the Kokoro pool and a non-overlapping editorial charter. See `docs/Home.md` and memory for the full roster.
