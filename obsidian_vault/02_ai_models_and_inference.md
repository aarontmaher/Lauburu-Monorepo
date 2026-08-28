---
title: "02_ai_models_and_inference — Distributed Inference, RPC Sharding & GGUF Vault"
updated: "2026-08-27"
tags: [ai, inference, llamacpp, rpc_sharding, petals, exo, gguf, spec-02]
---

# 02_ai_models_and_inference — Distributed Inference, RPC Sharding & GGUF Vault

## 📋 Scope & Hardware Allocation
Orchestrates distributed inference and model layer sharding across the **82.8 GB Pooled VRAM** mesh (108.0 GB Physical RAM across 7 devices), achieving 100% local self-sufficiency and $0 recurring cloud spend.

## 🧠 Distributed Inference Engines & Protocols
1. **llama.cpp RPC Distributed Tensor Sharding (Ports 8081–8084):**
   - Shards large frontier models (e.g. Qwen 2.5 Coder 32B `Q4_K_M`, DeepSeek R1 32B `IQ2_XXS`) across Apple Silicon Metal Performance Shaders (MPS) via Thunderbolt 4 (0.277ms RTT).
2. **Petals Distributed DHT Swarm:**
   - Heterogeneous layer swarming across Linux and mobile nodes using Kademlia DHT routing for fault-tolerant block execution.
3. **Exo Peer-to-Peer Model Sharding:**
   - Dynamic decentralized model sharding with ring-topology pipeline parallelism.
4. **GGUF Vault & Model Quantization Manifests:**
   - Automated quantization pipelines and weight distribution manifests across local NVMe storage.

## 🤖 Assigned Subsystem Specialist AI
- **Specialist Agent:** `spec-02-ai-inference-mesh`
- **Focus Areas:** GGML tensor kernels, llama.cpp RPC orchestration, Petals DHT routing, Exo pipeline sharding.

## 🔗 Knowledge Graph Connections
- **Master Index:** [[Index]]
- **Hardware Pooling:** [[7_DEVICE_MESH_AND_VRAM_POOL]]
- **Specifications:** [[CUSTOM_AI_SHARDING_DAEMON_PETALS_DHT_SPEC]], [[TERMIUS_TUI_UNIFIED_AI_SHARDING_SPEC]]
- **Connected Modules:** [[05_agents_and_swarms]], [[12_continuous_lora_evolution]]
