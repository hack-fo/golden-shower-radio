# Taste Seeding

**SPEC:** SPEC-RADIO-SEEDING-029

The station is autonomous — it decides what to play without a human in the loop. But on the very
first boot, you get one chance to give the AI a musical reference point. This is **taste seeding**.

---

## The three modes

When you run `bash scripts/run.sh` for the first time on a fresh install, you will be asked:

```
Pre-seed the station's taste? (ONE-TIME choice — restarts never re-ask)

  [a] anchor   Lean hard on your taste — stay close to what you already love
  [c] compass  Use your taste as a loose compass — explore outward into adjacent sounds
  [W] wopr     Full autonomy — the AI decides everything itself, no seed (default)
```

### Anchor

The AI leans **hard** on your provided taste reference. It bases the set strongly on those
artists, genres, and eras — and their close neighbours. Think of it as telling the AI:
_"play music like what I already know I love."_

The seed is still a **soft bias**, not a hard whitelist. The AI can always drift or surprise
you, and will continue playing even if the seed runs dry.

### Compass

The AI uses your taste reference as a **loose compass**. It stays tonally informed — if you
seeded indie folk it won't suddenly go death metal — but it deliberately explores outward into
adjacent genres and unexpected discoveries. Good choice if you want the station to grow beyond
your existing library.

### WOPR

No seeding. **Full autonomy.** The AI self-directs from day one, guided only by its own
editorial judgement. Named after the computer in WarGames. This is the default if you press
Enter or decline — it is also the fallback if anything goes wrong reading the seed.

---

## What counts as a taste reference?

You can provide any combination of:

| Source | How to use |
|---|---|
| **Spotify CSV export** | Export your Liked Songs or a playlist from Spotify, drop the `.csv` into `data/db/`, and enter the filename when prompted |
| **Dropped music files** | Any music files already in `data/music/` can be read as a taste signal — choose **y** when asked |

Both are optional. If you pick Anchor or Compass but provide no references, the seed
degrades gracefully to WOPR behaviour.

You can also provide the CSV export at acquisition time: when asked _"Also DOWNLOAD the CSV
tracks?"_, choosing **y** will enqueue those tracks for Soulseek acquisition, growing the
library directly from your taste seed.

---

## This is a one-time decision

The choice is written to `data/db/seed-config.json` and locked with a `seed_decided` marker
file. Subsequent runs — including restarts in the middle of a live broadcast — skip the
prompt entirely. The station always boots and plays regardless of what you chose.

To reset and re-prompt: delete `data/db/seed_decided` and restart.

To set the mode non-interactively (CI / headless):

```bash
SEED_MODE=anchor bash scripts/run.sh
SEED_MODE=compass SEED_CSV=liked-songs.csv bash scripts/run.sh
SEED_MODE=wopr bash scripts/run.sh
```

---

## How it works inside the brain

The seed config is read at startup by `brain/seeding.py`. The chosen mode controls a
**framing directive** that rides alongside the taste references in the curator's LLM prompt:

- **Anchor** → `"LEAN HARD on this listener's taste: base the set strongly on these artists..."`
- **Compass** → `"use this listener's taste as a LOOSE COMPASS: stay tonally informed but deliberately explore outward..."`
- **WOPR** → no directive, no references — the prompt is unchanged from full-autonomy mode

The seed never hard-filters the library. The AI can always play anything in its catalog — the
framing is persuasion, not a whitelist. The station never stops playing because of a seed.

---

## Adding new modes (developers)

Modes and their descriptions are defined at the top of the `resolve_seed()` function in
`scripts/run.sh` as three parallel arrays:

```bash
local -a _SEED_KEYS=( "a"      "c"       "W" )
local -a _SEED_MODES=("anchor" "compass" "wopr")
local -a _SEED_DESCS=(
  "Lean hard on your taste — stay close to what you already love"
  "Use your taste as a loose compass — explore outward into adjacent sounds"
  "Full autonomy — the AI decides everything itself, no seed (default)"
)
```

The prompt builds itself from these arrays, so adding a new mode requires:
1. Appending to all three arrays
2. Adding a `case` branch in the read loop
3. Adding the mode's framing directive to `_MODE_FRAMING` in `brain/seeding.py`
