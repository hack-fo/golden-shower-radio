# Host Lived Experience

SPEC-RADIO-HOSTLIFE-032. A per-persona loop that gives each curator host a lived experience between shows: they "read" recent news from the editorial news ledger, react to charter-relevant stories, form opinions, and arrive at each show with grounded talking points based on real items. **Never invents facts** — every engagement bit is tied to a real, dated, attributed news item.

---

## The loop: SELECT → ENGAGE → TASTE → FRAME

The `LivedExperienceLoop` runs once per persona per show-gap (between shows, not on every track). It has four phases:

### SELECT — Pick relevant stories

`LedgerReader` reads the read-only OD-007 news ledger (already stored by the news engine — hostlife does NOT fetch web or poll feeds). It filters to items that match the persona's editorial charter (genre interests, topic affinities, era preferences). A configurable cap (default 5 items per window) bounds LLM cost.

### ENGAGE — Form a reaction

For each selected item, one LLM call asks the persona to react — agree, disagree, draw a connection to their musical taste, flag curiosity or skepticism. The output is an `EngagementBit`: the persona's reaction + the source attribution (item ID, date, outlet). **cite-or-don't-say** is load-bearing: if the item's claim can't be cited, the persona doesn't use it on air.

### TASTE — Update taste signals

`TasteFeeder` pushes the engagement outcome (positive/negative reaction + the associated artist/genre/era) into the PROGRAMMING-007 persona taste loop as a discovery signal. A story about a new album release from a genre the persona already likes reinforces that genre; a disappointing review may dampen it slightly.

### FRAME — Compose on-air talking points

`FramingComposer` assembles a short grounded narration from the engagement bits — concrete, attributed things the host can say between songs. This context is passed to the talk director when the persona next prepares a link, via the `inject_lived_experience_context()` seam (HOSTCTX-016).

---

## Key invariants

**cite-or-don't-say** — Every engagement bit carries `source_attribution = {item_id, date, outlet}` from the real news item. Framing is built exclusively from real bits; no hallucinated facts can enter the on-air script through this path.

**Degenerate baseline** — No news, cold persona, empty charter match, or disabled ledger all produce an empty lived-experience safely. The persona simply has no extra context for their next show. Normal show, no stall, no error.

**Exception-isolated throughout** — Every public method catches all exceptions and returns a safe default. Hostlife never raises into the director tick or the playout path.

**News ledger read-only** — Hostlife does not poll feeds, fetch the web, or write a second news store. It reads a projection the existing `NewsLedger` already maintains.

**News anchor exempt** — The news anchor is a TTS route, not a curator persona. `persona_identity.is_news_anchor()` short-circuits the loop for the anchor; it never receives a lived-experience context.

---

## Configuration

| Variable | Default | Effect |
|---|---|---|
| `BRAIN_HOSTLIFE_ENABLED` | `false` | Enable the lived-experience loop |
| `BRAIN_HOSTLIFE_ITEMS_PER_WINDOW` | `5` | Max news items per persona per show-gap |
| `BRAIN_HOSTLIFE_ENGAGE_MODEL` | (inherits) | Model for per-item engagement calls |

---

## Relationship to other subsystems

| Subsystem | Relationship |
|---|---|
| `news_ledger.py` | Source of news items (read-only) |
| `persona.py` / `persona_identity.py` | Persona charter used for story filtering |
| `ledger.py` (OD-007) | Destination for engagement events |
| `playbook.py` / `talk.py` | Consumes lived-experience context at show prep time |
| HOSTCTX-016 | `inject_lived_experience_context()` seam that delivers framing to talk director |
