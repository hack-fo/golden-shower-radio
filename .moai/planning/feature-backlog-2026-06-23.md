# Feature Backlog & Plan Capture — 2026-06-23

Captured during a `/moai plan` batch when the agent runtime (`manager-spec`) was in a
sustained outage and could not auto-author SPECs. This file preserves the VERBATIM user
prompts, the LOCKED design decisions, and the SPEC decomposition so `manager-spec` (+
`plan-auditor`) can author the formal EARS SPECs (013–018) the moment the runtime recovers.

Status legend: 🔵 planned (this doc) · 🟡 SPEC drafting · 🟢 SPEC done · ⏸ blocked.

---

## Secrets received (place in gitignored `secrets/` — orchestrator is perm-denied there)

- **AcoustID API key** = `wfu2hpwRny` → `secrets/brain.env` as `BRAIN_ACOUSTID_API_KEY=wfu2hpwRny` (ENRICH-012 fingerprinting).
- **MusicBrainz live-feed replication token** = `qP7ZfGkJ8ibPbxNXfSqsXruepgg7zpzSjTszSusj` → MB mirror replication config (SPEC-017), to be placed when the mirror is stood up (likely on Hetzner).

## Cross-cutting infra decision

- **MB mirror will live on the user's Hetzner Cloud instance**, NOT local WSL disk → removes the ~39 GB local-disk constraint. Local brain queries the remote MB endpoint. (Supersedes the earlier "API-only / local disk too small" analysis.)

---

## Verbatim user prompts (source of truth for SPEC authoring)

> 1. "Create a taste-map/vizualisers/make charts based on playtime rather than playcount/ analyze monthly/yearly top stats as well as recommend tracks and artists/LastWave. If we could somehow get short reasoning behind why it grabbed a song, and the brain logic tying songs together that'd be interesting too. Stats, graphs and logical reasoning behind its decisions presented on a separate website, where all this data is continously being updated/kept/presnted from data in the database"

> 2. "Ensure that there is duplication control on downloaded songs, so that we do not download multiple versions of the same song, unless it has a good, valid reason for having multiple copies (IE, live show/concert vs album)"

> 3. "Add a heart-icon on the website, to let users indicate that they really liked this song. An opposite icon would be good too, but the risk of abuse is too high i think. Can you think of a good way of doing it? How can users say the dislike a song without the risk of abuse?"

> 4. "Have the hosts tell you what year a song is from, and what album it came off of too - maybe some curiousa about it too, or funny short anecdote. Just something nice that's interesting to the listener. Cycle what, how and when as you wish, each host and persona has their own will and style, If no scheduled host, then do as you want and see fit - you're the director"

> 5. "Host our own copy of the muscibrainz API or something, that we can query locally to update and sanitize our id3 tags for all our downloaded music. And for the different hosts/shows to be able to correctly gather information about when an album released, who produced it, who's credited on the albums, related record labels or whatnot that may be of interest for a radio host"

> 6. "Completely redesign the website for this project, make it 2026 - impressive, sleek yet sexy. Make 'last played songs' remember the last played songs even after icecast restarts so it's not just blank."

> 7. "Maybe cross check this with discogs and last.fm?"

Run flags requested: `/effort ultracode`, `ultrathink`.

---

## Locked design decisions (orchestrator + user, this session)

- **Dislike mechanism (#3): LIKES-ONLY + IMPLICIT DROP-OFF.** Heart (like) is the only explicit button: rate-limited, cookie-deduped, bound to a signed token for the *currently-airing* track. Negative signal is derived implicitly from listener drop-off (many distinct sessions disconnecting shortly after a track starts) — organic, nothing to abuse. NO explicit dislike button. Likes/drop-off feed the director as SOFT weights, never hard rotation control.
- **MB mirror (#5): host on Hetzner Cloud.** Local disk no longer the constraint. Open sub-question = exact size/variant (see SPEC-017 sizing below).
- **Hosts (#4): director's discretion** on cadence/style; per-persona will/style; when no scheduled host, the brain (director) decides. (User: "you're the director.")

---

## SPEC decomposition (IDs 013–018; ENRICH-012 already in progress)

### SPEC-RADIO-STATS-013 — analytics + insight site  🔵
- Separate read-only website, continuously updated from the DB.
- PLAYTIME-based (seconds actually aired), NOT playcount → requires a new `play_events` log (track, started_at, seconds_aired) persisted by the brain (from /api/airing + cue_out/true_end). Everything derives from this.
- Charts/visualizers, taste-map, monthly/yearly tops, track+artist recommendations ("LastWave" = Last.fm-style listening-trend viz over time).
- Surface the brain's per-song GRAB-REASON (already a field via PROGRAMMING-007 PL-008) + the song-linking logic (why this track followed that one).
- Cross-check artist/track similarity with Last.fm where useful.

### SPEC-RADIO-DEDUP-014 — download duplication control  🔵
- Gate acquisition so we don't grab the same recording twice UNLESS a valid distinct version (live/concert vs studio, remaster, different mix).
- Dedup key = canonical MusicBrainz **recording MBID** (from ENRICH-012 / MBMIRROR); fuzzy artist+title fallback when no MBID. Allow when release-type/version differs.
- Hook in brain/acquire.py before download + library has_key.

### SPEC-RADIO-LIKE-015 — listener like + implicit negative  🔵
- Heart/like per locked decision above; soft weights to the director; overlaps REQUEST-011.
- Implicit drop-off tracking (Icecast listener stats / session disconnects).

### SPEC-RADIO-HOSTCTX-016 — richer host talk (year/album/curiosa)  🔵
- Extend brain/talk.py: announce year + album + optional curiosa/anecdote.
- Facts SOURCED from ENRICH-012 / MBMIRROR (release date, album) + Last.fm/Discogs/MB trivia, GROUNDED per the host-voice-grounding rules (no confident-wrong facts).
- Per-persona style (host-roster: 5 EN + 2 FO, 1:1 voice↔persona); director discretion on cadence.

### SPEC-RADIO-MBMIRROR-017 — self-hosted MusicBrainz (on Hetzner) + Discogs/Last.fm  🔵
- Stand up MB mirror on the Hetzner Cloud instance; keep synced via the replication token.
- Brain queries the remote endpoint (config-gated host) instead of the rate-limited public API; public API as fallback. Powers ENRICH-012 id3 sanitization at volume + HOSTCTX rich facts (producer, credits, labels, release relationships).
- Discogs + Last.fm cross-check for producer/label/credits coverage + corroboration; rate-limited; provenance per field.
- SIZING (answer to "how much"): full `musicbrainz-docker` (Postgres + Solr search + the MB web service) ≈ 100–150 GB → provision a ~150 GB Hetzner volume for headroom + replication growth. Postgres-only (no Solr, query by joins/MBID) ≈ 50–80 GB. Minimal selective import (artist, recording, release, release_group, label, artist_credit, medium, track, and l_* relationship tables for credits/producer/label) ≈ 15–25 GB. RECOMMEND: on Hetzner (disk not scarce) run **full musicbrainz-docker** so the brain gets a drop-in local MB web-service endpoint (just repoint musicbrainzngs' hostname — minimal brain change, no schema coupling).

### SPEC-RADIO-WEBUI-018 — 2026 website redesign + durable last-played  🔵
- Complete redesign (sleek/impressive 2026); likely via the design workflow / expert-frontend.
- Persist `state.recent` (last-played ring) to the DB so it survives brain/Icecast restarts (today it's in-memory → blank after restart). This persistence is a small concrete fix; the redesign is the larger effort.

---

## Next actions
1. When the agent runtime recovers: `manager-spec` authors SPEC-013…018 from this doc (parallel where independent); `plan-auditor` reviews.
2. ENRICH-012 (in progress) is the dependency spine for 014/016/017 — finish its wiring first.
3. Suggested build order: ENRICH-012 → MBMIRROR-017 (data spine) → DEDUP-014 + HOSTCTX-016 → STATS-013 (needs play_events) → LIKE-015 → WEBUI-018.
