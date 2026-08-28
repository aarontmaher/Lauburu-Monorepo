---
name: sandbox-training
description: Guides autonomous local AI model training, shadow swarm benchmarking, and 24/7 LoRA distillation within an isolated sandbox, driving toward a $0 recurring cloud spend goal while retaining access to top-10 cloud AI APIs for continuous benchmarking and learning.
---

# Sandbox Training & Autonomous AI Distillation

The **Sandbox Training Skill** defines the methodology for continuously training, benchmarking, and evolving the Lauburu Swarm's local edge models (0.5B to 70B parameters) in an isolated, non-destructive sandbox.

---

## 1. Core Mission: The $0 Recurring Cloud Spend Goal

*   **Primary Objective:** Eliminate long-term reliance on expensive monthly API memberships and third-party cloud locks by making the local distributed mesh (Mac Air M4, Mac Worker via Thunderbolt, Linux Head Node, Pixel 10 Pro XL, Samsung S20+) 100% self-sufficient.
*   **The Pragmatic Knowledge Transfer Rule:** The $0 cloud spend goal is an economic destination, not a hard isolationist constraint. While driving toward complete self-sufficiency, the swarm retains on-demand API access to the **Top 10 Cloud Frontier Models** (Gemini 3.7 Flash, Gemini 1.5 Pro, Claude 3.5 Sonnet, GPT-4o, DeepSeek-R1, etc.) specifically to:
    1. Study frontier coding patterns and architectural solutions.
    2. Generate high-quality Chain-of-Thought (CoT) synthetic distillation datasets.
    3. Serve as an impartial judge during high-stakes Truth Audits.
    4. Provide fallback compute when local VRAM headroom is temporarily saturated.

---

## 2. Sandbox Training Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SANDBOX TRAINING PIPELINE                        │
│                                                                         │
│  [1. Frontier AI Teacher (On-Demand Cloud)]                             │
│  • Solves complex tasks & emits step-by-step Chain-of-Thought traces    │
│                                    ↓                                    │
│  [2. LoRA Dataset Synthesizer (Google Drive Sync)]                      │
│  • Curates clean JSONL pairs into /lora_datasets/                       │
│                                    ↓                                    │
│  [3. Distributed llama.cpp LoRA Trainer (Local Mesh)]                   │
│  • Fine-tunes local models (Qwen3-VL, DeepSeek-R1-32B, Qwen2.5-Coder)   │
│  • Sharded over 10Gbps Thunderbolt bridge & Tailscale overlay           │
│                                    ↓                                    │
│  [4. Shadow Swarm Benchmark Tournament (Genetic AI)]                    │
│  • Races local fine-tuned models against cloud outputs on branched code │
│  • Evaluates ELO rankings & Truth Audit compliance                      │
│                                    ↓                                    │
│  [5. Production Promotion Gate & NPU Bonus Grant]                       │
│  • When Local Model ELO >= Cloud ELO → 100% Production Promotion        │
│  • Automatically awards high-priority NPU execution grants to author   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Training Tiers & RAM Governor

To preserve system responsiveness, the sandbox trainer auto-scales based on available RAM headroom:

| Mode | Trigger Condition | Active Model & Action |
| :--- | :--- | :--- |
| **FULL TIER** | Idle mesh, > 12 GB headroom | Full fine-tuning of `DeepSeek-R1-32B` / `Qwen3-VL-32B` over Thunderbolt RPC shards. |
| **MEDIUM TIER** | Active development, 6-12 GB headroom | Lightweight adapter updates on `1.5B` - `7B` models. |
| **MINIMAL TIER** | Heavy production workload, < 6 GB headroom | Data curation, deduplication, and JSON formatting only (0 MB VRAM). |
| **EMERGENCY PAUSE** | Node RAM > 75% ceiling | Instantly pause all background training to yield compute to production apps. |

---

## 4. Benchmark Tournament Execution

1. **Branched Sandbox Execution:** The trainer provisions an isolated workspace branch (or `/sandbox/` directory) for each candidate model.
2. **Standard & Custom Evaluation:** Candidates are scored across:
   - `TRUTH_DETECT` (Zero fake data enforcement)
   - `DART_FIX` (Flutter/Dart code generation correctness)
   - `BLE_KNOWLEDGE` (Movesense/Polar real-time telemetry protocol adherence)
   - `SHOPIFY_UCP` (Catalog queries and payment state compliance)
   - `THUNDERBOLT_RPC` (Sharding latency and token throughput)
3. **Continuous Record Keeping:** Every tournament result, promotion event, and ELO shift is appended to `mesh_benchmarks/competent_models.json` and synced to `/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/evolution/`.

---

## 5. Production Promotion NPU Bonus Protocol

*   **The Core Mandate:** Anytime a feature, model architecture, UI/UX component, optimization, or dataset developed in the training sandbox/network is graduated and implemented in the real production project, the authoring AI model or node MUST be awarded high-priority **NPU Compute Bonus Grants**.
*   **Bonus Ledger:** All grants are recorded in `mesh_benchmarks/npu_bonus_ledger.json` and synced to `/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/evolution/npu_bonus_ledger.json`.
*   **Priority Execution:** Models with NPU Bonus Grants receive top-tier scheduling on Google Tensor G5 TPUs, Apple Neural Engines (ANE), and Qualcomm Hexagon NPUs, accelerating their iterative refinement loops with near-zero power draw (1.2W).
