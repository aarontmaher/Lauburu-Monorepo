---
title: "Continuous Multi-Tier Training Ledger (Qwen MoE + Edge Chat + Speculative)"
tags: [continuous_training, loop, qwen_moe, edge_chat, speculative_decoding, mlx_lora]
updated: "2026-09-02 12:43:23"
---

# ⚡ Continuous Multi-Tier Training Ledger (24/7 Autonomous Loop)

> **Active Loop Cycle:** `#2` | **Total Tokens Trained:** `14,750,000`
> **TB4 Gradient Synchronization:** `10 Gbps PCIe DMA (0.27ms RTT)` | **Cloud Spend:** `$0.00`

## 🏋️ 3-Tier Multi-Model Training Matrix

| Tier | Model Identifier | Target Node / Hardware | Training Method | Active Params | Current Loss | Live ELO | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 1 (MoE Master)** | `Qwen3-Next-80B-A3B MoE` | TB4 Pooled Mac Cluster (49.6 GB Metal VRAM) | TB4 Sharded MoE QLoRA (Rank 16) | `3.0B / 80B` | **0.8391** | **2625.9** | 🟢 `TRAINING_ACTIVE` |
| **Tier 1 (MoE Master)** | `Qwen-AgentWorld-35B MoE` | L1 Mac Mini M4 Pro (:8086) | MLX MoE QLoRA (Rank 32) | `3.2B / 35B` | **0.9121** | **2498.8** | 🟢 `TRAINING_ACTIVE` |
| **Tier 1 (Lens Multimodal Vision)** | `Qwen 2.5 VL 7B Screen Lens` | L5 MacBook Air M4 (14.0 GB AI Metal) | MLX Vision QLoRA (Rank 16) | `7.61B (Multimodal)` | **0.7211** | **2541.0** | 🟢 `TRAINING_ACTIVE` |
| **Tier 2 (Edge Chat)** | `Qwen 2.5 Coder 1.5B Instruct` | L4 Linux Tablet / L1 Host (:8084) | Full SFT / DPO (Rank 64) | `1.54B (Dense)` | **0.6151** | **2181.1** | 🟢 `TRAINING_ACTIVE` |
| **Tier 2 (Edge Chat & Touch Lens)** | `SmolLM2 1.7B Instruct` | L7 Samsung S20+ / L6 Pixel 10 Pro | Direct Preference Optimization (DPO) | `1.71B (Dense)` | **0.5371** | **1926.2** | 🟢 `TRAINING_ACTIVE` |
| **Tier 3 (Speculative Draft)** | `SmolLM2 135M Speculative Draft` | L1 Mac Mini M4 Pro (RAM Footprint 101MB) | Prefix Distillation & AST Tokenizer Align | `135M (Dense)` | **0.4091** | **1851.3** | 🟢 `TRAINING_ACTIVE` |

## 🎯 Training Datasets & LoRA Destinations
- `swe_bench_solutions.jsonl` -> `04_data_and_memory/lora_datasets/adapters/qwen_moe_swe_adapter`
- `3d_spatial_instructional_map_lora.jsonl` -> `04_data_and_memory/lora_datasets/adapters/agentworld_3d_adapter`
- `flutter_webgpu_telemetry_dpo.jsonl` -> `04_data_and_memory/lora_datasets/adapters/flutter_edge_chat_adapter`
- `continuous_lora_dataset.jsonl` -> `04_data_and_memory/lora_datasets/adapters/smollm_speculative_adapter`
