# SPEC-RADIO-SHOWS-020 — Research: The Last.fm API

> Status: research artifact (NOT a SPEC). Factual, verified against the official
> Last.fm API documentation fetched 2026-06-23. Every claim below was checked
> against a doc URL listed in the Sources section. Where a widely-repeated
> community claim could NOT be confirmed against the official docs (notably the
> "5 requests/second" rate limit), it is explicitly flagged as community-sourced.
>
> Scope of the user directive that this answers: "do deeper research on what
> Last.fm is, what it offers, and what we can pull via the API." This feeds the
> SHOWS-020 editorial show-variation engine (the `LF` REQ group: a richer,
> key-gated, rate-limited, exception-isolated Last.fm RESEARCH client).

---

## 1. What Last.fm is, and the shape of its public Web API

### 1.1 What Last.fm is

Last.fm is a **scrobbling-based music database and social music catalog**. Its
core mechanic — "scrobbling" — logs every track a user plays (from desktop
players, mobile apps, and streaming-service connectors) to that user's profile.
Aggregated across tens of millions of users over ~20 years, those play events
become a large behavioural dataset on top of which Last.fm layers:

- **Popularity signal** — per-artist / per-album / per-track `listeners` (unique
  users) and `playcount` (total scrobbles); plus weekly/all-time charts.
- **Crowd-sourced folksonomy tags** — free-text genre/mood/era labels users
  apply to artists, albums, and tracks (e.g. `synthwave`, `melancholic`,
  `90s`, `norwegian black metal`). This tag graph is Last.fm's most
  distinctive asset and the primary thing MusicBrainz/Discogs do NOT provide.
- **Similarity graph** — "similar artists" / "similar tracks" / "similar tags"
  derived from co-listening behaviour, each with a numeric match score.
- **Editorial-ish bios / wikis** — crowd-edited artist and track biographies
  (`bio` / `wiki`), with a `summary` and a longer `content` field. NOTE: these
  are user-contributed and unsourced — see §5(b) and §6.

Last.fm is therefore best understood as the **taste, popularity, and tag layer**
of the music-metadata world. It is authoritative for "what do listeners call
this and what else do they listen to," NOT for "what is the canonical release /
credit / label" (that is MusicBrainz + Discogs — see §6).

### 1.2 Shape of the public Web API

- **Root endpoint (REST):** `http://ws.audioscrobbler.com/2.0/`
  (the historical "audioscrobbler" host; HTTPS is available and should be
  preferred). All methods are invoked against this single endpoint.
- **Method dispatch:** every call passes a `method` query parameter in
  `package.method` form, e.g. `method=artist.getInfo`,
  `method=tag.getTopArtists`, plus method-specific arguments.
- **Verb:** read methods are plain HTTP `GET` with query-string parameters.
- **Response format:** Last.fm "responds in Last.fm idiom XML by default." Pass
  **`format=json`** to get JSON instead. (Caveat below.)
- **API key:** an `api_key` query parameter is **required on every call**,
  including read-only methods. Keys are obtained by creating an API account.
- **Auth model:** "All write services require authentication." **Read-only
  methods need ONLY an `api_key`** — no OAuth, no session key, no signature.
  Write methods and user-session methods require the full auth handshake
  (`auth.getSession` / `auth.getMobileSession` → session key → MD5 `api_sig`
  signature on each call). SHOWS-020 is read-only, so it never touches auth.
- **Identifiable User-Agent:** the docs explicitly request "an identifiable
  User-Agent header on all requests." Our client MUST set one.

#### JSON-format caveats (load-bearing for the client implementation)

Last.fm's JSON is a mechanical translation of its XML idiom, which produces two
quirks our parser MUST tolerate:

1. **Text nodes become `"#text"`.** Images and some scalar-with-attributes
   fields serialize as `{"#text": "...", "size": "large"}` (see the
   `image` arrays and `streamable` objects in the response examples below).
2. **Numbers and booleans are strings.** `playcount`, `listeners`, `streamable`,
   `match`, pagination counters — all come back as JSON strings
   (e.g. `"playcount": "124394"`). Cast on read; never assume numeric JSON types.
3. **Single-vs-list collapse.** A collection with one element may serialize as a
   single object instead of an array (e.g. one `tag` vs a `tag` array). The
   client must normalize to a list before iterating.
4. **Errors come back HTTP 200 with an error envelope.** A failed call returns
   `{"error": <code>, "message": "..."}` (see §3 error table), not an HTTP error
   status. The client MUST branch on the `error` key, not the HTTP code.

---

## 2. The read-method surface we can use WITHOUT user auth

All methods below are confirmed **"This service does not require authentication"**
in the official docs and need only `api_key` (+ `format=json`). Grouped by
package, with the concrete data each returns.

### 2.1 `artist` package

| Method | Required params | Returns (key fields) |
|---|---|---|
| `artist.getInfo` | `artist` (or `mbid`), `api_key`; opt: `lang`, `autocorrect`, `username` | `name`, `mbid`, `url`, `image[]`, `streamable`, `stats.listeners`, `stats.playcount`(`plays`), `similar.artist[]` (name/url/image), `tags.tag[]` (name/url), `bio` (`published`, `summary`, `content`), `ontour` flag. **Bio summary is truncated at ~300 chars.** |
| `artist.getSimilar` | `artist` (or `mbid`), `api_key`; opt: `limit`, `autocorrect` | `similarartists.artist[]` with `name`, **`match`** ("a similarity value between 0 (not similar) and 1 (very similar)"), `url`, `image[]`. This is the headline similarity signal. |
| `artist.getTopTags` | `artist` (or `mbid`), `api_key`; opt: `autocorrect` | `toptags.tag[]` with `name`, `count` (tag weight, 0–100 relative), `url`. The crowd-tag fingerprint of an artist. |
| `artist.getTopAlbums` | `artist` (or `mbid`), `api_key`; opt: `autocorrect`, `limit`, `page` | `topalbums.album[]` with `name`, `playcount`, `mbid`, `url`, `artist` sub-object, `image[]`; plus `@attr` pagination. |
| `artist.getTopTracks` | `artist` (or `mbid`), `api_key`; opt: `autocorrect`, `limit`, `page` | `toptracks.track[]` with `name`, `playcount`, `listeners`, `mbid`, `url`, `artist` sub-object, `image[]`, rank `@attr`. |

> The five `artist.*` methods above are exactly the LF-group surface the SPEC
> names (`artist.getInfo` / `artist.getSimilar` / `artist.getTopTags` plus
> `getTopAlbums`/`getTopTracks` as extensions).

### 2.2 `album` package

| Method | Required params | Returns (key fields) |
|---|---|---|
| `album.getInfo` | `artist`+`album` (or `mbid`), `api_key`; opt: `autocorrect`, `username`, `lang` | `name`, `artist`, `mbid`, `url`, `image[]`, `listeners`, `playcount`, `tracks.track[]` (per-track name/duration/url/rank), `tags.tag[]`, `wiki` (`published`/`summary`/`content`). |

### 2.3 `track` package

| Method | Required params | Returns (key fields) |
|---|---|---|
| `track.getInfo` | `track`+`artist` (or `mbid`), `api_key`; opt: `username`, `autocorrect` | `name`, `mbid`, `url`, **`duration`** (ms), `listeners`, `playcount`, `album` (artist/title/mbid/image), `toptags.tag[]`, `wiki` (`published`/`summary`/`content`), `streamable`/`fulltrack`. With `username`: user playcount + `userloved`. |
| `track.getSimilar` | `track`+`artist` (or `mbid`), `api_key`; opt: `autocorrect`, `limit` | `similartracks.track[]` with `name`, **`match`** (0–1 similarity), `playcount`, `duration`, `artist` sub-object, `url`, `image[]`. |

### 2.4 `tag` package (the folksonomy / theme-seed surface)

| Method | Required params | Returns (key fields) |
|---|---|---|
| `tag.getInfo` | `tag`, `api_key`; opt: `lang` | `name`, `url`, **`reach`** (number of users who applied it), **`total`/`taggings`** (usage frequency), `wiki` (`summary`/`content`/`published`). A tag's "size" and description. |
| `tag.getTopArtists` | `tag`, `api_key`; opt: `limit`, `page` | `topartists.artist[]` ranked by tag affinity: `name`, `mbid`, `url`, `image[]`, rank `@attr`. "Who defines this genre/mood." |
| `tag.getTopTracks` | `tag`, `api_key`; opt: `limit`, `page` | `tracks.track[]` ranked within the tag: `name`, `artist`, `mbid`, `url`, `image[]`, rank `@attr`. "The canon for this theme." |
| `tag.getSimilar` | `tag`, `api_key` | `similartags.tag[]` (`name`, `url`, `streamable`), "ranked by similarity, based on listening data." Lets us walk the tag graph (`disco` → `high energy` → ...). |

> NOTE on `tag.getSimilar`: per community reports it sometimes returns sparse or
> empty results for niche tags. Treat it as best-effort; do not block on it.

### 2.5 `chart` package (global trends)

| Method | Required params | Returns (key fields) |
|---|---|---|
| `chart.getTopArtists` | `api_key`; opt: `page`, `limit` (default 50) | `artists.artist[]`: `name`, `playcount`, `listeners`, `mbid`, `url`, `image[]`; `@attr` pagination. Global trending artists. |
| `chart.getTopTags` | `api_key`; opt: `page`, `limit` | `tags.tag[]`: `name`, `url`, `reach`, `taggings`. Trending tags/themes site-wide. |
| `chart.getTopTracks` | `api_key`; opt: `page`, `limit` (default 50) | `tracks.track[]`: `name`, `playcount`, `listeners`, `mbid`, `url`, `streamable`, `artist` sub-object; `tracks.@attr` page/perPage/totalPages/total. |

### 2.6 `geo` package (country-scoped trends)

| Method | Required params | Returns (key fields) |
|---|---|---|
| `geo.getTopArtists` | `country` (ISO 3166-1 name), `api_key`; opt: `limit`, `page` | `topartists.artist[]`: `name`, `listeners`, `mbid`, `url`, `image[]`; pagination. Country-popular artists. |
| `geo.getTopTracks` | `country` (ISO 3166-1 name), `api_key`; opt: `location` (metro), `limit`, `page` | `toptracks.track[]`: `name`, `playcount`, `mbid`, `url`, `streamable`, `artist` sub-object, `image[]`. "Most popular tracks last week by country." |

> The `geo` package is directly useful for region-flavoured shows (e.g. a Faroese
> or Nordic host: `country=Norway` / `country=Iceland`). `geo.getTopTracks` is
> explicitly a **last-week** window, so it naturally refreshes week to week —
> a built-in source of editorial novelty.

### 2.7 Methods that exist but need user auth (OUT of scope for SHOWS-020)

The `user.*` (e.g. `user.getRecentTracks`, `user.getTopArtists`,
`user.getLovedTracks`) and `library.*` methods read a specific Last.fm user's
listening history. Many read-only `user.*` calls work with just `api_key` IF you
supply a public `user=` parameter, but they describe a *Last.fm account's* taste,
not ours — SHOWS-020 has its own per-persona taste profiles (PROGRAMMING-007
Group PL) and does not want to import a stranger's scrobbles. **Write/scrobble
methods** (`track.scrobble`, `track.love`, `track.updateNowPlaying`, etc.) and
all `auth.*` session methods require the full signed-session handshake and are
explicitly out of scope. SHOWS-020 stays entirely within the unauthenticated
read surface in §2.1–§2.6.

---

## 3. Auth, rate limits, and Terms of Service

### 3.1 Auth (read path)

For everything SHOWS-020 needs: obtain one `api_key` from a Last.fm API account,
pass it on every request. No OAuth, no per-call signature, no session. The key
already exists in our codebase as `lastfm_api_key` in `brain/config.py`
(optional, empty default — the client must be key-gated and no-op when empty).

### 3.2 Rate limits — VERIFIED distinction (important)

There are **two different claims**, and they do not agree. The SPEC must respect
the stricter interpretation.

- **What the official ToS actually says (verified):** ToS clause 4.4 contains
  **no numeric limit**. Verbatim: *"Last.fm sets and enforces limits on use of
  the API to prevent abuse and ensure reliability of service (e.g. limiting the
  number of API requests that you may make or the number of users you may
  serve), in our sole discretion."* It requires respecting those limits and
  obtaining "express written consent" for higher usage. No "5/sec" appears in the
  current clause 4.4 text we fetched.
- **What the API intro page says (verified):** *"Be reasonable in your usage of
  the API and ensure you don't make an excessive number of calls. ... Your
  account may be suspended if your application is continuously making several
  calls per second or if you're making excessive calls."* — qualitative, not a
  hard number.
- **What the community universally cites (NOT found in current official text):**
  "no more than **5 requests per second per originating IP, averaged over a
  5-minute period**, without prior written consent." This figure appears in
  countless client libraries, Stack Overflow answers, and bug reports, and the
  navidrome/headphones error messages even link to `tos#4.4` when error 29 fires.
  It is almost certainly the historically-published threshold, but the **current
  clause 4.4 we fetched no longer states it numerically.**

- **Error 29 ("Rate Limit Exceeded — This application has made too many requests
  in a short period")** is real and observed in production by other clients.

**Polite ceiling SHOWS-020 should adopt (recommendation):** treat the community
**5 req/sec** figure as a hard ceiling and stay well under it. Because SHOWS-020
is a *research* client feeding a slow editorial loop (not a live request-serving
app), it should run at roughly **≤ 1 request/second with jittered spacing**, a
small bounded burst, exponential backoff on error 29 (and on error 16
"temporary error"), and a per-tick budget cap. This is comfortably "reasonable"
under both the qualitative ToS language and the community number.

### 3.3 Caching is a ToS REQUIREMENT, not an optimization

ToS clause 4.3.4: *"You will implement suitable caching in accordance with the
HTTP headers sent with web service responses."* Our research client MUST cache
responses (respecting cache headers / a sane TTL) — this is both compliance and
the right design for slow-changing data like bios, tags, and similarity.

### 3.4 The "Reasonable Usage Cap" — 100 MB of stored data

ToS clause 4.3.4 also caps stored Last.fm data: *"The licence granted to You is
temporary and restricted to a small portion of Last.fm Data ... not to exceed the
Reasonable Usage Cap in total at any time. The 'Reasonable Usage Cap' is a maximum
of 100 MB."* SHOWS-020 persists only small derived research notes (tags,
similar-artist names, match scores, bio snippets used as *input*), so staying
under 100 MB is easy — but the SPEC should state this as an explicit constraint
on any cache/store it builds, and prune accordingly.

### 3.5 Non-commercial restriction (the big one for a broadcast)

ToS clause 3.1: *"You are permitted to use the Last.fm Data solely for
non-commercial purposes and for no other purpose."* Commercial use requires a
separate **commercial use agreement**; using the data commercially without one is
a "material breach." For **commercial OR research/academic** use, Last.fm asks
you to contact **partners@last.fm** before use.

Implication for golden-shower-radio: an autonomous AI radio station that
broadcasts is a borderline/commercial-flavoured use of *derived* data. To stay
clean:
- Use Last.fm strictly as **private research input** to the LLM (theme seeds,
  similarity hops, popularity ranking) — NOT as published Last.fm-branded data.
- Do **not** re-publish raw Last.fm Data (bios, full tag dumps) as station
  content, and do not build a public mirror of it.
- If the station is ever monetized or the Last.fm data surfaces verbatim to
  listeners, the SPEC should flag a **partners@last.fm** contact as a
  prerequisite. Flag this caveat in the SPEC's compliance section.

### 3.6 Attribution

ToS clause 4.2.2 requires *"Crediting Last.fm ... where You have used Last.fm
Data,"* using the "powered by AudioScrobbler" treatment with links back to
Last.fm and the relevant artist/album pages. Since SHOWS-020 consumes Last.fm as
*internal research* (the host does not read Last.fm text on air verbatim), the
attribution surface is small — but if any Last.fm-derived text or link is ever
shown to listeners (e.g. on the station website), an attribution/credit MUST
accompany it. The `url` field returned by every method is the canonical
back-link to use.

---

## 4. Deprecated / unavailable surface (gaps the SPEC must NOT rely on)

- **Events / gigs API is RETIRED.** `artist.getEvents`, `artist.getPastEvents`,
  `geo.getEvents`, `event.*`, and `venue.*` were **removed** in Last.fm's March
  2016 relaunch and are gone — not merely deprecated. Multiple downstream
  projects (ampache, ruby-lastfm) confirm these endpoints stopped working.
  **Consequence for SHOWS-020:** "last shows / planned shows / upcoming gigs"
  **cannot come from Last.fm.** Live-event data, if ever needed, would have to
  come from a different source (e.g. Songkick / Setlist.fm). The SPEC's "last
  shows" and "planned shows" therefore mean **our own per-persona show
  history/schedule**, not Last.fm events — see §5(c)/(d).
- **Radio / streaming endpoints removed.** The old `radio.*` playlist/streaming
  methods were also retired in 2016; Last.fm is no longer a music *source*, only
  a *data* source. We supply our own audio (CORE-001 / ACQQUEUE-019).
- **Image URLs are stale/placeholder-prone.** Returned `image[]` URLs often point
  at legacy `userserve-ak.last.fm` hosts and may 404 or be blank for many
  entities. Do not depend on Last.fm images; IMAGING-010 owns artwork.
- **`mbid` is frequently empty.** Many chart/geo/similar results return
  `"mbid": ""`. Always reconcile by name and prefer MusicBrainz (MBMIRROR-017)
  as the MBID authority rather than trusting Last.fm's mbid field.
- **Bio/wiki quality is uneven and unsourced** (see §5b, §6) — usable as a lead,
  never as a citable fact.

---

## 5. Mapping to OUR use cases (which method feeds which)

### (a) Show-variation / editorial angles — the engine's fuel

The variation engine seeds fresh themes by *walking the Last.fm taste graph*
around a persona's existing territory, then asking the LLM to invent an angle the
persona has NOT recently run:

- **`artist.getSimilar`** + **`track.getSimilar`** → lateral hops from the
  persona's anchor artists to adjacent-but-fresh artists (use the `match` score
  to control how far to wander: high match = safe, lower match = bolder show).
- **`artist.getTopTags`** + **`tag.getSimilar`** + **`tag.getInfo`** → derive
  candidate *themes* (a tag, a tag-cluster, a mood/era) the persona could build a
  show around; `tag.getSimilar` walks to neighbouring themes for novelty.
- **`tag.getTopArtists`** + **`tag.getTopTracks`** → populate a chosen theme with
  a candidate roster/canon to hand the curation layer.
- **`chart.getTopTags`** / **`chart.getTopArtists`** / **`geo.getTopArtists`** /
  **`geo.getTopTracks`** → time-varying trend signal (charts refresh; geo is a
  *last-week* window) that injects natural week-to-week freshness and
  region-flavoured show ideas, filtered through the persona's taste so the roster
  never homogenizes.

These feed the SX (variation) requirement: candidate angles grounded in real
data, then rejected if too similar to the persona's recent-shows ledger.

### (b) Artist FACTS for host talk — RESEARCH INPUT ONLY, never aired raw

- **`artist.getInfo`** (bio summary/content, tags, listeners/playcount) and
  **`track.getInfo`** / **`album.getInfo`** (`wiki`, duration, popularity)
  provide colour for host talking points.
- [HARD] **These are crowd-sourced and unsourced.** Last.fm bios/wikis are
  user-edited free text with no citation and frequent errors. They MUST pass the
  station's grounding discipline (KNOWLEDGE-008 dated/sourced/freshness-gated
  fact graph + PROGRAMMING-007 Group PG grounded-voice fact contract + quality
  gate) before any of it reaches air. Last.fm bio text is a *lead to verify*, not
  a fact to broadcast. The authoritative fact owners are MusicBrainz
  (MBMIRROR-017) and KNOWLEDGE-008 — Last.fm only suggests *what to look up*.
- Popularity numbers (`listeners`, `playcount`) are safe to use as *relative*
  framing ("a cult act vs a household name") but should be described loosely, not
  quoted as precise live figures (they're cached snapshots, returned as strings).

### (c) "Last shows" = OUR per-persona show history (we persist it)

Last.fm has **no** way to tell us what shows a persona has run (its events API is
retired, §4, and it has no concept of our personas anyway). The "recent shows"
ledger the anti-repetition spine checks against is **our own persisted data** (SG
show/program model), *informed by* Last.fm research but *owned by us*. Last.fm
supplies the research that shaped each show; the record of which shows ran is
ours.

### (d) "Planned shows" = OUR forward schedule (we persist it)

Likewise, the forward schedule of upcoming per-persona shows is **our own data**
(SD scheduling/direction), produced by the variation engine and consumed by the
director. Last.fm contributes nothing to the schedule itself — it only feeds the
*content* of each planned show. **Last.fm is RESEARCH INPUT; the show history and
the schedule are our own data.**

---

## 6. Last.fm vs MusicBrainz (MBMIRROR-017) vs Discogs — who owns what

| Domain | Authority | Why |
|---|---|---|
| Canonical artist/release/recording identity, MBIDs, relationships, credits | **MusicBrainz (MBMIRROR-017)** | Structured, sourced, editorially governed identity graph; the MBID is the join key. |
| Labels, pressings, release credits (producer/engineer/personnel), catalog numbers | **Discogs** | Deep discography + credit data, especially for electronic/independent releases. |
| Crowd tags (genre/mood/era folksonomy), artist/track **similarity**, **popularity** (listeners/playcount), trend charts, geo trends, crowd bios | **Last.fm** | Behavioural + folksonomy data nobody else has at this scale. |

**Division of labour for SHOWS-020:**

- **Facts / credits / identity → MusicBrainz + Discogs.** When the host states
  something as true (who produced it, what year, which label), the source is
  MBMIRROR-017 / Discogs / KNOWLEDGE-008, never Last.fm.
- **Taste / theme / similarity / popularity → Last.fm.** When the engine asks
  "what's adjacent to this, what theme could I build, what's hot, what defines
  this genre," Last.fm is the right tool — and these are *research signals*, not
  broadcast facts, so they don't need the same citation rigor (but any *derived
  claim* aired about them still passes the grounding gate).
- **No overlap with ANALYSIS-006:** ANALYSIS-006 already has a key-gated Last.fm
  provider for `track.getTopTags` (per-track enrichment). SHOWS-020's LF client
  COMPLEMENTS it at the *artist/theme/show* level (`artist.getInfo` /
  `getSimilar` / `getTopTags` / `tag.*` / `chart.*` / `geo.*`) and must not
  duplicate the per-track tag-enrichment path ANALYSIS-006 owns.

**One-line summary:** MusicBrainz/Discogs tell us *what a record is*; Last.fm
tells us *what listeners call it, what it sounds adjacent to, and how popular it
is* — and only the former is ever aired as fact.

---

## Sources (only URLs actually fetched and verified for this document)

- Last.fm API home — https://www.last.fm/api
- Last.fm API intro (root URL, REST, auth model, "reasonable usage" guidance, User-Agent) — https://www.last.fm/api/intro
- Last.fm API REST guide (root `ws.audioscrobbler.com/2.0/`, example GET) — https://www.last.fm/api/rest
- Last.fm API Terms of Service (clauses 3.1 non-commercial, 4.2.2 attribution, 4.3.4 caching + 100 MB cap, 4.4 rate-limit-at-discretion, partners@last.fm contact) — https://www.last.fm/api/tos
- `artist.getInfo` (params, no-auth, bio/tags/similar/stats) — https://www.last.fm/api/show/artist.getInfo
- `artist.getSimilar` (no-auth, `match` 0–1 similarity score) — https://www.last.fm/api/show/artist.getSimilar
- `track.getInfo` (no-auth, duration ms / listeners / playcount / wiki / tags) — https://www.last.fm/api/show/track.getInfo
- `tag.getInfo` (+ tag.getTopArtists / tag.getTopTracks / tag.getSimilar; reach/taggings/wiki, all no-auth) — https://www.last.fm/api/show/tag.getInfo
- `tag.getSimilar` (no-auth, similarity ranked by listening data) — https://www.last.fm/api/show/tag.getSimilar
- `chart.getTopArtists` (+ chart.getTopTags / chart.getTopTracks; no-auth, page/limit) — https://www.last.fm/api/show/chart.getTopArtists
- `chart.getTopTracks` (no-auth, full response shape + error codes incl. 29 rate-limit) — https://www.last.fm/api/show/chart.getTopTracks
- `geo.getTopTracks` (no-auth, country last-week, `location` metro option) — https://www.last.fm/api/show/geo.getTopTracks
- `album.search` (example of no-auth search shape) — https://www.last.fm/api/show/album.search
- Events API retirement (March 2016 relaunch removed artist.getEvents et al.) — https://github.com/ampache/ampache/issues/1468 ; https://github.com/youpy/ruby-lastfm/issues/81
- Community-cited 5 req/sec rate limit + error 29 in the wild (NOT found verbatim in current ToS clause 4.4) — https://github.com/navidrome/navidrome/issues/2421 ; https://support.last.fm/t/api-rate-limit-for-user-api/112610

> Verification note: the "5 requests/second, averaged over 5 minutes, per IP"
> figure is community-sourced and could NOT be confirmed against the current
> clause 4.4 text fetched 2026-06-23 (which states limits are at Last.fm's "sole
> discretion" with no number). The SPEC should treat 5 req/sec as a hard ceiling
> and target ≤ 1 req/sec to stay safe under both the qualitative ToS and the
> community number.
