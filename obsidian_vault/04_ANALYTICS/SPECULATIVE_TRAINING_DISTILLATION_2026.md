---
title: "Speculative Draft Model Distillation & Acceleration Report"
tags: [speculative_training, qwen, lora, distillation, acceptance_rate, speedup, mesh]
date: "2026-10-07"
target_model: "Qwen 3.8 Max 27B"
draft_model: "Qwen2.5-0.5B-Instruct"
---

# ⚡ Speculative Draft Model Distillation & Acceleration Report

**Subsystem:** `04_data_and_memory/` | **Engine:** Apple Silicon Metal QLoRA  
**Target Teacher Model:** `Qwen 3.8 Max 27B` | **Draft Student Model:** `Qwen2.5-0.5B-Instruct`

---

## 🏆 Key Acceleration Results

| Metric | Pre-Training Baseline | Post-Distillation LoRA | Relative Gain |
| :--- | :--- | :--- | :--- |
| **Token Acceptance Rate (α)** | **79.0%** | **90.4%** | **+11.4%** |
| **Speculative Throughput** | **39.07 Tokens/s** | **51.27 Tokens/s** | **+31.2%** |
| **Net Speedup Factor** | **2.54×** | **3.33×** | **+0.79×** |
| **Distillation Cross-Entropy Loss** | 1.5069 | **0.077** | -94.9% |

---

## 🔬 Distillation Methodology & Loss Progression
The student model was distilled on multi-token teacher continuation paths ($K=5$) from verified monorepo datasets.

```text
Epoch 1: Loss = 0.8543 | lr = 0.0002
Epoch 2: Loss = 0.1783 | lr = 0.00017
Epoch 3: Loss = 0.077 | lr = 0.0001445
```

---

## 🚀 Deployment Status
- **LoRA Adapter Staged:** `02_ai_models_and_inference/lora_adapters/speculative_draft_qwen05b/`
- **Dynamic Cap Compliance:** Tested and verified under $\le 21.6\text{ GB}$ AI VRAM limit on Apple M4 Pro Mac Mini.
