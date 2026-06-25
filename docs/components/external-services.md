# External Services & API Keys

A practical operator reference for every external service the station touches.
Organised by whether you **need** an account to use it.

---

## Summary table

| Service | Requires account? | Cost | Needed for | Env var / Config |
|---|---|---|---|---|
| **Claude MAX** | Yes — MAX subscription | Subscription | LLM (curation, talk, research) — required | OAuth creds in `~/.claude` |
| **Soulseek / slskd** | Yes — Soulseek account | Free | P2P music acquisition | `SLSKD_API_KEY` + slskd own config |
| **AcoustID** | Yes — free app key | Free | Audio fingerprint ID | `BRAIN_ACOUSTID_API_KEY` |
| **Last.fm** | Yes — free API key | Free | Genre enrichment + show research | `BRAIN_LASTFM_API_KEY` |
| **Discogs** | Yes — free personal token | Free | Cross-check enrichment | `BRAIN_DISCOGS_TOKEN` |
| **The Guardian** | Yes — free developer key | Free | News enrichment | `BRAIN_GUARDIAN_API_KEY` |
| **TheAudioDB** | No — public test key built in | Free | Genre/mood metadata | `BRAIN_THEAUDIODB_KEY` (default `123`) |
| **MusicBrainz** | No — User-Agent only | Free | Track identification + metadata | `BRAIN_MB_USER_AGENT` |
| **Cover Art Archive** | No | Free | Album artwork embed | _(automatic when albumart enabled)_ |
| **yt-dlp / YouTube** | No (for public content) | Free | Acquisition fallback | _(no key)_ |
| **RSS news feeds** | No | Free | News + music press content | `BRAIN_NEWS_FEEDS` (default seeded) |
| **Human-DJ sources** | No | Free | Show research (off by default) | per-source flag |
| **teldutala.fo** | No — unauthenticated | Free | Faroese TTS (planned, not yet built) | _(not yet wired)_ |
| **ElevenLabs** | Yes — paid API key | Paid | Premium TTS (future opt-in) | _(not yet wired)_ |

---

## Services that require an account

### Claude MAX subscription — REQUIRED

The brain's intelligence runs entirely through Claude. By default it authenticates
via the host's `~/.claude` OAuth credentials — a logged-in **Claude MAX subscription**.

#### Auth modes (`BRAIN_LLM_AUTH`)

| Mode | Value | How it works | When to use |
|---|---|---|---|
| **OAuth / mount** | `oauth` *(default)* | Reads `~/.claude/.credentials.json` mounted from the host | Standard setup with a logged-in host machine |
| **OAuth / token** | `token` | Reads `CLAUDE_CODE_OAUTH_TOKEN` from env — no mount needed | CI, headless Docker, secondary account |
| **API key** | `api_key` | Passes `ANTHROPIC_API_KEY` to the Claude CLI subprocess | Pay-per-use billing (uncommon, billed separately) |

**Default (`oauth`) setup:**
1. Subscribe to Claude MAX at claude.ai
2. Install the Claude CLI: `npm install -g @anthropic-ai/claude-code`
3. Log in: `claude login`
4. Confirm `~/.claude/.credentials.json` exists on the host

**Headless / token setup** (e.g., second account or CI):
1. Run `claude setup-token` on any logged-in machine to generate a token
2. Add to `secrets/.env`:
   ```dotenv
   BRAIN_LLM_AUTH=token
   CLAUDE_CODE_OAUTH_TOKEN=your-token-here
   ```
   No `~/.claude` mount required.

**API key setup** (pay-per-use, not recommended for daily use):
```dotenv
BRAIN_LLM_AUTH=api_key
ANTHROPIC_API_KEY=sk-ant-...
```

**IMPORTANT:** Do NOT set `ANTHROPIC_API_KEY` without also setting `BRAIN_LLM_AUTH=api_key`.
If `ANTHROPIC_API_KEY` is present without the mode override, the brain strips it at boot
(in `brain/main.py`) and `brain/llm.py` also strips it from every subprocess — three
layers of defense ensure accidental key presence never silently bills pay-per-use credits.

**Config fields:** `anthropic_model` (`ANTHROPIC_MODEL`, default `claude-sonnet-4-6`) ·
`llm_auth_mode` (`BRAIN_LLM_AUTH`, default `oauth`)

---

### Soulseek / slskd — Required if using `--with-slskd`

Soulseek is the P2P music network. `slskd` is the daemon that connects to it and
exposes a local HTTP API the brain uses to search and download.

**Two separate things to configure:**

**1. Soulseek account (username + password → slskd's own settings)**

Create a free account at soulseek.org. Your username and password go into slskd's
own web UI or config file — not in this project's `secrets/.env`. Once slskd is
running and logged in, it stays connected on its own.

**2. slskd API key → `secrets/.env`**

slskd generates an API key for its local HTTP interface. Copy it from slskd's web
UI (Settings → API) and set it in `secrets/.env`:

```dotenv
SLSKD_API_KEY=your-slskd-api-key
```

Without this key the brain cannot talk to slskd (returns 401). The station still
plays the existing library; acquisition simply doesn't happen.

**slskd is off by default.** Start it with `bash scripts/run.sh --with-slskd`. Do
not enable it permanently in the compose file — it is user-initiated only.

---

### AcoustID — Optional (recommended)

AcoustID fingerprints audio files and resolves them against MusicBrainz recordings.
It is the most reliable way to identify music with wrong or missing tags.

**How to get a key:**
1. Register at acoustid.org/login (free, instant)
2. Go to "Your applications" → create a new application
3. Copy the API key

**Set in `secrets/.env`:**
```dotenv
BRAIN_ACOUSTID_API_KEY=your-key-here
```

**Without a key:** fingerprint identification is skipped gracefully. The brain
falls back to text-match (artist + title string search) against MusicBrainz. Tag
correction still works, just less accurately on files with bad metadata.

---

### Last.fm — Optional

Last.fm is used in two independent places:

1. **Metadata enrichment** (`BRAIN_ENRICHMENT_ENABLED`): genre consensus — one of
   several sources the enricher cross-checks for genre/mood tags
2. **Show research** (`BRAIN_SHOWS_ENABLED` + `shows_enabled`): the Last.fm research
   client (`brain/lastfm.py`) fetches similar-artist and tag data for show prep

**How to get a key:**
1. Create a free account at last.fm
2. Go to last.fm/api → "Get an API account"
3. Copy the API key (the secret is not needed)

**Set in `secrets/.env`:**
```dotenv
BRAIN_LASTFM_API_KEY=your-key-here
```

**Without a key:** both Last.fm providers log once at startup that the key is absent
and return empty results. Everything else continues normally. The stats site can
optionally use it for taste-map similarity (`BRAIN_STATS_LASTFM_ENABLED`) — also
off by default.

---

### Discogs — Optional

Discogs provides a cross-check for MusicBrainz enrichment results, adding a second
authoritative source for release metadata.

**How to get a token:**
1. Create a free account at discogs.com
2. Go to discogs.com/settings/developers → "Generate new token"
3. Copy the personal access token (no OAuth needed)

**Set in `secrets/.env`:**
```dotenv
BRAIN_DISCOGS_TOKEN=your-token-here
```

**Without a token:** the Discogs cross-check provider is disabled — it logs once
at startup and returns empty. MusicBrainz and TheAudioDB enrichment continue.

---

### The Guardian — Optional

The Guardian's developer API provides structured news content for the ORCH-005
news ledger, on top of the free RSS feeds.

**How to get a key:**
1. Register at open-platform.theguardian.com (free)
2. Request an API key (approved instantly)

**Set in `secrets/.env`:**
```dotenv
BRAIN_GUARDIAN_API_KEY=your-key-here
```

**Without a key:** Guardian enrichment is disabled gracefully. The news ledger
continues with the default RSS/Atom feed set (see Free sources below).

Requires `BRAIN_WORLD_MODEL_ENABLED=1` (ORCH-005 nervous system) to be active.

---

## Services with no account (or built-in defaults)

### TheAudioDB

Public API for genre, mood, biography, and related-artist data. The brain ships
with the free public test key `123` already set as the default.

```
BRAIN_THEAUDIODB_KEY=123   ← this is the actual public test key, not a placeholder
```

You can register at theaudiodb.com for a personal key, but the public `123` key
works for the station's query rate. No action required.

---

### MusicBrainz

The authoritative open music database. No API key needed — MusicBrainz only asks
for an identifying User-Agent string.

```
BRAIN_MB_USER_AGENT=GoldenShowerRadio/1.0 (radio brain)   ← default
```

Rate limit: 1 request/second on the public API. The brain's persistent result
cache (`BRAIN_MB_CACHE_ENABLED`, default ON) means each recording is only queried
once, making the public API sufficient at the station's scale.

**Optional: self-hosted mirror**

Set `BRAIN_MB_MIRROR_HOST` to point the brain at your own MusicBrainz mirror
(e.g., a Hetzner-hosted instance per MBMIRROR-017). Not yet wired in the code —
the config field is the seam.

---

### Cover Art Archive

The open album art database (part of the MusicBrainz ecosystem). No credentials
needed. The brain fetches front cover art and embeds it in the audio file when
`BRAIN_ALBUMART_ENABLED=1` (default ON) and `BRAIN_ENRICH_WRITE_FILES=1` (default ON).

---

### yt-dlp / YouTube

Used as the acquisition fallback when slskd cannot find a track. No API key
needed for public content. The brain shells out to `yt-dlp` (installed in the
image) with configurable timeout (`BRAIN_YTDLP_TIMEOUT_SEC`, default 120 s) and
size/duration caps.

No cookies or YouTube account are configured. A YouTube account would allow
access to age-restricted content but is not wired.

---

### RSS news feeds (default set)

The ORCH-005 news ledger polls a default set of RSS/Atom feeds — no credentials:

| Feed ID | Source | Type |
|---|---|---|
| `kvf` | kvf.fo | Faroese news (RSS) |
| `dimma` | dimma.fo | Faroese news (RSS) |
| `svt` | svt.se/nyheter | Nordic news (RSS) |
| `apnews` | apnews (via RSSHub) | International news (RSS) |
| `nme` | nme.com | Music press (RSS) |
| `the_fader` | thefader.com | Music press (RSS) |
| `paste` | pastemagazine.com/music | Music press (RSS) |
| `dj_magazine` | djmag.com | Electronic/DJ press (RSS) |
| `future_music` | futuremusic.com | Production/gear press (RSS) |

These are active when `BRAIN_WORLD_MODEL_ENABLED=1`. Add or replace feeds by
setting `BRAIN_NEWS_FEEDS` to a JSON array of `FeedEntry` records — see
`brain/news_feeds.py` for the schema.

---

### Human-DJ observation sources

The SHOWS-020 show-research system can observe what human DJs are playing as
editorial research leads. All sources use public APIs — no accounts needed.
**All are OFF by default** and must be explicitly enabled:

| Source | Enable flag | Notes |
|---|---|---|
| KEXP | `BRAIN_KEXP_THREAD_ENABLED=1` | KEXP `/v2/plays` — high-quality indie/world editorial |
| BBC Radio 1 | `BRAIN_BBC_THREAD_ENABLED=1` | BBC programmes segments API |
| NTS Radio | `BRAIN_NTS_THREAD_ENABLED=1` | NTS `/api/v2/live` — show/host/genre context |
| Sveriges Radio | `BRAIN_SR_THREAD_ENABLED=1` | SR API |
| ASOT | `BRAIN_ASOT_THREAD_ENABLED=1` | A State of Trance cue file |

Human-DJ clusters are editorial research leads — the AI uses them as a taste
signal, never as a direct track source or auto-acquisition trigger.

---

## Future services (not yet built)

### teldutala.fo — Planned (Faroese TTS)

The operator's own Acapela-backed Faroese TTS web service. **No credentials
needed** — the API is unauthenticated. Two-step: `POST /api/v1/tts → audioId`,
then poll until audio is ready.

Status: fully SPEC'd in VOICE-002 Group V-D. Not yet wired in `brain/voice.py`.
Adult voices only: `Hanna22k_NT` (female), `Hanus22k_NT` (male).

---

### ElevenLabs — Future opt-in (premium cloud TTS)

Commercial cloud TTS — highest quality but pay-per-character. **Not wired.**
Would require an API key and explicit opt-in. This will never be enabled by
default — no surprise billing.

```dotenv
# Future — not active yet
# ELEVENLABS_API_KEY=your-key-here
```

---

## Setting secrets

All API keys belong in `secrets/.env` (gitignored, never committed):

```dotenv
# secrets/.env — example with all optional keys
STATION_NAME=Golden Shower Radio
ANTHROPIC_MODEL=claude-sonnet-4-6
ICECAST_SOURCE_PASSWORD=change-me-please

# LLM auth (default: oauth — reads ~/.claude from host mount)
# BRAIN_LLM_AUTH=oauth             # default — requires ~/.claude mount
# BRAIN_LLM_AUTH=token             # headless OAuth, set CLAUDE_CODE_OAUTH_TOKEN too
# CLAUDE_CODE_OAUTH_TOKEN=...      # only when BRAIN_LLM_AUTH=token
# BRAIN_LLM_AUTH=api_key           # pay-per-use, set ANTHROPIC_API_KEY too
# ANTHROPIC_API_KEY=sk-ant-...     # only when BRAIN_LLM_AUTH=api_key

# Soulseek acquisition (only when running --with-slskd)
SLSKD_API_KEY=your-slskd-api-key

# Optional enrichment
BRAIN_ACOUSTID_API_KEY=your-acoustid-key
BRAIN_LASTFM_API_KEY=your-lastfm-key
BRAIN_DISCOGS_TOKEN=your-discogs-token
BRAIN_GUARDIAN_API_KEY=your-guardian-key
```

The brain will start and play music with only `STATION_NAME`,
`ICECAST_SOURCE_PASSWORD`, and the Claude OAuth credentials. Every other service
degrades gracefully when its key is absent.
