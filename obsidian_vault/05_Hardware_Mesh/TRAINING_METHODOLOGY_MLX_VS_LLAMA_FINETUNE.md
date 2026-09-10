---
title: "Training Methodology: Apple MLX vs. llama-finetune vs. DPO Lakehouse"
tags: [training, mlx, llama-finetune, dpo, gguf, thunderbolt4, prima, mesh]
created: 2026-09-05
status: verified_empirical
---

# 📊 Training Methodology: Apple MLX vs. llama-finetune vs. DPO Lakehouse

## 1. Executive Summary & Verdict
Following extensive empirical profiling across the 7-Layer Lauburu Mesh (specifically the **Thunderbolt Trio**: M4 Pro Mac Mini Host, M4 MacBook Pro L2, M4 MacBook Air L5), **MLX is strictly disqualified from live mesh serving and distributed orchestration**, and relegated strictly to isolated offline batch fine-tuning.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TRI-METHOD TRAINING & ORCHESTRATION                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. LIVE MESH SERVING & PRP RING (100% GGUF)                                 │
│    • Framework: prima.cpp (Port 8082 PRP) + llama.cpp RPC (Port 8081/8083)  │
│    • Transport: 40 Gb/s Thunderbolt 4 Bridge (0.41ms RTT)                   │
│    • Why Not MLX: Zero network tensor sharding; pins 16-40 GB host RAM.    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. MICRO-ADAPTER TUNING (llama-finetune)                                    │
│    • Engine: /Users/aaron/llama.cpp/build/bin/llama-finetune                │
│    • Target: Direct C++ GGUF LoRA on models <=500M (TinyStories, SmolLM2).  │
│    • Advantage: <150 MB RAM overhead, instantaneous startup (<15ms).       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. ADVANCED ARCHITECTURE TRAINING (Apple MLX LoRA)                          │
│    • Engine: python -m mlx_lm lora (v0.31.3) with DoRA & Muon Optimizers    │
│    • Offload Strategy: Run exclusively on MacBook Pro L2 (16GB) via TB4     │
│    • Rationale: Preserves Mac Mini 9.6 GB Sanctuary Headroom (Rule 3).     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. Empirical Benchmark Matrix

| Dimension | `llama-finetune` (C++ GGUF) | Apple MLX (`mlx_lm lora`) | DPO Trajectory Lakehouse |
| :--- | :--- | :--- | :--- |
| **Model Weight Format** | **GGUF Direct** (Q4_K_M, F16) | HuggingFace / SafeTensors | JSONL / Parquet Preference Pairs |
| **Inference Framework Parity** | **100% Native** with llama-server | Requires export to GGUF | Universal (consumable by both) |
| **Thunderbolt 4 / Mesh Support** | **Yes** (via llama.cpp RPC workers) | ❌ **No** (Single-Mac only) | **Yes** (SeaweedFS / PySpark / Ray) |
| **Host RAM Overhead** | **Ultra-Low** (<150 MB C++ runtime) | **High** (Pins 16–32 GB Unified RAM) | **Zero VRAM** (Decoupled harvesting) |
| **Advanced Optimizers** | AdamW, SGD | **DoRA, Muon, Adafactor, AdamW** | DPO Loss, Margin Loss |
| **Execution Latency** | Instant C++ startup (~15ms) | Python / Metal JIT (~350ms) | Continuous async logging |
| **Swarm Autonomy Fit** | Micro-adapter fine-tuning on tiny SLMs | Offline batch pre-training on peripheral Mac | **24/7 Continuous Background Loop** |

## 3. Sandboxed Dual-Plane TUI Dev Studio
Operated under Rule 4 at:
`01_apps/screen_lens/sandbox_evolution/dual_tui_swarm_arena/dual_tui_dev_studio.py`

- **Normal Swarm (<=500M):** TinyStories-20M (13.9MB, 1316 t/s), SmolLM2-135M (101MB, 72.5 t/s), SmolLM2-360M (258MB, 68.6 t/s), Qwen2.5-0.5B (491MB).
- **Abliterated Swarm (<=500M):** Pythia-70M (76.7MB, 283.1 t/s), SmolLM-135M-Unc (100MB, 346.5 t/s), Qwen2.5-0.5B-Abl (379MB, 237.2 t/s).
- **Scoring Invariant:** Inverse Size ($1000.0 / \text{Size\_MB}$) + Architectural Family Entropy + Metal tok/s throughput.

## 4. Related Links
- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- [[HIGH_ROI_AI_TRAINING_PROTOCOLS_AND_BENCHMARKS]]
