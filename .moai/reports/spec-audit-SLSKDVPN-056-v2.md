# SPEC Re-Audit Report: SPEC-RADIO-SLSKDVPN-056 v0.2.0

Re-audit of: v0.1.0 (prior verdict FAIL @ 0.83)
Auditor stance: adversarial, fresh eyes. Reasoning context ignored per M1 Context Isolation — only the binding `spec.md` + `acceptance.md` (with `plan.md` for cross-reference) were graded.

**Verdict: PASS**
**Content-quality score: 0.95 / 1.0** (up from 0.83)

---

## Closure Table — 4 Must-Fixes + Critical Pubkey Trap

| Item | Status | Evidence (binding spec.md / acceptance.md) |
|------|--------|--------------------------------------------|
| **MF-1** fail-open → fail-closed | **CLOSED** | REQ-VK-006 (spec L157-161): "If the registration call fails ... then the system shall not ... start slskd on the direct `gsr` network (fail-closed)". AC-VK-006 (accept L51-54) makes it a binary check (no addr written, gluetun not started, slskd NOT on direct gsr, `ERROR:` printed). Reinforced by NFR-V-3 (L275-276). No REQ contradicts: only REQ-VW-001 (L115) runs slskd direct, and that is gated on VPN *disabled*, a disjoint state. |
| **MF-2** version guard | **CLOSED** | REQ-VP-009 (spec L201-206): `docker compose ... config` preflight that aborts non-zero with `ERROR:` naming "Docker Compose ≥ 2.24.4". NFR-V-2 (L270-274) floor reads **≥ 2.24.4** and names the config-merge preflight as the authoritative gate. Grep confirms **zero** stale `2.24.0` occurrences anywhere. AC-VP-009 + AC-NFR-V-2 present. |
| **MF-3** leak-check contract | **CLOSED** | REQ-VV-005 (spec L235-238): "If the in-namespace egress probe is blocked or times out, then the check shall treat it as a soft note (blocked probe means the kill-switch held — no leak) and shall not raise a leak alarm"; curl/docker absent ⇒ skip note, no abort. Binding + AC-VV-005 (accept L107-109) + NFR-V-6. |
| **MF-4** VPN_SERVER_* remap | **CLOSED** | REQ-VP-010 (spec L207-210): pins `VPN_SERVER_COUNTRIES → SERVER_COUNTRIES`, `VPN_SERVER_CITIES → SERVER_CITIES` in the compose `environment:` block; "gluetun shall not be expected to read the `VPN_SERVER_*` names directly." AC-VW-004 (accept L23-26) asserts a **CHOSEN** value reaches gluetun's `SERVER_*` (not blank/auto): "docker compose config shows the chosen value reaching gluetun's SERVER_COUNTRIES/SERVER_CITIES"; AC-VP-010 (L87-88) gives the concrete `VPN_SERVER_COUNTRIES=se ⇒ SERVER_COUNTRIES: se` assertion. |
| **CRITICAL pubkey encoding** | **CLOSED** | REQ-VK-004 (spec L148-153): MANDATES account on stdin (`--data @-`) + pubkey via `curl --data-urlencode "pubkey=<key>"`; explicitly forbids the hand-built `printf 'account=%s&pubkey=%s'` form. AC-VK-004 (accept L44-48) asserts the curl invocation uses `--data-urlencode` (not the printf form). Scenario **B-7** (accept L219-227) proves a `+`/`/`-containing key registers and verifies end-to-end (Mullvad receives the exact key ⇒ gluetun `healthy` handshake ⇒ Mullvad egress). No stale `/wg/` trailing slash remains (grep clean). |

---

## Expert-devops Corrections — landed as testable REQ/AC?

| Correction | Status | Evidence |
|-----------|--------|----------|
| wg-guard dropped / openssl default | CLOSED | REQ-VK-002 (L136-144): openssl `pkey -pubout` same-tool derivation; correctness proof is end-to-end (handshake + Mullvad egress), explicitly NOT a `wg pubkey` equality check. NFR-V-5 (L279-281): openssl X25519 default, "shall not require `wireguard-tools`". `wg pubkey` appears only in negated/dropped context (grep verified). |
| SLSKD_URL parity | CLOSED | REQ-VP-011 (L211-214) + AC-VP-011 (L89-91): never persist `SLSKD_URL`; `unset` unless `SLSKD_VPN_ENABLED=1`. |
| paired profiles | CLOSED | REQ-VP-012 (L215-218) + AC-VP-012 (L92-93): `--profile slskd --profile slskd-vpn` together; neither activated alone. |
| gluetun on `gsr` load-bearing | CLOSED | REQ-VP-001 (L174-178): "gluetun shall be a member of the `gsr` network — this is load-bearing ... shall not be moved off `gsr`." AC-VP-001. |
| no `:8000` publish (icecast collision) | CLOSED | REQ-VP-003 (L182-185) + AC-VP-003 (L68-70). |
| egress via `docker exec gsr-gluetun wget` | CLOSED | REQ-VV-001 (L222-225): "via `docker exec gsr-gluetun wget -qO- <ip-echo-url>` (NOT gluetun's control server ...)". AC-VV-001. |
| gluetun-restart orphans slskd | CLOSED | Section 9 (L312-316): documented as fail-closed, healer deferred to SELFHEAL-030. |

---

## P1–P6 polish

| Item | Status | Evidence |
|------|--------|----------|
| P1 EARS label on REQ-VS-002 | CLOSED (see minor note D2) | REQ-VS-002 now labeled `(Unwanted Behavior)` (L260). |
| P2 REQ-VG-003 concrete | CLOSED | L248-253: concrete port-forward doc deliverable (AirVPN/ProtonVPN + `VPN_PORT_FORWARDING=on` + `VPN_PORT_FORWARDING_PROVIDER`). AC-VG-003. |
| P3 BRAIN_HTTP_HOST untouched in binding spec | CLOSED | REQ-VP-004 (L186-190): "shall not modify `BRAIN_HTTP_HOST` or the brain's own listen bind." AC-VP-004 diffs the brain env. |
| P4 subjective → binary (ERROR/WARN/PASS) | CLOSED | REQ-VV-002 (L226-228) emits `WARN: LEAK` / `PASS`; REQ-VK-006 / REQ-VP-009 emit `ERROR:`. AC-VV-002 "(Binary, greppable verdicts.)" |
| P5 explicit `$GSR_LOG` secret-scan AC | CLOSED | AC-NFR-V-7 (accept L148-151): "an explicit `grep` of `$GSR_LOG` (the tee'd logfile) for the fixture account number and private key returns zero hits." |
| P6 host real-IP never logged | CLOSED | REQ-VV-004 (L231-234) + AC-VV-004 (L104-106): host public IP "NEVER written to the log or terminal (a grep ... returns zero hits)". |

---

## Regression / New-Hole Hunt (5 added REQs + changed REQs)

Grep-verified structural integrity:
- **1:1 REQ↔AC**: 36 bold REQ definitions (VW×5, VK×8, VP×12, VV×5, VG×3, VS×3) ↔ 36 bold AC definitions, each appearing **exactly once**. 7 NFR ↔ 7 AC-NFR. **No orphan REQ, no orphan AC, no duplicate ID, no gap.** VP runs 001–012, VV runs 001–005 — contiguous.
- **EARS labels**: all 36 REQs carry an EARS pattern label; all NEW/changed REQs check out — VP-009 (Event-Driven, well-formed "When…shall"), VP-010 (Ubiquitous), VP-012 (State-Driven "While…shall"), VV-005/VK-006/VP-008/VV-002 (Unwanted "If…then…shall", canonical), VK-002/VK-004 (Event-Driven), VG-003 (Ubiquitous).
- **Internal consistency** (checked pairwise, no contradictions):
  - VP-010 remap vs VW-004/005 storage: wizard stores `VPN_SERVER_*`, compose maps to `SERVER_*` — complementary, consistent.
  - VK-006 fail-closed vs VP-012 paired-profile: no path starts slskd without a healthy gluetun; on provisioning failure neither profile is activated for slskd, and `service:gluetun` + `depends_on healthy` blocks slskd from starting bare. Consistent.
  - VV-001 egress-check vs VV-005 soft-note: probe → VV-002 interprets equal=`WARN: LEAK` / differ=`PASS`; blocked/timeout → VV-005 soft note. No overlap conflict.
  - VP-004 (enabled ⇒ `gluetun:5030`) vs VP-011 (never persist, unset when off): the `${SLSKD_URL:-http://slskd:5030}` default is protected in both directions. Consistent.
- **Frontmatter**: `version: 0.2.0` (correct), HISTORY has both 0.1.0 and 0.2.0 rows, project SPEC schema (`id/version/status/created/updated/author/priority/issue_number/depends_on`) intact — matches sibling SPEC-RADIO-* convention.

No new must-fix defects and no regressions were introduced by the revision.

---

## Defects Found (all minor — none blocking)

- **D1** — spec.md L232-238 / L222-225: `REQ-VV-001` names `docker exec … wget` for the in-namespace probe while `REQ-VV-005`/`NFR-V-6` degrade on "`curl` or `docker`" being unavailable. These are two different fetches (in-ns wget for the VPN exit IP; host-side curl for the host public IP) and are individually correct, but the tool-naming split is not spelled out in the binding REQ text and could confuse an implementer. Severity: minor. Suggested (non-blocking): one clause in REQ-VV-001/VV-005 noting the host-IP fetch uses curl and the in-ns fetch uses the container's wget.
- **D2** — spec.md L211-214 (`REQ-VP-011`) and L260-262 (`REQ-VS-002`) are labeled `(Unwanted Behavior)` but are written as unconditional `shall not` prohibitions rather than the canonical EARS unwanted form `If [undesired condition], then the [system] shall …`. Prohibition-style unwanted requirements are widely accepted, so this is a labeling nicety, not a correctness defect. Severity: minor. (P1 asked only for a *label* on VS-002, which is present.)
- **D3 (informational, pre-existing, not a v0.2.0 regression)** — Frontmatter uses `created`/`updated` and omits generic-MoAI `created_at`/`labels`. This matches the repo's established SPEC-RADIO-* schema and was accepted in v0.1.0; flagged only for cross-template awareness. Not counted against the score.

---

## Chain-of-Verification Pass

Second-look, re-reading the sections I moved through quickly on the first pass:
- **Every REQ read**, not skimmed: re-confirmed VK-002 (openssl same-tool derivation + end-to-end proof), VK-004 (stdin account + `--data-urlencode` + printf-ban), VK-006 (fail-closed triple `shall not`), VK-007 (resume re-derives pubkey — testable, idempotent), VP-009/010/011/012, VV-005.
- **REQ sequencing end-to-end** (not spot-checked): grep uniq-count proves contiguous VW1-5/VK1-8/VP1-12/VV1-5/VG1-3/VS1-3, zero dup/gap.
- **Traceability for every REQ** (not sampled): 36↔36 bold-definition parity via grep; NFR 7↔7.
- **Exclusions specificity**: Section 8 has 7 concrete entries (brain/icecast tunneling; GUI; Mullvad port-forward; OpenVPN; auto-revoke; multi-hop/SOCKS/per-persona; separate healer) — each names a specific excluded behavior, no vague filler.
- **Cross-requirement contradictions**: pairwise-checked the four highest-risk interactions (listed above) — none found.
- New finding surfaced on second pass: D1 (wget/curl tool-naming split) — added above as minor.

---

## Recommendation

**PASS.** All four plan-auditor must-fixes and the critical pubkey-encoding trap are genuinely closed in the *binding* `spec.md` + `acceptance.md` (not merely in `plan.md`), each with a testable REQ and a matching binary AC. All six expert-devops corrections and all P1–P6 polish items landed as testable requirements. Traceability is strictly 1:1 across 36 REQ + 7 NFR with no gaps, duplicates, or orphans, and the five newly added requirements introduce no contradictions or regressions. The remaining defects (D1, D2) are minor wording/labeling refinements that do not affect implementability and are safe to fold into the Run phase; D3 is a pre-existing convention note. Score 0.95.
