---
id: SPEC-RADIO-SLSKDVPN-056
version: 0.2.0
status: draft
created: 2026-07-01
updated: 2026-07-01
author: charlie
priority: Medium
issue_number: TBD
depends_on:
  - SPEC-RADIO-SETUP-040
  - SPEC-RADIO-CORE-001
---

# SPEC-RADIO-SLSKDVPN-056 — Optional Mullvad VPN Routing for slskd Acquisition

## HISTORY

| Version | Date       | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
|---------|------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 0.1.0   | 2026-07-01 | Initial draft, occupying the global-incrementing SLSKDVPN-056 id (next after HOSTVOICE-049 / KNOWLEDGE-039 lineage; 056 reserved for this deliverable). Adds an OPT-IN, DEFAULT-OFF path to route ONLY the slskd (Soulseek) container's traffic through a Mullvad VPN via a `gluetun` sidecar (`network_mode: service:gluetun`), with a WireGuard kill-switch. Credential UX is account-number → auto-register: the operator supplies only the 16-digit Mullvad account number; run.sh generates a WireGuard keypair once, registers the public key with Mullvad's WireGuard API, stores the private key + assigned address, and reuses them on later runs (device-slot safe). Provider is config-driven (`VPN_SERVICE_PROVIDER`, default `mullvad`) so a port-forwarding provider can be swapped later. Distinct REQ namespaces: VW (wizard/config flags), VK (WireGuard key lifecycle), VP (compose topology), VV (post-up verify), VG (provider-configurability), VS (secrets discipline). Total: 31 REQ + 7 NFR. Verified against sources before drafting — see Section 3. |
| 0.2.0   | 2026-07-01 | Audit-driven revision (plan-auditor FAIL 0.83: MF-1..4 + P1..6; expert-devops corrections, all verified). CRITICAL pubkey-encoding trap closed: REQ-VK-004 now mandates `curl --data-urlencode` for the pubkey (a manual `printf 'account=%s&pubkey=%s'` corrupts `+`/`/` in a base64 key → Mullvad registers a wrong key, returns a valid-looking CIDR, tunnel never handshakes) with the account on stdin. MF-1: REQ-VK-006 is now fail-closed (slskd stays DOWN, never direct). MF-2: added REQ-VP-009 (`docker compose config` preflight abort; Compose floor ≥ 2.24.4, merge-test authoritative). MF-3: added REQ-VV-005 (blocked/timeout egress = soft note, not a leak; graceful degradation binding). MF-4: added REQ-VP-010 pinning `VPN_SERVER_*`→gluetun `SERVER_*` mapping. REQ-VK-002: openssl X25519 is the default keygen, pubkey derived by the same tool, `wg`-equality guard dropped — correctness proof is end-to-end (gluetun handshake healthy + Mullvad egress). Added REQ-VP-011 (never persist `SLSKD_URL`; unset unless enabled) and REQ-VP-012 (paired `--profile slskd --profile slskd-vpn`). Strengthened VP-001 (gluetun MUST join `gsr`), VP-003 (do not publish gluetun :8000 — icecast collision), VP-004 (BRAIN_HTTP_HOST untouched), VV-001 (`docker exec gsr-gluetun wget`, not the control server), VV-002/VV-004 (binary WARN/PASS lines; host public IP never logged). REQ-VG-003 made concrete (port-forward documentation deliverable). Added Section 9 (gluetun-restart orphans slskd — fail-closed, healer deferred to SELFHEAL-030). Total: 36 REQ + 7 NFR. |

---

## 1. Purpose

Give the operator an optional way to route the slskd (Soulseek) acquisition container's
network traffic through a Mullvad VPN with a kill-switch, so downloading happens behind the
VPN. It is opt-in and default OFF. The rest of the stack (brain, icecast, liquidsoap) stays
on the direct network — only slskd is tunneled.

Credential entry is deliberately minimal: the operator types just the Mullvad **account
number**. `scripts/run.sh` does the rest (generate a WireGuard keypair, register the public
key with Mullvad, retrieve the assigned tunnel address, wire up the sidecar), once, and reuses
the stored key on subsequent runs.

## 2. Problem Statement

Today `slskd` (compose service `gsr-slskd`, behind the `slskd` profile) runs on the shared
`gsr` bridge network and talks to Soulseek directly from the host's IP. Some operators want
that P2P acquisition traffic to leave via a VPN exit, with a kill-switch that drops slskd's
traffic if the tunnel fails. The stack is fully Dockerized under WSL2, so the Mullvad host app
(split-tunnel) cannot target a single container — the isolation must happen at the container
network layer.

Two forces make this non-trivial:

1. **Topology switch.** Putting slskd behind `network_mode: service:gluetun` strips slskd of
   its own network identity and ports. The brain then can no longer reach it at
   `http://slskd:5030` — it must use `http://gluetun:5030`. That switch must be conditional on
   the VPN toggle and must leave the default-OFF stack behaviorally identical to today.

2. **Credential lifecycle.** Mullvad is now WireGuard-only (OpenVPN removed) and caps device
   keys per account. Naively registering a new key on every start would exhaust the account's
   device slots. Key generation + registration must be idempotent: register once, reuse.

## 3. Verified Research Facts

Verified during drafting (2026-07-01). The three version-sensitive items were checked against
primary sources, not assumed:

- **Mullvad is WireGuard-only.** OpenVPN was removed from the Mullvad app in release 2025.14
  (2025-12-10); Mullvad's OpenVPN servers are taken down on or before **2026-01-15**. The
  classic `OPENVPN_USER=<account number>` flow is dead — WireGuard is the only path.
  (Source: mullvad.net/en/blog/removing-openvpn-from-the-mullvad-vpn-app — confirmed.)
- **gluetun Mullvad WireGuard env.** `VPN_SERVICE_PROVIDER=mullvad`, `VPN_TYPE=wireguard`,
  `WIREGUARD_PRIVATE_KEY=<base64>`, `WIREGUARD_ADDRESSES=<CIDR, e.g. 10.x.x.x/32>`;
  `SERVER_CITIES` / `SERVER_COUNTRIES` optional (blank ⇒ gluetun auto-selects);
  `WIREGUARD_ENDPOINT_PORT` defaults to 51820. gluetun's `FIREWALL` kill-switch is ON by
  default. (Source: qdm12/gluetun-wiki setup/providers/mullvad.md — confirmed. gluetun's
  OpenVPN-for-Mullvad support is being removed in step with Mullvad.)
- **Mullvad WireGuard key registration API.** `POST https://api.mullvad.net/wg` (NO trailing
  slash — a **correction** to the "/wg/" form in the brief) with form body
  `account=<number>` and url-encoded `pubkey=<base64 public key>`; the response body is the
  assigned address(es) in CIDR form (e.g. `10.x.x.x/32`) and is accepted only if it matches
  `^[0-9a-f:/.,]+$`. The endpoint is idempotent on `pubkey` — re-registering the same public
  key returns the same address and does not consume a new device slot. (Source: official
  mullvad/mullvad-wg.sh — confirmed; endpoint shape unchanged.)
  - **Encoding caveat (expert-devops, CRITICAL).** The base64 `pubkey` MUST be url-encoded by
    the HTTP client (`curl --data-urlencode "pubkey=<key>"`), never hand-encoded: a naive
    `printf 'account=%s&pubkey=%s'` form-encode turns a `+` in the key into a space (and `/`
    stays raw), so Mullvad registers a **corrupted** key, returns a valid-looking CIDR, and the
    tunnel never handshakes. The account is sent on stdin (`--data @-`) to keep it off argv.
- **No port forwarding on Mullvad (removed 2023).** Outbound Soulseek search/download still
  works behind Mullvad; INCOMING peer connectivity is reduced because Mullvad offers no port
  forwarding. This is the rationale for making the provider configurable — AirVPN / ProtonVPN
  still offer port forwarding through gluetun.

## 4. Scope

### In Scope

- A wizard toggle (default No) and config flag `SLSKD_VPN_ENABLED` (default `0`) that opt the
  slskd container into VPN routing.
- Account-number → auto-register credential UX: prompt only for the Mullvad account number;
  generate + register a WireGuard key once; store and reuse.
- A `gluetun` sidecar (provider-configurable, Mullvad default) with the WireGuard kill-switch
  on, slskd on `network_mode: service:gluetun`, gated behind a new `slskd-vpn` compose profile.
- Conditional `SLSKD_URL` so the brain reaches slskd at `gluetun:5030` when VPN is on and
  `slskd:5030` when off, with the brain→slskd X-API-Key path unchanged.
- A non-fatal post-up verify that proves slskd's egress actually leaves via the tunnel
  (egress-IP leak check) plus gluetun-healthy and slskd-reachable-through-gluetun probes.
- Secrets discipline consistent with SETUP-040 (silent input, trim, chmod 600, no secrets in
  logs or process list), with VPN secrets in `secrets/.env` (never `secrets/brain.env`).

### Out of Scope

See Section 8 (Exclusions).

## 5. Requirements (EARS)

### Group VW — Opt-In Wizard & Config Flags

- **REQ-VW-001** (State-Driven): While `SLSKD_VPN_ENABLED` is unset or `0` (the default), the
  system **shall** run the stack with no gluetun sidecar and slskd on the direct `gsr` network,
  such that the running stack is behaviorally identical to the pre-056 stack.
- **REQ-VW-002** (Event-Driven): When the first-run wizard reaches the acquisition phase and
  slskd is enabled, the wizard **shall** present a VPN toggle whose default is No.
- **REQ-VW-003** (Event-Driven): When the operator enables the VPN toggle, the wizard **shall**
  prompt for the 16-digit Mullvad account number via silent input, trim surrounding whitespace
  and any stray carriage return, and never echo or log it.
- **REQ-VW-004** (Optional): Where the operator wants a specific exit location, the wizard
  **shall** accept an optional country and/or city (stored as `VPN_SERVER_COUNTRIES` /
  `VPN_SERVER_CITIES`, mapped to gluetun's `SERVER_COUNTRIES` / `SERVER_CITIES` per REQ-VP-010);
  a blank value **shall** leave gluetun to auto-select the exit.
- **REQ-VW-005** (Ubiquitous): The wizard **shall** persist `SLSKD_VPN_ENABLED`,
  `VPN_SERVICE_PROVIDER`, `VPN_SERVER_COUNTRIES`, `VPN_SERVER_CITIES`, and `MULLVAD_ACCOUNT`
  into `secrets/.env` (never `secrets/brain.env`).

### Group VK — WireGuard Key Lifecycle

- **REQ-VK-001** (State-Driven): While both `WIREGUARD_PRIVATE_KEY` and `WIREGUARD_ADDRESSES`
  are present in `secrets/.env`, provisioning **shall** reuse them and **shall not** generate
  or register a new key (device-slot protection).
- **REQ-VK-002** (Event-Driven): When a keypair must be generated, the system **shall** produce
  an X25519 WireGuard keypair using `openssl` as the default generator (no `wireguard-tools`
  install required) and **shall** derive the public key from the freshly generated private key
  with the same tool that produced it (openssl `pkey -pubout`). The keypair's correctness
  **shall not** be asserted via a `wg pubkey` equality check (unrunnable exactly when
  `wireguard-tools` is absent); the authoritative correctness proof is end-to-end — gluetun
  reaching a healthy WireGuard handshake (REQ-VV-003) and the egress-IP check showing a Mullvad
  exit (REQ-VV-001/002). A corrupted or wrong key yields no handshake, gluetun stays unhealthy,
  and fail-closed (NFR-V-3) catches it.
- **REQ-VK-003** (Ubiquitous): The system **shall** persist the private key
  (`WIREGUARD_PRIVATE_KEY`) before issuing the registration call, so a generated key is never
  lost mid-flow.
- **REQ-VK-004** (Event-Driven): When registering, the system **shall** POST to
  `https://api.mullvad.net/wg` with the account delivered on stdin (`--data @-`, so it never
  appears on argv) and the public key passed as `curl --data-urlencode "pubkey=<key>"` so `+`
  and `/` in the base64 key are correctly percent-encoded by curl. The system **shall not**
  hand-encode the form body (a manual `printf 'account=%s&pubkey=%s'` corrupts `+`/`/`, silently
  registering a wrong key — see Section 3 encoding caveat).
- **REQ-VK-005** (Event-Driven): When the registration responds, the system **shall** accept
  the body only if it matches `^[0-9a-f:/.,]+$`, parse the assigned CIDR address, and store it
  as `WIREGUARD_ADDRESSES`.
- **REQ-VK-006** (Unwanted Behavior): If the registration call fails (network error, empty
  body, or a body that does not match the address pattern), then the system **shall not** write
  `WIREGUARD_ADDRESSES`, **shall not** bring up gluetun, **shall not** start slskd on the direct
  `gsr` network (fail-closed — acquisition pauses rather than leaking), and **shall** print a
  line prefixed `ERROR:` naming the registration failure and stating that acquisition is paused.
- **REQ-VK-007** (State-Driven): While `WIREGUARD_PRIVATE_KEY` is present but
  `WIREGUARD_ADDRESSES` is absent (a prior registration failed after the key was stored),
  provisioning **shall** re-derive the public key from the stored private key and re-attempt
  registration, relying on the endpoint's idempotency to return the same address without
  consuming a new device slot.
- **REQ-VK-008** (Ubiquitous): The system **shall** document the force-regeneration path
  (removing the `WIREGUARD_*` lines from `secrets/.env`) and **shall** warn that Mullvad caps
  device keys per account (~5), so force-regeneration should be paired with revoking the old
  key in the Mullvad account panel.

### Group VP — Compose Topology

- **REQ-VP-001** (State-Driven): While the VPN is enabled, the stack **shall** add a `gluetun`
  sidecar with `cap_add: NET_ADMIN`, device `/dev/net/tun`, and environment sourced from
  `secrets/.env`. gluetun **shall** be a member of the `gsr` network — this is load-bearing:
  `gsr` membership is what lets the brain reach slskd at `gluetun:5030` through the kill-switch,
  so gluetun **shall not** be moved off `gsr`.
- **REQ-VP-002** (State-Driven): While the VPN is enabled, the slskd service **shall** run with
  `network_mode: "service:gluetun"` and **shall not** publish its own ports or attach to `gsr`
  directly.
- **REQ-VP-003** (State-Driven): While the VPN is enabled, the operator web-UI port `5030`
  **shall** be published on the gluetun container so the operator's browser reaches the slskd
  UI at `http://localhost:5030` exactly as before. gluetun's own control-server port `8000`
  **shall not** be published (it would collide with icecast's host `8000:8000`).
- **REQ-VP-004** (State-Driven): While the VPN is enabled, the brain **shall** reach slskd at
  `http://gluetun:5030`; while the VPN is disabled, the brain **shall** reach slskd at
  `http://slskd:5030`. This switch is confined to the slskd target URL: the system **shall not**
  modify `BRAIN_HTTP_HOST` or the brain's own listen bind (changing it would break the brain's
  own reachability on `gsr`).
- **REQ-VP-005** (Ubiquitous): gluetun **shall** be configured with the firewall/kill-switch
  on, DNS handled by gluetun, and IPv6 disabled, so there is no DNS or IPv6 leak.
- **REQ-VP-006** (Ubiquitous): The brain→slskd X-API-Key authentication (`SLSKD_API_KEY`)
  **shall** be unchanged regardless of VPN state.
- **REQ-VP-007** (State-Driven): While the VPN is enabled, the VPN topology **shall** be gated
  behind a `slskd-vpn` compose profile, mirroring the existing `slskd` profile pattern, so it
  activates only when enabled.
- **REQ-VP-008** (Unwanted Behavior): If gluetun's tunnel is not yet established, then slskd
  (sharing gluetun's netns behind the kill-switch) **shall** have no egress until the tunnel is
  up, so there is no leak window during startup.
- **REQ-VP-009** (Event-Driven): When the VPN is enabled, before bringing the stack up run.sh
  **shall** run `docker compose -f docker-compose.yml -f docker-compose.vpn.yml --profile slskd
  --profile slskd-vpn config` as a preflight and, if it exits non-zero, **shall** abort with a
  line prefixed `ERROR:` naming the compose-merge/version prerequisite (Docker Compose ≥ 2.24.4
  for the `!reset` merge). This `config`-merge check is the authoritative, version-independent
  gate — a passing merge is what matters, not the version string alone.
- **REQ-VP-010** (Ubiquitous): The gluetun service **shall** receive its exit-location selection
  by mapping `VPN_SERVER_COUNTRIES` → `SERVER_COUNTRIES` and `VPN_SERVER_CITIES` →
  `SERVER_CITIES` in the compose `environment:` block (interpolated from the exported
  `secrets/.env`); gluetun **shall not** be expected to read the `VPN_SERVER_*` names directly.
- **REQ-VP-011** (Unwanted Behavior): The system **shall not** persist `SLSKD_URL` into
  `secrets/.env`, and unless `SLSKD_VPN_ENABLED=1` run.sh **shall** actively `unset SLSKD_URL`
  before `docker compose up`, so a leftover `SLSKD_URL=http://gluetun:5030` can never override
  the `${SLSKD_URL:-http://slskd:5030}` default and point the brain at an absent gluetun.
- **REQ-VP-012** (State-Driven): While the VPN is enabled, run.sh **shall** activate both
  `--profile slskd` and `--profile slskd-vpn` together in one place (slskd carries only the
  `slskd` profile, gluetun only `slskd-vpn`); activating either profile alone (gluetun with
  nothing behind it, or slskd on the direct network) **shall not** occur.

### Group VV — Post-Up Verify

- **REQ-VV-001** (Event-Driven): When the stack is up with the VPN enabled, run.sh **shall**
  run a non-fatal egress-IP check that reads the exit IP from within gluetun's network namespace
  via `docker exec gsr-gluetun wget -qO- <ip-echo-url>` (NOT gluetun's control server, whose
  routes are private/auth-gated), and compare it to the host's own public IP.
- **REQ-VV-002** (Unwanted Behavior): If the observed egress IP equals the host's own public
  IP, then the check **shall** emit a line prefixed `WARN: LEAK` stating that slskd's traffic is
  NOT leaving via the tunnel; if the two IPs differ, it **shall** log a `PASS` line.
- **REQ-VV-003** (Event-Driven): When it runs, the verify **shall** also assert that gluetun
  reports healthy and that slskd is reachable through gluetun (`:5030` answers).
- **REQ-VV-004** (Ubiquitous): The verify **shall** be non-fatal (warn only) and **shall** log
  the VPN exit IP (a shared Mullvad exit, safe to log); the host's own public IP **shall not** be
  written to any log or the terminal at all — the comparison is done in memory and only the
  `PASS`/`WARN: LEAK` verdict plus the VPN exit IP are logged.
- **REQ-VV-005** (Unwanted Behavior): If the in-namespace egress probe is blocked or times out,
  then the check **shall** treat it as a soft note (a blocked probe means the kill-switch held —
  no leak) and **shall not** raise a leak alarm; if `curl` or `docker` is unavailable, the check
  **shall** print a skip note and **shall not** abort startup.

### Group VG — Provider-Configurability

- **REQ-VG-001** (Ubiquitous): `VPN_SERVICE_PROVIDER` **shall** default to `mullvad` and
  **shall** be a configuration value, so a different gluetun-supported provider can be selected
  without re-architecting the topology.
- **REQ-VG-002** (Ubiquitous): The generic WireGuard credential variables
  (`WIREGUARD_PRIVATE_KEY`, `WIREGUARD_ADDRESSES`) **shall** be provider-neutral so a provider
  with its own credential flow can populate them.
- **REQ-VG-003** (Ubiquitous): The SPEC **shall** ship a documented, concrete port-forwarding
  path for a capable provider: the docs **shall** state that setting `VPN_SERVICE_PROVIDER` to a
  port-forwarding provider (e.g. AirVPN or ProtonVPN) with `VPN_PORT_FORWARDING=on` and
  `VPN_PORT_FORWARDING_PROVIDER=<provider>` in gluetun, and pointing slskd's listen port at the
  forwarded port, restores incoming Soulseek peer connectivity. No port-forwarding code is built
  for Mullvad (it offers none); the requirement is the documentation deliverable.

### Group VS — Secrets Discipline

- **REQ-VS-001** (Ubiquitous): The Mullvad account number and `WIREGUARD_PRIVATE_KEY` **shall**
  be treated as secrets: silent input, whitespace/CR-trimmed, stored in `secrets/.env` at
  `chmod 600`.
- **REQ-VS-002** (Unwanted Behavior): The system **shall not** log the account number or the
  private key, and **shall not** pass either on any command-line argument, so neither is exposed
  in `ps` / the process list (the account reaches curl on stdin per REQ-VK-004).
- **REQ-VS-003** (Ubiquitous): VPN secrets **shall** live in `secrets/.env`, never in
  `secrets/brain.env`, consistent with the existing `ANTHROPIC_API_KEY` isolation rule.

## 6. Non-Functional Requirements

- **NFR-V-1** (Default-off parity): With the VPN disabled, `docker compose config` and the
  running brain container environment **shall** be behaviorally identical to the pre-056 stack.
- **NFR-V-2** (Compose merge prerequisite): The slskd `network_mode` switch relies on a compose
  override mechanism (Compose `!reset` on `networks`/`ports`, available in Docker Compose
  ≥ 2.24.4). The authoritative, version-independent gate is the `docker compose config` merge
  preflight (REQ-VP-009): a clean merge is what matters — the version number is only the
  documented prerequisite the preflight enforces when the merge fails.
- **NFR-V-3** (Fail-closed): A VPN-provisioning failure **shall never** fall back to running
  slskd on the direct network; acquisition **shall** pause (slskd stays down) instead.
- **NFR-V-4** (Idempotency): Repeated run.sh invocations **shall** register at most one device
  key per account (no device-slot exhaustion).
- **NFR-V-5** (Minimal host deps): Key generation **shall** use `openssl` X25519 as the default
  generator and **shall not** require `wireguard-tools` to be installed; the openssl path is
  cryptographically sound (clamping is applied at use-time by both openssl and WireGuard).
- **NFR-V-6** (Graceful verify degradation): The leak-check **shall** degrade gracefully when
  `curl` or `docker exec` is unavailable (skip with a note; never abort startup).
- **NFR-V-7** (Secret-hygiene regression): A dry run **shall** show zero occurrences of the
  account number or private key in combined stdout+stderr, and no VPN secret on any argv.

## 7. Assumptions

- The operator has a funded Mullvad account and its 16-digit account number.
- Docker Compose is v2 and ≥ 2.24.4 (for the `!reset` override-merge mechanism; enforced by the
  REQ-VP-009 preflight); the host has `openssl` (WSL2 default) and `docker`.
- `secrets/.env` is gitignored and already used by run.sh for other secrets.
- SETUP-040's wizard host (`scripts/run.sh` v0.4) provides the reusable primitives
  (`_set_env_var`, `read -rs`, `provision_*` idempotency, `prepare_filesystem`, `resolve_slskd`
  / `PROFILE_ARGS`, `load_secrets`, `check_slskd_web`).

## 8. Exclusions (What NOT to Build)

- **Routing brain / icecast / liquidsoap through the VPN.** This SPEC tunnels ONLY slskd.
- **Any GUI or web control for the VPN.** Configuration is wizard + `secrets/.env` only.
- **Port forwarding on Mullvad.** Mullvad removed it; not offered, not emulated. (Provider-
  configurability leaves the door open for a port-forwarding provider — but building that
  provider's port-forward flow is out of scope here.)
- **OpenVPN support.** Mullvad is WireGuard-only; no OpenVPN path is built.
- **Auto-revoking old device keys on force-regeneration.** Revocation is a documented manual
  step in the Mullvad account panel; the SPEC does not call any revoke API.
- **Multi-hop, SOCKS/HTTP proxy exposure from gluetun, or per-persona/per-download VPN
  selection.** Single tunnel for the slskd container, full stop.
- **A separate healer/monitor for tunnel uptime.** The kill-switch (fail-closed) is the safety
  mechanism; ongoing tunnel monitoring is deferred (SELFHEAL-030 territory, not owned here).

## 9. Known Operational Limitation

Restarting the gluetun container orphans slskd: slskd keeps a handle to the now-dead network
namespace and must itself be restarted to regain egress. This is fail-closed (loss of egress,
never a leak); automated recovery is deferred to SELFHEAL-030 and is out of scope here.
