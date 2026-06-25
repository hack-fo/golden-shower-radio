# SPEC-RADIO-RESEARCH-036 — Research Notes

## Go Codebase Assessment

The Go binary (`cmd/radiod/main.go`) starts a full parallel radio station using
`director.New(anthropicKey, model, lib, st, acq, queries)` — this calls the
Anthropic API directly with a pay-per-use key. The Python brain uses the MAX
subscription OAuth via claude-agent-sdk. They are mutually incompatible auth
schemes. The Go binary is NOT started by `scripts/run.sh` or any Docker Compose
service in `deploy/`. It is pure dead code.

Every `internal/` Go package has a direct Python equivalent in `brain/` that is
richer in every dimension (more sources, more SPEC compliance, personas, shows,
knowledge, etc.). Removing the Go code eliminates ~2,000 lines with no functional
change to the running station.

`bunfig.toml`, `package.json`, `node_modules/`, `yarn.lock`, `pnpm-lock.yaml`
are likely from a Bun/JS toolchain that also appears unused. These should be
assessed in the same audit pass.

## LLM Call Analysis

The station currently makes the following LLM calls (confirmed from source):

1. `llm.curate_batch()` — `brain/director.py:328` — once per director tick
2. `llm.generate_talk_script()` — `brain/talk.py:168,205,413` — per track transition when show active
3. `llm.adversarial_factcheck()` — `brain/talk.py:450` — per talk script when enabled
4. `llm.design_persona_identity()` — `brain/minting.py:356` — once per new persona
5. `llm.design_show_angle()` — `brain/shows.py:785` — once per show variation
6. `llm.research_show_prep()` — `brain/main.py:448` — pre-show per featured artist

The candidate fit-scoring (REQ-RS-003) would be call #7, triggered only in
freeform mode with `BRAIN_RS_ENABLED=true`.

## Token Cost Estimation

- curate_batch: ~300 tokens in + ~250 tokens out = ~550 tokens/tick
- generate_talk_script: ~800 tokens in + ~400 tokens out = ~1200 tokens/script
- adversarial_factcheck: ~600 tokens in + ~200 tokens out = ~800 tokens/script
- design_persona_identity: ~300 tokens in + ~200 tokens out (rare)
- design_show_angle: ~400 tokens in + ~150 tokens out (rare)
- research_show_prep: ~500 tokens in + ~400 tokens out (pre-show, optional)
- fit_scoring (new): ~600 tokens in (pool) + 50 tokens context + ~300 tokens out = ~950 tokens/tick

The fit-scoring call adds ~950 tokens to a freeform tick vs. ~550 for the
existing curate_batch. The tradeoff: eliminates hallucinated track suggestions
that can never be acquired.

## Candidate-Set-First: Why Now?

The current curate_batch() asks the LLM to invent tracks from its training
data. The LLM regularly returns tracks that exist but are not on any source the
acquirer can find. The candidate-set-first approach inverts this: the LLM
only ranks REAL LIBRARY TRACKS. Every pick is guaranteed acquirable (already
in the library). This is strictly better — lower hallucination rate, lower
wasted-acquisition cost.

## Discogs vs Last.fm Coverage

- Last.fm: strong on similar artists, tags, play counts. Weak on bios.
- Discogs: strong on artist bios, labels, release year, masters. No similar-artist graph.
- Wikipedia: strong on formation, members, awards, history. Slower SPARQL.
- MusicBrainz (existing): strong on MBID, relationships, labels.

Discogs + Wikipedia together fill the bio gap that Last.fm cannot.

## Press Source Technical Assessment

| Source | RSS available? | Notes |
|--------|--------------|-------|
| Paste Magazine | Yes — https://www.pastemagazine.com/music/feed/ | Standard RSS |
| NME | Yes — https://www.nme.com/feed/ | Standard RSS |
| DIY Magazine | Yes — https://diymag.com/feed/ | Standard RSS |
| The Fader | Yes — https://www.thefader.com/rss | Standard RSS |
| Crack Magazine | Likely — check /feed or /rss | May need HTML scrape |
| Magnetic Magazine | Yes — https://www.magneticmag.com/feed/ | Standard RSS |
| GAFFA | Swedish; RSS likely at gaffa.se/feed/ | Language: Swedish |
| Close-Up Magazine | Check; metal focus | May need HTML scrape |
| Denimzine | Small zine; RSS unknown | Fallback: HTML scrape |

RSS-first strategy covers most sources without a custom scraper. The 2-3 that
need HTML scraping use httpx + BeautifulSoup with standard `<article>` or
`<h2 class="post-title">` selectors (common WordPress pattern used by all
small music zines).

## Dedup Approach: Concept-Hash Design

The concept-hash for editorial facts is:
```
SHA-256(entity_class + ":" + predicate + ":" + normalised_value)
```

Where `normalised_value` = `value.lower().strip()` with year-like patterns
normalised to `YYYY` (e.g. "in 1985" and "in the year 1985" both normalise to
"1985"). This catches most paraphrase pairs for facts like formation year and
founding location. For longer bio text, MinHash (128-permutation) on 3-gram
shingles gives reliable ≥0.85 similarity detection with fast computation.

## Analysis Context Packet Token Estimate

One-line context summary example:
```
Currently playing: "Teardrop" by Massive Attack | 100 BPM · key Em (7A) · energy 0.48 · genre Trip-Hop
```
This is ~30 tokens. Well within the NFR-A-1 ≤50 token budget.
