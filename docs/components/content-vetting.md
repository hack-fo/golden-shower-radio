# Content Vetting

SPEC-RADIO-VETTING-027. A three-tier cheapest-first cascade that keeps non-music content (podcasts, audiobooks, interviews, lectures) out of the library before it reaches playout. Off by default; enabled via `BRAIN_VETTING_ENABLED=true`.

---

## Why this exists

Soulseek and yt-dlp results are noisy. A search for a song can return a live interview, a lecture, or an audiobook chapter with matching metadata. Without a gate, these land in the library and air as music. The cascade screens every candidate before download and again before the library ingests a file from disk.

---

## Three-tier cascade

Tiers run cheapest first. A definitive `non_music` verdict short-circuits the remaining tiers.

**Tier 1 — metadata keywords + size/duration heuristics (free, synchronous)**
Matches the candidate title and filename against a configurable keyword list (`BRAIN_VETTING_KEYWORDS`, defaults to: podcast, audiobook, interview, lecture, sermon, ASMR, full episode, chapter, episode, ted talk, standup comedy, etc.). Also fires on chapter-numbering patterns ("Episode 4", "Part 2", "Chapter 1"). Duration and file size are supporting signals only — long duration alone never produces a ban (REQ-VK-001). Outputs `music`, `non_music`, or `ambiguous`.

**Tier 2 — source category (free, synchronous)**
Uses the category field from the slskd/yt-dlp response metadata. A category of "podcast" or "audiobook" from the source is a strong non-music signal.

**Tier 3 — speech likelihood from audio analysis (deferred, requires ANALYSIS-006)**
Reads the `speech_likelihood` score that ANALYSIS-006 attaches to analyzed tracks. A high speech fraction (configurable threshold, default 0.85) combined with at least one other signal yields a `non_music` verdict. Tier 3 is skipped when the score is unavailable — it never blocks a candidate it cannot assess.

**Confidence gating (REQ-VK-001 "≥2 corroborating signals")**
A `non_music` verdict requires at least two corroborating signals from different tiers. Duration alone, or a single keyword hit without corroboration, produces `ambiguous` — not a ban.

---

## Ban list (Group VB)

Confirmed non-music candidates land in a soft, reversible ban list (`brain/banlist.py`) stored in JSON alongside the brain database.

- Every record carries: `key` (normalized artist+title slug), `status` (`banned` / `pending_review` / `cleared`), `cooldown_until`, `evidence` dict, `confidence`, and timestamps.
- Bans are **soft** — no permanent blacklist. Every ban has a cooldown period after which the candidate is re-eligible. An explicit `unban()` path exists (REQ-VB-004).
- `is_banned()` is checked **before** acquisition search (REQ-VB-001), so banned keys are skipped entirely without network I/O.

---

## Gate wiring

| Gate point | Location | What it checks |
|---|---|---|
| Pre-download | `acquire.py` (`Acquirer.vet()`) | Title/filename/category before queueing the download |
| Pre-library | `library.py` (ingestion scan) | Full cascade including speech likelihood for files on disk |

---

## Configuration

| Variable | Default | Effect |
|---|---|---|
| `BRAIN_VETTING_ENABLED` | `false` | Enable the cascade. Off = all candidates pass silently. |
| `BRAIN_VETTING_KEYWORDS` | (built-in set) | Comma-separated keyword additions |
| `BRAIN_VETTING_SPEECH_THRESHOLD` | `0.85` | Speech-likelihood cutoff for Tier 3 |
| `BRAIN_BAN_COOLDOWN_HOURS` | `168` | Hours until a banned key is re-eligible (default 1 week) |

---

## Offensive-content gate (Group VR)

A separate, narrower gate (`OffensiveVerdictStub`) screens for identity-hate content using an LLM judgment call. It is allow-by-default (REQ-VR-001) — it only bans content that unambiguously targets a protected class. It never bans on profanity, adult themes, or controversy alone.

---

## Key invariants

- A cascade error returns `allow` — never a crash, never a silent block (NFR-V-2).
- Duration alone never bans; ≥2 corroborating signals required (REQ-VK-001).
- Long-form music (full albums, classical works) is explicitly protected (REQ-VK-002/003).
- The ban list is off when `vetting_enabled=False`; the `BanList` object is never constructed.
