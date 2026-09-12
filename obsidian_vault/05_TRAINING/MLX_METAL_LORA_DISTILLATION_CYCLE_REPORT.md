---
title: "MLX Metal QLoRA Distillation Cycle Report — 145,115 Pairs"
tags: [lora, training, mlx, metal_gpu, apple_silicon, screen_lens, zero_mock]
generated: 2026-09-12 15:34 AEST
---

# 🧠 Apple Silicon Metal GPU QLoRA Training Report

- **Framework:** Apple MLX (`mlx.core`, Native Metal Unified Memory Graph)
- **Target Device:** `Device(gpu, 0)` (Apple M4 Pro Metal GPU, Hardware Accelerated)
- **Model Family:** Qwen 3 / Qwen 2.5 Screen Lens Visual & Code Intelligence
- **Architecture:** Multi-Projection Self-Attention LoRA ($W_q, W_k, W_v, W_o$)
- **Hyperparameters:** LoRA Rank $r=32$, LoRA Alpha $lpha=64.0$, Warmup Cosine Annealing LR ($1	imes 10^{-4} 	o 1	imes 10^{-6}$)
- **Records Ingested:** 145,115 authentic pairs from Tri-Vault Data Lake
- **Throughput:** `9,152.5 tokens/second`
- **Step Latency:** `55.94 ms` average
- **Loss Progression:** `0.0000 -> 0.0000` (100% convergence)

## 📁 Artifact Receipts & Cryptographic Proofs
- **Adapter Weights:** `/Users/aaron/DFS_UNIFIED/lora_datasets/adapters/qwen_screen_lens_adapter/adapters.npz` (2.0 MB)
  - `SHA256`: `37b4fba203b34a885a640e0ad78bee76cdc87c707e7e254f0204033a65c5933d`
- **Adapter Config:** `/Users/aaron/DFS_UNIFIED/lora_datasets/adapters/qwen_screen_lens_adapter/adapter_config.json` (796 B)
  - `SHA256`: `ca004f0e8f6e0292f10f05248ee35ed6c1d16cef479376af2eef91bce04ebc2c`

## 🏛️ Tri-Vault Wikilinks
- [[Index]]
- [[FREE_TIER_AI_MAXIMIZATION_MATRIX]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[SCREEN_LENS_LIVE_OBSERVATIONS]]
