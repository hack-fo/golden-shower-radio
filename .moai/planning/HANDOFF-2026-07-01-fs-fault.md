# HANDOFF — 2026-07-01 — FILESYSTEM FAULT + session state

**Autonomous run STOPPED due to a disk/filesystem fault.** This note lives on the still-writable
main mount because `.claude/session-state.md` is now on a read-only submount and can't be updated.

## ⚠ FILESYSTEM FAULT (operator action required)

Two ext4 submounts inside the repo have **remounted READ-ONLY after I/O errors** (`errors=remount-ro`):

- `scripts/` → device `/dev/sdd`, now `ro` — **cannot write run.sh / test-run.sh**
- `.claude/` → separate submount, now `ro` — **cannot update session-state.md**
- Main mount (`.`, `brain/`, `deploy/`, `docs/`, `.git/`, `.moai/`) is still `rw` — but it ALSO has
  `errors=remount-ro`, so it could go read-only if the disk keeps erroring.

**This is a disk/hardware problem, not a code problem.** Investigate before further work:
`dmesg | tail -50` (look for I/O errors / EXT4-fs errors on sdd), `sudo fsck /dev/sdd`, then remount rw.
Autonomous building was halted because writing code onto an actively-erroring disk risks data loss.

## ✅ SAFE / SHIPPED (committed + pushed — no loss)

- **SLSKDVPN-056** (optional Mullvad VPN for slskd): SPEC `d3b4015` + impl `2bc2e5b`, **PUSHED** to
  `origin/feature/SPEC-RADIO-SLSKDVPN-056`. Verified correct (1435-line run.sh, provision_mullvad_wg,
  correct argv derive, no broken env variant). PR: https://github.com/hack-fo/golden-shower-radio/pull/new/feature/SPEC-RADIO-SLSKDVPN-056
  - Static-verified: bash -n; 137/137 tests; `docker compose config -q` merge exit 0; default-OFF byte-identical. Audited PASS 0.95.
  - Known follow-up (low sev, documented in-code): `_wg_derive_pub` passes WG private key on python argv (ps-visible during provisioning only; key also in chmod-600 secrets/.env). Harden via a `-c`+env form later (an env-var+heredoc swap broke derivation — needs its own test).
  - OPERATOR-ONLY live test (needs Docker daemon + funded Mullvad acct): real WG handshake, egress-IP leak check, kill-switch, brain-through-gluetun. Run `bash scripts/run.sh --check` after enabling.
- **SETUP-040 v0.3 `80b1a02` + v0.4 `4d631b9`** (splash→colour, slskd web auth, SU-10 probe) — in the
  SLSKDVPN branch history (pushed). Also on local branch `feature/SPEC-RADIO-SETUP-040-v0.3` (not pushed under that name).

## 🟡 DEFERRED (blocked by the FS fault)

- **LINEUP-050 wiring** (the intended "next sane plan"): brain/ IS writable, but deferred because
  (a) building on a faulting disk is unsafe, (b) session-state can't be maintained (.claude ro),
  (c) the LINEUP working tree is polluted (see below) and can't be cleaned while scripts/ is ro.
  Task unchanged: instantiate ShowRegistry/LineupController/WeeklyMatrixPlanner in brain/main.py behind
  cfg.lineup_enabled (config.py:703), feed world_model.show_registry, keep toggle-OFF byte-identical, do
  NOT edit frozen shows.py/lifecycle.py/schedule.py, then `python3 -m pytest brain/ -q`. See .claude/current-task.md.

## 🧹 CLEANUP the operator must do once the FS is writable again

1. Fix the disk / remount rw (see fault section).
2. Currently checked out on `feature/SPEC-RADIO-LINEUP-050`; the working tree wrongly holds SLSKDVPN's
   `scripts/run.sh` + `scripts/test-run.sh` (1435-line versions) as uncommitted changes — a branch-switch
   side effect that couldn't be reverted (scripts/ went ro). The SLSKDVPN versions are safely committed on
   the SLSKDVPN branch, so DISCARD the pollution: `git checkout -- scripts/run.sh scripts/test-run.sh`.
3. Stray untracked junk at repo root (home-like dotfiles `.bashrc`/`.gitconfig`/etc. + a test artifact
   literally named `"$CURL_TRACE"` from the curl-shim tests) — safe to remove.
4. Apply the shipped run.sh changes on the host: stop the stack + re-run run.sh (prints slskd web login once):
   `docker compose -p golden-shower-radio -f deploy/docker-compose.yml --env-file secrets/.env down` then `bash scripts/run.sh`.

## Detailed state

`.claude/session-state.md` (read-only now, but persisted) has the full pre-fault handoff. The roadmap
after LINEUP-050: other activation wins (ORCH-005, MEMORY-031, HOSTLIFE-032) or run FEATUREGATE-053 (#32).
</content>
