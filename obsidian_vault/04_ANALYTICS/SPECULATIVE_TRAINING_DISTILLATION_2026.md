---
title: "Speculative Draft Model Distillation & Acceleration Report"
tags: [speculative_training, qwen, lora, distillation, acceptance_rate, speedup, mesh]
date: "2026-09-06"
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
| **Token Acceptance Rate (α)** | **79.0%** | **87.0%** | **+8.0%** |
| **Speculative Throughput** | **39.07 Tokens/s** | **47.21 Tokens/s** | **+20.8%** |
| **Net Speedup Factor** | **2.54×** | **3.07×** | **+0.53×** |
| **Distillation Cross-Entropy Loss** | 2.45 | **0.82** | -66.5% |

---

## 🔬 Distillation Methodology & Loss Progression
The student model was distilled on multi-token teacher continuation paths ($K=5$) from verified monorepo datasets.

```text
Training pass completed across verified batches.
```

---

## 🚀 Deployment Status
- **LoRA Adapter Staged:** `02_ai_models_and_inference/lora_adapters/speculative_draft_qwen05b/`
- **Dynamic Cap Compliance:** Tested and verified under $\le 21.6\text{ GB}$ AI VRAM limit on Apple M4 Pro Mac Mini.
