# 02_ai_models_and_inference — Distributed Inference, RPC Sharding & GGUF Vault

## Scope & Hardware Allocation
Orchestrates distributed inference across the **82.8 GB Pooled VRAM** mesh.

## Inference Engines & Protocols
1. **llama.cpp RPC Sharding:** Bare-metal Metal Performance Shader (MPS) and Vulkan/CPU tensor distribution over 10Gbps Thunderbolt 4 and gigabit LAN (Port `50052`).
2. **Petals Decentralized DHT:** Fault-tolerant multi-WAN pipeline parallel sharding across edge devices (Pixel 10, Samsung S20, Linux Tablet).
3. **Exo Cluster:** Dynamic peer-to-peer AI layer splitting.
4. **Adaptive AI Sharding Router:** Dynamically benchmarks network latency and routes tensor computation over the fastest available interface (Thunderbolt > LAN > Wi-Fi Direct > Tailscale).

## Model Weight Vault Standards
- Strict Quantization Standard: `Q4_K_M`, `IQ3_M`, `IQ2_XXS`. Never `Q8_0` for models >= 32B.
- Flagship Ingestion Policy: Ingest newest frontier checkpoints (`DeepSeek-R1-32B/70B`, `Qwen 3.8 VL Max`, `Llama 4`, `Gemma 4`).


---
## 🤖 Assigned Subsystem Specialist AI
- **Specialist Agent:** `spec-02-ai-inference-mesh`
- **Assigned Model Tier:** `DeepSeek-R1-32B / Llama-3.3-70B`
- **Skill Definition:** `05_agents_and_swarms/antigravity_skills/spec-02-ai-inference-mesh/SKILL.md`
- **Governance Mandate:** Continuous recursive optimization of this subsystem's documentation, contracts, and test integrity.
