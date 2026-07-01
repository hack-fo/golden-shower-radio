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

# SPEC-RADIO-TLS-055 — TLS / HTTPS Architecture via Let's Encrypt (Single Caddy Edge)

## Overview

golden-shower-radio serves **everything over plain HTTP** today. Two surfaces
would go public in a real deployment — the station website + API on the brain
HTTP server (`:8080`) and the Icecast MP3 stream (`:8000/radio`) — and both are
cleartext with `0.0.0.0` host binds (`deploy/docker-compose.yml:15`–`:16`,
`:95`–`:96`). Neither backend can terminate TLS on its own:

- The brain HTTP server is Python stdlib `ThreadingHTTPServer` with **no
  `SSLContext`** (`brain/server.py:1216`). It cannot serve HTTPS as written.
- Icecast runs on the env-only `moul/icecast` image with **no `icecast.xml`
  mounted** (`deploy/docker-compose.yml:8`–`:17`), so the XML-only
  `<listen-socket ssl>` / `<ssl-certificate>` knobs cannot be set.

The user intends to **host publicly and cannot run plain HTTP**. This SPEC
delivers a TLS/HTTPS architecture built on **Let's Encrypt** using a **single
Caddy reverse-proxy container as the only internet-facing service**: it
terminates TLS on `:443`, auto-issues and auto-renews certificates, reverse-
proxies `radio.<domain>` → `brain:8080` and `stream.<domain>` → `icecast:8000`
over the internal `gsr` Docker network, and every backend host-bind is narrowed
so the proxy is the only reachable edge. **HTTP-01 is the default ACME
challenge** (the target is a dedicated server with controllable inbound
networking); **DNS-01 is the documented fallback** for CGNAT / blocked-`:80`.

Deployment target is a **dedicated dual-Xeon E5 server**, not the current WSL2
dev host. The WSL2/CGNAT reachability caveat therefore applies only to local
dev, not to the production box, which is assumed to have a direct or
port-forwarded public IP.

This is a **brownfield DevOps/security SPEC**. It **adds** a Caddy service +
`Caddyfile`, **modifies** `deploy/docker-compose.yml`, `brain/config.py`,
`brain/server.py`, and `brain/website.py`, and leaves the Liquidsoap source path
and the internal harbor untouched. Every requirement is an EARS statement over
WHAT the system must observably do; the code surface (`[DELTA]`
EXISTING/MODIFY/NEW) is enumerated in `plan.md`, not here. The full technical
basis, alternatives comparison, and citations are in
`.moai/specs/SPEC-RADIO-TLS-055/research.md`.

---

## HISTORY

### v0.1.1 (2026-07-01) — Editorial polish (plan-audit fixes)

- No behaviour change; requirement/AC/NFR counts unchanged (37 REQ / 42 AC /
  5 NFR). Applied the five minor plan-audit fixes from
  `.moai/reports/plan-audit/SPEC-RADIO-TLS-055-review-1.md`:
  - **D1 (label accuracy)** — relabelled REQ-TR-004 / REQ-TH-005 / REQ-TH-006
    from "(Unwanted Behaviour)" to "(Ubiquitous)". Each is a bare ubiquitous
    negative constraint ("shall not …") with no If-trigger, so the Unwanted-form
    tag was wrong. Requirement text is unchanged.
  - **D2 (non-normative verbs)** — recast REQ-TH-010 and REQ-TS-002 into proper
    EARS Optional-Feature form: the normative verb is now "shall" and the
    optionality lives in the "Where …" precondition, removing "recommended"/"may"
    from the requirement bodies. Intent preserved exactly (TH-010 = admin
    disabled/unproxied on public deploys, referencing FEATUREGATE-053; TS-002 =
    HSTS `preload` is an opt-in added only after HTTPS is proven stable and is
    effectively irreversible).
  - **D4 (untestable AC)** — in `acceptance.md`, replaced AC-NFR-TLS-2's
    "latency comparable" judgement call with a concrete, binary-checkable
    continuity bound (sustained ≥10-minute play, zero client-observed cut-outs,
    now-playing metadata refresh within a bounded time).
  - **D5 (declarative lead)** — rewrote REQ-TO-001 so the normative "shall not"
    leads; the registered-domain / authoritative-DNS operator prerequisite
    remains the primary gating fact.
  - **D3** — no change: `created` (not `created_at`) is the uniform project
    frontmatter convention across all sibling SPECs.

### v0.1.0 (2026-07-01) — Initial draft

- Authored from `.moai/specs/SPEC-RADIO-TLS-055/research.md` (authoritative
  technical basis) against verified code state (2026-07-01, branch
  `feature/SPEC-RADIO-LINEUP-050`): `deploy/docker-compose.yml` (icecast
  `8000:8000` `:15`–`:16`; brain `8080:8080` `:95`–`:96`; harbor `expose 7138`
  `:54`–`:55`; slskd profile-gated `5030:5030` `:27`/`:37`–`:38`; `.claude`
  RW mount `:91`), `brain/config.py` (`http_host` default `0.0.0.0` `:44`;
  `icecast_public_port`/`icecast_mount` `:58`–`:59`), `brain/server.py` (stdlib
  `ThreadingHTTPServer`, no `SSLContext`, `:1216`; admin auth `:851`;
  `/admin/stream` dispatched **before** the auth check `:870`–`:873`),
  `brain/website.py` (`:14`–`:17` composes the player URL
  `http://<host>:<port>/radio` from `cfg.icecast_public_port`/`icecast_mount`).
- **[DECISION — dedicated server ⇒ HTTP-01 default]** The hosting target is a
  dedicated dual-Xeon box with controllable inbound networking (direct /
  port-forwarded public IP), not the WSL2 dev host. HTTP-01 is therefore the
  default challenge (zero-config in stock Caddy, no DNS credentials); DNS-01 is
  the documented fallback for CGNAT / ISP-blocked `:80` (needs a custom
  `xcaddy` build + a zone-scoped DNS-provider token). See REQ-TP-005 / REQ-TP-006.
- **[DECISION — no domain yet ⇒ prerequisite, not blocker]** No public domain,
  DNS, or public IP exists in the repo. The SPEC **designs the full
  architecture** but treats domain registration + DNS records + inbound
  reachability as an **operator PREREQUISITE**: ACME cannot issue until a
  resolvable hostname exists, and until then the stack degrades gracefully to
  plain HTTP (TLS is opt-in). See REQ-TO-001 / REQ-TO-002 / REQ-TO-007.
- **[DECISION — proxy the listener side, never native Icecast/brain TLS]** The
  `moul/icecast` image is env-only (no XML mount) and the brain stdlib server
  has no `SSLContext`; one Caddy edge covers both surfaces at once, and a proxy
  cert swap renews without dropping listeners (native Icecast TLS renewal would
  restart Icecast and drop every connection). See REQ-TR-004 / NFR-TLS-3.
- **[DECISION — Caddy over Traefik/nginx]** Caddy wins for this stack: automatic
  HTTPS with the least config (matches the always-on "radio never stops"
  philosophy under the 2026 45-day cert transition), **no `docker.sock` mount**
  (Traefik's label routing would mount a root-equivalent socket next to the
  Claude OAuth creds; `exposedByDefault` risks auto-publishing the harbor), and
  `flush_interval -1` solves Icecast streaming buffering in one directive (nginx
  needs five directives + a certbot sidecar). See `research.md` §"Reverse-proxy
  choice".
- **[RELATION — FEATUREGATE-053]** `BRAIN_ADMIN_ENABLED` (admin panel hard
  on/off) is owned by SPEC-RADIO-FEATUREGATE-053. This SPEC **recommends** the
  admin panel stay disabled or unproxied on public deploys and **references**
  053 rather than re-specifying it. See REQ-TH-010.
- **[ASSUMPTION — `/admin/stream` pre-auth bypass fix]** A separate fix moves
  `_check_admin_auth()` ahead of the `/admin/stream` dispatch
  (`brain/server.py:870`–`:873`). This SPEC **assumes that fix lands** and, as
  **defense-in-depth**, still blocks `/admin*` at the proxy regardless. See
  REQ-TH-003.
- **Counts:** 37 REQ (TP 8 / TR 6 / TH 11 / TS 5 / TO 7) + 5 NFR-TLS.

---

## Glossary

- **Edge / TLS edge** — the single Caddy container that publishes `:80` + `:443`
  and terminates TLS; the only internet-facing service.
- **Backend** — an origin behind the edge on the `gsr` network: the brain
  (`brain:8080`) or Icecast (`icecast:8000`).
- **`radio.<domain>`** — the public hostname for the website + public API
  surface (proxied to `brain:8080`).
- **`stream.<domain>`** — the public hostname for the audio stream (proxied to
  `icecast:8000`, mount `/radio`).
- **ACME** — the Automatic Certificate Management Environment protocol Let's
  Encrypt uses; **HTTP-01** validates over inbound `:80`, **DNS-01** validates
  via a TXT record (outbound only, needs a DNS API token).
- **STAGING** — the Let's Encrypt staging directory (untrusted certs, lax rate
  limits) used to prove config before switching to the production directory.
- **`flush_interval -1`** — the Caddy `reverse_proxy` directive that disables
  response buffering, required so the continuous MP3 stream is not stalled.
- **Mixed content** — an HTTP subresource embedded on an HTTPS page; browsers
  block it since Chrome 80 (2020), which is why the stream must also be HTTPS.
- **Reachability** — whether inbound TCP to the host's `:80`/`:443` actually
  arrives; issuance needs `:80` (HTTP-01), serving needs `:443` regardless of
  challenge. A cert cannot fix connection-refused.

---

## Requirements (EARS)

### Group TP — TLS Proxy (Caddy, Termination, ACME)

**REQ-TP-001 (Ubiquitous).**
The system **shall** run a single Caddy reverse-proxy container as the **only**
internet-facing service, publishing exactly two host ports — `80` and `443` —
and no other service **shall** publish a public host port.

**REQ-TP-002 (Event-Driven).**
**When** a client connects on `:443` for `radio.<domain>` or `stream.<domain>`,
the edge **shall** terminate TLS and forward the decrypted request to the
correct backend over the internal `gsr` network.

**REQ-TP-003 (Ubiquitous).**
The edge **shall** automatically obtain Let's Encrypt certificates for
`radio.<domain>` and `stream.<domain>` via ACME, with no manual `certbot`/
`acme.sh` step.

**REQ-TP-004 (State-Driven).**
**While** an issued certificate approaches expiry, the edge **shall** renew it
hands-off from inside the running daemon (no operator action, no external cron/
reload), so the 2026 90-day → opt-in 45-day cert-lifetime shrink cannot silently
lapse a certificate.

**REQ-TP-005 (Event-Driven).**
**When** a public domain resolves to the host and inbound `:80` is reachable,
the system **shall** use the **HTTP-01** challenge as the default ACME method
(stock `caddy:2`, no DNS credentials).

**REQ-TP-006 (Optional Feature).**
**Where** inbound `:80` is blocked or the host is behind CGNAT, the system
**shall** support **DNS-01** as a documented fallback challenge — proving control
via a `_acme-challenge` TXT record using a **custom `xcaddy` build** that bakes
in the DNS-provider plugin plus a **zone-scoped API token** supplied as a
gitignored secret. DNS-01 **shall** be documented as solving *issuance* only,
not *reachability* (inbound `:443` must still arrive).

**REQ-TP-007 (Event-Driven).**
**When** a client requests a non-ACME path over plain HTTP `:80`, the edge
**shall** redirect it to the `https://` equivalent, so no listener stays on a
cleartext connection.

**REQ-TP-008 (Ubiquitous).**
The edge **shall** rely on the proxy's secure TLS defaults (minimum TLS 1.2,
prefer 1.3, modern ciphers/curves, OCSP stapling) and **shall not** hand-roll a
cipher list.

### Group TR — Routing & Streaming

**REQ-TR-001 (Ubiquitous).**
The edge **shall** route `radio.<domain>` to `brain:8080` over the `gsr` network,
exposing only the public brain surfaces (`/`, `/status`, `/api/nowplaying`,
`/stats`, `/health`) subject to the Group TH blocks.

**REQ-TR-002 (Ubiquitous).**
The edge **shall** route `stream.<domain>` to `icecast:8000` over the `gsr`
network, passing the `/radio` mount through unchanged.

**REQ-TR-003 (State-Driven).**
**While** proxying the `/radio` stream route, the edge **shall** disable response
buffering (`reverse_proxy` with `flush_interval -1`) and use a long/effectively-
infinite read timeout, so the continuous MP3 is not stalled and now-playing
metadata does not stick.

**REQ-TR-004 (Ubiquitous).**
The system **shall not** terminate TLS inside Icecast (the env-only `moul/icecast`
image cannot mount `icecast.xml`) **nor** inside the brain stdlib server (no
`SSLContext`); a **single** proxy edge **shall** cover both surfaces.

**REQ-TR-005 (Ubiquitous).**
The brain website player **shall** emit an `https://stream.<domain>/radio` stream
URL (not `http://<host>:8000/radio`), so the HTTPS page has no blocked
mixed-content audio subresource.

**REQ-TR-006 (Ubiquitous).**
Icecast **shall** be proxied at a host/URL **root** (the `stream.<domain>`
subdomain), not a sub-path, because its admin UI, `/status-json.xsl`, and mount
handling emit absolute URLs; the brain website **shall** live on a separate
host/root (`radio.<domain>` or the apex).

### Group TH — Hardening & Exposure

**REQ-TH-001 (Ubiquitous).**
The brain HTTP backend **shall not** be reachable from the public internet
except through the edge: the `gsr`-internal `brain:8080` is the only path.
Preferred implementation is to **drop the host `ports:` publish** for brain so it
is reachable only by service name on `gsr`; if host-loopback debug access is
wanted, publish `127.0.0.1:8080:8080`. See the interaction note in `plan.md`:
setting the in-container listen bind `BRAIN_HTTP_HOST=127.0.0.1`
(`brain/config.py:44`, which scopes the whole server via
`brain/server.py:1216`) would make the brain unreachable to Caddy across the
Docker network and **must not** be used while the edge proxies over `gsr`.

**REQ-TH-002 (Ubiquitous).**
The Icecast backend **shall not** be reachable from the public internet except
through the edge on `stream.<domain>`: the `8000:8000` `0.0.0.0` host publish
**shall** be removed (reach as `icecast:8000` on `gsr`) or narrowed to
`127.0.0.1:8000:8000`.

**REQ-TH-003 (Event-Driven).**
**When** a request path matches `/admin` or `/admin/*`, the edge **shall** block
it (return 404/403) before it can reach the brain — as **defense-in-depth**
independent of, and in addition to, the assumed separate `/admin/stream`
pre-auth-bypass fix (`brain/server.py:870`–`:873`).

**REQ-TH-004 (Event-Driven).**
**When** a request matches the Icecast admin surface (`/admin/*`) or
`/status-json.xsl`, the edge **shall** block it (admin surface + listener-count
leak), unless a specific web player is explicitly configured to require the
status JSON.

**REQ-TH-005 (Ubiquitous).**
The edge **shall not** include the internal-only brain endpoints `/api/next` and
`/api/airing` in its public allowlist; these are consumed by Liquidsoap over the
`gsr` network and **shall not** be publicly reachable.

**REQ-TH-006 (Ubiquitous).**
The slskd Soulseek surface (`:5030`) **shall** never be proxied nor published to
`0.0.0.0`; it **shall** remain profile-gated (default OFF) and, when enabled,
bound to `127.0.0.1` (localhost / SSH-tunnel / VPN access only).

**REQ-TH-007 (Ubiquitous).**
The Liquidsoap harbor (`:7138`) **shall** remain `expose`-only on the `gsr`
network (`deploy/docker-compose.yml:54`–`:55`); this SPEC **shall not** regress
it to a published or proxied port.

**REQ-TH-008 (Ubiquitous).**
The brain **shall** trust the `X-Forwarded-For` and `X-Forwarded-Proto` headers
set by the edge, so `/stats` and the like-token HMAC rate-limiting see the real
client IP and the server is aware it is fronted by TLS.

**REQ-TH-009 (Ubiquitous).**
The deployment **shall** apply an outer provider/cloud firewall that
default-denies all inbound except `22`, `80`, and `443`, **and shall** treat the
compose `127.0.0.1` binds / dropped host publishes as the **real** control —
because Docker's iptables rules bypass a host `ufw deny`, so a bare `0.0.0.0`
publish stays internet-open regardless of `ufw`.

**REQ-TH-010 (Optional Feature).**
**Where** the deployment is public-facing, the admin panel **shall** be disabled
(via SPEC-RADIO-FEATUREGATE-053's `BRAIN_ADMIN_ENABLED`) or left unproxied at the
edge; this SPEC **references** 053 for the panel's hard on/off and **shall not**
re-specify it.

**REQ-TH-011 (Ubiquitous).**
The `/home/charlie/.claude` OAuth-credential mount into the brain
(`deploy/docker-compose.yml:91`) **shall** be scoped read-only/minimal before
public exposure, so an RCE or path-traversal on the now-public stdlib server
cannot exfiltrate live Claude MAX credentials.

### Group TS — Security Headers

**REQ-TS-001 (Ubiquitous).**
On HTTPS responses the edge **shall** emit an HSTS header
(`Strict-Transport-Security: max-age>=31536000; includeSubDomains`).

**REQ-TS-002 (Optional Feature).**
**Where** the operator opts into HSTS `preload` after HTTPS has been proven
stable, the edge **shall** append the `preload` token to the HSTS header **last**;
the SPEC **shall** document that `preload` is effectively irreversible, and the
day-one config **shall not** enable it.

**REQ-TS-003 (Ubiquitous).**
The edge **shall** emit `X-Content-Type-Options: nosniff`, `X-Frame-Options:
DENY` (or the CSP equivalent `frame-ancestors 'none'`), and
`Referrer-Policy: strict-origin-when-cross-origin`.

**REQ-TS-004 (Ubiquitous).**
The edge **shall** emit a Content-Security-Policy whose `media-src` and
`connect-src` include the stream origin (`https://stream.<domain>`), so the
`<audio>` player and any now-playing fetch are not blocked by the CSP.

**REQ-TS-005 (Optional Feature).**
**Where** cross-origin metadata JS (e.g. `icecast-metadata-js`) or a fetch of
`/status-json.xsl` is used, the edge **shall** inject CORS headers
(`Access-Control-Allow-Origin` + exposed `Icy-MetaInt`) at the proxy, because the
env-only Icecast image cannot set `http-headers` itself.

### Group TO — Operations & Prerequisites

**REQ-TO-001 (Ubiquitous).**
The system **shall not** attempt ACME issuance until a resolvable public hostname
with authoritative A/AAAA records for `radio.<domain>` and `stream.<domain>`
pointing at the host exists; a **registered domain name** with authoritative DNS
is the **operator prerequisite** that gates this, and the SPEC **shall** state it
plainly as the primary gating fact.

**REQ-TO-002 (State-Driven).**
**While** no domain, DNS, or inbound reachability is configured, the stack
**shall** continue to operate over plain HTTP on the dev host — TLS is **opt-in**
and its absence **shall not** break existing local operation (graceful
degradation).

**REQ-TO-003 (Ubiquitous).**
Initial certificate issuance **shall** target the Let's Encrypt **STAGING**
directory to prove config, and **shall** switch to the production directory only
after a clean staging issuance, to avoid burning the 5-duplicate-certs/week and
5-failed-validations/hour production rate limits.

**REQ-TO-004 (Ubiquitous).**
The edge's certificate + ACME-account-key store (Caddy `/data`) **shall** persist
on a named, chmod-protected volume, so a container recreate does not force
re-issuance.

**REQ-TO-005 (Unwanted Behaviour).**
**If** the certificate store is lost, **then** the edge **shall** re-issue
automatically on next start, and the SPEC **shall** document the rate-limit
exposure (re-verify against STAGING first if debugging).

**REQ-TO-006 (Ubiquitous).**
An **ACME account email** (Caddy `email` global option) **shall** be configured
so Let's Encrypt can send expiry/problem notices.

**REQ-TO-007 (Ubiquitous).**
The SPEC **shall** document that the HTTP-01 default requires open inbound `:80`
for issuance **and every renewal**, and that serving requires open inbound `:443`
regardless of challenge — a **reachability prerequisite** satisfied on the target
dedicated server by a direct/port-forwarded public IP. The WSL2/CGNAT
connection-refused caveat **shall** be scoped to local dev only; if a
CGNAT/blocked-`:80` situation arises there, a Cloudflare Tunnel / Tailscale
Funnel / VPS relay is the documented reachability path (not the primary design).

---

## Non-Functional Requirements

**NFR-TLS-1 (No plaintext public path).**
Once TLS is live, the only internet-reachable host ports **shall** be `80` (ACME
+ redirect to `:443`) and `443`; no backend port (`8080`, `8000`, `5030`,
`7138`) **shall** be reachable from the public internet. A downgrade path to
cleartext backends **shall not** exist.

**NFR-TLS-2 (Stream continuity preserved).**
The edge **shall not** materially harm stream latency or continuity: with
`flush_interval -1` and a long read timeout the continuous MP3 **shall** play
without periodic cut-outs and now-playing metadata **shall not** stick.

**NFR-TLS-3 (Renewal without listener drop).**
Certificate renewal **shall** occur without dropping connected listeners — a
proxy in-daemon cert swap, **not** an Icecast restart.

**NFR-TLS-4 (No secret exposure).**
The edge **shall** mount **no** `docker.sock`; any DNS-provider API token (DNS-01)
and the ACME account key **shall** live only in gitignored secrets / the
persisted volume; the `.claude` OAuth mount **shall** be minimal/read-only
(REQ-TH-011). The edge **shall not** widen the secret blast radius.

**NFR-TLS-5 (Renewal reachability).**
Under HTTP-01, inbound `:80` and the `/.well-known/acme-challenge/` path **shall**
remain reachable for every renewal; the SPEC **shall not** prescribe fully
firewalling `:80` while HTTP-01 is the active challenge.

---

## Exclusions (What NOT to Build)

- **No native Icecast TLS.** The env-only `moul/icecast` image cannot mount
  `icecast.xml`; listener-side TLS is delivered by the proxy edge (REQ-TR-004).
- **No stdlib-brain TLS.** The brain `ThreadingHTTPServer` gets no `SSLContext`;
  TLS is terminated at the edge, not in Python (REQ-TR-004).
- **No Cloudflare Tunnel / Tailscale Funnel as the primary design.** The target
  dedicated server has direct inbound reachability; tunnels are documented only
  as a CGNAT/blocked-`:80` fallback (REQ-TO-007), not the day-one architecture.
- **No CDN, no multi-node/HA, no load balancing.** A single edge on one host.
- **No rate limiter in the stock build.** Public-endpoint throttling
  (`mholt/caddy-ratelimit`) is noted in `research.md` as a later custom-`xcaddy`
  option; it is **out of scope** here (stock `caddy:2` for HTTP-01).
- **No `/admin/stream` pre-auth-bypass code fix.** That fix is owned by a
  separate change; this SPEC assumes it lands and adds proxy-level `/admin*`
  blocking as defense-in-depth (REQ-TH-003).
- **No admin-panel on/off design.** `BRAIN_ADMIN_ENABLED` is owned by
  SPEC-RADIO-FEATUREGATE-053; this SPEC only references it (REQ-TH-010).
- **No domain purchase / DNS automation.** Domain registration, DNS record
  creation, and inbound port-forwarding are operator prerequisites (Group TO),
  not build tasks.
- **No implementation code in this SPEC.** Code surface is enumerated as
  `[DELTA]` markers in `plan.md`.
