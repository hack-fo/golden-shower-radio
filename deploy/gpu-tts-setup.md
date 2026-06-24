# GPU TTS Setup — Qwen3-TTS + Chatterbox on the RTX 2000 Ada (8 GB)

Prep for VOICE-002 Phase 1.5: add Qwen-TTS + Chatterbox as local GPU TTS providers + an A/B harness.
The brain image is deliberately CPU-only-torch; these run in a SEPARATE GPU `tts` sidecar so the brain
stays lean. Engine choice is verified to fit 8 GB (see Sources at bottom).

## Verified engine fit (8 GB Ada 2000)
- **Qwen3-TTS 0.6B** (24 kHz). The 0.6B (NOT the 1.7B) is the 8 GB fit; ~real-time (RTF 0.85–1.15);
  FlashAttention-2 recommended (−20–25% VRAM, +30–40% speed).
- **Chatterbox-Turbo** (350M, 22.05 kHz, ~4.5 GB during generation) — comfortable on 8 GB; voice-clone +
  emotion. `pip install chatterbox-tts`; self-host server option: `devnen/Chatterbox-TTS-Server`.
- Run ONE engine at a time for the A/B (no co-residency needed; both fit individually).
- Kokoro (current primary) stays the baseline of the A/B; Piper stays the CPU fallback.

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
