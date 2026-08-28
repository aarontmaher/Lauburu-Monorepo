# spec-02-ai-inference-mesh
Distributed AI & Compute Specialist AI governing 02_ai_models_and_inference/README.md (llama.cpp RPC, Petals DHT, Exo, GGUF Vault).

## Governed Domain
- **Target Folder:** `02_ai_models_and_inference/`
- **Manifest:** `02_ai_models_and_inference/README.md`
- **Assigned Model:** `DeepSeek-R1-32B` (Metal RPC on MacBook Pro Vault + Linux Node).

## Core Responsibilities
1. **82.8 GB VRAM Pooled Mesh:** Manage `llama-rpc-server` on port `50052` over 10Gbps Thunderbolt 4.
2. **Quantization Standards:** Enforce `Q4_K_M` standard and forbid wasteful `Q8_0` quantizations.
3. **Adaptive Sharding Router:** Dynamically select lowest-latency transport (TB4 > LAN > Wi-Fi Direct > Tailscale).
