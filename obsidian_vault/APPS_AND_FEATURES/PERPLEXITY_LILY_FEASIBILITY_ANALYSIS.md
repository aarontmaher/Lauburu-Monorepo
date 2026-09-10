---
title: "Perplexity Lily Inference Engine: Technical Feasibility & Compatibility Analysis"
date: "2026-09-08"
tags: [perplexity, lily, qwen36, apple_silicon, metal, m4_pro, m5, mesh_architecture]
status: "EVALUATED_EMPIRICAL"
---

# 🌸 Perplexity Lily Inference Engine: Feasibility Analysis

- Canonical Links: [[Index]], [[CANONICAL_PROJECT_AND_STORAGE_RULE]], [[MAC_MINI_EXCLUSIVE_LOCAL_AI_BENCHMARK]]
- Source Repo: [`perplexityai/pplx-garden/lily`](https://github.com/perplexityai/pplx-garden/tree/main/lily)

---

## 🔬 Official Engine Specifications (Direct from `lily/README.md`)

Lily is a specialized single-process Rust inference server with hand-written Metal kernels designed exclusively for on-device greedy decoding of **`Qwen3.6-35B-A3B`** in MLX affine 4-bit format.

| Dimension | Perplexity Lily Specification | Lauburu Host / Mesh Current State | Compatibility Verdict |
| :--- | :--- | :--- | :--- |
| **GPU Architecture** | Apple GPU family 10+ (`MTLGPUFamilyApple10` / M5+) | Apple M4 Pro (`MTLGPUFamilyApple9` / 1009) | ❌ **INCOMPATIBLE** (M5 hardware instruction target) |
| **OS Requirement** | macOS 26+ (Metal tensor instructions) | macOS 15.x / Darwin 24.6.0 | ❌ **INCOMPATIBLE** (Requires future Metal tensor APIs) |
| **Unified RAM** | 32 GB+ recommended (19.4 GB checkpoint) | 24.0 GB UMA (`recommendedMaxWorkingSetSize = 19.07 GB`) | ❌ **EXCEEDS WORKING SET** (19.4 GB > 19.07 GB limit) |
| **Model Weights** | Strict MLX affine Q4 (Group size 64) ONLY | GGUF Vault (`llama.cpp` / `prima.cpp`) | ❌ **PROHIBITED** (Rule 8: Universal GGUF invariant) |
| **Decoding Support** | Greedy decoding ONLY (`temp = 0`) | Full sampling, speculative draft, reasoning tags | ⚠️ **RESTRICTIVE** |
| **Distributed / Mesh** | Monolithic single-device ONLY (No RPC/P2P) | 10Gbps TB4 DMA Bridge, Pipelined-Ring Parallelism | ❌ **NO MESH SUPPORT** |

---

## ⚖️ Architectural Comparison: Lily vs. Current Stack

1. **Host Memory Physics on 24 GB M4 Pro:**
   - Lily's `mlx-community/Qwen3.6-35B-A3B-4bit` requires **19.4 GB** just for model weights.
   - On the 24 GB Mac Mini, Apple Metal enforces `recommendedMaxWorkingSetSize = 19,069.67 MB` (~19.07 GB). Loading a 19.4 GB checkpoint causes an immediate kernel allocation failure.
   - In contrast, our current `Qwen 3.8 27B UD` (16.34 GiB GGUF with `-ub 256`) and `DeepSeek-Coder-V2 16B MoE` (9.65 GiB) fit and run on Metal with 100% stability.
2. **Mesh Sharding vs. Monolithic Lock-In:**
   - Lily cannot distribute layers across nodes.
   - Our `prima.cpp` PRP engine over the 10Gbps Thunderbolt 4 bridge pools **40.0 GB UMA** across the Mac Mini (L1) and MacBook Pro (L2) at **0.277 ms RTT**, allowing 72B–80B models to run without single-device memory limits.
3. **Engineering Utility from `pplx-garden`:**
   - While the standalone `lily` server cannot run on the M4 Pro due to the `MTLGPUFamilyApple10` requirement, the **Metal shader implementations** in `pplx-garden/lily/src/kernels/` provide valuable reference code for custom Metal MoE kernel optimizations.
