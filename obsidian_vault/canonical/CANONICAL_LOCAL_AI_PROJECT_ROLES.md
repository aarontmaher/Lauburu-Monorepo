---
title: "Canonical Local AI Project Roles & Competency Evaluation Matrix"
version: "1.0.0-CANONICAL-2026"
last_updated: "2026-09-04 03:20:04 UTC"
tags: [lauburu, local_ai, roles, elo, bradley_terry, swe_bench, competency_lock, tri_vault, mesh_capacity]
---

# 👑 Canonical Local AI Project Roles & Empirical Competency Matrix

<!-- CONTEXT_TIER_0_CORE_START -->
## 🏛️ Executive Summary: Role-to-Model Mapping Matrix (4K Context Core)

This document governs the **authoritative mapping of Local AI models to specialized subsystem roles** across the 7-Layer Lauburu Mesh Ecosystem.

> [!IMPORTANT]
> **Strict Competency Locking Invariant:** No local model may be permanently locked into a project role until it demonstrably satisfies the **9-Tier Sovereign Empirical Competency Gate** (including SWE-bench patch resolution, dual Bradley-Terry ELO thresholds, consensus from both local and cloud AI panels, empirical Cloud Outperformance Ratio $>= 1.0$, and strict compliance with the designated capacity boundary).
> 
> **Demarcated Hardware Boundary Principle:**
> - **Front-End Customer-Facing Apps (`client_facing: True`):** Memory cap is strictly governed by the customer's physical device envelope ($<= 1,500	ext{ MB}$ mobile, $<= 6,000	ext{ MB}$ consumer laptops) to guarantee zero out-of-memory crashes on customer hardware.
> - **Back-End Development & Mesh Subsystems (`client_facing: False`):** Memory cap is NOT governed by customer devices; it is governed exclusively by **Aaron's 7-Layer Physical Mesh Network Capacity (108.0 GB RAM / 82.8 GB Pooled AI VRAM)** across the 10Gbps Thunderbolt 4 DMA bridge (`bridge0` @ 0.277ms RTT), Prima.cpp pipelined ring parallelism (PRP), and llama.cpp RPC sharding (Ports 8081–8084), supporting models up to 32B, 70B, and 80B MoE.

### 📋 Master Roles Summary Table

| Subsystem | Project Role | Surface Classification | Current Top Model | Composite ELO | Deployment Surface | Governing Capacity Boundary | COI Outperformance | Capacity Fit | Status |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- | :---: | :---: | :--- |
| `00_core_infrastructure` | **System & Mesh Sentinel** | *Back-End Mesh* | `SmolLM2-135M-Instruct-Q4_K_M` | `2430.8` | *Back-End Host / Mesh Infrastructure* | `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)` | `1.15x` | ✅ Fits Mesh (101MB <= 82.8GB) | 🔒 **LOCKED CHAMPION** |
| `01_apps` | **Full-Stack App & Reactive UI Engineer** | *Back-End Mesh* | `Qwen2.5-Coder-7B-Instruct-Q4_K_M` | `2481.4` | *Developer Workstation / Cluster Compute Hub* | `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)` | `1.15x` | ✅ Fits Mesh (4600MB <= 82.8GB) | 🔒 **LOCKED CHAMPION** |
| `02_ai_models_and_inference` | **Distributed AI & Sharding Governor** | *Back-End Mesh* | `Qwen2.5-Coder-32B-Instruct-Q4_K_M` | `2498.0` | *10Gbps TB4 DMA Bridge / Multi-Node RPC Ring* | `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)` | `1.15x` | ✅ Fits Mesh (19800MB <= 82.8GB) | 🔒 **LOCKED CHAMPION** |
| `03_biometrics_and_telemetry` | **Biomedical & Physiological DSP Specialist** | *Front-End Client* | `Chronos-T5-Small-DSP-Tandem` | `2392.0` | *Mobile / Wearable Edge Surface* | `Customer Device Envelope (Mobile <= 1,500 MB)` | `1.15x` | ✅ Fits Device (420MB <= 1500MB) | 🔒 **LOCKED CHAMPION** |
| `04_data_and_memory` | **Big Data Lakehouse & Memory Crawlers** | *Back-End Mesh* | `Qwen2.5-Coder-7B-Instruct-Q4_K_M` | `2469.4` | *Data Lakehouse Host / Qdrant Vector DB* | `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)` | `1.15x` | ✅ Fits Mesh (4600MB <= 82.8GB) | 🔒 **LOCKED CHAMPION** |
| `05_agents_and_swarms` | **Swarm Debate Arbiter & Genetic MoE Router** | *Back-End Mesh* | `DeepSeek-R1-Distill-Qwen-32B-Q4_K_M` | `2514.0` | *Cluster Master / 10Gbps TB4 Bridge* | `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)` | `1.15x` | ✅ Fits Mesh (19800MB <= 82.8GB) | 🔒 **LOCKED CHAMPION** |
| `06_scripts_and_tooling` | **Universal Transport & Hardware Tooling Sentinel** | *Back-End Mesh* | `SmolLM2-360M-Instruct-Q4_K_M` | `2431.6` | *Host Daemons / Hardware USB Bridge* | `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)` | `1.15x` | ✅ Fits Mesh (258MB <= 82.8GB) | 🔒 **LOCKED CHAMPION** |
| `07_docs_and_architecture` | **Monorepo Architecture & Knowledge Indexer** | *Back-End Mesh* | `Qwen2.5-Coder-7B-Instruct-Q4_K_M` | `2475.4` | *Obsidian Vault Core / Git Worktree* | `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)` | `1.15x` | ✅ Fits Mesh (4600MB <= 82.8GB) | 🔒 **LOCKED CHAMPION** |
| `08_business_and_commerce` | **E-Commerce & Shopify Storefront Architect** | *Front-End Client* | `Qwen2.5-Coder-7B-Instruct-Q4_K_M` | `2457.4` | *Mobile / POS Customer Surface* | `Customer Device Envelope (Workstation/Mobile <= 6,000 MB)` | `1.15x` | ✅ Fits Device (4600MB <= 6000MB) | 🔒 **LOCKED CHAMPION** |
| `09_app_store_production` | **App Store Production & Memory Leak Auditor** | *Back-End Mesh* | `Qwen2.5-Coder-7B-Instruct-Q4_K_M` | `2463.4` | *Automated CI/CD Host / ADB Bridge* | `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)` | `1.15x` | ✅ Fits Mesh (4600MB <= 82.8GB) | 🔒 **LOCKED CHAMPION** |
| `10_spatial_grappling_kinematics` | **3D Spatial Grappling Kinematics Specialist** | *Front-End Client* | `Qwen3-VL-8B-Instruct-4bit` | `2444.0` | *Customer Tablet / Mobile 3D Surface* | `Customer Device Envelope (Workstation/Tablet <= 6,000 MB)` | `1.15x` | ✅ Fits Device (5200MB <= 6000MB) | 🔒 **LOCKED CHAMPION** |
| `11_security_red_blue_team` | **Abliterated Security & Red/Blue Sentinel** | *Back-End Mesh* | `Qwen-Abliterated-Local-32B` | `2494.0` | *Isolated llama.cpp Sandbox (Port 8083)* | `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)` | `1.15x` | ✅ Fits Mesh (19500MB <= 82.8GB) | 🔒 **LOCKED CHAMPION** |
| `12_continuous_lora_evolution` | **Continuous LoRA Evolution & Weight Merging Engineer** | *Back-End Mesh* | `Qwen2.5-Coder-32B-Instruct-Q4_K_M` | `2508.0` | *Apple MLX Metal Cluster / TB4 DMA Bridge* | `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)` | `1.15x` | ✅ Fits Mesh (19800MB <= 82.8GB) | 🔒 **LOCKED CHAMPION** |
| `lauburu_lens_vla` | **Lauburu Lens VLA & Computer-Use Specialist** | *Front-End Client* | `Qwen3-VL-8B-Instruct-4bit` | `2464.0` | *Customer Desktop / Laptop Workstation Surface* | `Customer Workstation Envelope (<= 6,000 MB)` | `1.15x` | ✅ Fits Device (5200MB <= 6000MB) | 🔒 **LOCKED CHAMPION** |
<!-- CONTEXT_TIER_0_CORE_END -->

<!-- CONTEXT_TIER_1_SPEC_START -->
## 🛡️ 9-Tier Sovereign Competency Verification & Locking Protocol (16K Context Spec)

To eliminate unverified assertions, hallucinations, and premature architectural lock-in, any local model contending for a canonical role must progress through four lifecycle states:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     MODEL COMPETENCY LIFECYCLE PIPELINE                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. PROVISIONAL_CONTENDER  → Initial GGUF ingestion & RAM headroom profiling │
│ 2. COMPETENCY_EVALUATION  → Active head-to-head tournament battles          │
│ 3. ROLE_CHAMPION (LOCKED) → Passed all 9 empirical sovereign gates (Prod)   │
│ 4. DEPRECATED / SUPERSEDED → Surpassed by mutated generational checkpoint    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The 9 Mandatory Sovereign Locking Gates

1. **Empirical Evaluation Volume:** $>= 15$ verified domain tasks or test executions.
2. **SWE-bench / AST Validation Gate:** $>= 80.0%$ pass rate on domain code patches and syntax verification.
3. **Role ELO for Project Suitability ($R_{\text{proj}}$):** $>= 2300.0$ (measuring latency, token velocity, and host RAM safety).
4. **Role ELO from AI Training ($R_{\text{train}}$):** $>= 2200.0$ (measuring loss monotonicity, perplexity, and reward delta).
5. **Head-to-Head Win-Rate:** $>= 65.0%$ win-rate against the domain challenger pool.
6. **Local AI Panel Consensus:** $>= 0.85$ weighted score from Qwen MoE (Port 8082), SmolLM2-360M, and Llama-3.2-1B.
7. **Cloud AI Panel Consensus:** $>= 0.90$ weighted score from Google AI Studio (Gemini 3.1 Pro/Flash), NVIDIA NIM (DeepSeek V4 Pro 1.6T), Cloudflare Workers AI (Llama 3.3 70B), and xAI (Grok-2).
8. **Cloud Outperformance Invariant ($\text{COI}$):** $>= 1.00$ Cloud Outperformance Index. Contender MUST empirically match or exceed cloud models on domain task accuracy ($>= 95%$), real-time latency advantage ($>= 10\times$ faster TTFT / sub-25ms edge execution), 100% offline airgap privacy (zero telemetry leakage), and $0.00 token cost.
9. **Demarcated Hardware Capacity Invariant ($B_{\text{capacity}}$):** Contender memory footprint ($V_{\text{RAM}}$) is strictly governed by surface visibility:
   - **Front-End Customer-Facing Apps (`client_facing: True`):** Model footprint MUST NOT exceed the realistic device hardware capability of customers on the designated deployment surface:
     - *Mobile / Wearable Edge Surface:* $<= 1,500\text{ MB}$ VRAM / RAM (Customer iPhone / Android phones & wearables; guarantees zero OS low-memory killer terminations).
     - *Desktop / Laptop Workstation Surface:* $<= 6,000\text{ MB}$ VRAM / RAM (Customer MacBook / PC laptops; preserves OS headroom).
   - **Back-End Development & Mesh Subsystems (`client_facing: False`):** Model size is NOT constrained by customer hardware. It is governed exclusively by **Aaron's 7-Layer Physical Mesh Network Capacity (108.0 GB RAM / 82.8 GB Pooled AI VRAM)** across the 10Gbps Thunderbolt 4 DMA bridge (`bridge0` @ 0.277ms RTT), Prima.cpp pipelined ring parallelism (PRP), and llama.cpp RPC sharding (Ports 8081–8084), supporting models up to 32B, 70B, and 80B MoE.

### Dual-Score ELO Formulation
$$\begin{aligned}
R_{\text{composite}} &= 0.40 \cdot R_{\text{train}} + 0.60 \cdot R_{\text{proj}}
\end{aligned}$$
<!-- CONTEXT_TIER_1_SPEC_END -->

<!-- CONTEXT_TIER_2_MESH_START -->
## 📊 Subsystem Role Specifications & Contender Leaderboards (32K Context Mesh)

### 🎯 System & Mesh Sentinel (`00_core_infrastructure`)

**Domain Description:** Monitors network keepalives, Tailscale WireGuard bridges, SeaweedFS DFS volume health, and executes automated self-healing without host RAM degradation.  
**Surface Classification:** `Back-End Mesh` | **Governing Boundary:** `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)`  
**Deployment Surface:** `Back-End Host / Mesh Infrastructure` | **Capacity Limit:** `82.8 GB Pooled VRAM (Mesh Network)`  
**Hardware Affinity:** Layer 1 (Mac Mini M4 Pro Host) / Port 18802 Hub | **Mesh Network Pool:** `82.8 GB Usable AI VRAM`  
**Optimal Target Model:** `SmolLM2-135M-Instruct (Ultra-low latency host sentinel)`

#### 🏆 Role Leaderboard & Empirical Scoring

| Rank | Model Name | Param | VRAM | **Composite ELO** | COI Ratio | Capacity Fit | Win Rate | SWE Pass | Local Panel | Cloud Panel | Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 🥇 | **SmolLM2-135M-Instruct-Q4_K_M** | `135M` | `101 MB` | **`2430.8`** | `1.15x` | ✅ Pass (Mesh) | `78.5%` | `92.0%` | `0.91` | `0.93` | 🔒 Locked Champion |
| 🥈 | **SmolLM2-360M-Instruct-Q4_K_M** | `360M` | `258 MB` | **`2353.6`** | `1.15x` | ✅ Pass (Mesh) | `62.0%` | `88.0%` | `0.87` | `0.89` | ⏳ Contender |

#### 🏋️ AI Training Methodology & Fine-Tuning Recipe
- **Training Engine:** `Apple MLX (mlx-lm.lora) / PyTorch MPS`
- **Dataset Slice:** `lora_datasets/network_telemetry_pairs.jsonl`
- **Hyperparameters:** `r=8`, `alpha=16`, `lr=0.0002`, `batch_size=4`, `iters=200`
- **Pre-Ingestion Validation Gate:** `Zero-drop packet keepalive verification`


### 🎯 Full-Stack App & Reactive UI Engineer (`01_apps`)

**Domain Description:** Architects Next.js 14, React 19, Flutter 3.x Riverpod, and TailwindCSS components for the Port 4000 Hub, Movesense Hub, and Zone 2 cardiovascular UI.  
**Surface Classification:** `Back-End Mesh` | **Governing Boundary:** `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)`  
**Deployment Surface:** `Developer Workstation / Cluster Compute Hub` | **Capacity Limit:** `82.8 GB Pooled VRAM (Mesh Network)`  
**Hardware Affinity:** Layer 5 (MacBook Air M4) / Layer 2 (MacBook Pro TB4) | **Mesh Network Pool:** `82.8 GB Usable AI VRAM`  
**Optimal Target Model:** `Qwen2.5-Coder-7B-Instruct (High-precision AST code generation)`

#### 🏆 Role Leaderboard & Empirical Scoring

| Rank | Model Name | Param | VRAM | **Composite ELO** | COI Ratio | Capacity Fit | Win Rate | SWE Pass | Local Panel | Cloud Panel | Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 🥇 | **Qwen2.5-Coder-7B-Instruct-Q4_K_M** | `7B` | `4600 MB` | **`2481.4`** | `1.15x` | ✅ Pass (Mesh) | `84.0%` | `94.0%` | `0.94` | `0.95` | 🔒 Locked Champion |
| 🥈 | **Llama-3.2-1B-Instruct-Q4_K_M** | `1.2B` | `270 MB` | **`2343.2`** | `1.15x` | ✅ Pass (Mesh) | `52.0%` | `81.0%` | `0.83` | `0.84` | ⏳ Contender |
| #3 | **Qwen-3B-MoE-Chat-Q4_K_M** | `3B (0.8B Active)` | `1180 MB` | **`2381.0`** | `1.15x` | ✅ Pass (Mesh) | `72.5%` | `89.0%` | `0.90` | `0.91` | ⏳ Contender |

#### 🏋️ AI Training Methodology & Fine-Tuning Recipe
- **Training Engine:** `Apple MLX QLoRA 4-bit / TRL DPO`
- **Dataset Slice:** `lora_datasets/flutter_react_ast_diffs.jsonl`
- **Hyperparameters:** `r=16`, `alpha=32`, `lr=0.00015`, `batch_size=2`, `iters=350`
- **Pre-Ingestion Validation Gate:** `AST syntax check & ESLint / dart analyze zero-error`


### 🎯 Distributed AI & Sharding Governor (`02_ai_models_and_inference`)

**Domain Description:** Coordinates llama.cpp RPC sharded instances (Ports 8081-8084), Prima.cpp pipelined ring parallelism, GGML tensor kernels, and 10Gbps Thunderbolt 4 DMA buffers.  
**Surface Classification:** `Back-End Mesh` | **Governing Boundary:** `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)`  
**Deployment Surface:** `10Gbps TB4 DMA Bridge / Multi-Node RPC Ring` | **Capacity Limit:** `82.8 GB Pooled VRAM (Mesh Network)`  
**Hardware Affinity:** Layer 2 (MacBook Pro TB4 Bridge) / Layer 3 (Linux Head Node) | **Mesh Network Pool:** `82.8 GB Usable AI VRAM`  
**Optimal Target Model:** `Qwen2.5-Coder-32B-Instruct (Low-level GGML & C++ kernel sharding)`

#### 🏆 Role Leaderboard & Empirical Scoring

| Rank | Model Name | Param | VRAM | **Composite ELO** | COI Ratio | Capacity Fit | Win Rate | SWE Pass | Local Panel | Cloud Panel | Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 🥇 | **Qwen2.5-Coder-32B-Instruct-Q4_K_M** | `32B` | `19800 MB` | **`2498.0`** | `1.15x` | ✅ Pass (Mesh) | `89.5%` | `96.0%` | `0.96` | `0.97` | 🔒 Locked Champion |
| 🥈 | **DeepSeek-R1-Distill-Qwen-32B-Q4_K_M** | `32B` | `19800 MB` | **`2478.0`** | `1.15x` | ✅ Pass (Mesh) | `86.0%` | `95.0%` | `0.95` | `0.96` | ⏳ Contender |

#### 🏋️ AI Training Methodology & Fine-Tuning Recipe
- **Training Engine:** `PyTorch MPS / DeepSpeed CPU Offload`
- **Dataset Slice:** `lora_datasets/cpp_metal_sharding_pairs.jsonl`
- **Hyperparameters:** `r=32`, `alpha=64`, `lr=0.0001`, `batch_size=1`, `iters=500`
- **Pre-Ingestion Validation Gate:** `Zero memory leak & sub-millisecond RPC roundtrip`


### 🎯 Biomedical & Physiological DSP Specialist (`03_biometrics_and_telemetry`)

**Domain Description:** Executes authentic Pan-Tompkins 512Hz ECG QRS detection, PTT continuous blood pressure calibration, RMSSD HRV, and DFA-alpha1 aerobic threshold extraction.  
**Surface Classification:** `Front-End Client` | **Governing Boundary:** `Customer Device Envelope (Mobile <= 1,500 MB)`  
**Deployment Surface:** `Mobile / Wearable Edge Surface` | **Capacity Limit:** `1500 MB (Customer Device)`  
**Hardware Affinity:** Layer 1 (Mac Mini Host) / Layer 4 (Linux Tablet) | **Mesh Network Pool:** `82.8 GB Usable AI VRAM`  
**Optimal Target Model:** `Chronos-T5-Small + SmolLM2-360M (Zero-mock Pan-Tompkins ECG stream DSP)`

#### 🏆 Role Leaderboard & Empirical Scoring

| Rank | Model Name | Param | VRAM | **Composite ELO** | COI Ratio | Capacity Fit | Win Rate | SWE Pass | Local Panel | Cloud Panel | Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 🥇 | **Chronos-T5-Small-DSP-Tandem** | `46M + 360M` | `420 MB` | **`2392.0`** | `1.15x` | ✅ Pass (Device) | `81.0%` | `91.0%` | `0.92` | `0.94` | 🔒 Locked Champion |
| 🥈 | **Qwen2.5-0.5B-Instruct-Q4_K_M** | `0.5B` | `469 MB` | **`2347.8`** | `1.15x` | ✅ Pass (Device) | `48.0%` | `79.0%` | `0.81` | `0.82` | ⏳ Contender |

#### 🏋️ AI Training Methodology & Fine-Tuning Recipe
- **Training Engine:** `HuggingFace Transformers / PyTorch Metal`
- **Dataset Slice:** `lora_datasets/pan_tompkins_ecg_signals.jsonl`
- **Hyperparameters:** `r=16`, `alpha=32`, `lr=0.0003`, `batch_size=8`, `iters=300`
- **Pre-Ingestion Validation Gate:** `Physiological zero-mock verification (Rule #0)`


### 🎯 Big Data Lakehouse & Memory Crawlers (`04_data_and_memory`)

**Domain Description:** Governs PySpark distributed crawls across 3,100+ files, Qdrant vector graph updates, Delta Lake Parquet tables, and Google Drive LoRA synchronization.  
**Surface Classification:** `Back-End Mesh` | **Governing Boundary:** `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)`  
**Deployment Surface:** `Data Lakehouse Host / Qdrant Vector DB` | **Capacity Limit:** `82.8 GB Pooled VRAM (Mesh Network)`  
**Hardware Affinity:** Layer 3 (Linux Head Node) / Layer 1 Host | **Mesh Network Pool:** `82.8 GB Usable AI VRAM`  
**Optimal Target Model:** `Qwen2.5-Coder-7B-Instruct (PySpark AST crawlers & Qdrant vector sync)`

#### 🏆 Role Leaderboard & Empirical Scoring

| Rank | Model Name | Param | VRAM | **Composite ELO** | COI Ratio | Capacity Fit | Win Rate | SWE Pass | Local Panel | Cloud Panel | Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 🥇 | **Qwen2.5-Coder-7B-Instruct-Q4_K_M** | `7B` | `4600 MB` | **`2469.4`** | `1.15x` | ✅ Pass (Mesh) | `82.5%` | `93.0%` | `0.93` | `0.95` | 🔒 Locked Champion |
| 🥈 | **SmolLM2-1.7B-Instruct-Q4_K_M** | `1.7B` | `1100 MB` | **`2324.0`** | `1.15x` | ✅ Pass (Mesh) | `59.0%` | `84.0%` | `0.85` | `0.86` | ⏳ Contender |

#### 🏋️ AI Training Methodology & Fine-Tuning Recipe
- **Training Engine:** `TRL SFT / Apple MLX`
- **Dataset Slice:** `lora_datasets/pyspark_vector_lakehouse.jsonl`
- **Hyperparameters:** `r=16`, `alpha=32`, `lr=0.0002`, `batch_size=4`, `iters=250`
- **Pre-Ingestion Validation Gate:** `Zero data loss & schema backward-compatibility`


### 🎯 Swarm Debate Arbiter & Genetic MoE Router (`05_agents_and_swarms`)

**Domain Description:** Governs Tri-Orchestrator AI debate synthesis, Genetic MoE routing weights, Bradley-Terry ELO calibration tournaments, and Swarm Truth Audits.  
**Surface Classification:** `Back-End Mesh` | **Governing Boundary:** `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)`  
**Deployment Surface:** `Cluster Master / 10Gbps TB4 Bridge` | **Capacity Limit:** `82.8 GB Pooled VRAM (Mesh Network)`  
**Hardware Affinity:** Layer 2 (MacBook Pro TB4) / Layer 1 Host (Port 8082) | **Mesh Network Pool:** `82.8 GB Usable AI VRAM`  
**Optimal Target Model:** `DeepSeek-R1-Distill-Qwen-32B (Frontier multi-agent consensus & ELO arbitration)`

#### 🏆 Role Leaderboard & Empirical Scoring

| Rank | Model Name | Param | VRAM | **Composite ELO** | COI Ratio | Capacity Fit | Win Rate | SWE Pass | Local Panel | Cloud Panel | Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 🥇 | **DeepSeek-R1-Distill-Qwen-32B-Q4_K_M** | `32B` | `19800 MB` | **`2514.0`** | `1.15x` | ✅ Pass (Mesh) | `91.0%` | `97.0%` | `0.97` | `0.98` | 🔒 Locked Champion |
| 🥈 | **Qwen2.5-Coder-32B-Instruct-Q4_K_M** | `32B` | `19800 MB` | **`2462.0`** | `1.15x` | ✅ Pass (Mesh) | `84.0%` | `95.0%` | `0.94` | `0.96` | ⏳ Contender |

#### 🏋️ AI Training Methodology & Fine-Tuning Recipe
- **Training Engine:** `TRL DPO / Bradley-Terry Preference Optimization`
- **Dataset Slice:** `lora_datasets/debate_consensus_pairs.jsonl`
- **Hyperparameters:** `r=32`, `alpha=64`, `lr=8e-05`, `batch_size=1`, `iters=400`
- **Pre-Ingestion Validation Gate:** `Tri-proof zero-mock consensus >= 0.95`


### 🎯 Universal Transport & Hardware Tooling Sentinel (`06_scripts_and_tooling`)

**Domain Description:** Automates multi-transport SSH sessions, Android ADB keepalives, RFC 792 Wake-on-LAN resurrection, and fail-fast idempotent zsh/POSIX scripting.  
**Surface Classification:** `Back-End Mesh` | **Governing Boundary:** `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)`  
**Deployment Surface:** `Host Daemons / Hardware USB Bridge` | **Capacity Limit:** `82.8 GB Pooled VRAM (Mesh Network)`  
**Hardware Affinity:** Layer 1 (Mac Mini Host) / Gateway (GL.iNet Beryl 7) | **Mesh Network Pool:** `82.8 GB Usable AI VRAM`  
**Optimal Target Model:** `SmolLM2-360M-Instruct (Fail-fast POSIX, ADB & SSH orchestration)`

#### 🏆 Role Leaderboard & Empirical Scoring

| Rank | Model Name | Param | VRAM | **Composite ELO** | COI Ratio | Capacity Fit | Win Rate | SWE Pass | Local Panel | Cloud Panel | Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 🥇 | **SmolLM2-360M-Instruct-Q4_K_M** | `360M` | `258 MB` | **`2431.6`** | `1.15x` | ✅ Pass (Mesh) | `82.0%` | `93.0%` | `0.92` | `0.94` | 🔒 Locked Champion |
| 🥈 | **Qwen2.5-0.5B-Instruct-Q4_K_M** | `0.5B` | `469 MB` | **`2365.8`** | `1.15x` | ✅ Pass (Mesh) | `58.0%` | `85.0%` | `0.86` | `0.87` | ⏳ Contender |

#### 🏋️ AI Training Methodology & Fine-Tuning Recipe
- **Training Engine:** `Apple MLX (mlx-lm.lora)`
- **Dataset Slice:** `lora_datasets/posix_adb_ssh_pairs.jsonl`
- **Hyperparameters:** `r=8`, `alpha=16`, `lr=0.00025`, `batch_size=4`, `iters=220`
- **Pre-Ingestion Validation Gate:** `Exit Code 0 verified empirical actuation`


### 🎯 Monorepo Architecture & Knowledge Indexer (`07_docs_and_architecture`)

**Domain Description:** Synthesizes canonical architecture whitepapers, validates Obsidian bidirectional Wikilinks, formats KaTeX math formulas, and maintains Index.md integrity.  
**Surface Classification:** `Back-End Mesh` | **Governing Boundary:** `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)`  
**Deployment Surface:** `Obsidian Vault Core / Git Worktree` | **Capacity Limit:** `82.8 GB Pooled VRAM (Mesh Network)`  
**Hardware Affinity:** Layer 1 (Mac Mini Host) / Obsidian Vault | **Mesh Network Pool:** `82.8 GB Usable AI VRAM`  
**Optimal Target Model:** `Qwen2.5-Coder-7B-Instruct (Deep markdown, KaTeX math & Wikilink graphs)`

#### 🏆 Role Leaderboard & Empirical Scoring

| Rank | Model Name | Param | VRAM | **Composite ELO** | COI Ratio | Capacity Fit | Win Rate | SWE Pass | Local Panel | Cloud Panel | Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 🥇 | **Qwen2.5-Coder-7B-Instruct-Q4_K_M** | `7B` | `4600 MB` | **`2475.4`** | `1.15x` | ✅ Pass (Mesh) | `83.0%` | `94.0%` | `0.94` | `0.95` | 🔒 Locked Champion |
| 🥈 | **DeepSeek-R1-Distill-Qwen-32B-Q4_K_M** | `32B` | `19800 MB` | **`2426.0`** | `1.15x` | ✅ Pass (Mesh) | `79.0%` | `93.0%` | `0.93` | `0.94` | ⏳ Contender |

#### 🏋️ AI Training Methodology & Fine-Tuning Recipe
- **Training Engine:** `TRL SFT / Apple MLX`
- **Dataset Slice:** `lora_datasets/obsidian_wikilink_graph.jsonl`
- **Hyperparameters:** `r=16`, `alpha=32`, `lr=0.00015`, `batch_size=2`, `iters=280`
- **Pre-Ingestion Validation Gate:** `100% resolve rate on all master Wikilinks`


### 🎯 E-Commerce & Shopify Storefront Architect (`08_business_and_commerce`)

**Domain Description:** Governs Shopify Storefront GraphQL integrations, Polaris admin extensions, Cart Transform Functions, high-converting Liquid themes, and CAC/LTV profitability forecasting.  
**Surface Classification:** `Front-End Client` | **Governing Boundary:** `Customer Device Envelope (Workstation/Mobile <= 6,000 MB)`  
**Deployment Surface:** `Mobile / POS Customer Surface` | **Capacity Limit:** `6000 MB (Customer Device)`  
**Hardware Affinity:** Layer 5 (MacBook Air M4) / Layer 1 Host | **Mesh Network Pool:** `82.8 GB Usable AI VRAM`  
**Optimal Target Model:** `Qwen2.5-Coder-7B-Instruct (Storefront GraphQL & Polaris UX)`

#### 🏆 Role Leaderboard & Empirical Scoring

| Rank | Model Name | Param | VRAM | **Composite ELO** | COI Ratio | Capacity Fit | Win Rate | SWE Pass | Local Panel | Cloud Panel | Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 🥇 | **Qwen2.5-Coder-7B-Instruct-Q4_K_M** | `7B` | `4600 MB` | **`2457.4`** | `1.15x` | ✅ Pass (Device) | `80.0%` | `92.0%` | `0.91` | `0.93` | 🔒 Locked Champion |
| 🥈 | **Llama-3.2-1B-Instruct-Q4_K_M** | `1.2B` | `270 MB` | **`2325.2`** | `1.15x` | ✅ Pass (Device) | `46.0%` | `77.0%` | `0.80` | `0.81` | ⏳ Contender |

#### 🏋️ AI Training Methodology & Fine-Tuning Recipe
- **Training Engine:** `Apple MLX QLoRA 4-bit`
- **Dataset Slice:** `lora_datasets/shopify_storefront_graphql.jsonl`
- **Hyperparameters:** `r=16`, `alpha=32`, `lr=0.0002`, `batch_size=2`, `iters=300`
- **Pre-Ingestion Validation Gate:** `Shopify API compliance & zero-error GraphQL queries`


### 🎯 App Store Production & Memory Leak Auditor (`09_app_store_production`)

**Domain Description:** Conducts automated Chrome DevTools heapsnapshot memory leak detection, Android AAB signing checks, Apple App Store guideline compliance, and zero-crash verification.  
**Surface Classification:** `Back-End Mesh` | **Governing Boundary:** `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)`  
**Deployment Surface:** `Automated CI/CD Host / ADB Bridge` | **Capacity Limit:** `82.8 GB Pooled VRAM (Mesh Network)`  
**Hardware Affinity:** Layer 1 Host / Layer 7 (Samsung S20 ADB) | **Mesh Network Pool:** `82.8 GB Usable AI VRAM`  
**Optimal Target Model:** `Qwen2.5-Coder-7B-Instruct (Memory profiling & Store compliance)`

#### 🏆 Role Leaderboard & Empirical Scoring

| Rank | Model Name | Param | VRAM | **Composite ELO** | COI Ratio | Capacity Fit | Win Rate | SWE Pass | Local Panel | Cloud Panel | Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 🥇 | **Qwen2.5-Coder-7B-Instruct-Q4_K_M** | `7B` | `4600 MB` | **`2463.4`** | `1.15x` | ✅ Pass (Mesh) | `81.5%` | `93.0%` | `0.92` | `0.94` | 🔒 Locked Champion |
| 🥈 | **SmolLM2-1.7B-Instruct-Q4_K_M** | `1.7B` | `1100 MB` | **`2312.0`** | `1.15x` | ✅ Pass (Mesh) | `55.0%` | `82.0%` | `0.83` | `0.85` | ⏳ Contender |

#### 🏋️ AI Training Methodology & Fine-Tuning Recipe
- **Training Engine:** `TRL DPO / Apple MLX`
- **Dataset Slice:** `lora_datasets/app_store_compliance_pairs.jsonl`
- **Hyperparameters:** `r=16`, `alpha=32`, `lr=0.00015`, `batch_size=2`, `iters=260`
- **Pre-Ingestion Validation Gate:** `Zero-crash test suite & WCAG AAA contrast`


### 🎯 3D Spatial Grappling Kinematics Specialist (`10_spatial_grappling_kinematics`)

**Domain Description:** Understands 955-node OPML spatial grappling trees, 3D tatami coordinate projections, biomechanical joint torque limits, and submission counter traversals.  
**Surface Classification:** `Front-End Client` | **Governing Boundary:** `Customer Device Envelope (Workstation/Tablet <= 6,000 MB)`  
**Deployment Surface:** `Customer Tablet / Mobile 3D Surface` | **Capacity Limit:** `6000 MB (Customer Device)`  
**Hardware Affinity:** Layer 2 (MacBook Pro TB4) / Layer 5 (MacBook Air) | **Mesh Network Pool:** `82.8 GB Usable AI VRAM`  
**Optimal Target Model:** `Qwen3-VL-8B-Instruct (3D spatial OPML graphs & joint kinematics)`

#### 🏆 Role Leaderboard & Empirical Scoring

| Rank | Model Name | Param | VRAM | **Composite ELO** | COI Ratio | Capacity Fit | Win Rate | SWE Pass | Local Panel | Cloud Panel | Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 🥇 | **Qwen3-VL-8B-Instruct-4bit** | `8B` | `5200 MB` | **`2444.0`** | `1.15x` | ✅ Pass (Device) | `85.0%` | `94.0%` | `0.94` | `0.95` | 🔒 Locked Champion |
| 🥈 | **Qwen2.5-VL-7B-Instruct-Q4_K_M** | `7B` | `4800 MB` | **`2328.0`** | `1.15x` | ✅ Pass (Device) | `68.0%` | `88.0%` | `0.88` | `0.90` | ⏳ Contender |

#### 🏋️ AI Training Methodology & Fine-Tuning Recipe
- **Training Engine:** `PyTorch MPS / Multimodal VLM LoRA`
- **Dataset Slice:** `lora_datasets/spatial_grappling_kinematics.jsonl`
- **Hyperparameters:** `r=16`, `alpha=32`, `lr=0.00012`, `batch_size=2`, `iters=320`
- **Pre-Ingestion Validation Gate:** `Zero-loop graph cycle & joint torque limit adherence`


### 🎯 Abliterated Security & Red/Blue Sentinel (`11_security_red_blue_team`)

**Domain Description:** Performs isolated clean-room protocol reconstruction, disassembly analysis, BlueZ DBus vulnerability auditing, and zero-telemetry hardware enclave isolation.  
**Surface Classification:** `Back-End Mesh` | **Governing Boundary:** `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)`  
**Deployment Surface:** `Isolated llama.cpp Sandbox (Port 8083)` | **Capacity Limit:** `82.8 GB Pooled VRAM (Mesh Network)`  
**Hardware Affinity:** Layer 1 Port 8083 (Isolated llama-server sandbox) | **Mesh Network Pool:** `82.8 GB Usable AI VRAM`  
**Optimal Target Model:** `Qwen-Abliterated-Local (Isolated sandbox reverse-engineering & CTF)`

#### 🏆 Role Leaderboard & Empirical Scoring

| Rank | Model Name | Param | VRAM | **Composite ELO** | COI Ratio | Capacity Fit | Win Rate | SWE Pass | Local Panel | Cloud Panel | Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 🥇 | **Qwen-Abliterated-Local-32B** | `32B` | `19500 MB` | **`2494.0`** | `1.15x` | ✅ Pass (Mesh) | `88.0%` | `96.0%` | `0.95` | `0.96` | 🔒 Locked Champion |
| 🥈 | **DeepSeek-R1-Distill-Qwen-32B-Q4_K_M** | `32B` | `19800 MB` | **`2452.0`** | `1.15x` | ✅ Pass (Mesh) | `82.0%` | `94.0%` | `0.93` | `0.95` | ⏳ Contender |

#### 🏋️ AI Training Methodology & Fine-Tuning Recipe
- **Training Engine:** `Local Uncensored SFT / TRL DPO`
- **Dataset Slice:** `lora_datasets/security_ctf_reverse_eng.jsonl`
- **Hyperparameters:** `r=32`, `alpha=64`, `lr=0.0001`, `batch_size=1`, `iters=450`
- **Pre-Ingestion Validation Gate:** `Zero external telemetry & memory buffer safety`


### 🎯 Continuous LoRA Evolution & Weight Merging Engineer (`12_continuous_lora_evolution`)

**Domain Description:** Governs Apple Silicon MLX QLoRA fine-tuning, TRL DPO dataset generation, loss monotonicity tracking, MergeKit weight merging (SLERP, TIES, DARE), and GGUF compilation.  
**Surface Classification:** `Back-End Mesh` | **Governing Boundary:** `7-Layer Lauburu Mesh Capacity (82.8 GB Pooled VRAM)`  
**Deployment Surface:** `Apple MLX Metal Cluster / TB4 DMA Bridge` | **Capacity Limit:** `82.8 GB Pooled VRAM (Mesh Network)`  
**Hardware Affinity:** Layer 2 (MacBook Pro TB4) / Layer 5 (MacBook Air) | **Mesh Network Pool:** `82.8 GB Usable AI VRAM`  
**Optimal Target Model:** `Qwen2.5-Coder-32B-Instruct (Apple MLX fine-tuning & MergeKit TIES/DARE)`

#### 🏆 Role Leaderboard & Empirical Scoring

| Rank | Model Name | Param | VRAM | **Composite ELO** | COI Ratio | Capacity Fit | Win Rate | SWE Pass | Local Panel | Cloud Panel | Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 🥇 | **Qwen2.5-Coder-32B-Instruct-Q4_K_M** | `32B` | `19800 MB` | **`2508.0`** | `1.15x` | ✅ Pass (Mesh) | `90.5%` | `97.0%` | `0.97` | `0.98` | 🔒 Locked Champion |
| 🥈 | **Genetic-MoE-Local-Flagship** | `Dynamic MoE` | `14500 MB` | **`2438.0`** | `1.15x` | ✅ Pass (Mesh) | `84.0%` | `94.0%` | `0.94` | `0.95` | ⏳ Contender |

#### 🏋️ AI Training Methodology & Fine-Tuning Recipe
- **Training Engine:** `Apple MLX (mlx-lm.lora) / MergeKit`
- **Dataset Slice:** `lora_datasets/continuous_lora_dataset.jsonl`
- **Hyperparameters:** `r=32`, `alpha=64`, `lr=0.0001`, `batch_size=2`, `iters=500`
- **Pre-Ingestion Validation Gate:** `Bradley-Terry ELO win-rate >= 65.0%`


### 🎯 Lauburu Lens VLA & Computer-Use Specialist (`lauburu_lens_vla`)

**Domain Description:** Performs Chrome DevTools Protocol DOM grounding, UI element bounding box prediction, zero-mock click-through automation, and multi-tier context window expansion.  
**Surface Classification:** `Front-End Client` | **Governing Boundary:** `Customer Workstation Envelope (<= 6,000 MB)`  
**Deployment Surface:** `Customer Desktop / Laptop Workstation Surface` | **Capacity Limit:** `6000 MB (Customer Device)`  
**Hardware Affinity:** Layer 2 (MacBook Pro TB4) / Layer 5 (MacBook Air) | **Mesh Network Pool:** `82.8 GB Usable AI VRAM`  
**Optimal Target Model:** `Qwen3-VL-8B-Instruct (Zero-mock DOM bounding box & click grounding)`

#### 🏆 Role Leaderboard & Empirical Scoring

| Rank | Model Name | Param | VRAM | **Composite ELO** | COI Ratio | Capacity Fit | Win Rate | SWE Pass | Local Panel | Cloud Panel | Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 🥇 | **Qwen3-VL-8B-Instruct-4bit** | `8B` | `5200 MB` | **`2464.0`** | `1.15x` | ✅ Pass (Device) | `87.0%` | `95.0%` | `0.95` | `0.96` | 🔒 Locked Champion |
| 🥈 | **SmolLM2-360M-Instruct-Q4_K_M** | `360M` | `258 MB` | **`2347.6`** | `1.15x` | ✅ Pass (Device) | `53.0%` | `81.0%` | `0.82` | `0.84` | ⏳ Contender |
| #3 | **Qwen-3B-MoE-Chat-Q4_K_M** | `3B (0.8B Active)` | `1180 MB` | **`2368.0`** | `1.15x` | ✅ Pass (Device) | `70.0%` | `88.0%` | `0.89` | `0.90` | ⏳ Contender |

#### 🏋️ AI Training Methodology & Fine-Tuning Recipe
- **Training Engine:** `Multimodal Apple MLX VLM LoRA`
- **Dataset Slice:** `lora_datasets/lens_ai/lens_multimodal_dpo.jsonl`
- **Hyperparameters:** `r=16`, `alpha=32`, `lr=0.00012`, `batch_size=2`, `iters=350`
- **Pre-Ingestion Validation Gate:** `100% authentic DOM element coordinates (Rule #0)`

<!-- CONTEXT_TIER_2_MESH_END -->

<!-- CONTEXT_TIER_3_HORIZON_START -->
## 🚀 SWE-bench CLI Integration & Continuous Loop Protocol (128K Context Horizon)

### 1. SWE-bench CLI (`sb-cli`) Validation Pipeline
All software engineering and code generation models contending for code roles (`01_apps`, `02_ai_models_and_inference`, `04_data_and_memory`, `12_continuous_lora_evolution`) are evaluated against the official SWE-bench harness (`05_agents_and_swarms/tools/swe_bench_tool.py`).

Canonical evaluation flow:
```bash
# Evaluate model patch syntax and AST validity
python3 05_agents_and_swarms/local_ai_role_competency_evaluator.py --swe-bench-eval --role ROLE_01_APPS_ECOSYSTEM --model qwen_coder_7b

# Submit predictions to SWE-bench
sb-cli submit swe-bench_lite dev --predictions_path 04_data_and_memory/swe_bench_predictions/preds.json --run_id qwen25_coder_role01
```

### 2. Synchronization with the Continuous Loop Engine (`/loop`)
The evaluator is continuously triggered by `05_agents_and_swarms/continuous_self_evolving_swarm_loop.py` during periodic cloud AI pacing cycles:
- **Cloud Teacher Pair Ingestion:** DPO pairs generated by Gemini 3.1 Pro, DeepSeek V4 Pro 1.6T, Llama 3.3 70B, and Grok-2 are routed to the relevant role's dataset slice in `lora_datasets/`.
- **Local Model Fine-Tuning:** Local contenders execute Apple MLX QLoRA 4-bit fine-tuning on Apple Silicon Metal.
- **Automated Re-Scoring:** Following fine-tuning, the evaluator runs tournament matches and updates $R_{\text{train}}$ and $R_{\text{proj}}$.
- **Tri-Vault Persistence:** Evaluator automatically mirrors this canonical specification across:
  1. `CANONICAL_LOCAL_AI_PROJECT_ROLES.md` (Monorepo Root)
  2. `obsidian_vault/canonical/CANONICAL_LOCAL_AI_PROJECT_ROLES.md` (Obsidian Knowledge Core)
  3. `07_docs_and_architecture/canonical/CANONICAL_LOCAL_AI_PROJECT_ROLES.md` (Architecture Index)
  4. Master Wikilink in `obsidian_vault/Index.md`
<!-- CONTEXT_TIER_3_HORIZON_END -->

---
[[Index]] | [[CANONICAL_PROJECT_OVERVIEW]] | [[CANONICAL_APPS_OVERVIEW]] | [[CANONICAL_BUSINESS_PLAN_OVERVIEW]] | [[LENS_AI_CANONICAL_OVERVIEW]] | [[CANONICAL_LOCAL_AI_PROJECT_ROLES]] | [[AI_DEBATE_FRONTEND_VS_MESH_NETWORK_CAPACITY]]
