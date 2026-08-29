---
title: "Qwen-AgentWorld-35B: Migration to Apple Silicon Mac for High-Speed MoE Fine-Tuning"
date: "2026-08-29"
author: "Antigravity Swarm Architect"
tags: [qwen_agentworld, mlx, apple_silicon, lora_training, m4_pro, metal]
---

# 🧠 Qwen-AgentWorld-35B-A3B: High-Speed Apple Silicon Training Architecture

## 1. Executive Summary

To achieve the fastest possible AI training throughput, **Qwen-AgentWorld-35B-A3B** (35B MoE, 3B active parameters) is targeted to the **Apple M4 Pro Mac Mini Host** (`24.0 GB Unified RAM`, `21.6 GB AI VRAM` @ **273 GB/s memory bandwidth**), leveraging **Apple MLX QLoRA** (Metal Zero-Copy Unified Memory) alongside **PyTorch MPS (`peft`/`trl`)**.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   APPLE SILICON HIGH-SPEED AGENTWORLD TRAINING PIPELINE                │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. TARGET HARDWARE NODE                                                                │
│    • Node: Mac_Node_Local (Apple M4 Pro)                                              │
│    • Memory: 24.0 GB Unified RAM (21.6 GB Dynamic AI VRAM Cap @ 90%)                  │
│    • Bandwidth: 273 GB/s unified memory bus (Zero CPU-GPU copy overhead)              │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. TRAINING ENGINES & COMPUTE PIPELINES                                                │
│    • Primary (Fastest): Apple MLX QLoRA (mlx-community/Qwen-AgentWorld-35B-A3B-4bit)  │
│    • Secondary: HuggingFace SFTTrainer + PEFT (LoRA rank=64, alpha=128 on MPS)        │
│    • Distributed Sharding: FSDP multi-Mac via 10Gbps Thunderbolt 4 (Mac Mini + Pro)    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. MULTI-DOMAIN TRAINING DATASET (63,385 Authentic Lauburu Samples)                   │
│    • MCP Tool Calling: nomad_autonomous_actions.jsonl, cron_governor_decisions.jsonl  │
│    • Terminal & SSH: nomad_autonomous_actions.jsonl, network_decisions.jsonl          │
│    • SWE & Code: ui_ux_improvements.jsonl, truth_audit_decisions.jsonl                │
│    • Android & ADB: shizuku_healing_actions.jsonl                                     │
│    • OS System Admin: cron_governor_decisions.jsonl                                   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Fast-Training Commands

```bash
# 1. Prepare multi-domain training dataset
python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/fast_train_agentworld_mac.py --prepare-only

# 2. Launch Apple MLX Metal QLoRA (Fastest on M4 Pro)
python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/fast_train_agentworld_mac.py --backend mlx --stage 1 --iters 500

# 3. Launch PyTorch MPS SFT Pipeline
python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/agentworld_train.py --model agentworld_35b --stage 1
```

---
