# SPEC Audit Report: SPEC-RADIO-SLSKDVPN-056

Auditor: plan-auditor (adversarial, independent)
Date: 2026-07-01
Scope: spec.md + plan.md + acceptance.md, cross-checked against live repo (deploy/docker-compose.yml, scripts/run.sh)

Reasoning context handling: The six "load-bearing concerns" supplied by the caller were treated as audit *targets to verify independently*, not as author reasoning to accept. Each was checked against the actual files and repo ground truth.

---

## Verdict: FAIL

- **Content-quality score: 0.83 / 1.0** (high-quality SPEC; clean EARS, 1:1 mapping, verified research, strong secrets discipline — but four genuine contract defects, one functional).
- **Must-fix defects: 4**
- **Minor polish: 6**
- FAIL rationale: One latent *functional* bug (server-pin var never reaches gluetun), plus three contract-completeness holes where load-bearing behavior lives only in `plan.md` prose (explicitly non-binding — `plan.md:4` states the EARS REQs and acceptance.md are the contract). A PASS would ship a country/city pin that silently does nothing and a verify with undefined behavior on the most common transient case.

## Must-Pass Firewall

- **MP-1 REQ numbering — PASS.** VW 001–005, VK 001–008, VP 001–008, VV 001–004, VG 001–003, VS 001–003, NFR-V 1–7. No gaps, no duplicates, consistent 3-digit padding. (spec.md:109–214, 218–234)
- **MP-2 EARS compliance — PASS.** All 31 REQ carry an EARS pattern label and structure. Two minor nits (see P1/P2) do not rise to failure.
- **MP-3 Frontmatter — PASS (against repo convention).** id/version/status/created/updated/author/priority/issue_number/depends_on all present and correctly typed (spec.md:1–13). Matches SETUP-040 convention exactly. No invented `labels` field; `version: 0.1.0`; `issue_number: TBD` — all as required. (The generic rubric's `created_at`/`labels` fields are superseded here by the caller-pinned repo convention, verified against `.moai/specs/SPEC-RADIO-SETUP-040/spec.md`.)
- **MP-4 Language neutrality — N/A.** Single-project infra SPEC (Docker/WSL2/shell), not multi-language tooling. Auto-pass.

No must-pass firewall failure. The FAIL is driven by the defect list below.

## Category Scores

| Dimension | Score | Band | Evidence |
|-----------|-------|------|----------|
| Clarity | 0.90 | 0.75–1.0 | Unambiguous topology switch (spec.md:48–55, plan.md:20–71); precise flags. Minor: REQ-VG-003 "shall not preclude" is aspirational. |
| Completeness | 0.75 | 0.75 | All sections + specific 7-entry Exclusions (spec.md:246–259). Sparse on Compose-preflight + verify-timeout behavior (MF-2, MF-3). |
| Testability | 0.80 | 0.75 | Most ACs binary. Weak spots: AC-VW-004 doesn't assert non-blank pin actually reaches gluetun (MF-4); verify-timeout undefined (MF-3). |
| Traceability | 1.00 | 1.0 | Exact 1:1: 31 REQ ↔ 31 Section-A ACs + 7 NFR ACs. No orphan ACs, no uncovered REQ. (acceptance.md:11–117) |

---

## Six Load-Bearing Correctness Concerns — PINNED / HOLE

**1. SLSKD_URL / topology switch — PINNED.**
Verified against repo: base compose line 81 is literally `SLSKD_URL: http://slskd:5030` and line 82 `SLSKD_API_KEY: ${SLSKD_API_KEY}` (matching plan.md:40–43). Default-off byte-identity is pinned by AC-NFR-V-1 (acceptance.md:101–103) via a `docker compose config` before/after diff — the resolved value is unchanged. `BRAIN_HTTP_HOST` appears nowhere in the compose (verified) and plan.md:45–47 explicitly forbids touching it; AC-NFR-V-1's full-config diff catches any regression indirectly. X-API-Key path intact: REQ-VP-006 + AC-VP-006 (spec.md:170–171, acceptance.md:63–64). Note: brain has NO `env_file: secrets/.env` (only brain.env) — the `${SLSKD_URL:-…}` interpolation resolves from run.sh's exported env at up-time, same mechanism as the existing `${SLSKD_API_KEY}`. Sound.

**2. Compose merge for `network_mode` — PINNED (merge + no-auto-start); HOLE (version preflight).**
Merge-cleanliness pinned by AC-NFR-V-2 (`docker compose … config` exits 0, yields `network_mode: service:gluetun` with no `networks`/`ports`) (acceptance.md:104–106). "Plain non-VPN up never starts gluetun" pinned by AC-VP-007 (acceptance.md:65–66). `!reset null` + ≥2.24.0 floor is accurate (Compose `!reset` landed v2.24.0). HOLE → **MF-2**: no REQ/AC requires run.sh to *detect* Compose <2.24.0 and abort with a clear prerequisite error; that behavior exists only in plan.md:178–180 risk prose. Low blast radius (an old Compose fails the `up` anyway), so minor — but currently unpinned.

**3. Key-registration idempotency + device limit — PINNED.**
≥10 runs → exactly one registration: AC-NFR-V-4 (acceptance.md:109–110). Store-private-key-before-register: REQ-VK-003 + AC-VK-003 (inject registration failure, confirm key persisted) (spec.md:132–134, acceptance.md:36–38). Resume-after-partial re-registers the SAME pubkey relying on endpoint idempotency: REQ-VK-007 + AC-VK-007 (acceptance.md:46–48). Crash analysis: keygen→store→register ordering means a crash before store loses only an *unregistered* key (harmless regenerate); a crash after store is caught by VK-007. Force-regen documented: REQ-VK-008 + AC-VK-008. No orphan path. Solid.

**4. Fail-closed (NFR-V-3) — PINNED at NFR/AC; HOLE (REQ-level consistency).**
The safety property IS contractually pinned: NFR-V-3 (spec.md:225–226) "never fall back to running slskd on the direct network; acquisition shall pause (slskd stays down)" + AC-NFR-V-3 (acceptance.md:107–108, forced provisioning failure ⇒ slskd DOWN, never direct). No startup leak window: REQ-VP-008 + AC-VP-008 (kill-switch blocks egress before tunnel) (spec.md:175–177, acceptance.md:67–69) — correct given gluetun FIREWALL=on brings firewall up before the tunnel. HOLE → **MF-1**: REQ-VK-006 (spec.md:141–143), the REQ that governs the failure branch, enumerates "shall not write WIREGUARD_ADDRESSES, shall not bring up gluetun, shall surface a clear error" but omits "shall not start slskd on the direct network." An implementer reading only REQ-VK-006 could stop gluetun yet still pass `--profile slskd` (plan.md:66 activates both profiles on VPN), starting slskd direct — the exact fail-open NFR-V-3 forbids. NFR-V-3 + AC-NFR-V-3 catch it, so not an uncovered hole, but the failure-branch REQ must be self-contained.

**5. Leak-check verify — PARTIAL; HOLE (timeout classification).**
Egress-from-netns vs host IP, non-fatal, privacy: REQ-VV-001/002/004 + AC-VV (spec.md:181–191, acceptance.md:73–80) — PINNED. Log shared exit IP, not operator real IP: REQ-VV-004 + AC-VV-004 — PINNED (testable as "full host-IP string absent"). Degrade without curl/docker: NFR-V-6 + AC-NFR-V-6 — PINNED. HOLE → **MF-3**: "a timed-out / unreadable in-namespace probe is a SOFT note (tunnel negotiating / kill-switch working), NOT a leak alarm" exists ONLY in plan.md:139–141. Grep of spec.md + acceptance.md for timeout/soft/negotiating/blocked = zero hits. REQ-VV-002 only fires the leak WARN on the *equal-IP* condition (so it won't false-alarm), but the timeout branch has NO positive requirement — AC-VV-001 assumes an IP is returned. Behavior on the most common transient case is undefined by the contract.

**6. Secrets discipline — PINNED.**
Account number + WG private key never on argv / never logged: REQ-VS-002 + AC-VS-002 + B-6 + NFR-V-7/AC-NFR-V-7 (spec.md:210–212, 233–234, acceptance.md:95–96, 115–117, 171–177). Registration body on stdin (`--data @-`, not `-d account=`): REQ-VK-004 + AC-VK-004 (acceptance.md:39–41). secrets/.env (never brain.env), chmod 600: REQ-VS-001/003 + AC-VS-001/003 + REQ-VW-005. Consistent with the existing ANTHROPIC_API_KEY isolation rule (verified in compose brain block comment). Solid.

---

## Must-Fix Defects

### MF-1 — Failure-branch REQ omits the fail-closed slskd guarantee (safety / consistency)
- **File / id:** spec.md REQ-VK-006 (spec.md:141–143).
- **What's wrong:** REQ-VK-006 lists gluetun-not-started but not slskd-stays-down. The single most safety-critical branch (provisioning failure) is not self-contained; only NFR-V-3 carries the "never on direct network" guarantee. Divergence between the governing REQ and the NFR invites a fail-open implementation (stop gluetun, still `--profile slskd` → slskd direct).
- **Fix:** Append to REQ-VK-006: "…and **shall not** start the slskd container on the direct `gsr` network (run.sh omits the `slskd` profile when the VPN is enabled but provisioning has failed)." Add an explicit AC (or extend AC-NFR-V-3) asserting no `gsr-slskd` and no `gsr-gluetun` container is running after a forced provisioning failure.

### MF-2 — No Compose-version preflight requirement (robustness / completeness)
- **File / id:** spec.md NFR-V-2 (spec.md:218–224); no AC.
- **What's wrong:** The ≥2.24.0 floor for `!reset` is only *documented* (NFR-V-2 + Assumptions). No REQ/AC requires run.sh to detect an older Compose and abort with a clear prerequisite error before attempting the VPN `up`. The behavior lives only in plan.md:178–180.
- **Fix:** Add REQ-VP-009 (Unwanted): "If the VPN is enabled and `docker compose` version < 2.24.0, then run.sh **shall** abort with a clear prerequisite error and **shall not** start gluetun or slskd." Add matching AC.

### MF-3 — Verify timeout/unreadable-egress behavior undefined in the contract (testability / completeness)
- **File / id:** spec.md REQ-VV-002 (spec.md:184–186); no AC covers the timeout branch.
- **What's wrong:** The "timeout is safe, emit a soft note, do NOT alarm as a leak" logic — load-bearing to avoid false leak alarms while the tunnel negotiates — exists only in plan.md:139–141. spec.md/acceptance.md contain zero mention of the timeout/blocked case. AC-VV-001 assumes an IP is always returned.
- **Fix:** Add a REQ (e.g. REQ-VV-005, Unwanted): "If the in-namespace egress probe times out or returns no readable IP, then the verify **shall** emit a soft note (tunnel negotiating / blocked by kill-switch) and **shall not** report a leak." Add AC asserting a timed-out probe produces a soft note distinct from the equal-IP leak WARN.

### MF-4 — Server-pin variables never reach gluetun (latent functional bug)
- **File / id:** spec.md REQ-VW-005 (spec.md:120–122) + AC-VW-004 (acceptance.md:23–24); plan.md:127.
- **What's wrong:** The wizard persists `VPN_SERVER_COUNTRIES` / `VPN_SERVER_CITIES`, but gluetun's actual env vars are `SERVER_COUNTRIES` / `SERVER_CITIES` (spec.md:68, plan.md:127). No REQ/plan/AC specifies the remap. If the override does `env_file: ../secrets/.env` passthrough, gluetun receives the `VPN_`-prefixed names, ignores them, and always auto-selects — so a chosen country/city silently does nothing. AC-VW-004 only checks the *blank* → auto-select case and never asserts that a non-blank value produces a `SERVER_COUNTRIES` pin in gluetun's config, so the test wouldn't catch it.
- **Fix:** Specify the remap in the override (`environment: SERVER_COUNTRIES: ${VPN_SERVER_COUNTRIES}`, `SERVER_CITIES: ${VPN_SERVER_CITIES}`) in plan.md §1.5, and strengthen AC-VW-004: "a non-blank `VPN_SERVER_COUNTRIES` yields `SERVER_COUNTRIES=<value>` in `docker compose config` for gluetun." Alternatively persist the flags under gluetun's exact names.

---

## Minor Polish (non-blocking)

- **P1** — REQ-VS-002 (spec.md:210) labeled "Unwanted Behavior" but is a ubiquitous prohibition (no IF-THEN trigger). Relabel Ubiquitous.
- **P2** — REQ-VG-003 (spec.md:201–203) "the design shall not preclude…" is aspirational; testability rests entirely on AC-VG-003 (docs + no code). Acceptable but note.
- **P3** — AC-VV-004 (acceptance.md:79–80) "not logged in full" is soft; define the pass condition as "the full host public-IP string does not appear in any log line."
- **P4** — "clear error" / "loud WARN" adjectives recur across ACs (e.g. AC-VK-006, AC-VV-002); the testable core (message emitted + exit code) is fine, but the adjectives themselves are subjective.
- **P5** — BRAIN_HTTP_HOST avoidance (the TLS-055 trap) lives only in plan.md:45–47. Consider an explicit Exclusion line in spec.md §8 so the contract, not just the plan, forbids it. (AC-NFR-V-1 config-diff catches it indirectly.)
- **P6** — AC-NFR-V-7 (acceptance.md:115–117) scans combined stdout+stderr; ensure the `$GSR_LOG` file itself is also grepped for secrets (AC-VS-002 "any log line" arguably covers this — make it explicit).

---

## Chain-of-Verification Pass

Second-look actions and findings:
- Re-read all 31 REQ + 7 NFR end-to-end; confirmed numbering has no gaps/dupes and every REQ has exactly one Section-A AC (traceability 1:1 holds).
- Cross-checked plan.md claims against the live repo: compose line 81/82, slskd `profiles/ports/networks`, absence of `BRAIN_HTTP_HOST`, and all named run.sh primitives (`_set_env_var`, `provision_slskd_web_creds`, `load_secrets`, `check_slskd_web`, `PROFILE_ARGS`, `resolve_slskd`, `GSR_HEALTH_TIMEOUT`, `GSR_LOG`, `GSR_DRY_RUN`, `SLSKD_PORT`, `SLSKD_CHOICE`) — all exist. Reuse claims are grounded.
- Grep-verified the three suspected contract holes (timeout-classification, compose-preflight, slskd-stays-down) are absent from spec.md/acceptance.md and present only in plan.md → confirmed MF-1/2/3 are genuine, not skim errors.
- New finding surfaced ONLY in the second pass: **MF-4** (VPN_SERVER_* vs gluetun SERVER_* variable-name mismatch) — the strongest defect, a latent functional bug that the existing AC-VW-004 would not catch. This is exactly the kind of cross-file naming drift the first pass under-weighted.
- Exclusions section re-checked for specificity: 7 concrete entries (spec.md:246–259), each names a real capability and why it's excluded — not vague. Good.
- Contradiction scan across the three files: config-flag names consistent EXCEPT the VPN_SERVER_*/SERVER_* handoff (MF-4). No other contradictions. Scope stays within the locked decisions (no creep).

## Recommendation (to manager-spec)

Address MF-1 through MF-4 before Run. Concrete order:
1. **MF-4 first** (functional): pin the `VPN_SERVER_* → SERVER_*` remap in plan.md §1.5 and strengthen AC-VW-004 to assert the pin reaches gluetun.
2. **MF-1**: extend REQ-VK-006 with the explicit slskd-stays-down clause + AC.
3. **MF-3**: add REQ-VV-005 + AC for the timeout/soft-note branch.
4. **MF-2**: add REQ-VP-009 + AC for the Compose ≥2.24.0 preflight abort.
5. Sweep P1–P6 while in the files.

The SPEC is otherwise unusually rigorous: EARS clean, traceability perfect, secrets discipline and idempotency fully pinned, research facts verified against primary sources. Re-audit after the four must-fixes lands it comfortably in PASS territory.

🗿 MoAI <email@mo.ai.kr>
