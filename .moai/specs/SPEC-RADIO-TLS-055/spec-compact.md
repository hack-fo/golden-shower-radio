---
id: SPEC-RADIO-TLS-055
version: 0.1.1
status: draft
created: 2026-07-01
updated: 2026-07-01
author: charlie
priority: High
issue_number: 55
labels: [radio, tls, https, security, devops]
---

# SPEC-RADIO-TLS-055 — Compact

**What:** a TLS/HTTPS architecture via Let's Encrypt using a **single Caddy
reverse-proxy container as the only internet-facing service**. It terminates TLS
on `:443`, auto-issues + auto-renews certs, proxies `radio.<domain>` →
`brain:8080` (website + public API) and `stream.<domain>` → `icecast:8000`
(the `/radio` mount) over the internal `gsr` network, and every backend host-bind
is narrowed so nothing bypasses TLS. **HTTP-01 default, DNS-01 documented
fallback.** Brownfield DevOps/security SPEC.

**Why now:** all web-facing surfaces are plain HTTP (`0.0.0.0` binds); the user
intends to host publicly and cannot run plain HTTP. Neither backend can terminate
TLS itself — the brain stdlib `ThreadingHTTPServer` has **no `SSLContext`**
(`brain/server.py:1216`), the `moul/icecast` image is **env-only, no XML mount**
(`docker-compose.yml:8`–`:17`). One proxy edge covers both.

## Load-bearing facts (verified 2026-07-01)

1. **Dedicated server ⇒ HTTP-01 default.** Target is a dual-Xeon box with
   direct/port-forwarded inbound, not the WSL2 dev host. DNS-01 is the fallback
   for CGNAT/blocked-`:80` (needs custom `xcaddy` + scoped DNS token) and fixes
   *issuance* only, not *reachability*.
2. **No domain yet ⇒ prerequisite, not blocker.** No domain/DNS/public IP exists.
   ACME cannot issue until a resolvable hostname exists; until then the stack
   degrades to plain HTTP (TLS opt-in).
3. **`BRAIN_HTTP_HOST=127.0.0.1` would BREAK proxying.** `cfg.http_host`
   (`config.py:44`) is the whole-server bind (`server.py:1216`); `127.0.0.1`
   binds container-loopback ⇒ Caddy (a different container) can't reach
   `brain:8080` over `gsr`. Correct fix: **drop the host `ports:` publish**, keep
   the app bind on `0.0.0.0`. The Docker publish `127.0.0.1:8080:8080` (host
   loopback) is a *different* mechanism, fine for debug. (Corrects the naive
   research reading.)
4. **HTTPS stream URL is a code change.** `brain/website.py:14`–`:17` composes
   `http://<host>:8000/radio` from `cfg.icecast_public_port`/`icecast_mount`;
   mixed-content blocking forces `https://stream.<domain>/radio` (new config +
   website change).

## Requirements (37 REQ / 5 NFR, 1:1 with acceptance.md)

- **TP** TLS proxy: 001 one-edge-only-edge (`:80`+`:443`) · 002 terminate+forward
  · 003 auto-issue · 004 hands-off renew (45-day-cert era) · 005 HTTP-01 default
  · 006 [Opt] DNS-01 fallback (custom xcaddy + scoped token; issuance-not-reach)
  · 007 `:80`→`:443` redirect · 008 secure defaults, no hand-rolled ciphers.
- **TR** routing/streaming: 001 radio→brain · 002 stream→icecast · 003
  `flush_interval -1` + long read timeout on `/radio` · 004 never native
  Icecast/brain TLS · 005 emit HTTPS player URL (anti-mixed-content) · 006 Icecast
  at host root not sub-path.
- **TH** hardening: 001 brain not public (drop publish; NOT `BRAIN_HTTP_HOST=127`)
  · 002 icecast not public · 003 block `/admin*` at edge (defense-in-depth over
  assumed pre-auth fix) · 004 block Icecast `/admin*`+`/status-json.xsl` · 005
  `/api/next`+`/api/airing` internal-only · 006 slskd never public/proxied · 007
  harbor stays `expose`-only · 008 trust `X-Forwarded-For/Proto` · 009 provider
  firewall 22/80/443 + Docker-bypasses-ufw ⇒ binds are real control · 010 [Opt]
  admin off/unproxied for public (ref FEATUREGATE-053) · 011 `.claude` mount RO.
- **TS** headers: 001 HSTS · 002 [Opt] preload last/irreversible · 003
  nosniff+X-Frame+Referrer-Policy · 004 CSP media-src/connect-src ⊇ stream origin
  · 005 [Opt] CORS at proxy for metadata JS.
- **TO** ops/prereq: 001 domain+DNS prerequisite (primary gate) · 002 graceful
  plain-HTTP degradation when absent · 003 STAGING-first · 004 persist Caddy
  `/data` volume · 005 auto-reissue on store loss (rate-limit aware) · 006 ACME
  email · 007 reachability prerequisite (`:80` issue+renew, `:443` serve; WSL2
  caveat = dev-only).
- **NFR-TLS-1..5:** no plaintext public path · stream continuity preserved · renew
  without listener drop · no secret exposure (no docker.sock, RO `.claude`,
  gitignored tokens) · `:80`+challenge-path reachable for renewal.

## [DELTA] surface

- **NEW** `deploy/Caddyfile` — global (ACME email, STAGING toggle) + `radio`/
  `stream` site blocks + `flush_interval -1` + `/admin*`/`/api/next`/`/api/airing`
  /`status-json.xsl` blocks + security headers/CSP; commented DNS-01 variant.
- **NEW** `caddy` service + `caddy_data`/`caddy_config` volumes in
  `deploy/docker-compose.yml` (stock `caddy:2`, no `docker.sock`, opt-in profile).
- **MODIFY** `deploy/docker-compose.yml` — drop brain `8080:8080` (`:95`–`:96`)
  + icecast `8000:8000` (`:15`–`:16`) host publishes; `.claude` mount →`:ro`
  (`:91`); add `BRAIN_STREAM_PUBLIC_URL`; set `ICECAST_HOSTNAME` if honored.
- **MODIFY** `brain/config.py` — add `stream_public_url` (empty⇒HTTP fallback);
  NOTE `http_host` (`:44`) stays `0.0.0.0` under proxying (do not "harden").
- **MODIFY** `brain/server.py` — trust `X-Forwarded-For/Proto`; assume (not own)
  the `/admin/stream` pre-auth-bypass fix (`:870`–`:873`).
- **MODIFY** `brain/website.py` — emit `stream_public_url` player URL else
  `http://<host>:<port>/radio` fallback (`:5`, `:14`–`:17`).
- **EXISTING** Liquidsoap→Icecast source (`radio.liq:179`–`:189`) stays on `gsr`
  (source-side proxy caveat N/A); harbor `expose 7138` (`compose:54`–`:55`) and
  slskd profile gating unchanged — must not regress.

## Cross-SPEC relationships (reference, do not duplicate)

- **FEATUREGATE-053** owns `BRAIN_ADMIN_ENABLED` (admin hard on/off) — recommend
  admin disabled/unproxied for public; reference, don't re-specify (REQ-TH-010).
- **`/admin/stream` pre-auth bypass** fixed by a separate change — assumed to
  land; edge still blocks `/admin*` as defense-in-depth (REQ-TH-003).

## Exclusions (What NOT to Build)

No native Icecast TLS · no stdlib-brain TLS · no Cloudflare Tunnel/Tailscale as
primary design (documented CGNAT fallback only) · no CDN/multi-node/HA · no rate
limiter in stock build (custom-xcaddy noted, out of scope) · no `/admin/stream`
code fix (separate SPEC) · no admin on/off design (FEATUREGATE-053) · no domain
purchase/DNS automation (operator prereq) · no implementation code.
