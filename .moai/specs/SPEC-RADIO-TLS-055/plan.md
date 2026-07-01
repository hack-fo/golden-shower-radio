---
id: SPEC-RADIO-TLS-055
version: 0.1.0
status: draft
created: 2026-07-01
updated: 2026-07-01
author: charlie
priority: High
issue_number: 55
labels: [radio, tls, https, security, devops]
---

# Implementation Plan — SPEC-RADIO-TLS-055

## Guiding constraints (carried from spec.md)

- **One edge, only edge.** A single Caddy container publishes `:80` + `:443` and
  is the only internet-facing service; every backend is `gsr`-internal
  (REQ-TP-001, NFR-TLS-1).
- **Proxy the listener side, never native TLS.** No `SSLContext` in the brain,
  no `icecast.xml` TLS; the edge covers both surfaces and renews without a
  listener drop (REQ-TR-004, NFR-TLS-3).
- **HTTP-01 default, DNS-01 documented fallback.** Dedicated server ⇒ direct
  inbound; stock `caddy:2` suffices. DNS-01 needs a custom `xcaddy` build +
  scoped DNS token, and fixes issuance only, not reachability (REQ-TP-005/006,
  REQ-TO-007).
- **Domain is a prerequisite, not a blocker.** Design is complete; issuance
  waits on a resolvable hostname; absent that, the stack stays plain-HTTP
  (REQ-TO-001/002).
- **Secret blast radius stays small.** No `docker.sock`; `.claude` mount
  minimal/RO; DNS tokens gitignored (NFR-TLS-4, REQ-TH-011).
- **Do not regress the internal path.** Liquidsoap → Icecast source stays on
  `gsr`; the harbor stays `expose`-only (REQ-TH-007).

---

## Design decisions

### D1 — `radio.<domain>` (website/API) vs `stream.<domain>` (audio) split

Icecast emits absolute URLs from its admin UI, `/status-json.xsl`, and mount
handling, so it must sit at a host root, not a sub-path (REQ-TR-006). Two
subdomains behind one edge: `radio.<domain>` → `brain:8080`, `stream.<domain>` →
`icecast:8000`. HTTP-01 issues per-hostname certs for both; no wildcard needed
(so no DNS-01 needed for issuance in the default path).

### D2 — Backend host-bind: drop the publish, do NOT set `BRAIN_HTTP_HOST=127.0.0.1`

This is the load-bearing subtlety the research flagged (REQ-TH-001). There are
**two distinct** "127.0.0.1" mechanisms and only one is correct here:

1. **Docker published-port host interface** — `127.0.0.1:8080:8080` binds the
   *host's* port to loopback. Safe. But intra-container traffic (Caddy →
   `brain:8080` on `gsr`) does not use the published host port at all; it uses
   the container's `gsr` IP.
2. **Application in-container listen bind** — `BRAIN_HTTP_HOST` feeds
   `cfg.http_host` (`brain/config.py:44`), which is the bind address of
   `ThreadingHTTPServer((cfg.http_host, cfg.http_port), …)` (`brain/server.py:1216`).
   Setting it to `127.0.0.1` binds the brain to **container-loopback**, so Caddy
   — a *different* container — can no longer reach `brain:8080` across `gsr`.
   **This would break proxying.**

Correct design: **remove the `ports:` publish** for brain (and Icecast) entirely
so they are reachable only by service name on the internal `gsr` network, and
**keep the in-container bind on `0.0.0.0`** (`BRAIN_HTTP_HOST` unset/`0.0.0.0`).
Nothing is published on the host, so nothing is internet-reachable; Caddy still
reaches `brain:8080`/`icecast:8000` on `gsr`. If host-loopback debug access is
desired, use `127.0.0.1:8080:8080` as the *publish* form — never the app bind.
The naive "set `BRAIN_HTTP_HOST=127.0.0.1`" reading of the research is therefore
**rejected** for the proxied topology; it is only valid if Caddy ran in the same
network namespace as the brain, which it does not.

### D3 — Stream URL is a code change, not just proxy config

The player URL is composed in `brain/website.py:14`–`:17` from
`cfg.icecast_public_port` + `cfg.icecast_mount` (currently
`http://<host>:8000/radio`). To avoid mixed-content blocking on the HTTPS page it
must become `https://stream.<domain>/radio`. That requires a configurable public
stream base (scheme + host), so `brain/config.py` gains a public-stream setting
and `website.py` uses it (REQ-TR-005). The internal Icecast status poll in
`brain/like.py:435` (`http://icecast:<port>`) stays internal and is unchanged.

### D4 — Stock `caddy:2` first; custom `xcaddy` only if forced

HTTP-01 + security headers + `flush_interval -1` are all in the stock binary.
A custom `xcaddy` image is needed **only** for DNS-01 (DNS-provider plugin) or a
rate limiter (`mholt/caddy-ratelimit`) — both out of the day-one scope. Keep the
image stock unless a CGNAT/blocked-`:80` reality forces DNS-01.

---

## [DELTA] Code surface

### NEW — `deploy/Caddyfile`

The reverse-proxy config, mounted read-only into the Caddy container. Contains,
at a high level:

- **Global options block:** ACME account `email`, and a commented
  `acme_ca https://acme-staging-v02.api.letsencrypt.org/directory` line for the
  STAGING-first flow (REQ-TO-003, REQ-TO-006). Secure TLS defaults are implicit
  (REQ-TP-008).
- **`radio.<domain>` site block:** `reverse_proxy brain:8080`; a `handle`/
  `respond 403` (or `404`) for `/admin*` (REQ-TH-003) and for `/api/next` +
  `/api/airing` (REQ-TH-005); security headers (HSTS, `nosniff`,
  `X-Frame-Options`, `Referrer-Policy`, CSP with the stream origin) (Group TS).
- **`stream.<domain>` site block:** `reverse_proxy icecast:8000` with
  `flush_interval -1` and a long read timeout on the `/radio` route (REQ-TR-003);
  `respond 403` for Icecast `/admin*` + `/status-json.xsl` (REQ-TH-004);
  optional CORS injection (REQ-TS-005).
- **Automatic `:80` → `:443` redirect** is Caddy default; ACME HTTP-01 keeps
  `/.well-known/acme-challenge/` served on `:80` (REQ-TP-007, NFR-TLS-5).
- **A documented DNS-01 variant** (commented) noting it requires a custom
  `xcaddy` image + a `{env.CF_API_TOKEN}`-style scoped token (REQ-TP-006).

Placeholders `<domain>` are operator-substituted; the file ships as a template
with `radio.example.test` / `stream.example.test` and a clear header comment
that TLS is inert until REQ-TO-001 prerequisites are met.

### NEW — Caddy service + volumes in `deploy/docker-compose.yml`

- A `caddy` service on the `gsr` network: `image: caddy:2` (stock), `restart:
  unless-stopped`, `ports: ["80:80", "443:443"]`, mounting `./Caddyfile:
  /etc/caddy/Caddyfile:ro` and named volumes `caddy_data:/data` (certs + ACME
  account key, REQ-TP-003/004, REQ-TO-004) + `caddy_config:/config`.
- Two named volumes `caddy_data`, `caddy_config` under the top-level `volumes:`
  key.
- **No `docker.sock` mount** (NFR-TLS-4).
- Guarded so it is **opt-in**: intended to run behind a compose profile (e.g.
  `--profile tls`) or a separate overlay file, so a domain-less dev host keeps
  the current plain-HTTP behaviour (REQ-TO-002). The exact profile/overlay
  mechanism is a run.sh/compose detail decided at Run time.

### MODIFY — `deploy/docker-compose.yml`

- **brain service (`:95`–`:96`):** remove the `8080:8080` host publish (reach as
  `brain:8080` on `gsr`); optionally `127.0.0.1:8080:8080` for host-loopback
  debug. Do **not** add `BRAIN_HTTP_HOST=127.0.0.1` (see D2). Add the public
  stream base env (e.g. `BRAIN_STREAM_PUBLIC_URL=https://stream.<domain>/radio`)
  for REQ-TR-005 (REQ-TH-001).
- **icecast service (`:15`–`:16`):** remove the `8000:8000` host publish (reach
  as `icecast:8000` on `gsr`); optionally `127.0.0.1:8000:8000` (REQ-TH-002).
  Set the advertised public `<hostname>` via the `moul` env (e.g.
  `ICECAST_HOSTNAME=stream.<domain>`) if honoured by the pinned tag (REQ-TR-006).
- **brain `.claude` mount (`:91`):** narrow to read-only / minimal
  (`- /home/charlie/.claude:/root/.claude:ro`) before public exposure
  (REQ-TH-011, NFR-TLS-4). If the OAuth refresh needs write, scope to the
  minimal token subpath instead of the whole dir — decided at Run time.
- **slskd (`:27`, `:37`–`:38`):** unchanged posture — stays profile-gated;
  document `127.0.0.1:5030:5030` for when the profile is on (REQ-TH-006).

### MODIFY — `brain/config.py`

- Add a public-stream setting used to compose the HTTPS player URL: e.g.
  `stream_public_url: str = _env("BRAIN_STREAM_PUBLIC_URL", "")` (empty ⇒ fall
  back to the existing `http://<host>:{icecast_public_port}{icecast_mount}`
  behaviour, preserving plain-HTTP dev). Keep `icecast_public_port` /
  `icecast_mount` (`:58`–`:59`) for the fallback (REQ-TR-005, REQ-TO-002).
- **Note only (no change here):** `http_host` (`:44`) is the whole-server bind;
  it stays `0.0.0.0` under the proxied topology (see D2). Documented so a future
  editor does not "harden" it to `127.0.0.1` and silently break Caddy routing.

### MODIFY — `brain/server.py`

- Teach the handler to read `X-Forwarded-For` / `X-Forwarded-Proto` from the edge
  so `/stats` and the like-token HMAC rate-limiting use the real client IP and
  the server knows it is TLS-fronted (REQ-TH-008). Trust these headers **only**
  from the proxy path (they arrive on the `gsr`-internal hop).
- Optionally set `protocol_version = "HTTP/1.1"` + `Content-Length` for upstream
  keep-alive to the edge (perf; not required for correctness).
- **Assumed elsewhere (not this SPEC):** the `/admin/stream` pre-auth-bypass fix
  moving `_check_admin_auth()` ahead of the `/admin/stream` dispatch
  (`:870`–`:873`). This SPEC blocks `/admin*` at the edge regardless (REQ-TH-003).

### MODIFY — `brain/website.py`

- Compose the `<audio>` source from `cfg.stream_public_url` when set, else the
  existing `http://<host>:{port}{mount}` fallback (`:14`–`:17`), so an HTTPS
  deploy emits `https://stream.<domain>/radio` and mixed content is avoided
  (REQ-TR-005). Update the module docstring (`:5`) accordingly.

### EXISTING — unchanged, must not regress

- **Liquidsoap → Icecast source path** (`deploy/config/radio.liq:179`–`:189`):
  the source connection pushes to `icecast:8000` over `gsr` and never traverses
  the edge — so the "don't reverse-proxy Icecast 2.4.x" source-side caveat does
  not apply (REQ-TR-002/004).
- **Liquidsoap harbor `expose 7138`** (`deploy/docker-compose.yml:54`–`:55`):
  stays `gsr`-only (REQ-TH-007).
- **slskd profile gating** (`:27`): default OFF, never proxied (REQ-TH-006).

---

## Milestones (priority order, no time estimates)

- **M1 — Compose topology (Priority High).** Add the `caddy` service + volumes;
  remove the brain + Icecast host publishes; narrow the `.claude` mount. Gate the
  edge behind an opt-in profile/overlay so dev stays plain-HTTP (REQ-TP-001,
  REQ-TH-001/002/011, REQ-TO-002/004, NFR-TLS-1/4).
- **M2 — Caddyfile routing + streaming (Priority High).** `radio`/`stream` site
  blocks; `reverse_proxy` with `flush_interval -1` + long read timeout on
  `/radio`; `:80`→`:443` redirect (Group TR, REQ-TP-002/007, NFR-TLS-2).
- **M3 — Hardening blocks (Priority High).** Block `/admin*`, Icecast
  `/admin*` + `/status-json.xsl`, and `/api/next` + `/api/airing` at the edge
  (REQ-TH-003/004/005).
- **M4 — Security headers (Priority High).** HSTS (no `preload` day-one),
  `nosniff`, `X-Frame-Options`, `Referrer-Policy`, CSP with the stream origin,
  optional CORS (Group TS).
- **M5 — Brain X-Forwarded + HTTPS player URL (Priority High).** `config.py`
  public-stream setting; `website.py` player URL; `server.py` `X-Forwarded-*`
  trust (REQ-TR-005, REQ-TH-008).
- **M6 — ACME issuance flow (Priority High).** STAGING-first global options;
  ACME email; document HTTP-01 default + DNS-01 fallback + reachability +
  firewall posture (Group TP, Group TO, REQ-TH-009, NFR-TLS-3/5).
- **M7 — Operator runbook (Priority Medium).** Prerequisite checklist (domain,
  DNS, inbound `:80`/`:443`, provider firewall), STAGING→prod switch, DNS-01
  custom-`xcaddy` path, degradation-when-domain-absent note.

---

## Technical approach

- **Caddy stock image** for the default HTTP-01 path (D4). The Caddyfile is a
  handful of directives; `reverse_proxy` auto-sets `X-Forwarded-*` and the Host
  header and auto-redirects `:80`→`:443`.
- **STAGING first** (REQ-TO-003): flip the `acme_ca` global to the staging
  directory, verify a clean issuance + a working proxied stream, then remove it
  for production. Persist `caddy_data` so the switch does not re-issue
  needlessly.
- **Reachability probe before buying a domain** (REQ-TO-007): confirm inbound
  `:80` and `:443` actually arrive at the dedicated server (a cert cannot fix
  connection-refused). On the WSL2 dev host this will likely fail — that is
  expected and is why TLS is opt-in there.
- **Firewall** (REQ-TH-009): the provider security group is the outer
  default-deny (22/80/443); the compose `no-publish` / `127.0.0.1` binds are the
  real control because Docker bypasses host `ufw`.

---

## Risks & mitigations

- **No public host / reachability** — the strongest independent blocker; a cert
  cannot fix connection-refused. Mitigation: reachability probe first; TLS is
  opt-in so a domain-less host is unaffected (REQ-TO-002/007).
- **`BRAIN_HTTP_HOST=127.0.0.1` breaks proxying** — the naive hardening reading.
  Mitigation: drop the host publish instead; keep the app bind on `0.0.0.0`
  (D2, REQ-TH-001).
- **Mixed content** — HTTPS site + HTTP stream silently breaks the player while
  the API looks fine. Mitigation: emit the HTTPS stream URL + CSP `media-src`
  (REQ-TR-005, REQ-TS-004).
- **Streaming buffering left on** — audio cuts, stuck metadata. Mitigation:
  `flush_interval -1` + long read timeout (REQ-TR-003, NFR-TLS-2).
- **Rate-limit self-DoS during setup** — 5 dup-certs/week, 5 failed-validations/
  hour. Mitigation: STAGING first (REQ-TO-003/005).
- **45-day certs (2026)** — any manual/cron renewal is a time bomb. Mitigation:
  in-daemon auto-renew (REQ-TP-004, NFR-TLS-3).
- **`docker.sock` / OAuth blast radius** — avoided by choosing Caddy (no socket)
  and scoping the `.claude` mount RO (NFR-TLS-4, REQ-TH-011).
- **`ufw` bypass by Docker** — a bare publish stays open. Mitigation: no-publish
  binds + provider firewall (REQ-TH-009, NFR-TLS-1).

---

## Test strategy (for Run phase)

- **Config-shape tests** (`brain/`): `stream_public_url` empty ⇒ HTTP fallback
  URL; set ⇒ HTTPS stream URL in `render_website(cfg)`; `X-Forwarded-For`/`-Proto`
  parsing yields the real client IP. Pure-Python, no network.
- **Caddyfile validation** (Run-time, non-unit): `caddy validate --config
  deploy/Caddyfile`; a STAGING issuance smoke test on a reachable host; a
  streaming smoke test (play `stream.<domain>/radio` for > 60s, confirm no
  cut-out + metadata updates); path-block probes (`/admin`, Icecast
  `/status-json.xsl`, `/api/next` → 403/404).
- **No live LE production issuance in CI** (rate limits) — STAGING or `caddy
  validate` only.
