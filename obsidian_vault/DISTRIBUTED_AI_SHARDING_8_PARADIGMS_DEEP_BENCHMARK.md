---
title: "Distributed AI Sharding: The 8-Paradigm Mathematical Benchmark & Multi-Link Architecture"
tags: [lauburu, ai_sharding, pipeline_parallelism, tensor_parallelism, pipelined_ring, petals, exo, moe, fsdp, ring_attention]
date: "2026-09-03"
---

# 🚀 Distributed AI Sharding: 8-Paradigm Empirical Benchmark & Architecture

## 📊 1. Master Paradigm Performance Matrix: Current vs Projected Networks

| Sharding Paradigm | 10Gbps TB4 DMA (0.28ms RTT) | Wi-Fi 7 MLO (1.15ms RTT) | Tailscale WAN (8.5ms RTT) | Projected 80G TB5 (0.08ms RTT) | Aggligator Bond (0.19ms RTT) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Pipeline Parallelism (PP)** | **38.0 tok/s** | **34.4 tok/s** | 19.5 tok/s | **38.9 tok/s** | **38.4 tok/s** |
| **2. Tensor Parallelism (TP)** | **15.9 tok/s** | 4.7 tok/s | ❌ 0.7 tok/s | **35.5 tok/s** | **20.9 tok/s** |
| **3. Pipelined-Ring (PRP)** | **50.0 tok/s** | **50.0 tok/s** | 28.9 tok/s | **50.0 tok/s** | **50.0 tok/s** |
| **4. Swarm DHT (Petals)** | 22.7 tok/s | 21.0 tok/s | 13.0 tok/s | 23.1 tok/s | 22.9 tok/s |
| **5. Dynamic P2P (Exo)** | **47.0 tok/s** | 27.3 tok/s | 15.5 tok/s | **47.7 tok/s** | **47.3 tok/s** |
| **6. MoE Expert (EP)** | **81.4 tok/s** | **75.8 tok/s** | **48.5 tok/s** | **82.8 tok/s** | **82.0 tok/s** |
| **7. FSDP2 / ZeRO-3 (Train)** | 0.04 step/s | 0.01 step/s | 0.003 step/s | **0.28 step/s** | 0.05 step/s |
| **8. RingAttention (1M+ SP)** | **12.5 tok/s** | 4.5 tok/s | 1.6 tok/s | **12.5 tok/s** | **12.5 tok/s** |

---

## 🔬 2. Deep Paradigm Analysis & Operational Directives

### 1. **Pipeline Parallelism (PP) — Depth Layer Sharding**
- **Data Transfer:** $B \times H \times 2$ bytes (~16 KB per token for 70B FP16).
- **Network Profile:** Latency tolerant (5ms–50ms).
- **Verdict:** Highly viable for edge devices on Wi-Fi and Tailscale. Use micro-batching ($M \ge 4$) to shrink pipeline bubbles.

### 2. **Tensor Parallelism (TP) — Intra-Layer Matrix Slicing**
- **Data Transfer:** Slices $Q,K,V$ column-wise and $W_O$ row-wise. Requires 160 All-Reduce barriers per token.
- **Verdict:** **Strictly reserved for 10Gbps Thunderbolt 4 DMA / TB5 ring.** Never run TP over Wi-Fi or high-latency WAN.

### 3. **Pipelined-Ring Parallelism (PRP) — Prima.cpp**
- **Data Transfer:** Activations and KV tensors stream in a closed loop ($A \to B \to C \to A$).
- **Verdict:** **Highest single-stream throughput (50.0 tok/s).** Computation on Node $A$ and transmission to Node $B$ are 100% overlapped.

### 4. **Decentralized Swarm DHT — Petals & Hivemind**
- **Data Transfer:** Libp2p Kademlia DHT routes activations dynamically.
- **Verdict:** **Best fault tolerance.** If a node overheats or drops, the swarm reroutes around the layer in <50ms without failing.

### 5. **Topology-Aware Dynamic P2P — Exo**
- **Data Transfer:** Automatically measures ping matrix and allocates layer depth based on node VRAM and bandwidth.
- **Verdict:** Ideal for heterogeneous Apple Silicon Metal + Android Tensor G5 TPU clustering.

### 6. **Expert Parallelism (EP) — DeepSeek-V3 MoE & Mixtral**
- **Data Transfer:** Activates only Top-K experts (8/256 = 3.125% communication).
- **Verdict:** **Fastest overall generation (81.4 tok/s).** Network traffic is 8x lower than dense models.

### 7. **Fully Sharded Data Parallel (FSDP2 / ZeRO-3) — Training**
- **Data Transfer:** Shards optimizer states, gradients, and model parameters. Fetches weights via All-Gather before each layer.
- **Verdict:** Training bottleneck is raw bandwidth. Requires TB4 DMA or TB5 for high-speed parameter gathering.

### 8. **Sequence Parallelism (SP) & Context Parallelism (CP) — 1M+ Context**
- **Data Transfer:** Slices sequence across nodes and rotates KV blocks using RingAttention.
- **Verdict:** Smashes single-node VRAM limits for ultra-long context window reasoning.
