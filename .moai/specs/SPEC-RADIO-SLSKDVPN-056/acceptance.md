# SPEC-RADIO-SLSKDVPN-056 — Acceptance Criteria

1:1 with `spec.md` requirements. Section A is the per-requirement acceptance summary (one entry
per REQ, concrete and testable). Section B gives Given-When-Then scenarios for the load-bearing
requirements. Section C is the Definition of Done and quality gates.

Parity: 36 REQ (VW×5, VK×8, VP×12, VV×5, VG×3, VS×3) + 7 NFR. Each REQ maps to one AC below.

---

## Section A — Per-Requirement Acceptance

### Group VW — Opt-In Wizard & Config Flags

- **AC-VW-001:** With `SLSKD_VPN_ENABLED` unset or `0`, `docker compose config` shows no
  `gluetun` service and slskd on `gsr` with `ports: 5030`; the brain env resolves
  `SLSKD_URL=http://slskd:5030`. (Ties NFR-V-1.)
- **AC-VW-002:** On first run with slskd enabled, the wizard prints a VPN prompt whose default
  (empty answer) is No; a non-interactive run leaves VPN OFF.
- **AC-VW-003:** The account-number prompt uses `read -rs` (no on-screen echo); the stored
  `MULLVAD_ACCOUNT` has no leading/trailing whitespace or CR; a dry-run log never contains the
  entered number.
- **AC-VW-004:** Entering a country/city stores `VPN_SERVER_COUNTRIES`/`VPN_SERVER_CITIES` AND
  `docker compose config` shows the chosen value reaching gluetun's `SERVER_COUNTRIES`/
  `SERVER_CITIES` env (per AC-VP-010, MF-4); leaving them blank stores empty values and gluetun's
  config shows no server pin (auto-select).
- **AC-VW-005:** After the wizard, `secrets/.env` contains `SLSKD_VPN_ENABLED`,
  `VPN_SERVICE_PROVIDER`, `VPN_SERVER_COUNTRIES`, `VPN_SERVER_CITIES`, `MULLVAD_ACCOUNT`;
  `secrets/brain.env` contains none of them.

### Group VK — WireGuard Key Lifecycle

- **AC-VK-001:** Given both `WIREGUARD_PRIVATE_KEY` and `WIREGUARD_ADDRESSES` exist, a second
  run makes no call to `api.mullvad.net` (verified by asserting no registration network call /
  no change to the stored key).
- **AC-VK-002:** The generated key is a valid 32-byte base64 X25519 private key produced by
  `openssl` (no `wireguard-tools` required), and the registered public key is derived from it via
  openssl `pkey -pubout`. Correctness is proven END-TO-END, not by a `wg pubkey` equality check:
  with a correct key gluetun reaches `healthy` (handshake) and the egress-IP check shows a Mullvad
  exit; a corrupted key leaves gluetun unhealthy and fail-closed keeps slskd down.
- **AC-VK-003:** After keygen, `WIREGUARD_PRIVATE_KEY` is written to `secrets/.env` before the
  registration call is issued (verified by injecting a registration failure and confirming the
  private key persisted).
- **AC-VK-004:** The registration is a POST to `https://api.mullvad.net/wg` with the account on
  stdin (`--data @-`, so it is absent from `ps`/argv) and the pubkey passed via
  `curl --data-urlencode "pubkey=..."`. A test asserts the curl invocation uses `--data-urlencode`
  for the pubkey (NOT a hand-built `printf 'account=%s&pubkey=%s'`), so `+`/`/` in the base64 key
  are preserved and Mullvad registers the correct key.
- **AC-VK-005:** A response of `10.x.x.x/32` is stored as `WIREGUARD_ADDRESSES`; a response that
  does not match `^[0-9a-f:/.,]+$` (e.g. an HTML error page) is rejected.
- **AC-VK-006:** Given a simulated API failure (unreachable host or non-address body), no
  `WIREGUARD_ADDRESSES` is written, gluetun is not started, slskd does NOT start on the direct
  `gsr` network (fail-closed), and a line prefixed `ERROR:` naming the failure + "acquisition
  paused" is printed.
- **AC-VK-007:** Given `WIREGUARD_PRIVATE_KEY` present but `WIREGUARD_ADDRESSES` absent, the
  next run re-derives the public key from the stored private key and re-registers; the returned
  address matches the earlier registration (idempotent, no new device slot).
- **AC-VK-008:** The banner/docs describe force-regen (remove `WIREGUARD_*` lines) and warn
  about the ~5-key device cap and revoking the old key in the account panel.

### Group VP — Compose Topology

- **AC-VP-001:** With VPN on, `docker compose config` shows a `gluetun` service with
  `cap_add: [NET_ADMIN]`, `/dev/net/tun`, env from `secrets/.env`, and membership in the `gsr`
  network (load-bearing — `gsr` is what makes `brain → gluetun:5030` reach slskd).
- **AC-VP-002:** With VPN on, the merged `slskd` service has `network_mode: service:gluetun`
  and NO `ports` and NO `networks` keys.
- **AC-VP-003:** With VPN on, host port `5030` is published on the gluetun container and
  `http://localhost:5030` reaches the slskd UI; gluetun's control port `8000` is NOT published
  (no collision with icecast's `8000:8000` — asserted in `docker compose config`).
- **AC-VP-004:** With VPN on, the brain env resolves `SLSKD_URL=http://gluetun:5030`; with VPN
  off, `http://slskd:5030`. `BRAIN_HTTP_HOST` and the brain's own listen bind are unchanged in
  both states (asserted by diffing the brain env).
- **AC-VP-005:** gluetun config shows `FIREWALL` on, gluetun-managed DNS, and IPv6 disabled.
- **AC-VP-006:** In both VPN states, `SLSKD_API_KEY` is passed to the brain unchanged and the
  brain's slskd REST calls carry the `X-API-Key` header.
- **AC-VP-007:** The gluetun service and the slskd network_mode patch appear only under the
  `slskd-vpn` profile / VPN override; a plain `docker compose up` (no VPN) does not start them.
- **AC-VP-008:** During startup before the tunnel is up, a probe from gluetun's netns to an
  external host fails (kill-switch blocks it); slskd gains egress only after the tunnel is
  established.
- **AC-VP-009:** With VPN on, run.sh runs `docker compose -f docker-compose.yml -f
  docker-compose.vpn.yml --profile slskd --profile slskd-vpn config` as a preflight; given a
  Compose that cannot perform the `!reset` merge, the preflight exits non-zero and run.sh aborts
  with an `ERROR:` line naming the ≥ 2.24.4 prerequisite (the merge result, not the version
  string, is the gate).
- **AC-VP-010:** Setting `VPN_SERVER_COUNTRIES=se` yields `SERVER_COUNTRIES: se` on the gluetun
  service in `docker compose config`; gluetun is never handed a bare `VPN_SERVER_*` name.
- **AC-VP-011:** `SLSKD_URL` is never written to `secrets/.env`; with `SLSKD_VPN_ENABLED` unset,
  run.sh `unset`s `SLSKD_URL` before `up`, so even a pre-exported `SLSKD_URL=http://gluetun:5030`
  does not reach the brain (brain resolves `http://slskd:5030`).
- **AC-VP-012:** With VPN on, the single compose invocation carries BOTH `--profile slskd` and
  `--profile slskd-vpn`; a test asserts neither profile is ever activated alone in the VPN path.

### Group VV — Post-Up Verify

- **AC-VV-001:** With VPN on, run.sh reads the egress IP via `docker exec gsr-gluetun wget -qO-
  <ip-echo-url>` (gluetun's netns, NOT its control server) and compares it to the host's public
  IP.
- **AC-VV-002:** If the reported egress IP equals the host's public IP, run.sh emits a line
  prefixed `WARN: LEAK`; if they differ, it logs a `PASS` line. (Binary, greppable verdicts.)
- **AC-VV-003:** The verify asserts gluetun health == healthy and that `:5030` answers through
  gluetun.
- **AC-VV-004:** The verify never exits non-zero on failure (WARN only); the VPN exit IP is
  logged; the host's real public IP is NEVER written to the log or terminal (a grep of the log +
  captured stdout for the host IP returns zero hits).
- **AC-VV-005:** Given the egress probe is blocked/times out (tunnel still negotiating), run.sh
  prints a soft note and does NOT emit `WARN: LEAK`; given `curl` or `docker` unavailable, it
  prints a skip note and startup exits 0.

### Group VG — Provider-Configurability

- **AC-VG-001:** With `VPN_SERVICE_PROVIDER` unset, gluetun receives `mullvad`; setting it to
  another gluetun-supported provider passes that value through with no topology change.
- **AC-VG-002:** `WIREGUARD_PRIVATE_KEY`/`WIREGUARD_ADDRESSES` are consumed by gluetun
  regardless of provider (no Mullvad-specific coupling in the compose/gluetun env).
- **AC-VG-003:** The shipped docs give a concrete port-forwarding recipe (set
  `VPN_SERVICE_PROVIDER` to AirVPN/ProtonVPN + `VPN_PORT_FORWARDING=on` +
  `VPN_PORT_FORWARDING_PROVIDER` in gluetun, point slskd's listen port at the forwarded port) and
  state Mullvad has none (reduced incoming peers); no port-forward code is shipped.

### Group VS — Secrets Discipline

- **AC-VS-001:** `MULLVAD_ACCOUNT` and `WIREGUARD_PRIVATE_KEY` are captured via silent input,
  trimmed, and `secrets/.env` is `chmod 600`.
- **AC-VS-002:** No VPN secret appears in any log line or in process argv; the account reaches
  curl on stdin (`--data @-`) per AC-VK-004, so it is absent from `ps`.
- **AC-VS-003:** No VPN secret is written to `secrets/brain.env`.

### NFR Acceptance

- **AC-NFR-V-1:** A diff of `docker compose config` and the brain container env with VPN off,
  before vs after this SPEC, shows no behavioral difference (the only source change,
  `SLSKD_URL` interpolation, resolves to the same value).
- **AC-NFR-V-2:** `docker compose -f docker-compose.yml -f docker-compose.vpn.yml --profile
  slskd --profile slskd-vpn config` exits 0 and yields a valid slskd `network_mode` merge; this
  merge result is the authoritative gate (version-independent), with Compose ≥ 2.24.4 documented
  as the prerequisite the REQ-VP-009 preflight enforces.
- **AC-NFR-V-3:** With VPN enabled but provisioning forced to fail, the stack comes up with
  slskd DOWN (never on the direct `gsr` network) and an `ERROR:` line stating acquisition is
  paused.
- **AC-NFR-V-4:** Ten consecutive run.sh invocations result in exactly one Mullvad key
  registration (asserted by call count / unchanged stored key).
- **AC-NFR-V-5:** On a host without `wireguard-tools` but with `openssl`, keygen succeeds via the
  default openssl X25519 path (wireguard-tools is never required).
- **AC-NFR-V-6:** With `curl` or `docker` unavailable, the verify prints a skip note and
  startup still succeeds (exit 0).
- **AC-NFR-V-7:** `GSR_DRY_RUN=1 bash scripts/run.sh` (with fixture VPN secrets) shows zero
  occurrences of the account number or private key in combined stdout+stderr, AND an explicit
  `grep` of `$GSR_LOG` (the tee'd logfile) for the fixture account number and private key returns
  zero hits, AND no VPN secret appears on argv (`ps` snapshot during the registration call).

---

## Section B — Given-When-Then (load-bearing)

### B-1 — Default-off is byte-identical (REQ-VW-001, NFR-V-1)

- GIVEN a fresh clone with `SLSKD_VPN_ENABLED` unset,
- WHEN `run.sh` brings the stack up,
- THEN no `gluetun` service exists, slskd runs on `gsr` publishing `5030`, and the brain's
  `SLSKD_URL` resolves to `http://slskd:5030`;
- AND the running brain container environment is identical to the pre-056 stack.

### B-2 — The SLSKD_URL / topology switch (REQ-VP-002, REQ-VP-004, REQ-VP-011, REQ-VP-012)

- GIVEN `SLSKD_VPN_ENABLED=1` with a valid stored WireGuard key,
- WHEN `run.sh` brings the stack up with BOTH `--profile slskd` and `--profile slskd-vpn` (in one
  invocation) plus `-f docker-compose.vpn.yml`,
- THEN the merged `slskd` service has `network_mode: service:gluetun` and no `ports`/`networks`;
- AND gluetun publishes `5030` and joins `gsr`;
- AND run.sh exports `SLSKD_URL=http://gluetun:5030` (per-invocation, never persisted) so the
  brain reaches slskd through gluetun; with the VPN off it `unset`s `SLSKD_URL` so the brain
  falls back to `http://slskd:5030`;
- AND the brain's slskd calls still carry the unchanged `X-API-Key` (SLSKD_API_KEY);
- AND `BRAIN_HTTP_HOST` / the brain's own bind are untouched.

### B-3 — Register once, reuse forever (REQ-VK-001, REQ-VK-007, NFR-V-4)

- GIVEN a first VPN-enabled run with no stored key,
- WHEN provisioning runs,
- THEN it generates a keypair, stores the private key, registers the public key once, stores
  the returned address;
- AND every subsequent run short-circuits on the presence of both stored values, making no
  further registration call;
- AND if the first run stored the private key but registration failed, the next run re-registers
  the SAME public key and receives the SAME address (no new device slot consumed).

### B-4 — Kill-switch, no leak (REQ-VP-008, REQ-VV-001, REQ-VV-002, REQ-VV-005)

- GIVEN the VPN stack is up,
- WHEN run.sh runs `docker exec gsr-gluetun wget -qO- <ip-echo-url>` inside gluetun's netns
  (which slskd shares),
- THEN the returned egress IP is a Mullvad exit IP and is NOT the host's own public IP, and
  run.sh logs a `PASS`;
- AND if the tunnel is down, gluetun's kill-switch blocks that egress entirely (the probe times
  out) rather than leaking via the host IP — run.sh prints a SOFT note (blocked = safe), NOT a
  leak alarm;
- AND if the observed egress IP ever equals the host's public IP, run.sh emits `WARN: LEAK`.

### B-5 — Fail-closed on provisioning failure (REQ-VK-006, NFR-V-3)

- GIVEN `SLSKD_VPN_ENABLED=1`,
- WHEN key registration fails (Mullvad API unreachable, bad account number, or a non-address
  response),
- THEN `WIREGUARD_ADDRESSES` is not written and gluetun is not started;
- AND slskd stays DOWN for this launch (it is NOT started on the direct `gsr` network);
- AND the rest of the stack comes up normally with an `ERROR:` line stating acquisition is paused.

### B-6 — Account/key secret hygiene (REQ-VS-002, REQ-VK-004, NFR-V-7)

- GIVEN the operator enters the account number and a key is generated,
- WHEN the registration POST is made,
- THEN the account number is sent via stdin (`--data @-`) and never appears in `ps`/argv, and the
  pubkey is url-encoded by `curl --data-urlencode` (not hand-built);
- AND an explicit `grep` of `$GSR_LOG` and of a dry-run's stdout+stderr for the account number
  and the private key returns zero hits.

### B-7 — Correct key registration + end-to-end proof (REQ-VK-002, REQ-VK-004, REQ-VV-003)

- GIVEN a freshly generated openssl X25519 keypair whose base64 pubkey contains `+` and/or `/`,
- WHEN run.sh registers it with `curl --data-urlencode "pubkey=..."`,
- THEN Mullvad receives the exact key (no `+`→space corruption) and returns the assigned CIDR;
- AND once gluetun starts, a correct key produces a WireGuard handshake so gluetun reaches
  `healthy` and the egress-IP check shows a Mullvad exit — this end-to-end result is the
  authoritative correctness proof (no `wg pubkey` self-check);
- AND a corrupted key would leave gluetun unhealthy, and fail-closed keeps slskd down.

---

## Section C — Definition of Done & Quality Gates

- [ ] All 36 REQ and 7 NFR have a passing AC.
- [ ] VPN-off parity proven (AC-NFR-V-1) — regression guard is green before any VPN code path
      is exercised.
- [ ] `docker compose ... config` merge preflight green + aborts on failure (AC-NFR-V-2,
      AC-VP-009); Compose ≥ 2.24.4 documented; merge result is the authoritative gate.
- [ ] Key-lifecycle idempotency proven across ≥10 runs with exactly one registration
      (AC-NFR-V-4); resume-after-partial path tested (AC-VK-007).
- [ ] Pubkey registered with `curl --data-urlencode` (AC-VK-004) and end-to-end correctness
      proven via gluetun-healthy + Mullvad-egress (AC-VK-002) — closes the silent-auth pubkey-
      encoding trap; no `wg pubkey` self-check.
- [ ] Egress-IP leak check demonstrably distinguishes tunneled vs host IP (AC-VV-002) and is
      non-fatal (AC-VV-004, AC-NFR-V-6).
- [ ] Fail-closed behavior verified (AC-NFR-V-3): provisioning failure ⇒ slskd down, never
      direct.
- [ ] `SLSKD_URL` never persisted; `unset` when VPN off (AC-VP-011); `VPN_SERVER_*`→`SERVER_*`
      remap reaches gluetun (AC-VP-010, AC-VW-004); paired profiles enforced (AC-VP-012).
- [ ] Secret-hygiene scan green (AC-NFR-V-7); VPN secrets confined to `secrets/.env`
      (AC-VS-003).
- [ ] Provider-swap path confirmed non-breaking (AC-VG-001/002); port-forwarding caveat
      documented (AC-VG-003).
- [ ] Docs updated (toggle, force-regen, port-forwarding caveat, provider swap) in the Sync
      phase.
- [ ] TRUST 5 gates pass on the touched shell/compose (shellcheck clean where run.sh changes;
      `docker compose config` valid in both VPN states).
