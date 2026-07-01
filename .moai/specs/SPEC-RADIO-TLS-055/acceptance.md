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

# Acceptance Criteria — SPEC-RADIO-TLS-055

Each scenario maps 1:1 to a requirement in `spec.md`. "The edge" means the single
Caddy container; "a backend" means `brain:8080` or `icecast:8000` on the `gsr`
network. Scenarios marked *(operator-deploy)* require the REQ-TO-001
prerequisites (domain + DNS + inbound reachability) and are verified on the
target dedicated server or a STAGING equivalent, not on the domain-less dev host.

---

## Group TP — TLS Proxy

### AC-TP-001 — one edge, only edge (REQ-TP-001)
- **Given** the TLS deployment is active,
- **When** the host's listening ports are enumerated (`ss -tlnp` / `docker
  compose ps`),
- **Then** only `80` and `443` are published to a public interface and they
  belong to the `caddy` service; no other service publishes a public host port.

### AC-TP-002 — TLS termination + backend forward (REQ-TP-002) *(operator-deploy)*
- **Given** valid certs for `radio.<domain>` and `stream.<domain>`,
- **When** a client makes an HTTPS request to either host,
- **Then** the edge completes the TLS handshake and the decrypted request reaches
  the correct backend over `gsr` (the backend logs the request).

### AC-TP-003 — automatic issuance (REQ-TP-003) *(operator-deploy)*
- **Given** the prerequisites are met and the edge starts fresh,
- **When** it boots,
- **Then** it obtains LE certificates for both hostnames via ACME with no manual
  `certbot`/`acme.sh` invocation.

### AC-TP-004 — hands-off renewal (REQ-TP-004)
- **Given** an issued certificate,
- **When** it approaches expiry,
- **Then** the edge renews it from inside the running daemon with no operator
  action and no external cron/reload.
- **Edge:** a 45-day-profile cert renews the same hands-off way as a 90-day cert.

### AC-TP-005 — HTTP-01 is the default (REQ-TP-005) *(operator-deploy)*
- **Given** a resolvable domain and reachable inbound `:80`,
- **When** issuance runs,
- **Then** validation occurs over HTTP-01 (`/.well-known/acme-challenge/…` on
  `:80`) using stock `caddy:2` with no DNS credentials configured.

### AC-TP-006 — DNS-01 documented fallback (REQ-TP-006)
- **Given** the operator documentation,
- **When** the CGNAT / blocked-`:80` case is consulted,
- **Then** it describes the DNS-01 path: a custom `xcaddy` image with the
  DNS-provider plugin + a zone-scoped API token as a gitignored secret, and
  states plainly that DNS-01 fixes issuance only, not inbound `:443` reachability.

### AC-TP-007 — HTTP→HTTPS redirect (REQ-TP-007)
- **Given** the edge is running,
- **When** a client requests a non-ACME path over `http://` on `:80`,
- **Then** the edge responds with a redirect to the `https://` equivalent.
- **And** ACME challenge requests on `:80` are still served (not redirected).

### AC-TP-008 — secure TLS defaults, no hand-rolled ciphers (REQ-TP-008) *(operator-deploy)*
- **Given** the edge is serving TLS,
- **When** the endpoint is scanned (e.g. `testssl.sh` / SSL Labs),
- **Then** TLS 1.2 is the floor, 1.3 is preferred, and no weak/legacy ciphers are
  offered, using Caddy defaults (the Caddyfile contains no explicit cipher list).

---

## Group TR — Routing & Streaming

### AC-TR-001 — website/API routing (REQ-TR-001) *(operator-deploy)*
- **Given** `radio.<domain>` resolves to the host,
- **When** a client requests `https://radio.<domain>/status`,
- **Then** the edge proxies to `brain:8080` and returns the status page (subject
  to the Group TH blocks).

### AC-TR-002 — stream routing (REQ-TR-002) *(operator-deploy)*
- **Given** `stream.<domain>` resolves to the host,
- **When** a client requests `https://stream.<domain>/radio`,
- **Then** the edge proxies to `icecast:8000` and the `/radio` mount streams
  unchanged.

### AC-TR-003 — streaming buffering off (REQ-TR-003) *(operator-deploy)*
- **Given** the `/radio` route configured with `flush_interval -1` + a long read
  timeout,
- **When** a listener plays `https://stream.<domain>/radio` for over 60 seconds,
- **Then** the audio plays continuously with no periodic cut-outs and now-playing
  metadata updates (does not stick).
- **Edge:** removing `flush_interval -1` reproduces the stall (negative control).

### AC-TR-004 — no native backend TLS (REQ-TR-004)
- **Given** the deployment config,
- **When** it is reviewed,
- **Then** Icecast has no `icecast.xml`/`<listen-socket ssl>` TLS and the brain
  has no `SSLContext`; TLS is terminated only at the edge.

### AC-TR-005 — HTTPS player URL, no mixed content (REQ-TR-005) *(operator-deploy)*
- **Given** `BRAIN_STREAM_PUBLIC_URL=https://stream.<domain>/radio` is set,
- **When** the website is rendered and loaded over HTTPS,
- **Then** the `<audio>` source is `https://stream.<domain>/radio` and the browser
  console shows no mixed-content block.
- **And Given** the env is unset (dev), **Then** the player falls back to
  `http://<host>:<port>/radio` (plain-HTTP dev preserved).

### AC-TR-006 — Icecast at a host root (REQ-TR-006) *(operator-deploy)*
- **Given** Icecast proxied at `stream.<domain>` (not a sub-path of
  `radio.<domain>`),
- **When** the stream and its emitted URLs are inspected,
- **Then** absolute URLs resolve correctly and the website lives on a separate
  host root (`radio.<domain>` or apex).

---

## Group TH — Hardening & Exposure

### AC-TH-001 — brain not publicly reachable; bind not broken (REQ-TH-001)
- **Given** the compose file with the brain host publish dropped and
  `BRAIN_HTTP_HOST` unset (`0.0.0.0` in-container),
- **When** the stack is up,
- **Then** the brain is unreachable on the host's public interface **and** the
  edge can reach `brain:8080` over `gsr` (a proxied request succeeds).
- **Edge (negative):** setting `BRAIN_HTTP_HOST=127.0.0.1` makes the edge's
  upstream request fail (documented as the wrong configuration).

### AC-TH-002 — Icecast not publicly reachable (REQ-TH-002)
- **Given** the `8000:8000` host publish removed,
- **When** a client hits the host's public IP on `:8000`,
- **Then** the connection is refused, while `https://stream.<domain>/radio`
  (via the edge) works.

### AC-TH-003 — `/admin*` blocked at edge (REQ-TH-003)
- **Given** the edge routing `radio.<domain>`,
- **When** a client requests `/admin` or any `/admin/*` (including
  `/admin/stream`),
- **Then** the edge returns 403/404 and the request never reaches the brain.
- **And** this holds independently of the separate `/admin/stream` pre-auth-bypass
  code fix (defense-in-depth).

### AC-TH-004 — Icecast admin + status JSON blocked (REQ-TH-004)
- **Given** the edge routing `stream.<domain>`,
- **When** a client requests `/admin/*` or `/status-json.xsl`,
- **Then** the edge denies it (no admin surface, no listener-count leak).

### AC-TH-005 — internal-only brain endpoints not public (REQ-TH-005)
- **Given** the edge allowlist,
- **When** a client requests `https://radio.<domain>/api/next` or `/api/airing`,
- **Then** the edge blocks it; Liquidsoap still reaches them as `brain:8080` on
  `gsr`.

### AC-TH-006 — slskd never public, never proxied (REQ-TH-006)
- **Given** the deployment (slskd profile OFF by default),
- **When** the config and ports are reviewed,
- **Then** `:5030` is not in any edge route and is not published to `0.0.0.0`;
  when the profile is enabled it binds `127.0.0.1` only.

### AC-TH-007 — harbor stays internal (REQ-TH-007)
- **Given** the compose file,
- **When** the liquidsoap service is inspected,
- **Then** `7138` remains `expose`-only on `gsr` (no `ports:`, not in any edge
  route) — unchanged from the current design.

### AC-TH-008 — X-Forwarded trust (REQ-TH-008)
- **Given** the brain fronted by the edge,
- **When** a request arrives with `X-Forwarded-For`/`X-Forwarded-Proto` set by the
  edge,
- **Then** the brain uses the forwarded client IP for `/stats` + like-token
  rate-limiting and treats the request as TLS-fronted.

### AC-TH-009 — firewall posture + Docker/ufw caveat (REQ-TH-009)
- **Given** the operator runbook,
- **When** the firewall section is consulted,
- **Then** it prescribes a provider/cloud default-deny except `22/80/443` **and**
  states that Docker bypasses host `ufw`, so the compose no-publish / `127.0.0.1`
  binds are the real control.

### AC-TH-010 — admin recommended off for public (REQ-TH-010)
- **Given** SPEC-RADIO-FEATUREGATE-053's `BRAIN_ADMIN_ENABLED`,
- **When** the public-deploy guidance is read,
- **Then** it recommends the admin panel be disabled or not proxied and
  references 053 without re-specifying the flag.

### AC-TH-011 — `.claude` mount scoped (REQ-TH-011)
- **Given** the brain service before public exposure,
- **When** the `/home/charlie/.claude` mount is reviewed,
- **Then** it is read-only/minimal (`:ro` or a minimal subpath), limiting OAuth
  credential exfiltration on an RCE/traversal.

---

## Group TS — Security Headers

### AC-TS-001 — HSTS present (REQ-TS-001) *(operator-deploy)*
- **Given** an HTTPS response from the edge,
- **When** headers are inspected,
- **Then** `Strict-Transport-Security` is present with `max-age>=31536000;
  includeSubDomains`.

### AC-TS-002 — preload is opt-in and last (REQ-TS-002)
- **Given** the security-headers documentation,
- **When** the HSTS section is read,
- **Then** `preload` is described as effectively irreversible, to be added last
  after HTTPS is proven, and it is **not** enabled in the day-one config.

### AC-TS-003 — baseline security headers (REQ-TS-003) *(operator-deploy)*
- **Given** an HTTPS response,
- **When** headers are inspected,
- **Then** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` (or CSP
  `frame-ancestors 'none'`), and `Referrer-Policy: strict-origin-when-cross-origin`
  are present.

### AC-TS-004 — CSP allows the stream origin (REQ-TS-004) *(operator-deploy)*
- **Given** a CSP that includes `https://stream.<domain>` in `media-src` and
  `connect-src`,
- **When** the HTTPS page loads the player,
- **Then** the `<audio>` source and now-playing fetch are not blocked by the CSP.
- **Edge:** a CSP omitting the stream origin reproduces a blocked player
  (negative control).

### AC-TS-005 — CORS injected when needed (REQ-TS-005) *(operator-deploy)*
- **Given** a web player using cross-origin metadata JS,
- **When** it fetches `/status-json.xsl` (if that path is deliberately allowed),
- **Then** the edge supplies `Access-Control-Allow-Origin` + exposes `Icy-MetaInt`
  (since the env-only Icecast image cannot).

---

## Group TO — Operations & Prerequisites

### AC-TO-001 — domain is a stated prerequisite (REQ-TO-001)
- **Given** the SPEC + runbook,
- **When** the prerequisites are read,
- **Then** a registered domain with A/AAAA records for `radio`/`stream` is stated
  as the primary gating fact, and issuance is documented as impossible until a
  resolvable hostname exists.

### AC-TO-002 — graceful degradation without a domain (REQ-TO-002)
- **Given** no domain/DNS/reachability configured (dev host),
- **When** the stack starts without the TLS profile,
- **Then** the existing plain-HTTP operation is unchanged (TLS opt-in; nothing
  breaks).

### AC-TO-003 — STAGING first (REQ-TO-003)
- **Given** the issuance flow,
- **When** it is followed,
- **Then** the operator issues against the LE STAGING directory first and switches
  to production only after a clean staging issuance.

### AC-TO-004 — cert store persists (REQ-TO-004)
- **Given** the `caddy_data` named volume,
- **When** the Caddy container is recreated,
- **Then** the existing certs + ACME account key survive and no re-issuance
  occurs.

### AC-TO-005 — automatic re-issue on store loss (REQ-TO-005)
- **Given** the `caddy_data` volume is deleted,
- **When** the edge next starts (prerequisites met),
- **Then** it re-issues automatically, and the runbook documents the rate-limit
  exposure (re-verify via STAGING if debugging).

### AC-TO-006 — ACME account email set (REQ-TO-006)
- **Given** the Caddyfile global options,
- **When** reviewed,
- **Then** an `email` is configured for LE expiry/problem notices.

### AC-TO-007 — reachability prerequisite documented (REQ-TO-007)
- **Given** the runbook,
- **When** the reachability section is read,
- **Then** it states HTTP-01 needs inbound `:80` for issuance + every renewal and
  serving needs inbound `:443`, satisfied on the dedicated server by a
  direct/port-forwarded public IP; the WSL2/CGNAT connection-refused caveat is
  scoped to dev only, with tunnel/relay as the documented dev fallback.

---

## Non-Functional Acceptance

### AC-NFR-TLS-1 — no plaintext public path (NFR-TLS-1)
- **Given** TLS is live,
- **When** the public interface is port-scanned,
- **Then** only `80` (redirect/ACME) and `443` respond; `8080`, `8000`, `5030`,
  `7138` are all connection-refused from the public internet.

### AC-NFR-TLS-2 — stream continuity preserved (NFR-TLS-2) *(operator-deploy)*
- **Given** the proxied stream,
- **When** `https://stream.<domain>/radio` is played continuously for at least
  10 minutes,
- **Then** the client observes zero audio cut-outs (the `<audio>` element does not
  fire a `stalled`/`waiting` event that ends in silence) and the now-playing
  metadata refreshes within 30 seconds of a track change.

### AC-NFR-TLS-3 — renewal without listener drop (NFR-TLS-3) *(operator-deploy)*
- **Given** a listener connected during a certificate renewal,
- **When** the edge swaps the cert in-daemon,
- **Then** the listener's stream is not interrupted (no Icecast restart occurs).

### AC-NFR-TLS-4 — no secret exposure (NFR-TLS-4)
- **Given** the deployment,
- **When** the Caddy service + secrets are reviewed,
- **Then** no `docker.sock` is mounted, any DNS API token lives only in gitignored
  secrets / the volume, and the `.claude` mount is minimal/RO.

### AC-NFR-TLS-5 — renewal reachability under HTTP-01 (NFR-TLS-5)
- **Given** HTTP-01 is the active challenge,
- **When** the firewall/runbook is reviewed,
- **Then** inbound `:80` and `/.well-known/acme-challenge/` remain reachable for
  renewals (the guidance never prescribes fully firewalling `:80`).

---

## Edge Cases & Negative Scenarios

- **EC-1 (no domain, TLS profile off):** dev host runs plain HTTP; enabling the
  TLS profile without a domain fails ACME loudly (logs) but the rest of the stack
  keeps serving — no crash loop of the whole compose (REQ-TO-002).
- **EC-2 (`BRAIN_HTTP_HOST=127.0.0.1` mistake):** edge upstream fails; documented
  as the wrong knob — drop the host publish instead (REQ-TH-001 / D2).
- **EC-3 (buffering left on):** `/radio` cuts out every few seconds + stuck
  metadata; fixed by `flush_interval -1` (REQ-TR-003, NFR-TLS-2).
- **EC-4 (mixed content):** HTTPS site + HTTP stream ⇒ silent player break while
  the API looks fine; fixed by the HTTPS stream URL + CSP `media-src`
  (REQ-TR-005, REQ-TS-004).
- **EC-5 (production rate-limit burn):** repeated failed prod issuance hits
  5-failed-validations/hour; mitigated by STAGING-first (REQ-TO-003).
- **EC-6 (cert store wiped):** volume loss forces re-issuance; auto-recovers but
  can trip dup-cert limits — STAGING re-verify (REQ-TO-004/005).
- **EC-7 (CGNAT on dev):** DNS-01 obtains a cert but `:443` still refuses; a
  tunnel/relay is required for reachability (REQ-TP-006, REQ-TO-007).
- **EC-8 (admin left proxied):** if `/admin*` blocking is misconfigured, the edge
  must still deny; the FEATUREGATE-053 `BRAIN_ADMIN_ENABLED=0` recommendation is
  the second layer (REQ-TH-003/010).

---

## Definition of Done

- [ ] Caddy edge publishes only `:80`/`:443`; brain + Icecast host publishes
      removed; nothing else public (REQ-TP-001, NFR-TLS-1).
- [ ] `radio.<domain>` → brain and `stream.<domain>` → Icecast with
      `flush_interval -1` on `/radio` (Group TR).
- [ ] `/admin*`, Icecast `/admin*` + `/status-json.xsl`, `/api/next` + `/api/airing`
      blocked at the edge (Group TH).
- [ ] HSTS + baseline headers + CSP-with-stream-origin emitted (Group TS).
- [ ] Brain emits HTTPS stream URL; trusts `X-Forwarded-*`; `.claude` mount RO
      (REQ-TR-005, REQ-TH-008/011).
- [ ] STAGING-first flow, persisted cert volume, ACME email, HTTP-01 default +
      DNS-01 fallback, reachability + firewall posture all documented
      (Group TO, REQ-TH-009).
- [ ] Domain-less dev host still runs plain HTTP (REQ-TO-002).
- [ ] No `docker.sock`; no native Icecast/brain TLS; no implementation beyond the
      `[DELTA]` surface in `plan.md` (Exclusions, NFR-TLS-4).
