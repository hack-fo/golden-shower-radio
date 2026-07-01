# slskd VPN — Optional Mullvad Routing (SPEC-RADIO-SLSKDVPN-056)

An opt-in, default-OFF way to route **only** the slskd (Soulseek) acquisition container's
traffic through a Mullvad VPN with a WireGuard kill-switch. The rest of the station (brain,
icecast, liquidsoap) stays on the direct network — only slskd is tunneled.

Because the stack is Dockerized under WSL2, the Mullvad host app cannot split-tunnel a single
container; the isolation happens at the container network layer via a
[gluetun](https://github.com/qdm12/gluetun) sidecar and `network_mode: "service:gluetun"`.

Default-OFF is byte-identical to the pre-056 stack: when the VPN is disabled, no gluetun
sidecar exists, slskd runs directly on the `gsr` network publishing `5030`, and the brain
reaches it at `http://slskd:5030`.

---

## Enabling the VPN

Two equivalent ways to turn it on:

1. **First-run wizard.** During setup, after the Soulseek/slskd credentials, the wizard asks
   `Route slskd via Mullvad VPN? [y/N]` (default **No**). Answer `y` and provide:
   - the **Mullvad account number** (input hidden; never echoed or logged),
   - an optional exit **country code** (e.g. `se`) and **city** (blank = gluetun auto-selects).
2. **Manually**, by setting `SLSKD_VPN_ENABLED=1` and `MULLVAD_ACCOUNT=<16 digits>` in
   `secrets/.env`, then restarting.

Keys written to `secrets/.env` (never `secrets/brain.env`):

| Key | Meaning |
|-----|---------|
| `SLSKD_VPN_ENABLED` | `1` = route slskd via VPN; `0`/absent = direct (default) |
| `VPN_SERVICE_PROVIDER` | gluetun provider, `mullvad` by default (config-driven) |
| `VPN_SERVER_COUNTRIES` | optional exit country code(s); remapped to gluetun's `SERVER_COUNTRIES` |
| `VPN_SERVER_CITIES` | optional exit city; remapped to gluetun's `SERVER_CITIES` |
| `MULLVAD_ACCOUNT` | your 16-digit Mullvad account number (secret) |
| `WIREGUARD_PRIVATE_KEY` | auto-generated once (secret); reused thereafter |
| `WIREGUARD_ADDRESSES` | tunnel address assigned by Mullvad (auto-populated) |

The wizard stores exit selection under the `VPN_SERVER_*` names; the compose override remaps
them to gluetun's `SERVER_COUNTRIES` / `SERVER_CITIES`. gluetun never reads the `VPN_SERVER_*`
names directly.

---

## Account-number → auto-register credential flow

You only ever type the Mullvad **account number**. On the next start, `provision_mullvad_wg()`
in `scripts/run.sh` does the rest — **once**:

1. If `WIREGUARD_PRIVATE_KEY` **and** `WIREGUARD_ADDRESSES` are already present, it reuses them
   and makes **no** API call (device-slot safe — see the ~5-device cap below).
2. Otherwise it generates a WireGuard keypair with **openssl** (X25519; no `wireguard-tools`
   install required) and stores the private key **before** registering, so a generated key is
   never lost mid-flow.
3. It registers the **public** key with Mullvad:
   `POST https://api.mullvad.net/wg`, with the account number delivered on **stdin**
   (`curl --data @-`, so it never appears in `ps`/argv) and the public key url-encoded by curl
   (`--data-urlencode`). This encoding is load-bearing: a hand-built form body would corrupt a
   `+`/`/` in the base64 key and silently register a wrong key that never handshakes.
4. It validates the response against `^[0-9a-f:/.,]+$`, takes the assigned IPv4 CIDR, and stores
   it as `WIREGUARD_ADDRESSES`.

If a run stored the private key but registration failed, the next run re-derives the public key
from the stored private key and re-registers — Mullvad's endpoint is idempotent on the public
key, so it returns the same address and consumes no new device slot.

Correctness is proven **end-to-end**, not by a local self-check: a correct key produces a
WireGuard handshake so gluetun reaches `healthy` and the egress-IP check shows a Mullvad exit; a
corrupted key leaves gluetun unhealthy and fail-closed keeps slskd down.

---

## Device cap & force re-provision

Mullvad caps WireGuard device keys at roughly **5 per account**. Provisioning registers **once**
and reuses the stored key forever, so repeated restarts never exhaust the slots.

To force a fresh key (e.g. after rotating providers or hitting the cap):

1. Remove the `WIREGUARD_PRIVATE_KEY` and `WIREGUARD_ADDRESSES` lines from `secrets/.env`.
2. Revoke the old key in the Mullvad account panel (WireGuard devices) to free the slot.
3. Restart — a new keypair is generated and registered.

```bash
sed -i '/^WIREGUARD_PRIVATE_KEY=/d;/^WIREGUARD_ADDRESSES=/d' secrets/.env
```

---

## Kill-switch & fail-closed behavior

- **Kill-switch (gluetun `FIREWALL=on`, the default).** slskd shares gluetun's network
  namespace; when the tunnel is down its traffic is **dropped**, never sent in the clear. During
  startup slskd waits for gluetun to report healthy (`depends_on: service_healthy`), so there is
  no leak window before the tunnel is up.
- **Fail-closed provisioning.** If key generation or registration fails, run.sh does **not** write
  the address, does **not** start gluetun, and does **not** start slskd on the direct `gsr`
  network. Acquisition simply **pauses** (slskd stays down) and an `ERROR:` line is printed. It
  never falls back to a direct, un-tunneled connection.
- **Compose-merge preflight.** The topology switch uses Compose `!reset` on slskd's
  `networks`/`ports` (Docker Compose **≥ 2.24.4**). Before bringing the stack up, run.sh runs
  `docker compose -f docker-compose.yml -f docker-compose.vpn.yml --profile slskd --profile
  slskd-vpn config` and aborts with an `ERROR:` prerequisite message if the merge fails. The
  clean merge is the authoritative, version-independent gate.
- **Known limitation.** Restarting the gluetun container orphans slskd (it keeps a handle to the
  now-dead namespace); restart slskd too to restore egress. This is fail-closed (loss of egress,
  never a leak); automated recovery is out of scope here.

---

## Port-forwarding caveat (incoming Soulseek peers)

Mullvad **removed port forwarding in 2023**. Outbound Soulseek search and downloads still work
behind Mullvad, but **incoming** peer connectivity is reduced (no forwarded listen port).

The provider is config-driven, so a port-forwarding provider can be swapped in without changing
the topology. For a provider that supports it (e.g. **AirVPN** or **ProtonVPN**):

1. Set `VPN_SERVICE_PROVIDER` to that provider and supply its WireGuard credentials.
2. Enable gluetun port forwarding: `VPN_PORT_FORWARDING=on` and
   `VPN_PORT_FORWARDING_PROVIDER=<provider>`.
3. Point slskd's listen port at the forwarded port.

No port-forwarding code is built for Mullvad (it offers none); the above is the documented path
for a capable provider.

---

## Verifying the tunnel

On a VPN-enabled launch, run.sh runs a **non-fatal** post-up verify (`check_slskd_vpn()`):

- Reads the egress IP from **inside gluetun's namespace** with
  `docker exec gsr-gluetun wget -qO- https://ipinfo.io/ip` (slskd shares that namespace) and
  compares it to the host's own public IP fetched with `curl` on the host.
  - **Different** ⇒ `PASS` (slskd egresses via the VPN). The Mullvad exit IP is logged; the
    host's own public IP is **never** logged.
  - **Equal** ⇒ `WARN: LEAK` (slskd traffic is NOT using the tunnel).
  - **Blocked / timed out** ⇒ a soft note, not a leak alarm — a blocked probe means the
    kill-switch held. If `docker`, `wget`, or `curl` is unavailable, the check skips with a note
    and never aborts startup.
- Also asserts gluetun reports **healthy** and that slskd answers through gluetun at `:5030`.

Re-run the deep tier at any time:

```bash
bash scripts/run.sh --check
```

The final banner notes when slskd is routed via Mullvad (provider + chosen exit), with no
secrets.

---

## How it maps to compose

- `deploy/docker-compose.yml` — brain's `SLSKD_URL: ${SLSKD_URL:-http://slskd:5030}` is the only
  base-file change; run.sh exports `SLSKD_URL=http://gluetun:5030` (per-invocation, never
  persisted) when the VPN is on, and `unset`s it otherwise.
- `deploy/docker-compose.vpn.yml` — the override applied only in VPN mode: the `gluetun` service
  (profile `slskd-vpn`, on `gsr`, publishing `5030` but **not** gluetun's control port `8000` to
  avoid colliding with icecast) and the slskd patch (`network_mode: "service:gluetun"` with
  `!reset` clearing its `networks`/`ports`). Both profiles (`slskd` + `slskd-vpn`) are always
  activated together.

---

## Tests

`scripts/test-run.sh` covers the VPN paths network-free (openssl keygen + pubkey derivation, the
`--data-urlencode`/stdin registration shape, register-once idempotency, resume-after-partial,
fail-closed, secret hygiene, the `VPN_SERVER_*`→`SERVER_*` remap, default-OFF parity, and a real
`docker compose config` merge of the `!reset` topology). The **live tunnel** (real WireGuard
handshake + egress leak check) needs a running Docker daemon and a funded Mullvad account and is
an operator manual test via `bash scripts/run.sh --check`.

```bash
GSR_DRY_RUN=1 bash scripts/test-run.sh
```
