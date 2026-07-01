# SPEC-RADIO-SLSKDVPN-056 — Implementation Plan

This plan describes HOW the requirements in `spec.md` are realized. It is guidance for the Run
phase; the SPEC's EARS requirements and `acceptance.md` are the contract. No code is written in
the Plan phase.

## 1. Technical Approach

### 1.1 Architecture (locked)

- VPN sidecar: **gluetun** (`qmcgaw/gluetun`), one container per stack.
- slskd runs with `network_mode: "service:gluetun"` — it shares gluetun's network namespace,
  so all of slskd's traffic egresses through the WireGuard tunnel and is dropped by gluetun's
  kill-switch when the tunnel is down.
- This is NOT the Mullvad host app: the stack is Dockerized under WSL2, where host split-tunnel
  cannot target a single container. Container-network isolation is the only correct layer.
- Provider is a config value (`VPN_SERVICE_PROVIDER`, default `mullvad`) so AirVPN / ProtonVPN
  (which have port forwarding, unlike Mullvad) can be swapped in later without re-architecting.

### 1.2 The topology switch (the load-bearing design point)

VPN OFF (default, unchanged from today):

```
brain  --gsr-->  slskd (own IP on gsr, publishes 5030)     SLSKD_URL=http://slskd:5030
```

VPN ON:

```
brain  --gsr-->  gluetun (owns netns + gsr membership, publishes 5030)
                   └── slskd (network_mode: service:gluetun, NO own ports/network)
                                                                SLSKD_URL=http://gluetun:5030
```

Two coordinated changes deliver the switch:

1. **Conditional `SLSKD_URL`.** In `deploy/docker-compose.yml`, change the brain's
   `SLSKD_URL: http://slskd:5030` (currently line 81) to
   `SLSKD_URL: ${SLSKD_URL:-http://slskd:5030}`. This mirrors the existing
   `SLSKD_API_KEY: ${SLSKD_API_KEY}` interpolation, which already relies on `load_secrets()`
   exporting values before `docker compose up`. run.sh exports `SLSKD_URL=http://gluetun:5030`
   only when `SLSKD_VPN_ENABLED=1`; otherwise the `:-` default keeps `http://slskd:5030`, so
   the VPN-off brain environment is byte-identical to today.
   - **Never persist `SLSKD_URL` (REQ-VP-011).** run.sh must NOT write `SLSKD_URL` into
     `secrets/.env`, and must actively `unset SLSKD_URL` unless `SLSKD_VPN_ENABLED=1`. A leftover
     `SLSKD_URL=http://gluetun:5030` would override the `:-` default and point the VPN-off brain
     at a gluetun that is not running (breaks NFR-V-1). `SLSKD_URL` is exported per-invocation
     only, never stored.
   - CORRECTION vs the brief's earlier framing: do NOT touch `BRAIN_HTTP_HOST` or any brain
     bind — the switch is purely the slskd target URL. The brain's own reachability
     (`:8080`, gsr) is unchanged.

2. **slskd network_mode + gluetun sidecar via a compose override.** Because a single service
   definition cannot carry two network modes, the VPN topology lives in a dedicated override
   file `deploy/docker-compose.vpn.yml`, applied by run.sh with an extra `-f` (and
   `--profile slskd-vpn`) only when the VPN is enabled. The override:
   - Declares the `gluetun` service (profile `slskd-vpn`; `cap_add: [NET_ADMIN]`;
     `devices: [/dev/net/tun]`; `env_file: ../secrets/.env`; `networks: [gsr]`; publishes
     `5030:5030` for the operator's browser; a healthcheck; `FIREWALL` kill-switch on;
     IPv6 disabled).
   - Patches the base `slskd` service to `network_mode: "service:gluetun"`, `depends_on`
     gluetun (healthy), and **clears** slskd's base `networks: [gsr]` and `ports: [5030]` so
     they do not conflict with `network_mode`.
   - The clearing is the merge subtlety: Compose additive-merge cannot remove keys, and
     `network_mode` + `networks` together is an error. Use Compose `!reset null` on `networks`
     and `ports` in the override (Docker Compose ≥ 2.24.4). This is enforced as a **preflight
     gate** (REQ-VP-009 / NFR-V-2): before `up`, run.sh runs `docker compose -f
     docker-compose.yml -f docker-compose.vpn.yml --profile slskd --profile slskd-vpn config`
     and ABORTS with an `ERROR:` prerequisite message if it exits non-zero. The `config` merge is
     the authoritative, version-independent gate (a clean merge is what matters); it must emit a
     `slskd` service with `network_mode: service:gluetun` and NO `networks`/`ports` keys.
   - When VPN is on, run.sh activates BOTH profiles together in one place
     (`--profile slskd --profile slskd-vpn`, REQ-VP-012): slskd carries only the `slskd` profile,
     gluetun only `slskd-vpn`; activating either alone leaves gluetun-with-nothing-behind-it or
     slskd-on-the-direct-network.

Why an override file rather than stuffing conditionals into the base compose: it keeps the
default path byte-identical (base file's slskd is untouched when VPN is off) and isolates the
version-sensitive `!reset` mechanism to a file that is only ever loaded in VPN mode.

### 1.3 WireGuard key lifecycle (idempotent, device-slot safe)

Provisioning function (new; mirrors `provision_slskd_web_creds()` idempotency, called BEFORE
`load_secrets` so the values are exported for the template/compose render):

1. **Short-circuit (REQ-VK-001):** if `secrets/.env` already has both
   `WIREGUARD_PRIVATE_KEY` and `WIREGUARD_ADDRESSES`, return immediately — reuse. This is the
   device-slot guard (Mullvad caps ~5 keys/account).
2. **Generate keypair (REQ-VK-002):** X25519.
3. **Store private key first (REQ-VK-003):** `_set_env_var WIREGUARD_PRIVATE_KEY` so a
   generated key is never lost even if registration crashes.
4. **Register (REQ-VK-004):** POST to `https://api.mullvad.net/wg` with the account on **stdin**
   (off argv) and the pubkey url-encoded **by curl** (never hand-encoded):
   `printf 'account=%s' "$acct" | curl -sS -m "$GSR_HEALTH_TIMEOUT" --data @- --data-urlencode "pubkey=$pub" https://api.mullvad.net/wg`.
   `--data-urlencode` is load-bearing: a manual `printf 'account=%s&pubkey=%s'` pre-encode turns
   a `+` in the base64 pubkey into a space (and leaves `/` raw), so Mullvad registers a CORRUPTED
   key, returns a valid-looking CIDR, and the tunnel never handshakes.
5. **Parse + validate (REQ-VK-005):** accept the response only if it matches `^[0-9a-f:/.,]+$`;
   take the assigned CIDR and `_set_env_var WIREGUARD_ADDRESSES`.
6. **Fail-closed (REQ-VK-006 / NFR-V-3):** if curl fails or the body is not an address, do NOT
   write `WIREGUARD_ADDRESSES`, do NOT bring gluetun up, print an `ERROR:` line naming the
   failure, and leave slskd DOWN this launch — never start slskd on the direct `gsr` network.
   Next run resumes at step (7).
7. **Resume-after-partial (REQ-VK-007):** if `WIREGUARD_PRIVATE_KEY` is present but
   `WIREGUARD_ADDRESSES` is absent, re-derive the public key from the stored private key and
   re-register. The endpoint is idempotent on pubkey — same key returns the same address, no
   new slot.
8. **Force-regen (REQ-VK-008):** documented as "remove the `WIREGUARD_*` lines from
   `secrets/.env` (and revoke the old key in the Mullvad account panel to free the slot)."

### 1.4 WireGuard keypair generation approach (chosen)

Decision (expert-devops): **`openssl genpkey -algorithm X25519` is the DEFAULT generator; do NOT
require `wireguard-tools`.** Derive the public key with the SAME tool that produced the private
key (openssl `pkey -pubout`), and register that derived key.

Rationale:
- `openssl` is on a stock WSL2 host and needs no install (NFR-V-5); `wireguard-tools` is NOT
  present by default. Making `wg` the primary tool is wrong because the `wg`-based correctness
  check is exactly unrunnable when `wg` is absent (the fallback case), giving false confidence.
- The openssl X25519 path is cryptographically sound. Clamping is applied at use-time by both
  openssl and WireGuard, so the openssl-derived public key is exactly what WireGuard presents on
  the wire — registering it with Mullvad is correct.

Exact deterministic extraction (WireGuard wants the raw 32-byte base64 scalar/point):
- private key = last 32 bytes of the 48-byte PKCS#8 DER:
  `openssl genpkey -algorithm X25519 -outform DER | tail -c 32 | base64 -w0`
- public key = last 32 bytes of the 44-byte SPKI DER derived from that private key:
  `openssl pkey -in priv.der -pubout -outform DER | tail -c 32 | base64 -w0`
- Rejected: a throwaway `docker run` keygen container (extra image pull); pure-python keygen
  (needs the `cryptography` package, not guaranteed present). `wireguard-tools` MAY be used if
  already installed, but is never required.

Correctness proof (REQ-VK-002) is END-TO-END, not a `wg pubkey` equality check: a corrupted or
wrong key produces no WireGuard handshake ⇒ gluetun never reaches `healthy` (REQ-VV-003) and the
egress-IP check shows no Mullvad exit (REQ-VV-001/002) ⇒ fail-closed (NFR-V-3) keeps slskd down.
The handshake + egress verdict IS the ground truth; a `wg pubkey` self-check is dropped because
it is unavailable precisely in the openssl-default case.

### 1.5 gluetun environment (rendered from secrets/.env)

Set on the gluetun service via an explicit `environment:` block (values interpolated from the
`load_secrets()`-exported `secrets/.env`): `VPN_SERVICE_PROVIDER=${VPN_SERVICE_PROVIDER:-mullvad}`,
`VPN_TYPE=wireguard`, `WIREGUARD_PRIVATE_KEY`, `WIREGUARD_ADDRESSES`, and the kill-switch/leak
defaults (`FIREWALL=on`, gluetun DNS, IPv6 off). Exact variable names are pinned in spec.md
Section 3 (verified against the gluetun wiki).

- **Server-selection remap (REQ-VP-010, MF-4).** The wizard stores `VPN_SERVER_COUNTRIES` /
  `VPN_SERVER_CITIES`, but gluetun reads `SERVER_COUNTRIES` / `SERVER_CITIES`. The override maps
  them explicitly in the `environment:` block: `SERVER_COUNTRIES: ${VPN_SERVER_COUNTRIES:-}` and
  `SERVER_CITIES: ${VPN_SERVER_CITIES:-}`. Without this remap a chosen country is silently
  ignored. gluetun never reads the `VPN_SERVER_*` names directly.
- **Do NOT publish gluetun's control-server port `8000`** — it collides with icecast's host
  `8000:8000`. Only `5030:5030` (the slskd UI) is published on gluetun.
- **`FIREWALL_INPUT_PORTS=5030` is optional**, added ONLY if the slskd UI must be reached from a
  non-host LAN machine; it is NOT set by default (host `localhost` access does not need it).

### 1.6 Post-up verify (non-fatal; mirrors check_slskd_web)

A new verify step (runs only when the VPN was enabled this launch, like `check_slskd_web` gates
on `SLSKD_CHOICE`):
- **Egress-IP leak check (REQ-VV-001/002).** Read the exit IP from INSIDE gluetun's netns with
  `docker exec gsr-gluetun wget -qO- https://ipinfo.io/ip` (gluetun ships busybox wget) — NOT
  gluetun's control server, whose routes are private/auth-gated by default. slskd shares that
  netns, so gluetun's egress IP == slskd's egress IP. Separately fetch the host's own public IP.
  Compare in memory: differ ⇒ log a `PASS` line; equal ⇒ emit `WARN: LEAK` (slskd traffic is NOT
  using the tunnel).
- **Blocked/timeout = soft note (REQ-VV-005, MF-3).** If the in-namespace probe is blocked or
  times out, the kill-switch held — NO leak — so print a soft note ("could not read VPN exit IP;
  tunnel may still be negotiating"), never a leak alarm. If `curl` or `docker` is unavailable,
  print a skip note and continue (never abort startup, NFR-V-6).
- **gluetun healthy + slskd reachable (REQ-VV-003):** `docker inspect` gluetun health ==
  healthy; `curl -m "$GSR_HEALTH_TIMEOUT" http://127.0.0.1:$SLSKD_PORT/` answers.
- **Privacy (REQ-VV-004):** log the VPN exit IP (shared Mullvad exit, safe); the host's own
  public IP is NEVER written to the log or terminal — only the `PASS`/`WARN: LEAK` verdict plus
  the VPN exit IP are logged. Reuse `-m "$GSR_HEALTH_TIMEOUT"` and the `log`/WARN style.

## 2. Files Touched (anticipated)

| File | Change |
|------|--------|
| `deploy/docker-compose.yml` | Brain `SLSKD_URL` → `${SLSKD_URL:-http://slskd:5030}` (only change to the base file). |
| `deploy/docker-compose.vpn.yml` | NEW override: gluetun service (profile `slskd-vpn`) + slskd `network_mode: service:gluetun` with `!reset` on `networks`/`ports`. |
| `scripts/run.sh` | New VPN wizard toggle + account prompt; `resolve_slskd_vpn()` paired-profile + `-f` selection with a `docker compose config` preflight (REQ-VP-009); `provision_wireguard_key()` (openssl X25519 keygen, register-once via `--data-urlencode`); export `SLSKD_URL=gluetun:5030` when on and `unset SLSKD_URL` otherwise (REQ-VP-011); render gluetun env incl. `VPN_SERVER_*`→`SERVER_*` remap; post-up `check_slskd_vpn()` leak verify. |
| `secrets/.env` (runtime, gitignored) | New keys: `SLSKD_VPN_ENABLED`, `VPN_SERVICE_PROVIDER`, `VPN_SERVER_COUNTRIES`, `VPN_SERVER_CITIES`, `MULLVAD_ACCOUNT`, `WIREGUARD_PRIVATE_KEY`, `WIREGUARD_ADDRESSES`. |
| docs (`docs/components/*`, runtime-config) | Document the toggle, force-regen, port-forwarding caveat, provider swap. (Sync phase.) |

## 3. Milestones (priority-ordered, no time estimates)

1. **M1 — Config surface & default-off parity.** Add the flags, the wizard toggle (default No),
   the `SLSKD_URL` interpolation, and the `unset SLSKD_URL` guard (REQ-VP-011). Prove VPN-off
   parity (NFR-V-1) before anything else.
2. **M2 — Key lifecycle.** `provision_wireguard_key()`: openssl X25519 keygen, register via
   `--data-urlencode` (account on stdin), parse+validate, store-priv-first, resume-after-partial,
   force-regen docs. Idempotency + device-slot safety (REQ-VK-*, NFR-V-4).
3. **M3 — Compose topology.** Override file, `!reset` merge (Compose ≥ 2.24.4) + `docker compose
   config` preflight abort (REQ-VP-009), `slskd-vpn` profile, paired-profile activation
   (REQ-VP-012), gluetun env render incl. `SERVER_*` remap (REQ-VP-010), no `:8000` publish,
   kill-switch/DNS/IPv6 defaults (REQ-VP-*).
4. **M4 — Fail-closed wiring.** Provisioning-failure ⇒ slskd stays down, never direct
   (NFR-V-3); startup no-leak window (REQ-VP-008).
5. **M5 — Verify.** `check_slskd_vpn()` egress-IP leak check + gluetun-healthy + slskd-through-
   gluetun, non-fatal, privacy-preserving (REQ-VV-*).
6. **M6 — Provider generality + docs.** Confirm `VPN_SERVICE_PROVIDER` swap path, document the
   port-forwarding caveat and AirVPN/ProtonVPN note (REQ-VG-*).

## 4. Risks & Mitigations

- **Silent auth failure from a corrupted registration key** (hand-encoded pubkey OR a bad
  extraction). Mitigate: register the pubkey with `curl --data-urlencode` (REQ-VK-004), derive
  the pubkey with the same tool that made the privkey, and rely on the END-TO-END proof —
  gluetun handshake healthy + Mullvad egress (REQ-VK-002 / REQ-VV-003); a bad key ⇒ no handshake
  ⇒ fail-closed. The `wg pubkey` self-check is dropped (unrunnable in the openssl-default case).
- **Compose `!reset` unsupported** on an older Compose. Mitigate: the `docker compose config`
  preflight (REQ-VP-009) aborts with an `ERROR:` prerequisite message (Compose ≥ 2.24.4) rather
  than failing confusingly at runtime; the merge check itself is the authoritative gate.
- **Device-slot exhaustion** if idempotency regresses. Mitigate: the REQ-VK-001 short-circuit is
  the first line of the provisioning function; NFR-V-4 asserts at most one registration across
  repeated runs.
- **Accidental direct-network fallback** on provisioning failure (would defeat the operator's
  intent to hide acquisition). Mitigate: NFR-V-3 fail-closed — slskd stays DOWN, verified.
- **Secret exposure** (account number on curl argv, key in logs). Mitigate: body on stdin
  (REQ-VS-002), silent input + trim + chmod 600 (REQ-VS-001), dry-run scan (NFR-V-7).

## 5. Delegation Notes

- Backend/infra domain (Docker networking, compose merge, WireGuard). Recommend **expert-devops**
  consultation for the gluetun/`network_mode: service:gluetun` topology and the `!reset` merge.
- Branch/PR handling → **manager-git**.
