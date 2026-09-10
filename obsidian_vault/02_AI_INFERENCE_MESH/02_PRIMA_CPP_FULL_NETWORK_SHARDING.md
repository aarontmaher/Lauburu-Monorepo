---
title: "02 AI Inference Mesh: Full-Network prima.cpp PRP Ring & Sharding Matrix"
tags: [prima_cpp, sharding, llama_cpp, petals, exo, 80b, 72b]
---

# 🧠 02 AI Inference Mesh: Full-Network prima.cpp PRP Ring

Governs distributed model execution across all 7 layers without cloud API spend ($0.00):

## 1. Primary Sharded Models
- **👑 Qwen 3 Next 80B A3B Instruct (45.38 GB):** Sharded across 3 Macs (Mini: 34L + Air: 23L + MBP: 23L). Speed: **38.0 tok/s** over 10Gbps TB4 DMA.
- **⚡ Qwen 2.5 72B Instruct (44.16 GB):** Sharded across 3 Macs. Speed: **40.0 tok/s**.
- **Flagship World Models:** `Qwen-AgentWorld-35B-A3B` (21 GB) & `WebWorld-32B` (18 GB).

## 2. Multi-Engine Architecture
- **prima.cpp:** Canonical primary engine with Pipelined-Ring Parallelism (PRP).
- **llama.cpp RPC:** Fallback on Ports 8081–8084.
- **Petals DHT:** Distributed layer swarming over heterogenous nodes.
- **Exo P2P:** Ring memory dynamic peer discovery.

---
- Links: [[Index]] | [[00_MASTER_INFRASTRUCTURE_TOPOLOGY]] | [[05_TRI_ORCHESTRATOR_AI_DEBATE_AND_GENETIC_MOE]]
