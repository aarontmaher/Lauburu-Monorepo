# 🎙️ PersonaPlex 7B v1 Full-Duplex Speech-to-Speech Architecture

## 1. Executive Summary
PersonaPlex 7B v1 is NVIDIA's open, full-duplex speech-to-speech conversational AI model based on Kyutai's Moshi architecture. It delivers real-time bidirectional audio streaming, natural conversational turn-taking, and customizable voice conditioning through 16 distinct voice prompts.

Within the Lauburu ecosystem, PersonaPlex provides the native conversational voice interface for the sovereign Screen Lens companion, TUI ecosystem, and multimodal agent swarms.

---

## 2. Model & Weight Topology

| Component | Repository / File | Size | Verified Hash / Snapshot |
|:--|:--|:--|:--|
| **Architecture** | `nvidia/personaplex-7b-v1` | — | `fdaf4090a61cb315c138a1faee287ffd6c716309` |
| **Model Safetensors** | `model.safetensors` | 16 GB | `4ed92973099ef939eb8991e63d1c6df5ae16c3139e48a9af7ff7623dcff4af30` |
| **Mimi Codec / Tokenizer** | `tokenizer-e351c8d8-checkpoint125.safetensors` | 367 MB | `f048bb447ef13dca10419d146db76e4efbe2f62776aa8c0a969f6e6ecdb35f11` |
| **Text Tokenizer** | `tokenizer_spm_32k_3.model` | 540 KB | `f2d5904efcb6443c683b58be42ab67c29377be8aa76eb1516e885ee8d9ceeb07` |
| **Voice Prompts** | `voices/` (`NATF0-3`, `NATM0-3`, `VARF0-4`, `VARM0-4`) | 16 files | Verified on disk |
| **Web UI Distribution** | `dist/` (HTML/JS/WASM audio decoders) | 2.1 MB | Verified on disk |

---

## 3. Dynamic Hardware Placement & Rule Compliance

### Rule 3 & Rule 10 Alignment (M4 Host Sanctuary)
- PersonaPlex 7B requires $\approx 16\text{ GB}$ of RAM/VRAM during active execution.
- Running PersonaPlex locally on the Mac Mini M4 Pro (24 GB RAM) concurrently with `llama-server` (6.9 GB RSS) would breach the **$\ge 4.8\text{ GB}$ host free RAM sanctuary** and trigger memory pressure.
- **Primary Execution Tier (Edge Offload):** PersonaPlex 7B runs natively on the **Pixel 10 Pro XL (Tensor G5, 16 GB RAM)**:
  - HTTPS / Web UI: `https://100.114.215.68:8998`
  - Full-Duplex S2S WebSocket: `wss://100.114.215.68:8998/api/chat`
  - PID: `23936` (Termux Debian container)
- **Secondary Local Tier (Fallback):** Managed via `02_ai_models_and_inference/personaplex/launch_personaplex.sh`:
  - Utilizes `--cpu-offload` to minimize VRAM footprint when run locally.
  - Weights cached in `~/.cache/huggingface/hub/models--nvidia--personaplex-7b-v1/`.

---

## 4. Client Integration

The monorepo connects to PersonaPlex via `01_apps/canonical_port/tui/services/personaplex_s2s_client.py`:
- **Dual-Plane Protocol:**
  - **Opcode 0x01 (JSON):** Session handshake, voice prompt selection (`text_prompt`, `voice_prompt`), text transcription streaming.
  - **Opcode 0x02 (Binary):** Raw PCM audio chunks (24 kHz / 16-bit mono) streamed bidirectionally with sub-200ms latency.
- **Barge-in Interruption:** Live VAD signals interrupt audio synthesis instantaneously.

---

## 5. Verification & Health Check

```bash
# Test connection to live PersonaPlex on Pixel 10
/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/personaplex/launch_personaplex.sh auto

# Direct HTTPS probe
curl -k -s -I https://100.114.215.68:8998/
```
