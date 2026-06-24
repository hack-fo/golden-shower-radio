# GPU TTS Setup — Qwen3-TTS + Chatterbox on the RTX 2000 Ada (8 GB)

Prep for VOICE-002 Phase 1.5: add Qwen-TTS + Chatterbox as local GPU TTS providers + an A/B harness.
The brain image is deliberately CPU-only-torch; these run in a SEPARATE GPU `tts` sidecar so the brain
stays lean. Engine choice is verified to fit 8 GB (see Sources at bottom).

## Verified engine fit (8 GB Ada 2000)
- **Qwen3-TTS 0.6B** (24 kHz). The 0.6B (NOT the 1.7B) is the 8 GB fit; ~real-time (RTF 0.85–1.15);
  FlashAttention-2 recommended (−20–25% VRAM, +30–40% speed).
- **Chatterbox-Turbo** (350M, 22.05 kHz, ~4.5 GB during generation) — comfortable on 8 GB; voice-clone +
  emotion. `pip install chatterbox-tts`; self-host server option: `devnen/Chatterbox-TTS-Server`.
- **Voxtral-TTS 4B** (Mistral, open-weights, released 2026-03-26; multilingual incl. English; zero/few-shot
  voice cloning from ~3 s reference audio; streaming, ~70 ms latency). 8 GB CAVEAT: full bf16 (~8 GB weights)
  is too tight with activations → run **fp8 or int8** (the Ada natively supports fp8); quantized ~4 GB fits
  comfortably. Resolve the exact TTS repo id from the mistralai/voxtral HF collection. A 4th A/B candidate.
- Run ONE engine at a time for the A/B (no co-residency needed; both fit individually).
- Kokoro (current primary) stays the baseline of the A/B; Piper stays the CPU fallback.
- **OmniVoice** (k2-fsa, Apache-2.0, ~3.27 GB) — diffusion-LM zero-shot TTS, **600+ languages (incl. Faroese)**,
  VOICE DESIGN by attributes (gender/age/pitch/accent — maps directly to the persona model) + voice cloning,
  RTF 0.025. Strong persona fit.

**FINAL LOCKED SET (user, 2026-06-24) — all on `/mnt/f/gsr-models/`; the VOICE-002 harness A/Bs these:**
Kokoro (baseline, in image) · `Voxtral-TTS-2603` · `Qwen3-TTS-12Hz-*` (0.6B Base+CustomVoice; 1.7B
Base+VoiceDesign+CustomVoice) · `OmniVoice` · `chatterbox-turbo`. MOSS-TTS evaluated + SKIPPED (flagship 17 GB /
GGUF 68 GB / TTSD 16.7 GB too large for F:; MOSS-TTS-Local-Transformer ~6 GB a future option). No more engines —
next is the VOICE-002 A/B harness + the listen test.

## Model storage — F: (/mnt/f, writable) [user-directed 2026-06-24]
**DOWNLOADED already (2026-06-24):** Voxtral-TTS-2603 is on F: at `/mnt/f/gsr-models/Voxtral-TTS-2603`
(7.5 GB `consolidated.safetensors` + `tekken.json` + `params.json` + `voice_embedding/`; Mistral native
format — load via mistral-inference/vLLM, NOT HF transformers config). The VOICE-002 build must use this
local copy, not re-download. Qwen3-TTS-0.6B + Chatterbox-Turbo still to pull to the same dir (~30 GB free).

Store ALL engine weights (Voxtral-TTS-4B, Qwen3-TTS-0.6B, Chatterbox-Turbo) on F: to keep the ext4 home
lean. Download target `/mnt/f/gsr-models`, mounted into the tts sidecar as the model-cache volume
(`HF_HOME=/mnt/f/gsr-models/hf`). CAVEAT: F: is an NTFS Windows mount; the HF hub cache uses blob<->snapshot
SYMLINKS that NTFS-via-WSL doesn't support → set `HF_HUB_DISABLE_SYMLINKS=1` (HF stores plain copies, a bit
more space) or `snapshot_download` into a flat dir. ~37 GB free covers all three (~4 + 1.5 + 1 GB).

## A. Host / deploy-box prerequisites — VERIFIED DONE (2026-06-24)
All host-side GPU plumbing is already in place and tested in-container:
- NVIDIA driver 595.59, CUDA 13.2; GPU = NVIDIA RTX 2000 Ada Generation (Laptop), 8188 MiB / ~8.59 GB.
- `nvidia-container-toolkit` 1.19.1 installed; Docker 29.1.3 with the `nvidia` runtime + `cdi:
  nvidia.com/gpu=all` registered.
- `docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi` → shows the Ada (PASS).
- `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime` image already pulled locally → `torch.cuda.is_available()
  == True`, device "RTX 2000 Ada", 8.59 GB. Use it as the Dockerfile.tts base (CUDA torch already present).
- Remaining operator task: a model-cache volume so Qwen/Chatterbox weights persist across rebuilds (trivial).

## B. What gets built (VOICE-002 Phase 1.5)
1. **`deploy/Dockerfile.tts`** — CUDA base image + CUDA torch + `chatterbox-tts` + qwen3-tts (0.6B) +
   flash-attn; a thin HTTP synth server (POST text+voice -> WAV), or reuse devnen Chatterbox server +
   a Qwen wrapper.
2. **`deploy/docker-compose.yml`** — a `tts` service with GPU passthrough:
   `deploy: resources: reservations: devices: [{driver: nvidia, count: 1, capabilities: [gpu]}]`
   (or `gpus: all`). Model-cache volume. Brain depends on it only when a GPU provider is selected.
3. **Providers in `brain/voice.py`** — `QwenProvider` + `ChatterboxProvider` (HTTP clients to the tts
   service) behind the existing `TTSProvider` interface, each with a VOICE-002 capability descriptor
   (REQ-V-A-009: native sample rate 24/22.05 kHz, chunk size, inter-chunk silence, seed support, optional
   `validate()` ASR hook). Selected via `BRAIN_TTS_PROVIDER=qwen|chatterbox|kokoro|piper`. Default stays
   Kokoro until the A/B picks a winner — the pluggable seam means the winner swaps in with zero changes to
   personas/talk/minting.
4. **A/B harness** (`scripts/tts-ab.sh` or `brain/tts_ab.py`) — renders identical sample scripts through
   Kokoro / Qwen3-TTS-0.6B / Chatterbox-Turbo into labelled WAVs in one folder for the operator to listen
   and pick the primary (naturalness is a human judgment). Reports per-engine RTF (speed) too.

## C. The decision (user-in-the-loop)
After B, the operator: runs the harness, listens, picks the primary by ear (Qwen is the frontrunner lean;
confirm on the real GPU — don't bank pre-test). Sets `BRAIN_TTS_PROVIDER` to the winner. Voice-palette
expansion (more distinct voices = more personas) follows separately.

## Sources (verified 2026-06-24)
- Qwen3-TTS hardware/VRAM (0.6B vs 1.7B, 8 GB tier, FlashAttention-2): qwen3-tts.app hardware guide;
  Medium "High-Quality Long-Form TTS with Qwen3 Open-Weight Models".
- Chatterbox VRAM/install/Turbo (~4.5 GB, pip install chatterbox-tts, self-host server): devnen/
  Chatterbox-TTS-Server (GitHub); dev.to "How to Install and Run Chatterbox Locally".

Relates to [[voice-tts-ab]], [[gpu-hardware]], and .moai/planning/full-spec-completion-roadmap.md (Phase 1.5).
