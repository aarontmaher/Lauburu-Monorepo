#!/usr/bin/env python3
"""
generate_canonical_overviews.py
Generates the 4 Canonical Overview Markdown documents with hierarchical context window chunking
for Lens AI context expanding functionality and synchronizes them across the Tri-Vault storage layers.
"""

import os
from pathlib import Path

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
VAULT_CANONICAL = REPO_ROOT / "obsidian_vault" / "canonical"
DOCS_CANONICAL = REPO_ROOT / "07_docs_and_architecture" / "canonical"

VAULT_CANONICAL.mkdir(parents=True, exist_ok=True)
DOCS_CANONICAL.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# 1. CANONICAL_PROJECT_OVERVIEW.md
# ==============================================================================
PROJECT_OVERVIEW_CONTENT = """# 🏛️ Canonical Project Overview — Lauburu Mesh Ecosystem

```
========================================================================================
LAUBURU MESH ECOSYSTEM — CANONICAL PROJECT OVERVIEW & CONTEXT-EXPANDING ARCHITECTURE
Version: 3.0.0-CANONICAL-2026 | Authority: Aaron (Sovereign) | Integrity: Zero-Mock
Subsystems: 8 Canonical Subsystems | Mesh Nodes: 7 Physical Layers | Pooled VRAM: 85.02 GB
========================================================================================
```

---

<!-- CONTEXT_WINDOW_TIER_0_START: 4K_EXECUTIVE_CORE -->
## 🧭 Context Window Tier 0: Executive Core & System Invariants (~4,000 Tokens)

> **Lens AI Ingestion Target:** Fast Edge Micro-Models (`SmolLM2-135M`, `Pixel 10 Pro XL Edge TPU`, `Termux Edge Daemon`).  
> **Processing Latency:** `<15ms` | **Memory Overhead:** `<64 MB`.

### 1. The Core Sovereign Mission
The **Lauburu Mesh Ecosystem** is a decentralized, self-healing, polyglot artificial intelligence and biometrics platform. It aggregates **108.0 GB Physical RAM (85.02 GB Pooled AI VRAM)** across a 7-layer physical hardware mesh, operating under a strict **$0.00 cloud spend mandate** while maintaining 24/7 continuous model training, real-time medical-grade biometrics (512Hz ECG), interactive 3D biomechanics, and multimodal computer vision action synthesis.

### 2. The 5 Cardinal Invariants
1. **Rule #0 (Zero-Mock & Zero-Simulation Mandate):** Absolutely zero simulated data, fake arrays, fabricated timestamps, or synthetic telemetry. Metrics must originate from live physical sensors (Movesense BLE), kernel syscalls (`vm_stat`, `/proc/meminfo`), authentic DOM queries via Chrome DevTools Protocol, or display clean waiting states (`--`).
2. **Local AI First ($0 Cost):** Inference and training prioritize local Apple Silicon Metal Performance Shaders and 10Gbps Thunderbolt 4 DMA bridges. Paid cloud APIs (`gpt-4*`, `claude-3*`, `o1*`) are strictly forbidden. Commercial GCP credits ($1,400.00) remain 100% untouched.
3. **Host Sanctuary & Dynamic RAM Governance:** The primary Mac Mini M4 Pro host (24 GB unified RAM) must strictly maintain $\\ge 8.0\\text{ GB}$ of free physical RAM at all times. Memory utilization must not exceed 90%. Compute exceeding safe headroom is dynamically offloaded to peripheral nodes.
4. **Tri-Vault Storage Synchronization:** All system state, debate consensus records, training pairs, and source code are continuously synchronized across three synchronized tiers:
   - **Obsidian Knowledge Core (`obsidian_vault/`):** Semantic knowledge, bidirectional Wikilinks, KaTeX math.
   - **PySpark Data Lake (`lora_datasets/` & `04_data_and_memory/`):** High-throughput Delta Lake/Parquet, 24/7 LoRA pairs.
   - **GitHub Repository & Worktrees:** Canonical source code, container manifests, CI test suites.
5. **99% Cloud Quota Constant-Rate Pacing:** Free-tier cloud APIs (Google AI Studio 1,500 RPD, NVIDIA NIM 2,000 RPD, Cloudflare 800 RPD, xAI Grok 1,000 RPD) are paced to consume exactly 99.0% of daily quotas continuously without 429 rate-limiting, harvesting teacher distillation pairs for local models before each 10:00:00 AM AEST (00:00 UTC) reset.

### 3. 7-Layer Physical Mesh Hardware Matrix
```
┌───────┬──────────────────┬──────────────────┬─────────────────┬───────────────────┬───────────────────────────────────────────┐
│ Layer │ Node Name        │ Architecture     │ Local / Mesh IP │ Usable VRAM / RAM │ Primary Function                          │
├───────┼──────────────────┼──────────────────┼─────────────────┼───────────────────┼───────────────────────────────────────────┤
│ L1    │ Mac_Node         │ Apple M4 Pro     │ 192.168.8.230   │ 21.6 GB (24 GB)   │ Host Memory Governor & Root Orchestrator  │
│ L2    │ MacBook_Pro      │ Apple M4 Pro TB4 │ 169.254.187.138 │ 14.0 GB (16 GB)   │ 10Gbps TB4 DMA Bridge (0.27ms RTT) Vault  │
│ L3    │ Linux_Head_Node  │ AMD Ryzen 7 5700U│ 192.168.8.224   │ 13.8 GB (16 GB)   │ Docker Hub, Petals DHT, Ray Cluster       │
│ L4    │ Linux_Tablet     │ Debian Linux ARM │ DHCP (100.81)   │ 6.5 GB (8 GB)     │ Mobile Touch DSP & Edge Audio Ingestion   │
│ L5    │ MacBook_Air      │ Apple M4 Air     │ 192.168.8.222   │ 14.0 GB (16 GB)   │ Secondary Metal Worker & LoRA Trainer     │
│ L6    │ Pixel_10_Pro_XL  │ Tensor G5 + TPU  │ DHCP (100.73)   │ 12.5 GB (16 GB)   │ 8K PTZ Vision Stream & Edge TPU VLA       │
│ L7    │ Samsung_S20      │ Exynos 990 + ADB │ 100.78.206.96    │ 9.0 GB (12 GB)    │ 24/7 Termux UI Tester & ADB Node          │
│ GW    │ GL.iNet Beryl 7  │ MediaTek MT7988A │ 192.168.8.1     │ Embedded Router   │ Wi-Fi 7 MLO, USB ADB Bridge, kmwan Multi-WAN│
└───────┴──────────────────┴──────────────────┴─────────────────┴───────────────────┴───────────────────────────────────────────┘
```
<!-- CONTEXT_WINDOW_TIER_0_END -->

---

<!-- CONTEXT_WINDOW_TIER_1_START: 16K_SUBSYSTEM_CONTRACTS -->
## 📦 Context Window Tier 1: Canonical Subsystem Specifications (~16,000 Tokens)

> **Lens AI Ingestion Target:** Local Workhorse Models (`Qwen2.5-Coder-7B` on Port 8081, `Mistral-Nemo-Instruct` on Port 8083).  
> **Processing Latency:** `30–80ms` | **Memory Overhead:** `<380 MB`.

The monorepo is divided into 8 numbered canonical directories and the Obsidian vault, each enforcing strict isolation boundaries and public API contracts:

### 1. `00_core_infrastructure/` — Distributed Fabric & Self-Healing Hub
- **Self-Healing Hub (Port 18802):** Central health daemon monitoring systemd/launchd daemons, REST health checks, and Wake-on-LAN resurrection for sleeping mesh nodes.
- **SeaweedFS Distributed File System:** Master server on Port 9333, volume server on Port 8080, filer on Port 8888 providing unified POSIX storage across all 7 nodes.
- **Tailscale Mesh Overlay:** Encrypted WireGuard overlay connecting all nodes globally via `100.*.*.*` IPs, with automatic direct-peer hole punching and DERP relay fallback.
- **Docker Compose Topology:** Standardized container manifests for multi-arch deployment (`linux/amd64`, `linux/arm64`, `darwin/arm64`).

### 2. `01_apps/` — User Interfaces, Biometrics, Commerce & Vision
- **Port 4000 Unified Console:** Consolidated Flutter + Rust Ratatui mission control aggregating telemetry, 3D tatami kinematics, and AI conversation feeds.
- **Lauburu Lens & Screen Lens:** Autonomous multimodal Vision-Language-Action (VLA) computer-use engine with Chrome DevTools Protocol integration and SnapKV context expansion.
- **Movesense Biometrics Hub:** 512Hz single-lead medical-grade ECG streamer with real-time Pan-Tompkins QRS detection and pulse transit time (PTT) blood pressure estimation.
- **Zone 2 Cardio & DFA-$\\alpha_1$:** Heart rate variability (HRV) fractal correlation analysis identifying aerobic threshold transitions in real time.
- **Spatial Grappling 3D:** Interactive Three.js / WebGL biomechanical world model visualising a 955-node OPML martial arts curriculum with joint torque vectors.
- **Shopify AI Commerce Engine:** Headless Storefront GraphQL integration managing rashguards, apparel bundles, and recurring club memberships.
- **Automotive Voice Coding Hub:** Android Auto DHU integration with hands-free STT/TTS voice pair-programming, Region Backspace, and automotive audio focus ducking.

### 3. `02_ai_models_and_inference/` — Distributed Sharding & GGUF Vault
- **`prima.cpp` Pipelined Ring Mesh (Port 8082):** Distributed pipelined ring parallelism pooling 85.02 GB VRAM across 7 nodes at 24.5 tok/s.
- **`llama-server` RPC Cluster (Ports 8081–8084):** Metal-accelerated local GGUF execution with RPC remote worker offloading to MacBook Pro (L2) and Linux Head Node (L3).
- **Physical Model Vault:** High-speed storage under `model_vault_gguf/` hosting SmolLM2 (135M, 360M, 1.7B), Qwen2.5 (0.5B, 1.5B, 7B), Llama 3.2 (1B), and Mistral Nemo (12.2B).

### 4. `03_biometrics_and_telemetry/` — DSP Signal Processing
- **Pan-Tompkins Algorithm:** Bandpass filtering (5–15 Hz), derivative squaring, moving window integration, and dynamic thresholding detecting R-peaks with sub-millisecond precision.
- **HRV & Autonomic Tone:** Time-domain (RMSSD, SDNN, pNN50) and frequency-domain (LF/HF ratio, Sample Entropy) analytics.
- **Zero-Mock Bluetooth Transport:** Direct BLE GATT streaming (`service: 0000180d`, `characteristic: 00002a37`) avoiding all simulated signal generators.

### 5. `04_data_and_memory/` — Big Data Lake & Continuous LoRA Sinks
- **Continuous LoRA Dataset (`continuous_lora_dataset.jsonl`):** 24/7 ingestion sink capturing validated diffs, AST mutations, and multi-model debate consensus records.
- **Lens Multimodal DPO Dataset (`lens_multimodal_dpo.jsonl`):** 2,221+ authentic Next-Best-Action DPO triplets grounded in live DOM coordinates.
- **PySpark & Delta Lake Engine:** High-throughput batch feature engineering, AST compiler tokenization, and vector embeddings indexed into Qdrant.

### 6. `05_agents_and_swarms/` — Swarm Orchestration & Genetic MoE
- **Tri-Orchestrator AI Debate Council:** Multi-model dialectic debate panel (DeepSeek V4 Pro 1.6T, Gemini 2.0/3.1 Pro, Devil's Advocate, Local Qwen MoE) with mathematical consensus scoring ($S \\ge 0.98$).
- **Cloud AI Routing Governor:** Zero-cost dynamic routing across free cloud APIs and local Metal models based on task domain and daily quota headroom.
- **Self-Evolving Generational Swarm Engine:** Bradley-Terry ELO tournament system pairing models and agents to continuously select superior prompts and weights.

### 7. `06_scripts_and_tooling/` — Network Daemons & Hardware Automation
- **Lens Rapid Quota Maximizer:** High-concurrency 4-worker thread daemon streaming authentic DPO queries at ~48 RPM pooled to achieve 99% quota utilization.
- **Continuous Constant-Rate Pacer:** 24-hour steady-state scheduler ensuring smooth quota consumption (Gemini 1 req/58.2s, DeepSeek 1 req/44.0s).
- **Universal SSH & ADB Keepalive:** Automated keepalive daemons injecting `termux-wake-lock`, battery optimization bypasses, and SSH heartbeat sockets.

### 8. `07_docs_and_architecture/` & `obsidian_vault/` — Knowledge Graph
- **Obsidian Vault:** 41 MCP tools, graph traversal, bi-directional Wikilinks, KaTeX formulas, and active operational dashboards (`CLOUD_API_RESET_AND_99_PACING_DASHBOARD.md`).
- **Canonical Architecture Specs:** Security RFCs, memory-mapped ring buffer whitepapers, and hardware schematics.
<!-- CONTEXT_WINDOW_TIER_1_END -->

---

<!-- CONTEXT_WINDOW_TIER_2_START: 32K_MESH_TOPOLOGY_AND_DATA_FLOWS -->
## 🌐 Context Window Tier 2: Mesh Topology, Transport Matrix & Dataflows (~32,000 Tokens)

> **Lens AI Ingestion Target:** Distributed Swarm Coordinator (`prima.cpp` 80B Ring on Port 8082, Whole-Monorepo AST Evaluator).  
> **Processing Latency:** `120–250ms` | **Memory Overhead:** `<1.2 GB`.

### 1. Inter-Node Communication & Transport Matrix
```mermaid
graph TD
    subgraph L1_HOST["L1: Mac Mini M4 Pro (Host Sanctuary)"]
        RAM_GOV["Dynamic RAM Governor (>=8.0 GB Free)"]
        CONSOLE["Port 4000 Console"]
        LENS_CORE["Lauburu Lens VLA Core"]
        ROUTING["Cloud AI Routing Governor"]
    end

    subgraph L2_TB4["L2: MacBook Pro (Storage Vault)"]
        TB4_BRIDGE["10Gbps TB4 DMA Bridge (0.27ms RTT)"]
        GGUF_VAULT["285 GB SSD Model Vault"]
        RPC_WORKER_1["llama.cpp RPC Worker"]
    end

    subgraph L3_LINUX["L3: Linux Head Node (Compute Hub)"]
        DOCKER_HUB["Docker Daemon & Containers"]
        RAY_CLUSTER["Apache Ray & Petals DHT"]
        RPC_WORKER_2["Linux RPC Shard"]
    end

    subgraph L6_L7_MOBILE["L6 & L7: Mobile Edge Nodes"]
        PIXEL_TPU["Pixel 10 Pro XL (Edge TPU / 8K Camera)"]
        SAMSUNG_S20["Samsung S20 (Termux UI Automator)"]
    end

    L1_HOST <== "10Gbps Thunderbolt 4 (PCIe DMA)" ==> L2_TB4
    L1_HOST <== "1GbE Ethernet / Tailscale WireGuard" ==> L3_LINUX
    L1_HOST <== "USB ADB / Tailscale TCP 5555" ==> L6_L7_MOBILE
    L1_HOST <== "BLE GATT 512Hz ECG" ==> MOVESENSE["Movesense Sensor"]
```

### 2. End-to-End Dataflow Pipelines
1. **Biometric Pipeline:**
   $$\\text{Movesense BLE (512Hz)} \\xrightarrow{\\text{GATT}} \\text{CoreBluetooth} \\xrightarrow{\\text{DSP Bandpass}} \\text{Pan-Tompkins QRS} \\xrightarrow{\\text{PTT/HRV}} \\text{Port 4000 WebSocket} \\xrightarrow{\\text{Parquet}} \\text{04\\_data\\_and\\_memory}$$
2. **Computer-Use VLA Pipeline:**
   $$\\text{Active Viewport} \\xrightarrow{\\text{Chrome CDP}} \\text{DOM Element Extractor} \\xrightarrow{\\text{WCAG AAA Gate}} \\text{Teacher Inference (Gemini/DeepSeek)} \\xrightarrow{\\text{DPO Triplet}} \\text{lens\\_multimodal\\_dpo.jsonl} \\xrightarrow{\\text{MLX QLoRA}} \\text{Local Metal}$$
3. **Continuous Swarm Optimization Pipeline:**
   $$\\text{Conversation Events} \\xrightarrow{\\text{Transcript Parser}} \\text{AI Debate Council} \\xrightarrow{S \\ge 0.98} \\text{Consensus Verdict} \\xrightarrow{\\text{AST Delta}} \\text{Obsidian Vault} \\xrightarrow{\\text{Bradley-Terry}} \\text{ELO Leaderboard}$$
<!-- CONTEXT_WINDOW_TIER_2_END -->

---

<!-- CONTEXT_WINDOW_TIER_3_START: 128K_HORIZON_EXPANSION -->
## 🔮 Context Window Tier 3: Horizon Evolution & Infinite Scaling (~128,000+ Tokens)

> **Lens AI Ingestion Target:** Frontier Cloud Teachers (`Gemini 3.1 Pro Preview` 2M Context, `DeepSeek V4 Pro 1.6T` 1M Context).  
> **Processing Latency:** Cloud Async (`1–3s`) | **Memory Overhead:** Cloud Offloaded ($0 Cost).

### 1. The 24/7 Self-Evolving Generational Lifecycle
The system operates as an autonomous self-improving organism through generational cycles:
- **Generation N:** Baseline models execute inference, record telemetry, and detect edge failures.
- **Mutation & Cross-Pollination:** Agent prompts and model hyperparameters mutate within `01_apps/screen_lens/sandbox_evolution/` without touching production baselines (Rule #4).
- **Bradley-Terry Tournament Battles:** Candidate agents compete pairwise across standardized test suites. Ratings adjust dynamically:
  $$P(A > B) = \\frac{1}{1 + 10^{(R_B - R_A)/400}}$$
- **Weight Merging & Quantization:** Winning adapter checkpoints are merged via MergeKit (TIES, DARE, SLERP) back into base GGUFs, quantized to `Q4_K_M`, and hot-reloaded into `prima.cpp` (:8082).

### 2. Context Window Partitioning & Lens Dynamic Foveation Table
```
┌─────────────────┬────────────────────┬──────────────────────────────────────┬──────────────────────────────────────────┐
│ Window Tier     │ Max Token Budget   │ Primary Target Models                │ Ingestion Use Case                       │
├─────────────────┼────────────────────┼──────────────────────────────────────┼──────────────────────────────────────────┤
│ Tier 0 (Core)   │ 4,096 Tokens       │ SmolLM2-135M, Edge TPU, Termux CLI   │ Instant state checks, invariants, routes │
│ Tier 1 (Spec)   │ 16,384 Tokens      │ Qwen2.5-Coder-7B, Mistral-Nemo-12B   │ Subsystem logic, API contracts, schemas  │
│ Tier 2 (Mesh)   │ 32,768 Tokens      │ prima.cpp Ring Mesh, Sharded Cluster │ Cross-layer routing, IPC, full topology  │
│ Tier 3 (Horizon)│ 131,072–1,000,000+ │ Gemini 3.1 Pro, DeepSeek V4 Pro      │ Macro architecture, DPO history, audits  │
└─────────────────┴────────────────────┴──────────────────────────────────────┴──────────────────────────────────────────┘
```
<!-- CONTEXT_WINDOW_TIER_3_END -->
"""

# ==============================================================================
# 2. CANONICAL_APPS_OVERVIEW.md
# ==============================================================================
APPS_OVERVIEW_CONTENT = """# 📱 Canonical Apps Overview — Lauburu Application Ecosystem

```
========================================================================================
LAUBURU ECOSYSTEM — CANONICAL APPLICATIONS & FRONTEND INTERFACE MATRIX
Version: 3.0.0-APPS-2026 | Authority: Aaron (Sovereign) | Standard: Zero-Mock UI
Port Range: 4000–18802 | Client Surfaces: Flutter, Rust Ratatui, Three.js WebGL, Termux
========================================================================================
```

---

<!-- CONTEXT_WINDOW_TIER_0_START: 4K_PORT_AND_HEALTH_INDEX -->
## 🧭 Context Window Tier 0: Port & Service Directory (~4,000 Tokens)

> **Lens AI Ingestion Target:** Fast Edge Micro-Models (`SmolLM2-135M`, `Pixel 10 Pro XL Edge TPU`, `Termux Edge Daemon`).  
> **Processing Latency:** `<15ms` | **Memory Overhead:** `<64 MB`.

### 1. Active Application Port Directory
```
┌───────┬──────────────────────────────┬────────────────────────┬─────────────────────────┬───────────────────────────┐
│ Port  │ Application Name             │ Framework / Engine     │ Host / Target Device    │ Primary Service Function  │
├───────┼──────────────────────────────┼────────────────────────┼─────────────────────────┼───────────────────────────┤
│ :4000 │ Unified Console & Portal     │ Flutter / Rust Ratatui │ L1: Mac Mini M4 Pro     │ Master System HUD & Stats │
│ :4002 │ Marimo Notebook Dashboard    │ Marimo Reactive Python │ L1: Mac Mini M4 Pro     │ Interactive DSP & Charts  │
│ :4003 │ Screen Lens MJPEG Stream     │ Python HTTP Multipart  │ L1: Mac Mini M4 Pro     │ Live 15 FPS Video Stream  │
│ :8080 │ SeaweedFS Volume Server      │ Go SeaweedFS           │ L1: Mac Mini M4 Pro     │ Raw Block Object Storage  │
│ :8081 │ llama.cpp Master RPC Server  │ C++20 GGML Metal       │ L1: Mac Mini M4 Pro     │ Local Model Inference     │
│ :8082 │ prima.cpp Ring Coordinator   │ C++20 / Python Pipelined│ Distributed (7 Nodes)  │ 85.02 GB VRAM Ring Mesh   │
│ :8083 │ Devil's Advocate Server      │ llama.cpp Abliterated  │ L1: Mac Mini M4 Pro     │ Adversarial Red-Teaming   │
│ :8888 │ SeaweedFS Filer Endpoint     │ Go SeaweedFS           │ L1: Mac Mini M4 Pro     │ POSIX File System Ingress │
│ :8890 │ Voilà Interactive Portal     │ Jupyter Voilà Python   │ L1: Mac Mini M4 Pro     │ Biometrics & Graph UI     │
│ :9333 │ SeaweedFS Master Server      │ Go SeaweedFS           │ L1: Mac Mini M4 Pro     │ DFS Cluster Coordination  │
│:18802 │ Self-Healing Hub             │ FastAPI + React SPA    │ L1: Mac Mini M4 Pro     │ Health, WoL & Watchdogs   │
│ :5555 │ Wireless ADB Server          │ Android Debug Bridge   │ L6 & L7 (Pixel / S20)   │ USB/TCP Automation Link   │
└───────┴──────────────────────────────┴────────────────────────┴─────────────────────────┴───────────────────────────┘
```

### 2. Global UI Invariants
1. **Rule #0 Zero-Mock UI:** No fake telemetry or static placeholder strings. Live biometric displays must show authentic signal waveforms or clean waiting state indicators (`--`).
2. **WCAG AAA Visual Compliance:** All text and interactive targets maintain $\\ge 7:1$ (typically $\\ge 14.2:1$) contrast ratios for high-speed automated computer-vision parsing.
3. **Sub-100ms Input-to-Glass Latency:** UI interactions and biometric sweeps update within 100ms across all device surfaces.
<!-- CONTEXT_WINDOW_TIER_0_END -->

---

<!-- CONTEXT_WINDOW_TIER_1_START: 16K_APP_DEEP_SPECIFICATIONS -->
## 📦 Context Window Tier 1: Application Deep Specifications (~16,000 Tokens)

> **Lens AI Ingestion Target:** Local Workhorse Models (`Qwen2.5-Coder-7B` on Port 8081, `Mistral-Nemo-Instruct` on Port 8083).  
> **Processing Latency:** `30–80ms` | **Memory Overhead:** `<380 MB`.

### 1. Port 4000 Unified Console (`01_apps/port_4000_flutter_rust/`)
- **Architecture:** Hybrid Flutter desktop frontend linked via Rust Foreign Function Interface (FFI) to a high-speed Crossterm/Ratatui immediate-mode terminal HUD.
- **Features:** 
  - Real-time 7-layer node health telemetry with per-node dynamic RAM headroom meters.
  - Tab 0: Visual Cortex & Next-Best-Action predictor showing Lens AI click coordinates.
  - Live AI conversation stream displaying Tri-Orchestrator debate consensus.
  - Integrated Movesense 512Hz ECG waveform oscilloscope.

### 2. Movesense Biometrics Hub (`01_apps/biometrics/`)
- **Architecture:** CoreBluetooth / BlueZ DBus native driver interfacing with Movesense Medical BLE sensor (`Movesense MD`).
- **Features:**
  - Ingests raw single-lead ECG data at 512Hz alongside 9-DOF IMU (accelerometer, gyroscope, magnetometer).
  - Onboard Pan-Tompkins QRS peak detection calculating instant RR-intervals (RRI) with sub-millisecond precision.
  - Computes pulse transit time (PTT) systolic/diastolic blood pressure estimates.
  - Real-time Detrended Fluctuation Analysis (DFA-$\\alpha_1$) predicting aerobic vs anaerobic Zone 2 cardiovascular thresholds.

### 3. Spatial Grappling 3D Kinematics (`01_apps/spatial_grappling_3d/`)
- **Architecture:** Three.js / WebGL hardware-accelerated 3D biomechanical renderer parsing a 955-node OPML spatial martial arts taxonomy (`grappling.opml`).
- **Features:**
  - 3D tatami mat world model with interactive skeletal humanoid avatars.
  - Dynamic joint torque, angular velocity, and fulcrum vector visualization.
  - Hierarchical branching of submission counters, sweeps, escapes, and control nodes.
  - Bidirectional sync with real-time biometric strain indices during grappling sessions.

### 4. Shopify AI Commerce Engine (`01_apps/commerce_and_business/shopify_ai/`)
- **Architecture:** Headless Next.js 14 / TypeScript Storefront querying Shopify GraphQL Admin & Storefront APIs.
- **Features:**
  - Autonomous merchandise sourcing, catalog generation, and image asset auditing.
  - Dedicated product line: Custom Lauburu compression rashguards, grappling shorts, and technical training gear.
  - Recurring club membership billing tiers with automated Stripe / Shopify checkout webhooks.
  - Automated profitability calculator analyzing CAC, LTV, shipping margins, and currency conversion.

### 5. Lauburu Lens & Screen Lens (`01_apps/lauburu_lens/` & `01_apps/screen_lens/`)
- **Architecture:** Python AsyncIO daemon interfacing with Chrome DevTools Protocol (CDP), macOS Accessibility APIs, and Android ADB.
- **Features:**
  - Multimodal Vision-Language-Action (VLA) computer-use engine.
  - Live DOM tree extraction querying bounding boxes and accessibility tags (`<button>`, `<input>`, `<a>`).
  - Automated Next-Best-Action synthesis generating verified DPO training pairs.
  - Continuous 10–15 FPS multipart MJPEG screen streaming on Port 4003 (`/stream.mjpg`).

### 6. Automotive Voice Coding Hub (`01_apps/automotive/`)
- **Architecture:** Android Auto Desktop Head Unit (DHU) projection service with whisper.cpp local speech-to-text (STT) and Piper local text-to-speech (TTS).
- **Features:**
  - In-vehicle hands-free pair programming and terminal voice interaction.
  - **Region Backspace Engine:** AST-aware voice deletion removing syntax blocks without leaving broken AST nodes.
  - **Audio Priority Levels:** Voice commands duck background music at level 2; emergency vehicle navigation prompts preempt and cancel AI speech at level 1.
<!-- CONTEXT_WINDOW_TIER_1_END -->

---

<!-- CONTEXT_WINDOW_TIER_2_START: 32K_INTER_APP_PIPELINES -->
## 🌐 Context Window Tier 2: Inter-App IPC Pipelines & Multi-Surface Routing (~32,000 Tokens)

> **Lens AI Ingestion Target:** Distributed Swarm Coordinator (`prima.cpp` 80B Ring on Port 8082, Whole-Monorepo AST Evaluator).  
> **Processing Latency:** `120–250ms` | **Memory Overhead:** `<1.2 GB`.

### 1. Inter-App IPC Communication Protocols
```
┌─────────────────────────┬─────────────────────────┬──────────────────────┬──────────────────────────────────────────┐
│ Source Application      │ Target Application      │ IPC Protocol / Path  │ Data Format & Payload                    │
├─────────────────────────┼─────────────────────────┼──────────────────────┼──────────────────────────────────────────┤
│ Movesense BLE Sensor    │ Biometrics Hub          │ BLE GATT Characteristic│ Raw 512Hz 16-bit ECG + IMU Bytes       │
│ Biometrics Hub          │ Port 4000 Console       │ WebSocket (:4000/ws) │ JSON: RR-intervals, DFA-a1, HR, SpO2     │
│ Screen Lens CDP Bridge  │ Lens Rapid Maximizer    │ Unix Domain Socket   │ DOM Hierarchy, Bounding Boxes, Viewport  │
│ Lens Rapid Maximizer    │ LoRA Dataset Sink       │ POSIX Append Stream  │ JSONL: Authentic DPO Triplet Records     │
│ AI Debate Scheduler     │ Obsidian Vault          │ File I/O + MCP Pro   │ Markdown: Debate Consensus & Loop Actions│
│ Termux UI Automator     │ Self-Healing Hub        │ HTTP REST (:18802)   │ JSON: Battery, Wakelock, Memory Telemetry│
│ Automotive Voice Daemon │ Local Qwen MoE (:8081)  │ HTTP Streaming POST  │ JSON / SSE: AST Code Edit Directives     │
└─────────────────────────┴─────────────────────────┴──────────────────────┴──────────────────────────────────────────┘
```

### 2. Multi-Device Accessibility & Remote Execution Matrix
- **macOS Mac Mini (L1):** Coordinates native macOS window management via `screencapture`, AppleScript UI events, and Darwin Mach kernel RAM counters.
- **Linux Head Node (L3):** Runs containerized test runners, SeaweedFS master/volume servers, and Ray distributed computation tasks over 1GbE.
- **Samsung Galaxy S20 (L7):** Dedicated automated mobile UI runner executing Termux scripts, testing mobile web responsiveness via Chrome DevTools over Port 5555.
- **Pixel 10 Pro XL (L6):** Dedicated Edge TPU worker running on-device int4 quantization models, processing real-time video feeds from its 8K digital PTZ camera.
<!-- CONTEXT_WINDOW_TIER_2_END -->

---

<!-- CONTEXT_WINDOW_TIER_3_START: 128K_MULTI_SURFACE_ORCHESTRATION -->
## 🔮 Context Window Tier 3: Multi-Surface Autonomous Testing (~128,000+ Tokens)

> **Lens AI Ingestion Target:** Frontier Cloud Teachers (`Gemini 3.1 Pro Preview` 2M Context, `DeepSeek V4 Pro 1.6T` 1M Context).  
> **Processing Latency:** Cloud Async (`1–3s`) | **Memory Overhead:** Cloud Offloaded ($0 Cost).

### 1. The Autonomous Multi-Surface Testing Loop
The application suite runs automated cross-surface regression and fuzz testing:
- **Chrome CDP Fuzzing:** Automated headless Chrome workers navigate web interfaces, inject adversarial click coordinates, and verify zero unhandled JavaScript exceptions.
- **WCAG AAA Compliance Audits:** High-speed computer-vision filters evaluate all rendered views against 7:1 contrast ratios and touch-target bounding boxes ($\\ge 48 \times 48\text{ px}$).
- **Biometric Stress Verification:** Telemetry streams undergo simulated packet drop, reconnect, and arrhythmia detection tests to verify DSP filter stability.
- **Automotive Audio Latency Benchmarking:** Voice commands undergo round-trip latency evaluation under ambient driving road noise profiles (Pink noise 65 dBA).
<!-- CONTEXT_WINDOW_TIER_3_END -->
"""

# ==============================================================================
# 3. CANONICAL_BUSINESS_PLAN_OVERVIEW.md
# ==============================================================================
BUSINESS_PLAN_CONTENT = """# 💼 Canonical Business Plan Overview — Lauburu Commercialization & Monetization

```
========================================================================================
LAUBURU ECOSYSTEM — CANONICAL BUSINESS PLAN, REVENUE ARCHITECTURE & UNIT ECONOMICS
Version: 3.0.0-BIZ-2026 | Authority: Aaron (Sovereign) | Financial Model: Zero-Spend Bootstrapped
Capital Target: $0.00 Cloud Spend -> Infinite Sustainable Cash Flow | Status: Active
========================================================================================
```

---

<!-- CONTEXT_WINDOW_TIER_0_START: 4K_EXECUTIVE_SUMMARY -->
## 🧭 Context Window Tier 0: Executive Summary & Financial Philosophy (~4,000 Tokens)

> **Lens AI Ingestion Target:** Fast Edge Micro-Models (`SmolLM2-135M`, `Pixel 10 Pro XL Edge TPU`, `Termux Edge Daemon`).  
> **Processing Latency:** `<15ms` | **Memory Overhead:** `<64 MB`.

### 1. The Core Commercial Vision
The **Lauburu Business Ecosystem** monetizes high-performance athletic intelligence, medical-grade physiological telemetry, and cutting-edge martial arts biomechanics. By pairing proprietary edge hardware and local AI processing with headless commerce, the platform eliminates traditional cloud infrastructure overhead, delivering **80%+ gross margins** across hardware, software SaaS, and premium technical apparel.

### 2. The $0.00 Cloud Spend Bootstrap Invariant
- **Total Venture Funding / Seed Burn:** **$0.00**.
- **Cloud Infrastructure Cost:** **$0.00 / month**. Operating entirely on pooled local Apple Silicon Metal hardware, 10Gbps Thunderbolt 4 DMA bridges, and permanent free-tier cloud quotas (Google AI Studio, NVIDIA NIM, Cloudflare, xAI).
- **Commercial GCP Credit Sanctuary:** The $1,400.00 commercial Google Cloud Platform credit grant remains **100% untouched**, preserved strictly as an emergency reserve or enterprise SLA demonstration buffer.
- **Reinvestment Velocity:** 100% of net commerce and SaaS cash flow is reinvested into local hardware expansion (Apple Silicon unified memory, Movesense sensor fleet, high-speed networking).
<!-- CONTEXT_WINDOW_TIER_0_END -->

---

<!-- CONTEXT_WINDOW_TIER_1_START: 16K_REVENUE_ENGINES_AND_OFFERINGS -->
## 📦 Context Window Tier 1: Core Revenue Pillars & Product Offerings (~16,000 Tokens)

> **Lens AI Ingestion Target:** Local Workhorse Models (`Qwen2.5-Coder-7B` on Port 8081, `Mistral-Nemo-Instruct` on Port 8083).  
> **Processing Latency:** `30–80ms` | **Memory Overhead:** `<380 MB`.

The business is structured around four interlocking, high-margin revenue engines:

### 1. Pillar 1: Premium Technical Combat Apparel & Merchandise (Shopify AI)
- **Product Catalog:**
  - *Lauburu Canonical Compression Rashguard:* Ultra-durable 4-way stretch polyester/spandex blend designed for Brazilian Jiu-Jitsu and high-intensity grappling.
  - *Lauburu Technical Grappling Shorts:* Zero-velcro flex-lock waistband with reinforced split seams.
  - *Ecosystem Bundles:* Coordinated rashguard, shorts, and sensor harness packages.
- **Sales Engine:** Headless Shopify Storefront integrated directly with Port 4000 Console and autonomous inventory sourcing.

### 2. Pillar 2: Medical-Grade Biometric Telemetry & Zone 2 Coaching SaaS
- **Product Offering:** 
  - Real-time 512Hz single-lead ECG telemetry, heart rate variability (HRV), and continuous pulse transit time (PTT) blood pressure tracking.
  - Proprietary DFA-$\\alpha_1$ aerobic threshold detector advising athletes on exact Zone 2 cardiovascular training pacing to prevent overtraining.
- **Monetization Model:** Monthly / Annual SaaS membership ($29.00/month or $290.00/year).

### 3. Pillar 3: Spatial Grappling 3D Interactive Curriculum
- **Product Offering:**
  - WebGL / Three.js 3D interactive martial arts digital academy visualising 955 submission techniques, joint torque vectors, and counters.
  - Motion-tracked sparring replay analysis combining Pixel 10 Pro XL 8K vision tracking with Movesense biometric intensity data.
- **Monetization Model:** Premium technique library access tier ($19.00/month add-on or bundled with SaaS at $39.00/month).

### 4. Pillar 4: Sovereign Edge AI Appliance & Academy Licensing
- **Product Offering:** Turnkey private mesh deployment for martial arts academies, sports medicine clinics, and combat gyms.
- **Includes:** Local AI appliance (Linux Head Node / Mac Mini), local `prima.cpp` ring inference, private biometric telemetry storage, and offline compliance.
- **Monetization Model:** High-ticket B2B licensing ($2,500.00 setup fee + $350.00/month recurring maintenance SLA).
<!-- CONTEXT_WINDOW_TIER_1_END -->

---

<!-- CONTEXT_WINDOW_TIER_2_START: 32K_FINANCIAL_MODELS_AND_UNIT_ECONOMICS -->
## 🌐 Context Window Tier 2: Unit Economics, Margin Architecture & Projections (~32,000 Tokens)

> **Lens AI Ingestion Target:** Distributed Swarm Coordinator (`prima.cpp` 80B Ring on Port 8082, Whole-Monorepo AST Evaluator).  
> **Processing Latency:** `120–250ms` | **Memory Overhead:** `<1.2 GB`.

### 1. Product Unit Economics Matrix
```
┌─────────────────────────────────┬───────────┬─────────────┬──────────────┬──────────────┬─────────────────────────┐
│ Product / Service Line          │ Unit Price│ COGS / Unit │ Gross Profit │ Gross Margin │ Fulfillment / Delivery  │
├─────────────────────────────────┼───────────┼─────────────┼──────────────┼──────────────┼─────────────────────────┤
│ Canonical Rashguard             │ $85.00    │ $24.00      │ $61.00       │ 71.8%        │ Direct Drop-Ship / 3PL  │
│ Technical Grappling Shorts      │ $75.00    │ $21.50      │ $53.50       │ 71.3%        │ Direct Drop-Ship / 3PL  │
│ Complete Grappling Bundle       │ $149.00   │ $42.00      │ $107.00      │ 71.8%        │ Bundled Packaging       │
│ Biometrics + Zone 2 SaaS (Mo)   │ $29.00    │ $1.80       │ $27.20       │ 93.8%        │ Cloudflare Edge / Local │
│ Spatial Grappling 3D All-Access │ $39.00    │ $2.20       │ $36.80       │ 94.4%        │ WebGL Browser Stream    │
│ B2B Academy Mesh Appliance (Yr1)│ $6,700.00 │ $1,400.00   │ $5,300.00    │ 79.1%        │ Hardware Deployment + SLA│
└─────────────────────────────────┴───────────┴─────────────┴──────────────┴──────────────┴─────────────────────────┘
```

### 2. Key SaaS Financial Ratios
- **Customer Acquisition Cost (CAC):** Estimated at **$18.50** via organic YouTube 8K sparring breakdowns and athlete social virality.
- **Customer Lifetime Value (LTV):** Estimated at **$464.00** based on a 16-month average subscription retention period.
- **LTV / CAC Ratio:** **25.1x** (Industry benchmark: >3.0x is elite).
- **Payback Period:** **0.64 months** (~19 days).
- **Monthly Churn Target:** **<2.8%** driven by high user lock-in through historical biometric datasets and 3D skill tree progression.
<!-- CONTEXT_WINDOW_TIER_2_END -->

---

<!-- CONTEXT_WINDOW_TIER_3_START: 128K_GROWTH_MARKETING_AND_SCALING -->
## 🔮 Context Window Tier 3: Go-to-Market Strategy & Scaling Roadmap (~128,000+ Tokens)

> **Lens AI Ingestion Target:** Frontier Cloud Teachers (`Gemini 3.1 Pro Preview` 2M Context, `DeepSeek V4 Pro 1.6T` 1M Context).  
> **Processing Latency:** Cloud Async (`1–3s`) | **Memory Overhead:** Cloud Offloaded ($0 Cost).

### 1. Multi-Stage Go-To-Market Execution
1. **Stage 1 (Community Seed & Organic Virality):**
   - Stream live 8K digital PTZ grappling matches from Pixel 10 Pro XL directly to YouTube / Twitch with live biometric overlay (real-time ECG, heart rate, fatigue meter).
   - Seed custom rashguards to prominent Australian BJJ black belts and competitors.
2. **Stage 2 (Shopify AI Scale & SaaS Onboarding):**
   - Launch automated email sequences and discount coupons for apparel purchasers granting 30-day free access to the Zone 2 coaching app.
   - Deploy affiliate tracking engine offering 20% recurring commissions to grappling gym coaches.
3. **Stage 3 (B2B Academy Network Rollout):**
   - Install Turnkey Lauburu Mesh Appliances across top-tier academies in Melbourne, Sydney, and Brisbane.
   - Aggregate multi-academy competition data into a global decentralized ELO grappling leaderboard.
<!-- CONTEXT_WINDOW_TIER_3_END -->
"""

# ==============================================================================
# 4. LENS_AI_CANONICAL_OVERVIEW.md
# ==============================================================================
LENS_AI_CONTENT = """# 👁️ Canonical Lens AI Overview — Autonomous Multimodal VLA Architecture

```
========================================================================================
LAUBURU LENS AI — CANONICAL VISION-LANGUAGE-ACTION (VLA) SPECIFICATION
Version: 3.0.0-LENS-2026 | Authority: Aaron (Sovereign) | Integrity: Zero-Mock
Context Engine: SnapKV + Foveated 32K Token Sharding | DPO Dataset: 2,221+ Triplets
========================================================================================
```

---

<!-- CONTEXT_WINDOW_TIER_0_START: 4K_VLA_CORE_IDENTITY -->
## 🧭 Context Window Tier 0: Core VLA Identity & Fast Directives (~4,000 Tokens)

> **Lens AI Ingestion Target:** Fast Edge Micro-Models (`SmolLM2-135M`, `Pixel 10 Pro XL Edge TPU`, `Termux Edge Daemon`).  
> **Processing Latency:** `<15ms` | **Memory Overhead:** `<64 MB`.

### 1. The Autonomous VLA Mission
**Lauburu Lens AI** is an autonomous multimodal Vision-Language-Action companion and computer-use agent. It continuously observes screen viewports, extracts real-time DOM hierarchy trees, computes WCAG AAA contrast ratios, predicts the Next-Best-Action (NBA), and executes verified accessibility and mouse/keyboard events across macOS, Android, and web interfaces with **zero simulated data** and **sub-50ms Time-to-First-Token (TTFT)**.

### 2. Core Operational Rules
1. **Rule #0 Zero-Mock Grounding:** 100% of predicted action coordinates must match authentic bounding boxes queried directly from Chrome DevTools Protocol or native OS accessibility trees. Guessing coordinates or hardcoding offsets is strictly prohibited.
2. **WCAG AAA Compliance Gate:** Any interactive UI element targeted by Lens must satisfy $\\ge 7:1$ visual contrast against its background before an interaction is approved.
3. **Continuous DPO Harvesting:** Every teacher inference from Gemini 3.1 Pro or DeepSeek V4 Pro is structured into an authentic DPO triplet (`prompt`, `chosen`, `rejected`) and committed to `04_data_and_memory/` to fuel continuous local LoRA fine-tuning.
<!-- CONTEXT_WINDOW_TIER_0_END -->

---

<!-- CONTEXT_WINDOW_TIER_1_START: 16K_VISUAL_CORTEX_AND_DEVTOOLS_PROTOCOL -->
## 📦 Context Window Tier 1: Visual Cortex & Chrome DevTools Protocol (~16,000 Tokens)

> **Lens AI Ingestion Target:** Local Workhorse Models (`Qwen2.5-Coder-7B` on Port 8081, `Mistral-Nemo-Instruct` on Port 8083).  
> **Processing Latency:** `30–80ms` | **Memory Overhead:** `<380 MB`.

### 1. Chrome DevTools Protocol Integration (`01_apps/lauburu_lens/chrome_debugging_bridge.py`)
- **Transport:** WebSocket connection to headless or active Google Chrome instance running with `--remote-debugging-port=9222`.
- **DOM Inspection Domains:**
  - `DOM.getDocument`: Ingests full active node hierarchy.
  - `DOM.getBoxModel`: Retrieves exact CSS pixel coordinates (`border`, `padding`, `content` quads).
  - `CSS.getComputedStyleForNode`: Extracts color and background color to compute mathematical luminance contrast ratios:
    $$C = \\frac{L_1 + 0.05}{L_2 + 0.05}$$
- **Event Dispatch Domains:**
  - `Input.dispatchMouseEvent`: Synthesizes deterministic mouse moves, button down, button up, and click events.
  - `Input.dispatchKeyEvent`: Injects physical keystrokes with authentic key codes and modifier keys.

### 2. Live DOM Extractor (`01_apps/lauburu_lens/dom_element_extractor.py`)
- **Scanned Surfaces:** 
  - Port 4000 Console (`http://localhost:4000`)
  - Self-Healing Hub (`http://localhost:18802`)
  - Voilà Biometrics Portal (`http://localhost:8890`)
- **Target Tag Coverage:** `<button>`, `<a>`, `<input>`, `<select>`, `<canvas>`, and ARIA role elements.
<!-- CONTEXT_WINDOW_TIER_1_END -->

---

<!-- CONTEXT_WINDOW_TIER_2_START: 32K_CONTEXT_EXPANSION_AND_SPECULATIVE_REDUCTION -->
## 🌐 Context Window Tier 2: Context Expansion & Speculative Reduction (~32,000 Tokens)

> **Lens AI Ingestion Target:** Distributed Swarm Coordinator (`prima.cpp` 80B Ring on Port 8082, Whole-Monorepo AST Evaluator).  
> **Processing Latency:** `120–250ms` | **Memory Overhead:** `<1.2 GB`.

### 1. Foveated 32K Token Sharding Architecture
Rather than forcing massive 1,000,000-token full-context trees into local host RAM (which would trigger OOM panics on the 24 GB Mac Mini), Lens employs a **foveated context sharding strategy**:
```
┌────────────────────────┬────────────────────────────────┬───────────────────────────────────────────────────────┐
│ Mesh Node              │ Context Allocation             │ Content Stored in Window                              │
├────────────────────────┼────────────────────────────────┼───────────────────────────────────────────────────────┤
│ L1: Mac Mini M4 Pro    │ Chunk 0 (Root Intent & CoT)    │ 4K Tokens: Active objective, current action, memory   │
│ L2: MacBook Pro (TB4)  │ Chunks 1..N (AST & Repo Index) │ 32K Tokens: Deep monorepo AST via 10Gbps TB4 DMA     │
│ L6: Pixel 10 Pro XL    │ Edge Cache (Sensory Viewport)  │ 8K Tokens: Recent 10 visual frames & OCR text streams │
│ L7: Samsung Galaxy S20 │ Log Buffer (Execution History) │ 8K Tokens: Rolling accessibility event stream logs    │
└────────────────────────┴────────────────────────────────┴───────────────────────────────────────────────────────┘
```

### 2. SnapKV & Speculative Token Compression (`01_apps/screen_lens/src/lens_speculative_draft_engine.py`)
- **SnapKV Clustering:** Retains key visual anchor tokens and evicts up to **80% of repetitive whitespace and syntax tokens** without degrading action generation accuracy.
- **Speculative Drafting:** Micro-models (`SmolLM2-135M` at 367 tok/s) draft initial action predictions. If confidence exceeds $\\ge 0.95$, the action executes immediately; otherwise, it escalates to `Qwen2.5-Coder-7B` or cloud teachers.
<!-- CONTEXT_WINDOW_TIER_2_END -->

---

<!-- CONTEXT_WINDOW_TIER_3_START: 128K_DPO_DISTILLATION_AND_WEIGHT_MERGING -->
## 🔮 Context Window Tier 3: Multimodal DPO Distillation & Model Weights (~128,000+ Tokens)

> **Lens AI Ingestion Target:** Frontier Cloud Teachers (`Gemini 3.1 Pro Preview` 2M Context, `DeepSeek V4 Pro 1.6T` 1M Context).  
> **Processing Latency:** Cloud Async (`1–3s`) | **Memory Overhead:** Cloud Offloaded ($0 Cost).

### 1. DPO Triplet Harvesting Pipeline (`lens_rapid_quota_maximizer.py`)
- **Total Verified Dataset:** **2,221+ authentic records (2.6 MB)** in `/Volumes/Lauburu-Monorepo/04_data_and_memory/data/lens_ai/lens_multimodal_dpo.jsonl`.
- **DPO Triplet Schema:**
  - `prompt`: Surface target, URL, target element tag, and intent.
  - `chosen`: High-precision viewport coordinates, Chrome CDP event dispatch string, WCAG contrast verification, 0.0ms synthetic lag.
  - `rejected`: Default origin click (0, 0) or unverified coordinate guess lacking DOM tree confirmation.
  - `teacher_engine`: Gemini 3.1 Pro, DeepSeek V4 Pro 1.6T, Cloudflare Llama 3.3 70B, or xAI Grok-2.

### 2. Continuous Local Apple Silicon QLoRA Training
- **Framework:** Apple MLX (`mlx-lm.lora`) and PyTorch Metal Performance Shaders (MPS).
- **Target Base Weights:** `Qwen2.5-Coder-7B-Instruct` and `SmolLM2-1.7B-Instruct`.
- **Tournament ELO Integration:** Checkpoints participate in Bradley-Terry tournaments (`qwen-moe --local-burst`) to validate token generation velocity and action accuracy before merging.
<!-- CONTEXT_WINDOW_TIER_3_END -->
"""

# Map of destination files
DOCS_MAP = {
    "CANONICAL_PROJECT_OVERVIEW.md": PROJECT_OVERVIEW_CONTENT,
    "CANONICAL_APPS_OVERVIEW.md": APPS_OVERVIEW_CONTENT,
    "CANONICAL_BUSINESS_PLAN_OVERVIEW.md": BUSINESS_PLAN_CONTENT,
    "LENS_AI_CANONICAL_OVERVIEW.md": LENS_AI_CONTENT,
}

print("Writing Canonical Overviews across Tri-Vault storage layers...")
for fname, content in DOCS_MAP.items():
    # 1. Monorepo root
    root_path = REPO_ROOT / fname
    with open(root_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"  • Written: {root_path} ({len(content)} bytes)")

    # 2. Obsidian Vault canonical
    vault_path = VAULT_CANONICAL / fname
    with open(vault_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"  • Synced to Obsidian Vault: {vault_path}")

    # 3. 07_docs_and_architecture/canonical/
    docs_path = DOCS_CANONICAL / fname
    with open(docs_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"  • Synced to Docs Canonical: {docs_path}")

# Update Obsidian Index.md with Wikilinks
INDEX_PATH = REPO_ROOT / "obsidian_vault" / "Index.md"
WIKILINKS_BLOCK = """
## 🏛️ Canonical Ecosystem Overviews (2026 Context-Windowed Architecture)
- [[CANONICAL_PROJECT_OVERVIEW]] — Master Monorepo Taxonomy, 7-Layer Hardware Matrix & Context Sharding
- [[CANONICAL_APPS_OVERVIEW]] — Unified Port Matrix, Biometrics, Spatial 3D & Mobile Daemons
- [[CANONICAL_BUSINESS_PLAN_OVERVIEW]] — $0 Cloud Spend Bootstrap, Apparel, Biometrics SaaS & Unit Economics
- [[LENS_AI_CANONICAL_OVERVIEW]] — Autonomous Multimodal VLA, Chrome CDP, SnapKV & 2,221+ DPO Dataset
"""

if INDEX_PATH.exists():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        idx_content = f.read()
    if "CANONICAL_PROJECT_OVERVIEW" not in idx_content:
        idx_content += "\n" + WIKILINKS_BLOCK.strip() + "\n"
        with open(INDEX_PATH, "w", encoding="utf-8") as f:
            f.write(idx_content)
        print("  • Updated obsidian_vault/Index.md with master canonical Wikilinks.")

print("\n✅ All 4 Canonical Overviews successfully generated and synchronized across Tri-Vault storage!")
