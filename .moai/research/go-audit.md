# Go Codebase Audit — SPEC-RADIO-RESEARCH-036 REQ-RG-002

**Audit date:** 2026-06-25
**Auditor:** MoAI (manager-docs)
**Decision:** ALL Go files classified DEAD. Deleted in commit following this audit.

## Background

The Go binary (`cmd/radiod`) was the original brain of Golden Shower Radio, built
before the Python `brain/` package existed. At some point during development, the
Python brain replaced it entirely. The Go binary has NOT been the production brain
for multiple SPEC generations (at minimum since SPEC-RADIO-ORCH-005).

**The key incompatibility:** `deploy/docker-compose.yml` uses `Dockerfile.brain`
(the Python brain). The old `deploy/Dockerfile` built the Go binary and is the only
file that referenced it in the deploy stack. `docker-compose.yml` never started
`radiod` as a service. `scripts/run.sh` starts only the Python brain.

**Auth incompatibility:** The Go director called `NewDirector(anthropicKey, model, ...)`
— it uses a pay-per-use Anthropic API key. The Python brain uses the MAX subscription
OAuth via `claude-agent-sdk` with `ANTHROPIC_API_KEY` deliberately stripped from
the subprocess environment. Running both would result in incorrect billing.

## File Classification

| File | Classification | Python equivalent | Rationale |
|------|---------------|------------------|-----------|
| `cmd/radiod/main.go` | DEAD | `brain/main.py` | Entry point for the old Go station. Not started by any live deploy target. Uses pay-per-use API key auth. |
| `internal/acquire/acquire.go` | DEAD | `brain/acquire.py` | Acquisition worker. Python version is richer: slskd + yt-dlp fallback, DEDUP-014, MusicBrainz enrichment, vetting gate. |
| `internal/config/config.go` | DEAD | `brain/config.py` | Configuration loader. Python version covers 100+ config fields vs ~10 in Go. |
| `internal/director/director.go` | DEAD | `brain/director.py` | LLM curation loop. Python version has personas, shows, seeding, ORCH-005 world model, PROGRAMMING-007. |
| `internal/director/seeds.go` | DEAD | `brain/seeding.py` | Seed track list. Python version is SEEDING-029 (operator taste seed, ANCHOR/LEAN/WOPR modes). |
| `internal/library/library.go` | DEAD | `brain/library.py` | Track index. Python version has MBID, ANALYSIS-006 features, dedup, SQLite backend. |
| `internal/playout/playout.go` | DEAD | `brain/server.py` `/api/next` | Old Liquidsoap telnet push. Replaced by HTTP pull architecture. |
| `internal/scheduler/scheduler.go` | DEAD | `brain/shows.py` + `brain/director.py` | Show scheduler. Python version is SHOWS-020 + PROGRAMMING-007 with persona/show/variation. |
| `internal/slskd/slskd.go` | DEAD | `brain/slskd.py` | Soulseek client. Python version is behaviorally identical + integrated with SKIP-028. |
| `internal/state/state.go` | DEAD | `brain/state.py` | Station state store. Python version is ORCH-005-aware with world model slots. |
| `internal/store/store.go` | DEAD | `brain/sqlite_store.py` | Persistence layer. Python version owns brain.db, state.db, events.db, knowledge.db. |
| `internal/web/web.go` | DEAD | `brain/server.py` | HTTP server. Python version serves /api/next, /api/nowplaying, /stats, /api/decisions. |
| `internal/web/index.go` | DEAD | `brain/website.py` | HTML page renderer. Python version is WEBUI-018 glassmorphism design. |

## Additional Dead Files Removed

| File | Classification | Rationale |
|------|---------------|-----------|
| `go.mod` | DEAD | Go module definition. No Go code remains. |
| `deploy/Dockerfile` | DEAD | Built and ran the Go binary. `docker-compose.yml` uses `Dockerfile.brain` (Python). Never started in the live stack. |
| `bunfig.toml` | DEAD (empty) | 0-byte Bun config file. No Bun/JS toolchain in use. |
| `package.json` | DEAD (empty) | 0-byte npm package manifest. No JS toolchain in use. |
| `package-lock.json` | DEAD (empty) | 0-byte npm lockfile. |
| `pnpm-lock.yaml` | DEAD (empty) | 0-byte pnpm lockfile. |
| `yarn.lock` | DEAD (empty) | 0-byte yarn lockfile. |

## Verification

**AC-RG-001:** `grep -r "radiod\|cmd/radiod\|go run\|go build" deploy/ scripts/`
returned results ONLY in `deploy/Dockerfile` (now deleted) and `deploy/docker-compose.yml`
(comment only: `# slskd lands in ../data/music, which liquidsoap and radiod also mount`
— this comment referred to the old stack and is now stale; no live service starts radiod).

**AC-RG-002:** This file satisfies the requirement.

**AC-RG-003:** After deletion: `find . -name "*.go" | wc -l` returns 0.
`go.mod` absent. `scripts/run.sh` and `deploy/` remain functional (Python brain unchanged).
