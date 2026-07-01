# SPEC-RADIO-TLS-055 — TLS / Let's Encrypt Architecture Research

Status: research (pre-plan)
Author: research synthesis
Date: 2026-07-01

## Overview

golden-shower-radio ships today as a single-host Docker Compose stack that serves
**everything over plain HTTP**. Two surfaces would go public in a real deployment — the
station website + API on the brain HTTP server (`:8080`) and the Icecast MP3 stream
(`:8000/radio`) — and both are cleartext with `0.0.0.0` host binds. Neither backend can
terminate TLS on its own:

- The brain HTTP server is Python stdlib `http.server.ThreadingHTTPServer` with **no
  `SSLContext`** (`brain/server.py:1216`). It cannot serve HTTPS as written.
- Icecast runs on the env-only `moul/icecast` image with **no `icecast.xml` mounted**, so
  the XML-only `<listen-socket ssl>` / `<ssl-certificate>` knobs are not exposable.

Therefore HTTPS on this stack **requires adding a new TLS-terminating reverse-proxy
service**. This document recommends **Caddy with the ACME HTTP-01 challenge by default**
(DNS-01 as the documented fallback), terminating on `:443`, fronting both backends over the
internal `gsr` Docker network, with every backend host-bind narrowed to `127.0.0.1` so the
proxy is the only internet-facing container.

This is an architecture recommendation, not a turnkey plan. The single largest gating fact
is that **no domain, DNS, public IP, or deploy target exists anywhere in the repo today**,
and the host is a WSL2 box with unproven inbound reachability. TLS cannot be issued or served
until the operator supplies those prerequisites (see Prerequisites and Open Decisions).

## Current web-facing surfaces

| Surface | Bind / publish | Plaintext | Intended public | Evidence (file:line) |
|---|---|---|---|---|
| Brain HTTP server (website, `/api/*`, `/status`, `/api/nowplaying`, `/stats`, `/admin`) | host `0.0.0.0:8080` -> container `8080` (default `0.0.0.0`, override `BRAIN_HTTP_HOST`/`BRAIN_HTTP_PORT`) | yes | operator-choice | `brain/config.py:44-45`; `brain/server.py:1216`; `deploy/docker-compose.yml:95-96` |
| Icecast MP3 stream (mount `/radio`) + Icecast admin (`/admin/*`, `/status-json.xsl`) | host `0.0.0.0:8000` -> container `8000` | yes | yes | `deploy/docker-compose.yml:8-17`; `deploy/config/radio.liq:179-189`; `brain/config.py:58-59`; `README.md:26-29,211` |
| Liquidsoap harbor control (`POST /api/skip_cmd`) | container-only `expose 7138` (NO host publish); `gsr` network only | yes | **no** | `deploy/config/radio.liq:57-69`; `deploy/docker-compose.yml:52-56`; `brain/config.py:769-771` |
| slskd Soulseek Web UI + REST API | host `0.0.0.0:5030` -> container `5030`, behind compose profile `slskd` (default OFF) | yes | **no** | `deploy/docker-compose.yml:19-39`; `brain/config.py:24` |

Auth posture that matters for a public TLS front door:

- `/admin/*` is Bearer-token gated (`brain/server.py:851-867`, token from `BRAIN_ADMIN_TOKEN`,
  `brain/config.py:47-51`); empty token => admin surface 404s (feature-off).
- **AUTH BYPASS BUG:** `/admin/stream` is dispatched **before** the auth check
  (`brain/server.py:870-872`), so that one admin sub-route bypasses the bearer gate.
  This must be fixed in code before brain is exposed.
- `/stats` and `/stats/track/*` are **public read-only, ON by default**
  (`brain/config.py:832`; `brain/server.py:447-450`).
- `/`, `/status`, `/api/nowplaying`, `/api/next`, `/api/airing`, `/health` are unauthenticated.
  `/api/next` + `/api/airing` are consumed by Liquidsoap over the internal network and appear
  **internal-only** — they should be blocked at the proxy, not exposed.
- `/api/like` + `/api/like-token` are HMAC-gated and OFF by default (`brain/config.py:797-800`).
- **Secret blast radius:** the brain container mounts `/home/charlie/.claude:/root/.claude`
  (Claude MAX OAuth creds). Any RCE / path-traversal in the stdlib server on a now-public
  brain exfiltrates live credentials. Scope this mount read-only / minimal before exposure.

## ACME challenge decision

**Primary: HTTP-01. Fallback: DNS-01.**

Pick by inbound reachability, which the repo does not yet establish:

- **HTTP-01 (recommended default IF the host has a clean public IP with forwardable `:80`).**
  Validation happens on inbound TCP `:80` (the CA fetches
  `http://DOMAIN/.well-known/acme-challenge/TOKEN`). It is Caddy's zero-config default, needs
  no DNS credentials, and is the simplest correct answer. `:80` must stay open for every
  renewal. Cannot issue wildcards — not needed here (a single `radio.<domain>` +
  `stream.<domain>` scheme is enough).
- **DNS-01 (fallback IF behind CGNAT / no static IP / ISP blocks `:80`).** Proves control via
  a TXT record at `_acme-challenge.DOMAIN`, works entirely outbound, and is the only challenge
  that issues wildcards. **Cost for Caddy:** the stock `caddy` image cannot do DNS-01; it
  requires a **custom `xcaddy` build** baking in the DNS-provider plugin (e.g.
  `caddy-dns/cloudflare`) plus a zone-scoped API token as an env var.
- **TLS-ALPN-01** is not recommended here — useful only when `:80` is blocked but `:443` is
  reachable, and it offers no advantage over DNS-01 for this stack.

Critical nuance: **DNS-01 solves cert issuance, not reachability.** On a CGNAT/WSL2 home host,
DNS-01 will obtain a cert but listeners still get connection-refused on `:443` until inbound
`:443` is forwarded — which then requires a Cloudflare Tunnel, Tailscale Funnel, or a public
VPS relay (the repo anticipates a Hetzner box but none is wired).

Operational rules for whichever challenge is chosen:

- **Always test against the Let's Encrypt STAGING directory first.** The 5-duplicate-certs /
  7-days and 5-failed-validations / hour limits are easy to burn while debugging.
- 2026 cert-lifetime shrink (90-day joined by an opt-in 45-day profile from 2026-05-13) makes
  **hands-off auto-renewal mandatory** — no manual `certbot` runs. Caddy renews internally
  (uses ARI where available; ARI-driven renewals are exempt from rate limits).
- `DNS-PERSIST-01` (2026, production targeted ~Q2 2026, no Caddy/Traefik support yet) is
  **future-facing only** — do not build a day-one dependency on it.

## Reverse-proxy choice + why

**Recommendation: Caddy** as the single TLS-terminating reverse proxy, fronting both
`brain:8080` and `icecast:8000` over the `gsr` network, publishing only `80` and `443`.

| Dimension | Caddy (recommended) | Traefik | nginx + certbot |
|---|---|---|---|
| Automatic ACME | Default; ~5-line Caddyfile issues + auto-renews. Built-in HTTP-01 + TLS-ALPN-01. DNS-01 needs custom `xcaddy` build | Native HTTP-01 **and** DNS-01, no custom build; certs in `acme.json` (chmod 600 volume) | No native ACME; separate certbot/acme.sh container + renewal cron + nginx reload hook (3+ moving parts) |
| Compose integration | Lowest: 1 service, 1 Caddyfile, 1 volume, **no docker.sock** | Label auto-discovery but **requires mounting `docker.sock`** | Highest: nginx + certbot + shared cert volume + reload coordination |
| Config verbosity | Lowest: auto `X-Forwarded-*`, auto Host header, auto `:80`->`:443` redirect | Medium, two-layered (static + labels) | Highest: manual `server`/`ssl_certificate`/`proxy_set_header`/upstream keepalive |
| Renewal / maintenance | Fully hands-off, internal to daemon | Hands-off, internal to daemon | Out-of-band cron + reload; **highest burden** |
| Streaming (Icecast `/radio`) | `flush_interval -1` (single directive; no buffering, keeps upstream alive) | Streams by default; must not attach buffering middleware; verify timeouts | `proxy_buffering off; proxy_request_buffering off; proxy_http_version 1.1; chunked_transfer_encoding on; proxy_read_timeout 3600s` |
| Rate limiting | **Not in stock binary** — needs `xcaddy` + `mholt/caddy-ratelimit` | **Built-in** middleware | Built-in (`limit_req`) |
| Security footprint here | No socket; smallest blast radius | `docker.sock` mount next to Claude OAuth creds = root-equivalent risk; `exposedByDefault=true` can auto-expose the unauthenticated harbor/slskd | certbot sidecar + cron surface |

Why Caddy wins for **this** stack specifically:

1. Automatic HTTPS with the least config matches the station's autonomous, always-on operating
   philosophy ("the radio never stops"; no operator to babysit a `certbot` cron/reload dance).
   The 45-day-cert transition makes internal auto-renew effectively mandatory.
2. **No `docker.sock` needed.** Traefik's docker-provider label routing requires mounting
   `docker.sock` into the one internet-facing container — on a host that also bind-mounts
   Claude MAX OAuth creds RW into brain, that is a root-equivalent blast radius. Traefik's
   `exposedByDefault=true` also risks auto-publishing the unauthenticated Liquidsoap harbor
   (`:7138`) unless explicitly disabled per service — a regression the current no-proxy design
   does not have.
3. `flush_interval -1` is the single directive that solves the Icecast streaming-buffering
   problem; nginx needs five directives and a certbot sidecar for the same result.

When the others would win: **Traefik** if the stack grew to many dynamically-added services
needing label auto-discovery (not the case — two stable public surfaces) and if built-in rate
limiting outweighed the `docker.sock` risk. **nginx + certbot** only if deep nginx expertise
or tuning dominated; it is strictly more moving parts for the identical result and a poor fit
for hands-off autonomy — assessed **not feasible end-to-end** here without the same
prerequisites plus a fragile cross-container reload hook.

**Rate-limiting note:** the stock Caddy binary has no rate limiter. To throttle public
`/api/*`, `/stats`, `/health` on the thread-per-connection stdlib server, build a custom Caddy
image via `xcaddy` with `mholt/caddy-ratelimit`. (This is the same custom-image mechanism
DNS-01 would need, so both can be baked into one image if required.)

## Icecast over TLS — approach + streaming caveats

**Approach: proxy the listener side through Caddy on `:443`. Do NOT pursue native Icecast TLS.**

Reasons specific to this stack:

- `moul/icecast` is env-only with no `icecast.xml` mount, so native `<listen-socket ssl>` /
  `<ssl-certificate>` is not exposable without replacing the image or mounting a full custom
  XML — heavier than adding a proxy.
- The brain website on `:8080` needs external TLS regardless (stdlib server, no `SSLContext`),
  so **one proxy covers both surfaces at once**.
- Native TLS renewal would need a post-hook to rebuild `bundle.pem` (fullchain **then**
  privkey) and **restart Icecast — which drops every connected listener**. A proxy reload swaps
  the cert with no listener drop.

The well-known **"don't reverse-proxy Icecast 2.4.x" warning does NOT apply here.** That caveat
is about the **source-upload** side (`Expect: 100-continue`, infinite content-length, no
chunked encoding). In this stack Liquidsoap pushes to `icecast:8000` **directly over the
internal `gsr` network** (`radio.liq:179-189`); the source connection never traverses the proxy.
Only listener playback crosses the proxy, which proxies fine on 2.4.x.

Load-bearing streaming caveats:

- **Buffering MUST be off** on the `/radio` route or the continuous MP3 stalls/cuts every few
  seconds and now-playing metadata sticks. Caddy: `reverse_proxy` with `flush_interval -1`
  (also keeps the upstream request alive if a client disconnects). Long/effectively-infinite
  read timeout for the continuous connection.
- **Mixed content is the real driver.** Since Chrome 80 (2020) browsers block HTTP subresources
  on an HTTPS page. Once the site is HTTPS, an embedded `http://host:8000/radio` `<audio>`
  source is blocked — so the stream **must** also be HTTPS. Serving it through the same TLS
  edge fixes both surfaces in one move. The website player URL hint
  (`brain/config.py:58-59` `icecast_public_port`/`icecast_mount`; player emits
  `http://host:8000/radio`) must be updated to `https://stream.<domain>/radio` — this is a
  **code change**, not just proxy config.
- **Icecast must live at a host/URL root, not a sub-path.** The admin UI, `/status-json.xsl`,
  and mount handling emit absolute URLs, so proxy Icecast at a dedicated subdomain
  (`stream.<domain>` -> `icecast:8000`) with `/radio` passing through unchanged. Put the brain
  website on a different host/root (`radio.<domain>` or apex).
- Set Icecast's advertised public `<hostname>` (`moul` env `ICECAST_HOSTNAME`, if honored by
  the pinned tag) to the public domain, or `/status-json.xsl` and stream URLs advertise the
  internal container host:port.
- **CORS:** cross-origin metadata JS (`icecast-metadata-js`) and any fetch of
  `/status-json.xsl` need `Access-Control-Allow-Origin` + exposed `Icy-MetaInt`. The env-only
  image exposes no `http-headers` config, so inject CORS **at the proxy**.
- **Block Icecast `/admin/*` and `/status-json.xsl` at the proxy** (admin surface + listener-
  count leak) unless a specific web player requires status JSON.

## Security / exposure matrix

Ideal end-state: the **only two host ports reachable from the internet are `80` and `443`**,
both owned by Caddy. Everything else is proxied behind `443` or kept internal.

| Surface | Public? | How | Compose change |
|---|---|---|---|
| Caddy `:80` (ACME + `:80`->`:443` redirect) | **PUBLIC** | `0.0.0.0:80` | new service publishes `80:80` |
| Caddy `:443` (TLS edge) | **PUBLIC** | `0.0.0.0:443` | new service publishes `443:443` |
| Brain `:8080` (site, `/status`, `/api/nowplaying`, `/stats`) | via `:443` only | proxy -> `brain:8080` | `8080:8080` -> `127.0.0.1:8080:8080` **and** `BRAIN_HTTP_HOST=127.0.0.1` (or drop host-publish, reach as `brain:8080`) |
| Icecast `:8000` (`/radio`) | via `:443` only (`stream.<domain>`) | proxy -> `icecast:8000`, `flush_interval -1` | `8000:8000` -> `127.0.0.1:8000:8000` (or drop host-publish) |
| Brain `/admin/*` | **BLOCKED** at proxy | proxy returns 404/403 for `/admin` + `/admin/*` | plus fix `/admin/stream` pre-auth bypass; add explicit `BRAIN_ADMIN_ENABLED` off-switch (default false) |
| Brain `/api/next`, `/api/airing` | **BLOCKED** (internal-only) | not in proxy allowlist | consumed by Liquidsoap over `gsr` |
| Icecast `/admin/*`, `/status-json.xsl` | **BLOCKED** at proxy | proxy denies path | admin user is `admin` + `ICECAST_ADMIN_PASSWORD` — never public |
| slskd `:5030` | **NEVER public, NEVER proxied** | stays profile-gated (default OFF) | when enabled: `5030:5030` -> `127.0.0.1:5030:5030` (localhost / SSH-tunnel / VPN only) |
| Liquidsoap harbor `:7138` | **NEVER public, NEVER proxied** | stays `expose` only (internal `gsr`) | unchanged — do not regress |

Additional hardening the SPEC must encode:

- **Docker bypasses `ufw`.** A bare `8000:8000` publish stays open to `0.0.0.0` even with a
  `ufw deny`. The real fix is `127.0.0.1:` binds in compose **plus** a cloud/provider firewall
  (security group) as the outer default-deny layer (allow only `22`, `80`, `443`).
- TLS defaults: rely on Caddy secure defaults (min TLS 1.2, prefer 1.3, modern ciphers/curves,
  OCSP stapling on). Do not hand-roll cipher lists.
- Security headers are **not** automatic: add HSTS (`max-age>=31536000; includeSubDomains`;
  add `preload` **last**, only after HTTPS is proven — it is effectively irreversible),
  `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` (or CSP `frame-ancestors 'none'`),
  `Referrer-Policy: strict-origin-when-cross-origin`, and a CSP whose `media-src` / `connect-src`
  includes the stream origin (or the player breaks).
- Persist Caddy `/data` (certs + ACME account key) on a named volume, chmod-protected; losing
  it forces re-issuance and risks rate limits.
- Teach `brain/server.py` to read `X-Forwarded-For` / `X-Forwarded-Proto` (real client IP for
  `/stats` + like-token HMAC rate-limiting; awareness of TLS). Optionally set
  `protocol_version='HTTP/1.1'` + `Content-Length` for upstream keep-alive.

## Prerequisites (operator must provide)

1. **A registered domain name** — none exists in the repo (Faroese theme suggests `.fo`, but
   nothing is registered/referenced; the only "Hetzner" mention is an unrelated deferred
   MusicBrainz-mirror seam). ACME cannot issue without a resolvable public hostname.
2. **Authoritative DNS control**: create A/AAAA records for `radio.<domain>` and
   `stream.<domain>` pointing at the host; for DNS-01, also create/delete TXT records — ideally
   via a provider with an API (Cloudflare, deSEC) + a zone-scoped API token as a secret.
3. **Public inbound reachability** — the true gating unknown on this WSL2 home host (double-NAT
   + likely CGNAT). HTTP-01 needs inbound `:80`; serving needs inbound `:443` regardless of
   challenge. If behind CGNAT / blocked `:80`: add a Cloudflare Tunnel, Tailscale Funnel, or a
   public VPS relay (over WireGuard/Tailscale). Confirm this **before buying a domain**.
4. **A persistent volume** for Caddy `/data` (cert + ACME account key store).
5. **An ACME account email** (Caddy `email` global option) for expiry/problem notices, and
   initial testing against the Let's Encrypt **STAGING** endpoint.
6. **Code fixes before exposure** (hard gate, not polish): move `_check_admin_auth()` ahead of
   the `/admin/stream` dispatch (`brain/server.py:870-873`); add `BRAIN_ADMIN_ENABLED`
   (default false); teach brain `X-Forwarded-*`; emit the HTTPS stream URL in the player;
   scope the `/home/charlie/.claude` mount read-only / minimal.
7. **Compose surgery**: rebind `brain:8080` and `icecast:8000` to `127.0.0.1` (+ `BRAIN_HTTP_HOST`),
   keep slskd `:5030` profile-gated and localhost-bound when on, keep harbor `:7138` `expose`-only,
   add the Caddy service publishing `80`/`443`.
8. **Custom Caddy image (only if required)**: `xcaddy` build baking in DNS-provider plugin
   (for DNS-01) and/or `mholt/caddy-ratelimit` (for public-endpoint throttling). Stock
   `caddy:2` suffices for HTTP-01 without rate limiting.

## Open decisions for the operator

1. **Domain + DNS API availability.** Is a domain registered (or will one be), and is it on a
   provider with an API token for DNS-01? This gates the challenge choice.
2. **ACME challenge type.** HTTP-01 (simplest, needs open inbound `:80`, stock Caddy) vs DNS-01
   (works behind CGNAT/blocked-`:80`, unlocks wildcard, needs custom `xcaddy` image + DNS token).
3. **Inbound reachability path.** Direct public IP with port-forward, or (for CGNAT/WSL2) a
   Cloudflare Tunnel / Tailscale Funnel / VPS relay? DNS-01 fixes issuance but not reachability.
4. **Serve the audio stream over the same TLS front, or keep it separate?** Recommended: same
   `:443` edge (`stream.<domain>`) to avoid mixed-content blocking. Keeping a parallel plain-HTTP
   mount is an option only for very old SNI-less hardware radios (cannot be embedded on the site).
5. **Reverse proxy engine.** Caddy (recommended) vs Traefik (built-in rate limiting, but
   `docker.sock` risk) vs nginx+certbot (most moving parts).
6. **Rate limiting now or later.** Ship a custom Caddy image with `mholt/caddy-ratelimit` from
   day one, or accept unthrottled public `/api` + `/stats` initially?
7. **Public `/stats` posture.** `/stats` is public-by-default — keep it public read-only behind
   HTTPS + rate limits, or block it at the proxy for a first exposure?

## Risks

- **No public host / WSL2 reachability is the strongest independent blocker** and applies to
  every approach equally — a certificate cannot fix connection-refused. Resolve before spending
  on a domain.
- **`/admin/stream` pre-auth bypass** (`brain/server.py:870-872`): world-reachable admin
  sub-route the moment brain is exposed, until fixed in code.
- **OAuth-cred blast radius:** `/home/charlie/.claude:/root/.claude` on a now-public brain
  (stdlib server, no timeouts/body limits/traversal audit) — an RCE/traversal exfiltrates live
  Claude MAX credentials. Scope read-only/minimal first.
- **`0.0.0.0` host binds bypass `ufw`:** adding `:443` does not remove the plaintext downgrade
  path; every backend stays cleartext-reachable until rebound to `127.0.0.1` + a cloud firewall.
- **Mixed content:** site HTTPS + stream HTTP silently breaks the player while the API looks
  fine — easy to miss if only the API is tested.
- **Streaming buffering left on:** classic Icecast-behind-proxy failure (audio cuts every few
  seconds, stuck metadata). Must set `flush_interval -1` + long read timeout.
- **Rate-limit self-DoS during setup:** 5-duplicate-certs / week and 5-failed-validations / hour
  are easy to hit debugging a broken config — use STAGING first.
- **45-day certs (2026):** any manual/cron-fragile renewal is a time bomb; a stopped proxy
  silently lets certs lapse. Auto-renewing proxy (Caddy) required.
- **Stock Caddy has no rate limiter:** deploying the stock image leaves public `/api` + `/stats`
  unthrottled on a thread-per-connection origin; slow-client floods can exhaust threads.
- **Cert-store loss:** not persisting Caddy `/data` forces re-issuance and can trip rate limits.
- **DNS-01 with Caddy** adds a custom `xcaddy` image to maintain (only incurred if wildcard or
  firewalled-`:80` forces it).

## Citations

- https://letsencrypt.org/docs/challenge-types/
- https://letsencrypt.org/docs/rate-limits/
- https://letsencrypt.org/2025/12/02/from-90-to-45
- https://letsencrypt.org/2026/02/24/rate-limits-45-day-certs
- https://letsencrypt.org/2026/02/18/dns-persist-01
- https://caddyserver.com/docs/automatic-https
- https://caddyserver.com/docs/caddyfile/directives/reverse_proxy
- https://caddyserver.com/docs/caddyfile/directives/tls
- https://caddyserver.com/docs/caddyfile/options
- https://doc.traefik.io/traefik/https/acme/
- https://doc.traefik.io/traefik/setup/docker
- https://github.com/nginx/nginx-acme/blob/main/README.md
- https://www.icecast.org/docs/icecast-trunk/config_file/
- https://icecast.org/docs/icecast-2.4.1/config-file.html
- https://wiki.xiph.org/Icecast_Server/known_reverse_proxy_restrictions
- https://www.cloudrad.io/help/https-streaming
- https://github.com/aswild/icecast-notes
- https://caddyserver.com/docs/json/apps/http/servers/routes/handle/reverse_proxy/flush_interval/
- https://github.com/eshaz/icecast-metadata-js
- https://github.com/mholt/caddy-ratelimit
