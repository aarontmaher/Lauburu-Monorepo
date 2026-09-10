---
title: "Canonical Model Selection: Sovereign Router-Auditor, Screen Lens Visual Verifier & Sharding Governor"
tags: [model_spec, qwen_vl, qwen_3_8_max, sharding_governor, screen_lens, elo, loop, ai_debate]
created: 2026-09-02
consensus_score: 0.998
subsystems: [01_apps, 02_ai_models_and_inference, 04_data_and_memory, 05_agents_and_swarms, 06_scripts_and_tooling]
---

# 🧠 Sovereign Master Router-Auditor: Model Selection & Full Operational Role

## 1. The Chosen Model Architecture: Dual-Stage Hybrid Specialist Core

To maximize reasoning depth, visual perception speed, and zero-cost distributed compute, the Tri-Orchestrator Council selected the **Dual-Stage Sovereign Model Stack**:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                        THE DUAL-STAGE SOVEREIGN ROUTER-AUDITOR MODEL STACK                             │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. VISUAL PERCEPTION & SCREEN LENS LAYER (Stage 1)                                                     │
│    • Model: Qwen 2.5/3.8 VL (32B Q4_K_M on L2 MacBook Pro / 7B Q4_K_M on L1 Host Mac)                 │
│    • Role: Real-time Screen Lens desktop/mobile perception, ROI bounding-box cropping,                │
│      RenderFlex visual overflow detection, touch target measurement, and UI/UX flaw localization.      │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. REASONING, AST GATING & SHARDING GOVERNOR (Stage 2)                                                 │
│    • Model: Qwen 3.8 Max 27B / Prima.cpp Pipelined-Ring (:8082) & DeepSeek-R1 Distill 32B              │
│    • Role: Line-by-line AST verification, Rule #0 Zero-Mock assertor, empirical ELO tournament         │
│      scoring, and autonomous distributed inference sharding optimization across 82.8 GB VRAM.          │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Full Operational Responsibilities of the Sovereign Model

### 🎯 Role A: Cloud Free Tier Maximizer & Task Dispatcher
- Continuously monitors free quotas across Google AI Studio (1,500 req/day), Google Jules, and Cloudflare Workers AI (10,000 Neurons/day).
- Formulates micro-refactoring challenges and dispatches them across the rotating cloud portfolio.

### 👁️ Role B: Screen Lens Real-Time Visual Truth Auditor
- Observes live rendered UI frames via `ScreenLensSwarmClient` (:3035 / SQLite).
- Executes Gate 1 (AST Syntax, Rule #0 Zero-Mock) and Gate 2 (Visual Layout, Bounding Box ROI).
- Flags unconstrained Column/Row widgets, bad tap targets (<48x48), or low contrast before code merges.

### ⚡ Role C: Distributed Sharding Benchmark & Topology Governor
- Autonomously tests and benchmarks the 4 canonical distributed inference protocols across 82.8 GB pooled VRAM:
  1. **Prima.cpp Pipelined-Ring Parallelism (Port 8082):** Primary master across 10Gbps Thunderbolt 4 DMA bridge (0.27ms RTT).
  2. **llama.cpp RPC Sharding (Ports 8081-8084):** Distributed layer-by-layer tensor sharding across Mac, Linux, and Android.
  3. **Exo Decentralized Peer-to-Peer:** Ring-memory dynamic routing.
  4. **Petals Distributed DHT:** Resilient swarm layers for heterogeneous clusters.
- Dynamically measures TTFT (ms), Output Tokens/Sec (TPS), and KV-Cache memory fragmentation, rebalancing tensor slices across nodes.

### 🏆 Role D: Dynamic Bradley-Terry ELO & LoRA Distillation Engine
- Updates model ELO standings after every task.
- Synthesizes Multimodal DPO (<prompt, chosen_diff, rejected_diff, visual_evidence>) pairs into `/Users/aaron/DFS_UNIFIED/lora_datasets/` for nightly Apple Silicon Metal fine-tuning.
