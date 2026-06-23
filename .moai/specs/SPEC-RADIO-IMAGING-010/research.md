# SPEC-RADIO-IMAGING-010 — Research

This SPEC is grounded in an adversarially-verified research dossier (an 8-agent workflow with a
host-verified ffmpeg toolchain check and live web verification of Suno's pricing/ToS). The
dossier is the authoritative source for the capability-honesty claims, the licensing posture, the
6-stage pipeline mechanics, and the imaging-design discipline encoded as EARS requirements.

## Dossier location (authoritative)

```
/tmp/claude-1000/-mnt-f-golden-shower-radio/e8ab03c7-aff2-4575-9056-567ac559e45c/tasks/wcufhaimt.output
```

JSON result of the verified workflow. Key fields: `dossier.verdict`
(`build-with-human-seeded-generation`), `dossier.generation_path`, `dossier.licensing`,
`dossier.pipeline` (6 stages, host-verified ffmpeg filters), `dossier.imaging_design`,
`dossier.should_author_spec` (true), `dossier.recommendation` (BUILD as the honest hybrid),
`dossier.open_questions`, `dossier.source_urls`, and `verdicts[]` (3 adversarial claims, 2
refuted / 1 not-refuted).

> Note: the dossier lives in a non-versioned `/tmp` task-output path and may be garbage-collected.
> The load-bearing facts it established are encoded directly in `spec.md` (Sections 1.1, 1.2, 1.6,
> the REQ groups, and the Risks) so the SPEC stands on its own if the file is gone.

## Verdict (verbatim summary)

`build-with-human-seeded-generation`. Exactly ONE step (bed generation) requires a human/UI touch;
the entire HARD requirement — the brain mixes/masters/cuts/edits/layers/schedules/serves — is
fully buildable today on the existing stack.

## The three adversarial claims (verdicts[])

| Claim | Verdict | Where encoded |
|-------|---------|---------------|
| The brain can AUTONOMOUSLY GENERATE Suno jingles via an official ToS-compliant API (Premier grants one) | **REFUTED** | REQ-IB-001 (no API, human-seeded), NFR-I-5 (honest capability) |
| Suno PREMIER output is CLEANLY licensed for 24/7 broadcast as station imaging | **REFUTED** (it is commercially-permitted but NON-exclusive / no-warranty / no-indemnity, not "clean ownership") | REQ-IB-003/004 (paid-tier-licensed class, non-exclusive furniture), NFR-I-6 |
| The brain can fully MIX/MASTER/CUT/EDIT + layer TTS over Suno beds autonomously with ffmpeg/pyloudnorm (already in the stack), no GUI | **NOT refuted** (verified achievable) | Group IP (REQ-IP-001…008) |

## Experimental autonomous-generation path (v0.2.0 addition — Group IX)

A v0.2.0 addition (coordinator-relayed) adds an EXPERIMENTAL, OPT-IN, OFF-BY-DEFAULT path
(Group IX) that POCs driving the real Suno UI with the project's OWN tooling — HEADED (not
headless) Chromium via Playwright + a persistent logged-in profile, navigated by claude-vision +
the DOM/accessibility snapshot — rather than a paid captcha solver (NopeCHA-style only a rare
fallback). This does NOT come from the dossier (the dossier refuted *compliant* autonomous
generation); it is a deliberately risk-accepted exception:

- It KNOWINGLY VIOLATES Suno ToS (robotic automation) and carries ACCOUNT-BAN RISK → mitigated by
  running ONLY on a secondary/throwaway account (never Premier) and keeping the human-seeded
  default fully intact (REQ-IX-001, NFR-I-8).
- It is DISTINCT from a third-party reverse-engineered API wrapper (which the dossier flagged and
  which REQ-IB-001 forbids absolutely) — it is first-party automation of the real human UI.
- Everything AFTER a downloaded bed lands in the drop dir is UNCHANGED (re-enters Group IB ingest +
  Group IP), so the dossier-grounded production half is untouched (REQ-IX-005).
- [CONSENT CAVEAT] This was relayed by the coordinator; coordinator-relayed consent is NOT user
  authority. The SPEC encodes the path as opt-in/off-by-default/ban-risk-acknowledged and records
  that ENABLING it requires the actual user's own explicit, risk-accepted opt-in (R-I-11). Confirm
  the ban risk + secondary-account constraint with the user directly before any implementation
  enables the path.
- Residual risks (R-I-11, NFR-I-8): ToS/ban, UI-change brittleness (maintenance), captcha-on-
  challenge (vision can't reliably solve hCaptcha/Turnstile → rare human/NopeCHA fallback),
  headless-detection (mitigated by headed + persistent profile). Generation is an infrequent batch
  chore, so semi-automatic (brain drives, human solves the rare captcha) is acceptable.

## Load-bearing facts → requirements

- **No public Suno API on any tier (Premier included), verified against suno.com/pricing; wrappers
  violate ToS + risk a ban** → REQ-IB-001, NFR-I-5 (the single most important honest constraint).
- **Generation is human-seeded; the brain owns 100% after the file lands in the drop dir** →
  REQ-IB-002 (local ingest), REQ-IP-001 (autonomous-after-ingest).
- **Paid-tier rights explicitly cover "radio station jingles and idents," no attribution, persist
  post-cancel; but non-exclusive, no copyright-vesting warranty, no indemnification; free-tier =
  attribution + weaker rights** → REQ-IB-003 (paid-only, generate-while-subscribed, free-tier
  forbidden), REQ-IB-004 (ledger class), NFR-I-6.
- **6-stage pipeline, host-verified ffmpeg 4.4.2 filters all present** (loudnorm, sidechaincompress,
  amix, acrossfade, aloop, atrim, afade, apad, adelay, asplit, silenceremove, dynaudnorm) →
  REQ-IP-002 (cut/phrase-snap/fades/`[End]`), REQ-IP-003 (loop/extend, 2s→6.0s verified), REQ-IP-004
  (TTS-layer + sidechain duck with the **`asplit=2` gotcha** — a label is consumable once),
  REQ-IP-005 (two-pass loudnorm to -16/-1.5/LRA11), REQ-IP-007 (verified toolchain, ~no new deps),
  REQ-IP-008 (catalog).
- **Anti-dramatic taste (BBC6/NTS/KEXP), gentle dynamics, do NOT brick-wall** → REQ-IP-006,
  REQ-IL-003 (per-show palette atop a station-wide cohesion floor).
- **Per-show/segment imaging system: jingle-spec table, ident taxonomy (sting/bumper/bump-out),
  catalogued library, variants for rotation, refresh cadence, director schedules boundaries** →
  Group IL (REQ-IL-001…005) + REQ-IS-003.
- **Serving via /api/next as a finer jingle/ident kind + a musical no-hard-cut radio.liq
  transition** → REQ-IS-001/002, reconciled with OPS-004 REQ-OE-007's `kind="imaging"` seam.
- **Non-blocking, bounded, resilient, no over-engineering** → NFR-I-1/2/4/7.

## Code seams referenced (shipping code)

- `brain/voice.py:340-342` — documented seam: "insert music-bed mixing / ducking / jingles between
  the WAV render and the final MP3 encode"; `_loudnorm_to_mp3` (loudnorm + libmp3lame 192k @
  44.1kHz). The production module parallels `produce_talk_clip` (REQ-IP-007).
- `brain/analysis.py` — pyloudnorm BS.1770 metering reused for the two-pass measurement pass
  (REQ-IP-005).
- `brain/server.py` — `Picker.pick()` / `NextItem.kind` (`music`/`talk`; OPS-004 adds
  `imaging`/`news`) / `/api/next` / `_annotate_uri`; the serving discriminator attaches here
  (REQ-IS-001).
- `brain/director.py` + `brain/talk.py` — scheduling seams the director uses to fire idents at
  boundaries (REQ-IS-003).
- `config.py` — shared loudnorm targets I=-16 / TP=-1.5 / LRA=11 (REQ-IP-005, NFR-I-3).
- `deploy/config/radio.liq` — the `%mp3(bitrate=320)` mount + transition logic, coordinated with
  the in-flight playout-transition fix (REQ-IS-002); the primary music mount stays unchanged.

## Boundary with OPS-004 (the key positioning)

OPS-004 Group OE (REQ-OE-001…012) already OWNS the imaging CONCEPT, the abstract 6-stage pipeline
DESIGN, the offline voice-over-bed ducking (REQ-OE-002), the two-pass loudnorm (REQ-OE-005), the
clip library + CLIPS_DIR (REQ-OE-006), the `kind="imaging"` pull insertion (REQ-OE-007), the
single-clean-track guard (REQ-OE-009), the license gate + ledger (REQ-OE-010), the
anti-overproduction default (REQ-OE-011), and the ready-buffer / serialized-generator discipline
(REQ-OE-012); plus the program-director cadence (Group OA). IMAGING-010 is the CONCRETE PRODUCTION
SUBSYSTEM that FULFILLS those OE requirements for one specific, verified bed source (human-seeded
Suno) — it references them by number and EXTENDS REQ-OE-010's ledger with a paid-tier-licensed bed
class (REQ-IB-004) rather than contradicting the "self-generated or CC0" gate text. See spec.md
Sections 1.4 and 2.

## Open questions (relayed from the dossier; surface to the user)

1. GPU plumbing for ident TTS (not needed for the audio post-stage; CPU likely fine for short ident
   voice lines).
2. Bed-batch cadence + ownership (who runs the Suno batch, how often, how many variants per show).
3. Per-show palette: start station-wide and diversify per show later, or define distinct per-show
   palettes (5 EN + 2 FO personas) now? (Default recommendation: start station-wide.)
4. Ident taxonomy + durations confirmation (sting 3-8s / bumper 8-15s / bump-out 15-30s; which carry
   TTS).
5. Duck depth + envelope (-8 to -12 dB suggested) — needs an ear-test pass (taste is subjective).
6. Scheduling policy (how often idents fire; every N tracks / boundaries / on the hour) — the
   director's call (OPS-004 REQ-OA-005).
7. Stems vs full mixdowns (Premier 12-track WAV stems give cleaner ducking but add a UI export
   step; mixdowns likely suffice for the understated style).
8. Loudness target for imaging (recommend reusing the -16 LUFS shared target to avoid level jumps).
9. bhive was UNAVAILABLE (API timeout) during research — re-run a bhive query on the Suno+ffmpeg
   ducking pattern when it returns and contribute the verified pipeline back per AGENTS.md.

## Source URLs (from the dossier)

suno.com/pricing; suno.com/terms-of-service; help.suno.com articles 9601665 / 2425729 / 2746945;
musicgpt.com/blog/suno-api; aimlapi.com/blog (the-suno-api-reality / suno-api-review);
techjacksolutions.com (suno-pricing / suno-commercial-use); hookgenius.app/learn/suno-instrumental-prompts;
blakecrosley.com/guides/suno; eesel.ai/blog/suno-review; terms.law/ai-output-rights/suno;
medium.com (Suno music 2026 — what creators own); musicinafrica.net (Suno/Warner ownership terms).
