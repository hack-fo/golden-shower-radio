# UI / Website Redesign Plan

Authored 2026-06-24. Lean execution plan (not the formal SPEC — WEBUI-018 is that, expand it via
manager-spec after the budget reset). Ties together what already exists + the new backend now built.

## What already exists (don't reinvent)
- **The live site**: ONE self-contained HTML page served from `state.website_html` by `brain/server.py`
  (`GET /`). Shows now-playing (title/artist/album), recently-played, library/acquiring counters, a
  schedule area. Live data via `/api/nowplaying` + `/status`. The page is a SWAPPABLE string (the brain/LLM
  can self-redesign it — CORE-001 seam).
- **WEBUI-018 spec (draft)** — already scopes the redesign as a VISUAL + UX refresh of the existing single
  page + its existing data; NOT a new app/framework.
- **`.moai/design/`** — research.md, system.md, spec.md, wireframes/, screenshots/ (design source of truth).
- **Brand context** — `.moai/project/brand/` (visual-identity.md palette/type, brand-voice.md, target-audience.md).

## Hard rails (the only fixed constraints, from WEBUI-018)
1. **Brain-only seam, no new runtime.** Served from `state.website_html` as a STATIC self-contained document.
   A build step MAY produce it, but the container serves a static string — NO SSR/Node/long-lived service
   added to the brain image.
2. **Durable, not authoritative.** The recent-played ring is a DISPLAY convenience, NEVER the rotation/
   no-repeat source of truth (that stays `recent_keys()`).
3. **LLM-self-redesign seam preserved** — the page stays a swappable string the brain can regenerate.

## Goals
Modern, on-brand front door (today's "looks 2024 + forgets what it just played"). Album-art-forward
now-playing hero; a real recently-played history; clean player; subtle station status; the schedule. And
forward-ready: surface the NEW backend (hosts/personas, shows, the 24h schedule, tracklists) as those
features activate — without a rebuild, degrading gracefully when they're off.

## Page sections
1. **Now-playing hero** — large album art (ALBUMART-021), title/artist/album, the on-air HOST/persona (when
   personas activate), live on-air indicator.
2. **Player** — the Icecast stream (play/pause/volume).
3. **Recently played** — scrollable history with art + timestamps (the durable recent ring).
4. **Schedule / what's-on** — current daypart/format-clock block; upcoming shows when the OA scheduler
   activates (today: the current block only).
5. **Hosts/personas** — host cards (name, voice, taste, current show) when personas activate.
6. **Station status** — library size, acquiring/downloading counters (subtle, not dominant).
7. **(Later)** per-show tracklists, like/request, listener feedback.

## Design + tech approach
- Execute against the brand `visual-identity.md` + the `.moai/design/` wireframes/system — those are the
  source; this plan is the sequencing, not a new design.
- Mobile-first responsive; dark-mode-friendly (radio = night listening); album-art-forward, tasteful
  streaming-radio feel.
- Build step outputs ONE self-contained HTML file (inlined CSS + minimal vanilla JS polling
  `/api/nowplaying` + `/status`; NO framework runtime in the container) → written to `state.website_html`.

## Phasing
- **Phase 1 — refresh existing**: re-skin the current page + data (now-playing, recently-played, counters,
  schedule area) to the new design. Ships on the CURRENT backend, immediately.
- **Phase 2 — surface the new backend**: host/persona cards, the real schedule grid, per-show context —
  rendered only when the data exists (degrades when personas/scheduler are off). Needs small API additions
  (`/api/schedule`, `/api/hosts`, host on now-playing).
- **Phase 3 — listener interactivity**: per-show tracklists, like/request, feedback — ties to STATS-013 /
  LIKE-015 / REQUEST-011 + the OB-006..009 website surface (play-history w/ show_id, tracklist render,
  feedback POST), which is the CORE-001 website self-edit gap.

## Sequencing vs the build roadmap
The visual refresh (Phase 1) is INDEPENDENT of the OPS-004/ORCH-005 build — it can run in parallel or first.
Phases 2–3 follow the backend activation (personas/scheduler on + the new API endpoints). Formalize WEBUI-018
via manager-spec (expand the draft) after the budget reset; then build Phase 1.

## Budget note
Authored at ~99% usage; the actual redesign build + the WEBUI-018 SPEC expansion wait for Sunday's reset.
This committed plan is the ready-to-execute roadmap. Relates to WEBUI-018, .moai/design/, [[github-project-board]],
and the full-spec-completion-roadmap (this is a parallel listener-facing track, separate from OPS-004/ORCH-005).
