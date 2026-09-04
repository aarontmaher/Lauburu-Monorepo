# 02_ai_models_and_inference — Distributed Inference, RPC Sharding & GGUF Vault

## Scope & Hardware Allocation
Orchestrates distributed inference across the **82.8 GB Pooled VRAM** mesh.

## Inference Engines & Protocols (Canonical Hierarchy)
1. **PRIMARY ENGINE: `prima.cpp` (Port `:8082`):** Canonical primary master across all devices that contain the model weights (Mac Mini M4 Pro, MacBook Pro, Linux Head Node). Pipelined-Ring Parallelism over 10Gbps TB4 DMA bridge delivering maximum token throughput.
2. **RESILIENT FALLBACK: `llama.cpp` (Port `:8083`):** Strictly used as an automatic fallback ONLY if an edge device lacks the local model weights or hardware topology to run `prima.cpp` properly.
3. **Petals Decentralized DHT:** Fault-tolerant multi-WAN pipeline parallel sharding across edge devices (Pixel 10, Samsung S20, Linux Tablet).
4. **Exo Cluster:** Dynamic peer-to-peer AI layer splitting.
5. **Adaptive AI Sharding Router:** Dynamically benchmarks network latency and routes tensor computation over the fastest available interface (Thunderbolt > LAN > Wi-Fi Direct > Tailscale).

## Model Weight Vault Standards & Pinned Roles
- **Master Local Orchestrator:** `Qwen3-30B-A3B (MoE)` pinned on Port `:8081`. The MoE router natively allocates specialized FFNN experts for visual parsing (when acting as the Lauburu Lens Supervisor).
- **Master Function Caller & Actuator:** `Nous Hermes 3 (Llama 3.1 8B/70B)`. Pinned specifically for strict JSON/tool calling. Hermes acts as the "Brain stem" for OpenClaw Android automation.
- **Pinned Devil's Advocate:** **`Qwen 3.8 Max 27B Abliterated`** (`Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf`) pinned on Port `:8083`.
- Strict Quantization Standard: `Q4_K_M`, `IQ3_M`, `IQ2_XXS`. Never `Q8_0` for models >= 32B.
- Flagship Ingestion Policy: Ingest newest frontier checkpoints (`DeepSeek-R1-32B/70B`, `Qwen 3.8 Max`, `Llama 4`, `Gemma 4`).

## Lauburu Lens & OpenClaw Integration Architecture
1. **The Eye (Lauburu Lens Supervisor):** Utilizing Qwen-VL-MoE architectures. The neural router automatically clusters spatial bounding-box tokens to dedicated visual experts.
2. **The Hand (OpenClaw Actuator):** Executes physical UI inputs via ADB/Termux directly on the Samsung S20 (Layer 7). 
3. **The Brain Stem (Hermes 3):** Translates the visual critiques from Qwen MoE into precise, structured JSON tool calls that trigger OpenClaw actions.

---
## 🤖 Assigned Subsystem Specialist AI
- **Specialist Agent:** `spec-02-ai-inference-mesh`
- **Assigned Model Tier:** `DeepSeek-R1-32B / Llama-3.3-70B`
- **Skill Definition:** `05_agents_and_swarms/antigravity_skills/spec-02-ai-inference-mesh/SKILL.md`
- **Governance Mandate:** Continuous recursive optimization of this subsystem's documentation, contracts, and test integrity.
