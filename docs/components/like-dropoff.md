# Listener Like + Drop-off

SPEC-RADIO-LIKE-015. Turns two listener signals — an explicit heart/like button and an implicit drop-off detection — into a soft, time-decayed affinity weight the curation director may consider when choosing the next track. **Off by default** (`like_enabled=False`). Enabling it requires `BRAIN_LIKE_ENABLED=true`.

---

## Two input signals

### Explicit like (Group LH)

A listener clicks a heart button on the station website. The click is validated via an **HMAC-signed token** minted by the brain and served to the page:

- The token is bound to the currently-airing artist + title + an issue timestamp + a random nonce, so a like can only be cast for a real on-air track.
- Tokens expire quickly (configurable TTL, default 60 s).
- Per-identity (hashed cookie) deduplication prevents double-liking the same recording within a window.
- Rate-limited per identity per track per window (REQ-LH-003).

The like endpoint: `GET /api/like-token` (mints the token) → `POST /api/like` (submits it). Both 404 when `like_enabled=False`.

### Implicit drop-off (Group LD)

The brain polls Icecast's public `/status-json.xsl` for aggregate listener counts per mount in a bounded background thread that **never blocks playout**. A significant listener drop within a short window after a track starts is treated as a mild negative signal. Suppressed below a minimum-audience floor (noise and privacy — you can't infer individual behaviour from a tiny count).

Drop-off is **aggregate only** — no individual tracking, no cookies in the poll (REQ-LP-002).

---

## Affinity store (Group LS)

Both signals normalize into a soft affinity entry keyed on the canonical recording key (`Track.key` / `normalize_key`) in SQLite (`events.db`).

- Each entry carries: recording key, signal type (`like` / `dropoff`), timestamp, identity hash (likes only), and a decayed weight.
- Stale signals beyond a configurable age are ignored and purged (REQ-LS-004).
- **[HARD] Affinity is a SOFT weight only** — never hard rotation control. The director MAY weigh it; it cannot force-play, force-skip, or hard-rotate (REQ-LS-002).

---

## Privacy

- Like identity: `SHA256(cookie_value + salt)` — no raw cookie, no account, no PII stored (REQ-LP-001/003).
- Drop-off: aggregate listener count delta only — no individual tracking.
- No public leaderboard. A like response confirms only per-listener receipt.

---

## Configuration

| Variable | Default | Effect |
|---|---|---|
| `BRAIN_LIKE_ENABLED` | `false` | Enable the entire subsystem |
| `BRAIN_LIKE_TOKEN_TTL_S` | `60` | Like token validity in seconds |
| `BRAIN_LIKE_RATE_LIMIT` | `5` | Max likes per identity per track per window |
| `BRAIN_DROPOFF_THRESHOLD` | `0.3` | Fraction of listeners leaving to trigger drop-off signal |
| `BRAIN_DROPOFF_WINDOW_S` | `30` | Window after track start to measure drop-off |
| `BRAIN_DROPOFF_MIN_AUDIENCE` | `3` | Minimum listeners before drop-off is measured |
| `BRAIN_AFFINITY_DECAY_DAYS` | `30` | Age beyond which signals are discarded |

---

## Key invariants

- With `like_enabled=False`: all endpoints 404, the Icecast poll never starts, events.db stays unwritten — the station behaves identically to pre-LIKE-015 (REQ-LX/never-half-exist).
- Every public method is exception-isolated — a like error never reaches the playout path.
- The heart button is not yet shown by default in the website UI (WEBUI-018 Phase 2 placeholder).
