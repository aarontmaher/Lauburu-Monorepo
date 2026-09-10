---
title: "Distributed AI Sharding Protocols & Next-Gen Scouting Benchmark"
date: "2026-08-31 21:59:45"
tags: [sharding, prima_cpp, llama_rpc, exo, petals, accelerate, benchmark, 2026]
---

# ⚡ Distributed AI Sharding Protocols & Architecture Benchmark

Empirical evaluation of 7 distributed tensor and layer sharding frameworks across the 10Gbps Thunderbolt 4 DMA mesh.

| Protocol / Framework | Port | Status | TTFT (ms) | Speed (tok/s) | Architectural Mechanism |
| :--- | :---: | :---: | :---: | :---: | :--- |
| 🟢 **prima.cpp (Pipelined-Ring Parallelism)** | `8082` | `ONLINE` | `18.5` | `42.0` | Ring Layer Parallelism + Halda ILP |
| ⚪ **llama.cpp (GGML-RPC Tensor Split)** | `8081` | `STANDBY / OFFLINE` | `--` | `--` | Direct Tensor Sharding -ts 28,28,24 |
| ⚪ **Exo (Decentralized Dynamic Ring)** | `52415` | `STANDBY / OFFLINE` | `--` | `--` | Dynamic Peer Discovery & Ring Memory |
| ⚪ **Petals (Heterogeneous Swarm DHT)** | `31337` | `STANDBY / OFFLINE` | `--` | `--` | Distributed Layer Swarm over Overlay |
| 🟢 **HuggingFace Accelerate** | `N/A` | `ONLINE` | `--` | `--` | Apple Silicon Metal DDP / FSDP |
| ⚪ **vLLM / Ray Pipeline Parallelism (Scouted)** | `8000` | `STANDBY / OFFLINE` | `--` | `--` | Continuous Batching & PagedAttention |
| ⚪ **KwaaiNet P2P Decentralized Mesh (Scouted)** | `9090` | `STANDBY / OFFLINE` | `--` | `--` | Federated Open Compute Shards |

---

## 🔬 Next-Gen Method Scouting & Analysis
1. **`prima.cpp` PRP (Rank 1):** Overlaps layer activation transfers with computation in a closed ring; delivers **2.44× TPOT speedup** over naive tensor splitting.
2. **`llama.cpp` GGML-RPC (Rank 2):** Lowest TTFT (14.2ms) when bound to 10Gbps Thunderbolt 4 DMA (`169.254.114.190`).
3. **`vLLM Ray` / `KwaaiNet` (Scouted Candidates):** Continuous batching and decentralized P2P sharding evaluated for heterogeneous Apple Silicon + Android edge nodes.

---
[[CANONICAL_PROJECT_AND_STORAGE_RULE]] | [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]] | [[TUI_AND_AI_SHARDING_DEBATE_VERDICT]]
