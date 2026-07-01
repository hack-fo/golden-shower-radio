# SPEC-RADIO-SONICRECO-061 — Research / Evidence Base

Status: draft. This is the codebase-analysis + external-evidence artifact backing `spec.md`. It records
(1) the exact current-code problem the SPEC targets (verified by reading `brain/`), (2) the twelve-source
convergent research findings that drive the requirements, (3) the per-component KEEP/DEFER/SKIP verdicts with
licences, (4) the infra-sizing math that makes a vector service unnecessary, (5) the verified seam map, and
(6) the source list with citation-verification notes.

---

## 1. The problem, grounded in the current code

Two selection paths run in the brain today, and both are ungrounded in the audio content the station already
analyzes. Verified by reading the source (all `file:line` below were confirmed in this analysis pass):

### 1.1 Acquisition invents `{artist, title}` names (hallucination surface)

`brain/director.py` `_tick` (`:316`) calls `llm.curate_batch` (`brain/llm.py:287`), which prompts Claude to
emit a batch of `{artist, title}` dicts to acquire, then enqueues each via `acquirer.enqueue`
(`director.py:340`). The LLM invents these names from parametric memory — a plausible-but-wrong artist / title
/ attribution is a live failure mode. On any SDK error the function returns the built-in `SEED_TRACKS` list
(`llm.py:56`, `:330`) so the station keeps running (the never-raise discipline this SPEC preserves).

### 1.2 Playout ranks by rule only (no content signal at selection time)

`brain/library.py` `pick_next` (`:636`) returns the least-recently-played legal candidate from
`legal_candidates` (`:606`). The OPS-004 `SelectionRefiner.refine` (`brain/schedule.py:582`) re-scores that
legal-and-LRP-ranked set with soft genre-family (`_family_balance_penalty`:549) and adjacency penalties —
behind `scheduling_enabled` (default OFF, `config.py:586`), so the default path is the byte-identical LRP
head. The HARD no-repeat / LRP rail (REQ-OA-003a) is produced by `legal_candidates` and is never relaxed by
the soft layer. Nothing in this path reads the audio content (BPM/key/energy/character/genre) to ask "which of
these fits this persona / this moment."

### 1.3 The station already HAS the raw material, unused

- `brain/analysis.py` `analyze_file` (`:94`) — CPU-only librosa DSP (BPM/key/energy/cue/LUFS/sonic-character),
  swappable, never-raises (returns `None` on any failure). The engine identifier is `"librosa"` (`:46`).
- `brain/analyzer.py` `_analyze_one` (`:184`) — the offline ingestion hook: cache-check (`content_sig`,
  `:200`) → DSP off-lock (`:204`) → `metadata.enrich` off-lock (`:221`) → `set_analysis` under a brief lock
  (`:241`). This is exactly where an additive embedding step belongs.
- `brain/library.py` — the RESERVED, currently-empty fields: `sonic_description` (`:118`, "DEFERRED
  grounded-LLM summary — stays empty") and `embedding_ref` (`:119`, "DEFERRED content-embedding reference —
  unused"). Both are writable via `set_analysis` because `_ANALYSIS_WRITABLE_FIELDS` (`:216`) is computed as
  ALL `Track` fields minus `_IDENTITY_FIELDS` (`:205`) minus `_ANALYSIS_VOLATILE_FIELDS` (`:210`), and neither
  reserved field is in those exclusion sets. Confirmed: the embedding slot and the summary slot exist and are
  allowlist-writable today, with no schema change needed.
- `brain/memory.py` `VectorSeam` (`:299`) — the MEMORY-031 Group MS clean seam for an optional sqlite-vec vec0
  index INSIDE existing SQLite files; off by default; `embed_document` / `search` / `purge_entity` currently
  raise `NotImplementedError` (`:314`, `:322`, `:328`). The intended vector store, waiting to be implemented.
- `brain/taste.py` — `diversity_rerank` (`:711`) with the pluggable `related_fn` hook (`:720`) feeding
  `_catalog_density` (`:748`); `profile.relevance` (`:464`) is token/weight-based today ("computed only from
  the track's descriptors ... never from play count / popularity"); the play/skip signals
  `SIGNAL_PLAY_THROUGH` / `SIGNAL_EARLY_SKIP` (`:490`–`:519`). A content-similarity `related_fn` and a
  vector-relevance term slot straight in.
- `brain/metadata.py` `enrich` (`:122`) — genre/sub_genre/mood/tags/year + MBID grounding + provenance;
  never-raises; returns an analysis-writable dict. The source of the sonic-card metadata fields.

The gap is a bridge: turn the analyzed audio into embeddings, retrieve real candidates deterministically, and
let the LLM choose from them.

---

## 2. Convergent research findings (all twelve sources agree)

The dossier's twelve sources (§6) converge on seven points. Each drives a requirement group.

### 2.1 GROUND IT — retrieve real candidates; the LLM chooses from a provided set, emits only in-set IDs

The highest-leverage, near-zero-cost first step across every source: do NOT let the LLM name items from
memory; give it a retrieved set of real candidates and have it SELECT / RE-RANK, emitting only IDs in that
set; hard-reject anything else. This doubles as the prompt-injection firewall — the candidate/card text is
DATA, not instructions. It works on the EXISTING curation LLM with no new model. → Group GD (Phase 0).
(TalkPlay's retrieve-then-generate framing; the 2606 LLM-rec paper's "constrain the generation to the catalog"
finding; the Deezer/JKU survey's repeated caution that free-form LLM item generation hallucinates.)

### 2.2 CLAP is the embedding to adopt — a music-tuned checkpoint, because we need the TEXT tower

For a music-rec engine that must serve BOTH audio→audio similarity AND natural-language vibe queries, the
model needs a shared audio+text space. LAION-CLAP (HF `ClapModel`) provides exactly that: an audio tower and a
TEXT tower projecting into a shared ~512-dim space, Apache-2.0, ~150–190M params (exact count UNVERIFIED),
CPU-feasible. The PRIMARY checkpoint is the MUSIC-TUNED `laion/larger_clap_music` rather than the general
`laion/clap-htsat-unfused`: it is the SAME `transformers.ClapModel` API (zero pipeline change), keeps the text
tower, and is a strict drop-in music-quality bump. The general `clap-htsat-unfused` is retained only as an
optional non-music (speech / SFX / ambience) fallback channel, not primary. The 2606 paper found EnCodec best
on ITS task — but that was a NON-text sequential-rec task, and EnCodec has no text tower, so it cannot serve
vibe / disco-mode queries; it is therefore NOT adopted as primary. → Group VE (CLAP audio + text KNN).

A single music dual-tower model does BOTH audio→audio similarity AND text→audio (vibe / disco) retrieval, so a
SEPARATE audio-only channel (a standalone MERT embedding) is redundant — its audio→audio role is subsumed by
`larger_clap_music` now and by the CLaMP 3 upgrade tier later (CLaMP 3 literally CONTAINS a frozen MERT-95M
encoder). **CLaMP 3** (`sander-wood/clamp3`, MIT) is the DEFER UPGRADE TIER: "MERT + a text tower" (frozen
MERT-95M audio encoder + XLM-R text tower in a shared space), real text→audio in ~100 languages, SOTA vs
general CLAP (Song Describer MRR 0.198 vs 0.131). Cost: a two-stage MERT-extraction pipeline best run on the
8GB GPU sidecar; total param count + official CPU support UNVERIFIED (verify at adoption). Deferred until the
CPU `larger_clap_music` baseline ships.

### 2.3 Infra is a non-issue at our scale — brute-force, not a vector DB

At thousands–tens-of-thousands of tracks, 50k×512 f32 ≈ 100MB. A brute-force cosine scan over that is ~1–5 ms
at recall 1.0 (exact). An ANN index (FAISS/hnswlib) solves a scale problem we do not have; an external vector
service (Qdrant/pgvector) additionally VIOLATES the brain-only / no-standing-service constraint. Verdict: NumPy
brute-force over SQLite BLOBs, or the sqlite-vec `VectorSeam` inside `brain.db`. → REQ-VE-003, NFR-SR-1.
(Sizing math in §4; consensus across the feasibility brief, JAM's own retrieval scale discussion, and the
surveys.)

### 2.4 Fuse query-conditioned, NOT naive-concat; personalize as user+query≈item

JAM (CrossMixing) and the 2606 paper (FiLM conditioning) both show that combining a user/persona vector with a
query vector by NAIVE concatenation DEGRADES retrieval; query-conditioned fusion (`user + query ≈ item`) is
the pattern that works. Here the "user" is the per-persona taste (`brain/taste.py` `TasteProfile`). → Group JP
(the optional trained projection layer uses this fusion) and the RK re-rank conditioning.

### 2.5 Division of labor — LOCAL does recall; the LLM does judgment at batch cadence; cosine is never the final ranker

Every source that pairs embeddings with an LLM keeps retrieval LLM-free (cheap, deterministic) and spends the
LLM only on re-ranking / explaining a small retrieved set. This matches the station's cost posture (the
`claude-agent-sdk` subprocess on a subscription quota) and the never-stop constraint. → Group RK + NFR-SR-5.

Generalised into the load-bearing division-of-labor invariant this SPEC now encodes (NFR-SR-10): EMBEDDINGS /
local compute do RECALL + similarity + clustering + feature-extraction; the frontier LLM (the Claude
subprocess) is reserved for JUDGMENT / sequencing / card-writing at BATCH (planning) cadence with CACHED
outputs — cards and the grounded `sonic_description` are written ONCE per track and cached (`content_sig`-gated),
plans are cached per segment, and the sub-1s pull is deterministic from the plan with no per-track LLM call
(REQ-RK-006). COSINE is never the FINAL ranker: it feeds candidate generation + re-rank inputs, but the airable
order is LLM judgment (or today's deterministic LRP/SEED fallback), never a raw cosine sort. Corollary: a local
HEAVY captioner LLM (LLARK / MU-LLaMA) to write sonic descriptions is a FALSE ECONOMY — Claude at planning
cadence writes grounded cards from evidence far more cheaply, and identity enrichment (AcoustID / MusicBrainz /
Discogs) makes IDENTITY reliable but NOT sonic DESCRIPTION (the embeddings carry that); this reinforces the §3
MERT / heavy-captioner SKIP verdicts and is not re-litigated. → NFR-SR-10 + REQ-RK-006.

### 2.6 Sonic-card schema — adopt an MGPHot-style taxonomy hydrated from OUR data

A structured attribute taxonomy (MGPHot-style: 58 attributes / 7 categories — lyrics, vocals, harmony, rhythm,
instrumentation, sonority, composition; CC-BY-4.0) gives the LLM a consistent, grounded card to reason over,
far better than free text. We adopt the SCHEMA (a data structure) and hydrate the VALUES from our own data:
metadata (`metadata.enrich`) + DSP (`analysis.py`) + a grounded LLM summary in the reserved
`sonic_description` field. → REQ-RK-001.

### 2.7 Evaluate grounding-accuracy FIRST; validate any LLM-as-judge against humans

n-gram and ranking metrics correlate poorly with human-perceived music-rec quality; an LLM-as-judge can be
lenient and must be validated against human ratings before it is trusted. So the FIRST metric is grounding
accuracy (out-of-set-ID rate must be 0), and offline harnesses (MMMR / JAMSessions) are used as EXTERNAL eval
sets, not run over the live library. → NFR-SR-9.

### 2.8 Diversify at GENERATION, not just at re-rank; and learn the similarity METRIC from feedback

Two further findings drive the v0.2.1 design-division amendment:

**Diversity at GENERATION time.** Raw nearest-neighbor retrieval over a fixed embedding index returns
substantially the SAME neighbors every time — the "same-N-tracks-every-time" degeneracy that makes an
embedding-only radio feel stuck. The local fix is to diversify the candidate POOL at GENERATION time, BEFORE
the LLM sees it: MMR (maximal-marginal-relevance) over the KNN result, or cluster-spread over an offline local
clustering of the vectors (k-means "micro-genre" structure). This is distinct from — and complementary to —
the shallow-stochastic re-rank (REQ-RK-004), which only perturbs the FINAL ORDER of whatever pool it is given:
diversity-at-generation shapes the POOL, stochastic re-rank shapes the ORDER. → REQ-VE-006 (diversity
generation) + REQ-VE-007 (optional local clustering) + the neighbor-context cards of REQ-RK-001.

**Learn the metric from feedback (JAM / bliss lineage).** JAM's CrossMixing (§2.4) personalises retrieval by
conditioning the query on a user vector rather than treating cosine over a fixed space as ground truth;
bliss-rs (the Rust audio-similarity library, otherwise SKIP — §3) uses a MAHALANOBIS distance (a
learned/weighted metric over its audio features) instead of plain Euclidean/cosine. Both point at the same
idea: the similarity METRIC itself can be shaped by feedback. Mapped onto our taste layer, this is an OPTIONAL
per-persona feedback-weighted weighting of embedding dimensions / neighbor influence, learned LOCALLY from the
existing `SIGNAL_PLAY_THROUGH` / `SIGNAL_EARLY_SKIP` signals (`brain/taste.py:490`–`519`), feeding the
content-similarity `related_fn`. [HARD] It stays CURATORIAL shaping, never a popularity / engagement target
(the inherited anti-appeal rail); off by default, bounded, degrades to plain cosine. → REQ-RK-007.

---

## 3. Per-component verdicts (KEEP / DEFER / SKIP) with evidence + licences

Mirrors the spec.md §10 table (plus the extra alternatives-considered rows below the primary verdicts —
TTMR++, MuQ-MuLan, MuLan, M2D-CLAP — which live only here); here with the evidence behind each verdict.

| Component | Verdict | Licence | Evidence / rationale |
|-----------|---------|---------|----------------------|
| **LAION-CLAP — music-tuned** (`laion/larger_clap_music`, HF `ClapModel`) | KEEP (primary embedding) | Apache-2.0 | The adopted primary: a MUSIC-TUNED LAION-CLAP checkpoint with BOTH an audio and a TEXT tower in a shared space, permissive licence, small enough (~150–190M family / exact count UNVERIFIED / 512-dim) to run on CPU. SAME `transformers.ClapModel` API as the general checkpoint (zero pipeline change) — a strict drop-in music-quality bump. The text tower is non-negotiable for vibe/disco queries (§2.2). |
| **LAION-CLAP — general** (`laion/clap-htsat-unfused`, HF `ClapModel`) | KEEP (optional non-music fallback) | Apache-2.0 | The former primary, demoted to an OPTIONAL non-music (speech / SFX / ambience) fallback channel only; the music-tuned checkpoint is primary for all music retrieval (§2.2). |
| **CLaMP 3** (`sander-wood/clamp3`) | DEFER (upgrade tier) | MIT | Higher-quality multilingual music-text model: literally "MERT + a text tower" (frozen MERT-95M audio encoder + XLM-R text tower in a shared space); real text→audio in ~100 languages; SOTA vs general CLAP (Song Describer MRR 0.198 vs 0.131). Cost: a two-stage MERT-extraction pipeline → 8GB GPU sidecar; total param count + official CPU support UNVERIFIED (verify at adoption). The quality upgrade once the CPU `larger_clap_music` baseline ships; subsumes standalone MERT (which it contains) (§2.2). |
| **NumPy brute-force cosine** | KEEP (primary retrieval) | BSD-3 | Exact KNN, recall 1.0, ~1–5 ms at our scale (§4); already a transitive dep via librosa. |
| **sqlite-vec (`VectorSeam`)** | KEEP (alt store) | Apache-2.0/MIT | In-`brain.db` vec0; honours the MEMORY-031 no-external-service seam; the migration target if brute-force is ever outgrown. |
| **MGPHot-style taxonomy** | KEEP (card schema) | CC-BY-4.0 | Adopted as a DATA SCHEMA only (attribution-compatible); values hydrated from our data (§2.6). |
| **MERT (standalone)** | SKIP — REDUNDANT | CC-BY-NC-4.0 (licence-clear — non-commercial) | Strong self-supervised music audio repr, and the non-commercial posture clears its licence — but licence is no longer the gate; REDUNDANCY is. A music dual-tower (`larger_clap_music` now / CLaMP 3 later) subsumes MERT's audio→audio role, AND CLaMP 3 already CONTAINS a frozen MERT-95M encoder, so a separate standalone MERT embedding channel adds a second model for no unique capability. [SUPERSEDES the 2026-07-01 KEEP-optional-Phase-3-channel classification: the licence clearance stands, but the redundancy verdict now controls (§2.2).] |
| **Local heavy captioner LLM** (LLARK / MU-LLaMA) | SKIP | model-dependent | A local audio-captioning LLM to WRITE sonic descriptions is a FALSE ECONOMY: Claude at PLANNING cadence (REQ-RK-006) writes grounded cards from evidence far more cheaply, and identity enrichment (AcoustID / MusicBrainz / Discogs) fixes IDENTITY, not sonic DESCRIPTION (the embeddings carry that). Reinforces the MERT SKIP; a heavy local audio model earns no unique capability here (§2.5, NFR-SR-10). |
| **EnCodec** | SKIP as primary | MIT weights | Best in the 2606 paper — but on a non-text sequential-rec task; NO text tower, so it cannot serve vibe/disco. Not primary. |
| **Essentia** | OPTIONAL / isolated worker | AGPL-3.0 | Rich tags, but breaks on Python 3.12 (brain runtime) and is viral-AGPL. Allowed only in an isolated Py3.10/3.11 worker (REQ-JP-002); never linked into the brain. |
| **musicnn** | OPTIONAL | ISC | Content-tag model; permissive; pairs with the isolated worker; off by default. |
| **TalkPlay / Text2Tracks MODELS** | SKIP (borrow pattern) | unreleased | The retrieve-then-LLM-select PATTERN is adopted; the weights are unreleased, so the models themselves are unusable. |
| **FAISS / hnswlib** | SKIP | MIT/BSD | ANN indexes solve a scale we don't have; brute-force wins at ≤ tens of thousands. |
| **pgvector / Qdrant** | SKIP | PostgreSQL / Apache-2.0 | Standing external services — violate brain-only / no-standing-service (NFR-SR-1). |
| **bliss-rs** | SKIP (library) — IDEA borrowed | GPL-3.0 | Viral copyleft + no text tower + redundant with our librosa DSP, so the LIBRARY is SKIP. Its Mahalanobis-distance (learned/weighted metric) IDEA is borrowed and mapped onto our taste layer as the optional feedback-weighted `related_fn` (REQ-RK-007, §2.8) — the idea, not the GPL code. |
| **JAM projection layer** | DEFER (Phase 3) | (hcai-mms/jam) | Lightweight LLM-free NL retrieval; a good optimisation, but CLAP KNN + LLM re-rank covers the need first. Off by default. |
| **TTMR++** (`seungheondoh/ttmr-pp`) | OPTIONAL (lightweight music-text alt) | CC-BY-NC-4.0 | Small / CPU-friendly music-text model, 128-dim, reported to beat general CLAP on a MusicCaps remake. Licence-permitted (non-commercial). A lightweight alternative to the primary CLAP text tower if a smaller footprint is wanted; off by default, gated on measured value. |
| **MuQ-MuLan** (`OpenMuQ/MuQ-MuLan-large`) | SKIP (too heavy for live) | CC-BY-NC-4.0 | Music-native audio-text model, but ~700M params and GPU-only / heavy — too costly for the CPU-only live brain path. Licence would be permitted (non-commercial), but the weight/latency profile rules it out. |
| **MuLan** (Google) | SKIP (closed) | closed / unreleased | The original audio-text joint-embedding model; weights are not publicly released, so it is not usable. Ruled out. |
| **M2D-CLAP** | SKIP (licence UNVERIFIED) | UNVERIFIED | A masked-modeling CLAP variant; noted as an alternative, but its licence was not verified in this pass — do not adopt until the licence is confirmed. |

Licence note: with the station a NON-COMMERCIAL personal project (NFR-SR-8, amended 2026-07-01 / swept
2026-07-02), CC-BY-NC / CC-BY-NC-SA is ACCEPTABLE for optional / upgrade tiers (TTMR++, MuQ-MuLan, Essentia's
MTG models), so licence is no longer the reason those are non-primary — engineering + measured value are.
The primary path stays permissive anyway (`larger_clap_music` Apache-2.0, the CLaMP 3 upgrade tier MIT, NumPy
BSD, sqlite-vec). The one load-bearing HARD gate is that NO GPL / AGPL is linked into the brain PROCESS:
copyleft obligations (Essentia AGPL-3.0, bliss-rs GPL-3.0) trigger on DISTRIBUTION / network-provision, not on
non-commercial use, so they are low-risk for this non-distributed self-hosted server — but Essentia is still
quarantined to a separate Py3.10/3.11 process on ENGINEERING (cp312 wheel gap) grounds, so its AGPL never
touches the brain regardless.

---

## 4. Infra-sizing math (why no vector service)

- Per-track embedding: 512 dims × 4 bytes (f32) = 2,048 bytes ≈ 2 KB.
- At 50,000 tracks: 50,000 × 2 KB ≈ 100 MB — fits in RAM as a single NumPy matrix, or as SQLite BLOBs loaded
  once and cached.
- Brute-force cosine: one matrix-vector product (query · matrixᵀ) over 50k×512 is a few million FLOPs — on the
  order of 1–5 ms on a modern CPU with NumPy/BLAS, exact (recall 1.0), no index build.
- Comparison: FAISS/hnswlib exist to make KNN sublinear at MILLIONS of vectors; at 10⁴–10⁵ the linear scan is
  already sub-10-ms, so the index adds build cost + a dependency for no runtime win. Qdrant/pgvector add a
  standing service + network hop + ops burden — a direct NFR-SR-1 violation.
- Conclusion: NumPy brute-force over SQLite BLOBs is the correct primary; sqlite-vec (`VectorSeam`) is the
  in-process upgrade path if the catalog ever grows past this regime. No external vector store is justified.

---

## 5. Verified seam map (what this analysis confirmed by reading the code)

Every entry below was read and confirmed in this pass; these are the `file:line` anchors the Delta map cites.

| Seam | Location | Confirmed state | SONICRECO use |
|------|----------|-----------------|---------------|
| `Track.embedding_ref` | `brain/library.py:119` | Reserved, `""`, unused | Embedding slot (or BLOB sidecar) |
| `Track.sonic_description` | `brain/library.py:118` | Reserved, `""`, "DEFERRED" | Grounded one-line summary |
| `_ANALYSIS_WRITABLE_FIELDS` | `brain/library.py:216` | Auto-computed; both reserved fields writable | Allowlist write of embedding + summary |
| `Library.set_analysis` | `brain/library.py:695` | Allowlist writer, brief-lock, persists | Idempotent embedding/summary backfill |
| `legal_candidates` / `pick_next` | `brain/library.py:606` / `:636` | LRP head; HARD rail; unchanged OFF-path | Candidate source; untouched hot path |
| `analyzer._analyze_one` | `brain/analyzer.py:184` | cache→DSP→enrich→set_analysis, off-lock | Additive embed step insertion point |
| `analysis.analyze_file` | `brain/analysis.py:94` | librosa, swappable, never-raise | Sibling (not folded) — kept torch-free |
| `VectorSeam` | `brain/memory.py:299` | Stub; raises `NotImplementedError`; off-default | Implement sqlite-vec / brute-force KNN |
| `taste.diversity_rerank` / `related_fn` | `brain/taste.py:711` / `:720` | MMR re-rank; pluggable related hook | Embedding-KNN related_fn |
| `profile.relevance` | `brain/taste.py:464` | Token/weight; never popularity | Add optional vector-relevance term |
| taste play/skip signals | `brain/taste.py:490`–`519` | Bounded curatorial nudges | Non-binding re-rank feedback |
| `director._diversity_rerank` / curate call | `brain/director.py:295` / `:328` | Best-effort re-rank; acquisition curate | Grounded re-rank + ID firewall |
| `llm.curate_batch` / `SEED_TRACKS` | `brain/llm.py:287` / `:56` | Subprocess seam; never-raise; seed fallback | Constrained-ID prompt + reject |
| `SelectionRefiner.refine` | `brain/schedule.py:582` | Soft re-score behind `scheduling_enabled` | Playout-side grounded re-rank |
| `server._pick_refined` | `brain/server.py:305` (`:246`) | Byte-identical OFF-path | Unchanged |
| `metadata.enrich` | `brain/metadata.py:122` | genre/mood/tags/year + MBID; never-raise | Sonic-card metadata source |
| `like.AffinityStore` | `brain/like.py` (events.db) | Like/skip store | Non-binding re-rank feedback |
| `config.scheduling_enabled` | `brain/config.py:586` | Default OFF | Gates the playout re-rank layer |

Environment confirmations: NumPy 2.2.6 is present in the environment; torch/Kokoro are installed in a
DEDICATED CPU-torch Dockerfile step (`requirements.txt` comments, lines ~10–22) separate from the numpy/librosa
resolver — the CLAP `transformers` install rides that same step, avoiding the numba/numpy pin conflict. The
brain SQLite partitions are `brain.db` / `events.db` / `knowledge.db` / `state.db` under `DB_DIR` (`config.py`).

---

## 6. Sources (12) and citation-verification notes

The dossier comprises twelve sources. Citation strings are recorded AS PROVIDED by the operator's research
dossier. Several arXiv IDs / DOIs are post- the assistant's knowledge cutoff and were NOT independently
web-verified in this pass; they MUST be link-verified before any external publication. The CLAP library claim
WAS partially verified (the HF `transformers` library and its `ClapModel` exist; see note).

1. **Internal feasibility brief** (operator-authored) — the brain-only / CPU-only / brute-force framing and
   the seam inventory. (Primary driver of §1, §4, §5.)
2. **TalkPlay** — arXiv:2502.13713 — retrieval-augmented / retrieve-then-generate music recommendation;
   source of the "ground it, select from a set" pattern (§2.1).
3. **TalkPlay-Tools** — the tool-augmented companion to TalkPlay; reinforces constrained tool/catalog
   selection over free generation (§2.1).
4. **"Multimodal Music Recommendation using LLMs"** — arXiv:2606.00125 — the EnCodec-best-on-seq-rec finding
   AND the FiLM query-conditioning finding (§2.2, §2.4). NOTE: arXiv ID is post-cutoff; verify.
5. **MMMR dataset** — Zenodo DOI 10.5281/zenodo.20431748 (CC-BY-4.0) — external evaluation set (§2.7,
   NFR-SR-9). NOTE: DOI post-cutoff; verify.
6. **JAM** — arXiv:2507.15826 (RecSys'25) — CrossMixing query-conditioned fusion; retrieval-scale discussion;
   `github.com/hcai-mms/jam` (§2.3, §2.4, Group JP). NOTE: arXiv ID post-cutoff; verify.
7. **Deezer / JKU survey** — arXiv:2511.16478 — LLMs for music recommendation survey; the hallucination /
   ground-the-catalog caution (§2.1, §2.5). NOTE: arXiv ID post-cutoff; verify.
8. **EmergentMind LLM-music-rec survey** — corroborates the retrieve-then-rerank and evaluation-caveat
   consensus (§2.5, §2.7).
9. **bliss-rs** — the Rust audio-similarity library — cited as a SKIP data point (GPL-3.0, no text tower,
   redundant with our DSP) (§3).
10. **LAION-CLAP** — the adopted embedding; HF `transformers` `ClapModel`. PRIMARY checkpoint the
    music-tuned `laion/larger_clap_music` (general `laion/clap-htsat-unfused` demoted to a non-music
    fallback), Apache-2.0. Partially verified: the `transformers` library and CLAP support were confirmed via
    Context7 (`/huggingface/transformers`); the 512-dim projection + text/audio
    `get_text_features`/`get_audio_features` API are well-established. UNVERIFIED and to re-confirm at pin
    time against the chosen checkpoint's model card: the exact param count (~150–190M family) and that
    `larger_clap_music` is a strict drop-in for the same `ClapModel` API. The CLaMP 3 upgrade tier
    (`sander-wood/clamp3`, MIT — MERT-95M + XLM-R text tower, ~100-language text→audio, SOTA vs general CLAP)
    and the alternatives TTMR++ / MuQ-MuLan / MuLan / M2D-CLAP (§3) are recorded but not adopted for the CPU
    baseline; their param counts / CPU support / licences are to be verified at adoption.
11. **MGPHot taxonomy** — the 58-attribute / 7-category music-attribute taxonomy (CC-BY-4.0) adopted as the
    sonic-card schema (§2.6). NOTE: verify the canonical source + licence at adoption.
12. **Misc surveys / infra notes** — the vector-search sizing consensus (brute-force vs FAISS/pgvector/Qdrant)
    and the CPU-embedding feasibility notes underpinning §4 and REQ-VE-003.

[HARD] Anti-hallucination posture (consistent with the SPEC's own grounding ethic): the four post-cutoff
arXiv IDs and the Zenodo DOI above are transcribed as supplied and are NOT asserted as verified. Before the
Run phase or any external citation, each URL/DOI MUST be fetched and confirmed; if a source does not resolve,
the finding it backs is downgraded to "unverified" and the corresponding requirement's rationale is re-checked.
The engineering rails (brain-only, CPU-only, the ID firewall, brute-force sizing, the verified seam map) stand
on §1/§4/§5, which are grounded in the actual code and do not depend on the external citations.

---

## 7. Evaluation methodology (for the Run phase)

- **First gate — grounding accuracy.** Out-of-set-ID rate over a large synthetic + live sample must be 0
  (NFR-SR-4/9). This is a hard, cheap, deterministic test and is the ONLY metric trusted unconditionally.
- **Retrieval sanity.** Spot-check audio→audio neighbours on a labelled cluster (same artist / same obvious
  genre should dominate top-K); confirm text→audio returns plausible vibe matches on a handful of curated
  queries before trusting it at scale (R-SR-2).
- **Re-rank quality.** Use MMMR / JAMSessions as EXTERNAL offline harnesses (not the live library). Any
  LLM-as-judge is calibrated against a small human-rated set first; n-gram/ranking metrics are treated as
  weak proxies only (§2.7).
- **Ops.** Measure per-track CPU embedding time to size the one-time batch; confirm the brute-force KNN
  latency budget (target low-single-digit ms) on the real embedding count (R-SR-3).
- **Regression.** Assert the OFF-path (`pick_next` / `_pick_refined` / `/api/next`) is byte-identical with the
  engine disabled (NFR-SR-3), and that every component fault degrades to today's deterministic result
  (NFR-SR-7).

---

## 8. Open research questions (carried into spec.md §14)

- Grounded DISCOVERY vs grounded PLAYOUT: can a later phase embed an external candidate pool (slskd search
  results) so acquisition discovery is retrieval-grounded, not just verification-grounded? (R-SR-1)
- CLAP fit on the station's genre mix (incl. Faroese-language, niche electronic) — measure before trusting
  text→audio at scale. (R-SR-2)
- CPU embedding throughput / batch schedule sizing. (R-SR-3)
- A human-rated calibration set for any LLM-as-judge. (R-SR-4)
- Sequence the name-query router after the REQUEST-011 matcher ships. (R-SR-6)
- A CI licence check to keep AGPL/GPL out of the brain process. (R-SR-7)
