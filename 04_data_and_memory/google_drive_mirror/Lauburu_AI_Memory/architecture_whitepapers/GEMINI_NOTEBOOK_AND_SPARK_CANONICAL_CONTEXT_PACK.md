# 🌐 Lauburu AI Mesh Ecosystem: Canonical Master Architecture & Context Pack
*Engineered for Gemini Notebook (NotebookLM), Gemini Spark, and Google AI Studio Knowledge Ingestion.*
*Version: 2026.1 | Monorepo Canonical Source: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`*

---

## 🏛️ 1. Executive Summary & Core Mission
The **Lauburu Mesh Ecosystem** is a 100% sovereign, high-throughput local AI inference, multi-agent swarm governance, and medical-grade biometrics telemetry mesh pooling **108.0 GB RAM (82.8 GB Usable AI VRAM)** across a 7-layer heterogeneous hardware topology. It enforces strict **Zero-Mock Data (Rule #0)** and operates toward a **$0 Recurring Cloud Spend Velocity**, using local quantized models on Apple Silicon Metal and AMD ROCm/Vulkan, with Cloud Frontier APIs (Gemini 3.1 Pro High / 3.7 Flash High) serving strictly as reasoning benchmarks and debate adjudicators.

---

## 📁 2. Canonical Tri-Vault Storage Protocol
All project memory, training telemetry, and code diffs synchronize across three synchronized storage layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TRI-VAULT STORAGE SYNCHRONIZATION                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. OBSIDIAN VAULT (Human & Semantic Knowledge Core)                         │
│    • Path: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/        │
│    • Managed via: Obsidian MCP Pro (41 tools, graph traversal, Wikilinks)   │
│    • Stores: Architecture whitepapers, AI debate consensus records,         │
│      continuous audit logs, network topologies, and system telemetry feeds. │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. PYSPARK & BIG DATA LAKE (High-Throughput Computation & Datasets)         │
│    • Paths: /Users/aaron/DFS_UNIFIED/lora_datasets/ & 04_data_and_memory/   │
│    • Engine: PySpark (pyspark), Delta Lake / Parquet, Qdrant Vector DB      │
│    • Stores: 3,100+ code file AST crawls, 435K+ LOC index, 24/7 LoRA       │
│      instruction pairs (TRL/PEFT/DPO), Pan-Tompkins 512Hz ECG streams.      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. GITHUB REPOSITORY & WORKTREES (Canonical Source Code & Version Control)  │
│    • Repo: aarontmaher/Lauburu-Monorepo (Host: /Users/aaron/DFS_UNIFIED)    │
│    • Managed via: gh CLI, Git Worktrees, Automated Multi-Tier CI Test Suites│
│    • Stores: Production application code, container manifests, microservices│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🌐 3. 7-Layer Physical Mesh Topology & Hardware Interconnect Matrix

| Layer | Node Name | Network Role | Local IP | Tailscale / Bridge IP | Dynamic RAM Ceiling | Hardware & Capabilities |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `Mac_Node` | Primary Host & Memory Governor | `192.168.8.230` | `100.119.199.76` | **90%** (21.6 GB AI) | Apple M4 Pro Mac Mini. Primary controller, memory governor, prompt ingestion. |
| **L2** | `MacBook_Pro` | Metal GPU RPC & Model Vault | `192.168.8.127` | `100.103.212.21` (TB4: `169.254.187.138`) | **90%** (14.0 GB AI) | **10Gbps Thunderbolt 4 Bridge (0.277ms RTT)**, 285 GB internal SSD model vault. |
| **L3** | `Linux_Mini` | Gateway Ingress & Compute Hub | `192.168.8.224` | `100.101.39.98` | **80%** (13.8 GB AI) | Intel 2018 Mac Mini (Linux), Docker Engine, Petals DHT Bootstrap & Apache Ray Head. |
| **L4** | `Linux_Tablet` | Mobile Compute & Touch DSP | DHCP | `100.81.92.125` | **75%** (6.5 GB AI) | Debian Linux Tablet, secondary Petals worker, lightweight biometrics telemetry. |
| **L5** | `MacBook_Air` | Secondary High-Speed Metal Worker | `192.168.8.222` | `100.121.202.34` | **90%** (14.0 GB AI) | Apple M4 MacBook Air, Metal Performance Shaders, LoRA fine-tuning & model distillation. |
| **L6** | `Pixel_10_Pro_XL` | 8K Vision Stream & Edge TPU | DHCP | `100.73.38.87` | **85%** (12.5 GB AI) | Google Tensor G5, Edge TPU, 8K Digital PTZ, UWB 3D Spatial Positioning Anchor. |
| **L7** | `Samsung_S20` | Dedicated Automated UI Tester | DHCP | `100.84.40.95` (Alt: `100.99.123.58`) | **75%** (9.0 GB AI) | Samsung Exynos 990, Router USB ADB default target for OpenClaw automated audits. |
| **GW** | `GL.iNet Router` | Core Gateway & USB Bridge | `192.168.8.1` | `100.122.185.123` | Embedded (512 MB) | SSID: `GL-MT3600BE-a0f-MLO`. Physical USB ADB daemon for hardware bus override. |

---

## 🧠 4. Canonical Local Inference Engine & Model Hierarchy

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                 CANONICAL LOCAL INFERENCE ENGINE HIERARCHY                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. PRIMARY ENGINE: prima.cpp (Port :8082)                                   │
│    • Canonical primary master across all devices that contain model weights │
│      (Mac Mini M4 Pro, MacBook Pro, Linux Head Node).                       │
│    • High-throughput Pipelined-Ring Parallelism over 10Gbps TB4 DMA Bridge. │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. RESILIENT FALLBACK: llama.cpp (Port :8083)                               │
│    • Strictly used as a fallback ONLY if an edge device lacks the local     │
│      model weights or hardware topology to run prima.cpp properly.          │
│    • Pinned Model: Qwen 3.8 Max 27B Abliterated (16.0 GB GGUF, 47.07 TPS).  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. MASTER LOCAL ORCHESTRATOR: Qwen 3.8 Max 27B (Port :8081)                 │
│    • Unabliterated coordinator pinned at /Users/aaron/models/Qwen3.8-Flash-Next│
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. EDGE ROUTER SLM: SmolLM2-135M / SmolLM2-360M (Port :18802 / router_ai)   │
│    • Running inside strict ≤ 300 MB container budget on GL.iNet OpenWrt.    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚔️ 5. Mandatory Default Hand-Off: `/ai-debate` Protocol
All non-trivial project choices, architectural crossroads, framework selections, and monorepo refactors MUST **default to handing off to the `/ai-debate` Tri-Orchestrator Protocol**:
1. **Local Dual Qwen Arena:** Qwen 3.8 Max (Master Orchestrator on `:8081`/`:8082`) vs **Qwen 3.8 Max 27B Abliterated** (Devil's Advocate on `:8083` via `Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf`).
2. **Cloud Frontier Shadow:** Gemini 3.1 Pro High & Gemini 3.7 Flash High for deep architectural reasoning and edge-case verification.
3. **Consensus Invariant:** Continuous iteration until mathematical consensus ($\Phi \ge 0.98$) is achieved before executing code diffs.

---

## 👁️ 6. Canonical Multimodal Perception & Development Historian Layer
The **Screen Lens Subsystem** (`01_apps/screen_lens/`) is a default, continuous perception layer:
- **macOS Desktop Lens (Port :3035):** Swift 6 standalone binary leveraging `ScreenCaptureKit` and Apple Vision Neural Engine (ANE) OCR (~187ms).
- **Mobile Edge Lens (Port :3035 / :3036):** Pixel 10 Pro XL Tesseract 5.5.2 LSTM OCR inside Termux.
- **Swarm Client (`05_agents_and_swarms/screen_lens_swarm_client.py`):** Real-time on-screen window context and full-text search across SQLite FTS5 (`~/.lauburu/screen_lens.sqlite`).
- **Autonomous AI Historian (`lauburu-dev-historian`):** 24/7 background development synthesis logging milestones directly to `obsidian_vault/00_CHRONOLOGY/LIVE_DEVELOPMENT_LOG_2026.md` and streaming DPO pairs to `project_development_history.jsonl`.
- **Hermes 3 & OpenClaw Integration:** `visual_action_mesh_orchestrator.py` links Screen Lens OCR to Hermes 3 Code-as-Action (`agent.click()`, `agent.type()`) and OpenClaw Shizuku Binder touch dispatch on Android.

---

## 📁 7. Canonical Monorepo Directory Hierarchy
```text
Lauburu-Monorepo/
├── 00_core_infrastructure/           # Self-Healing Hub (Port 18802), SeaweedFS DFS, Docker Compose, Tailscale daemons
├── 01_apps/                          # Screen Lens (:3035), Port 4000 Hub, Movesense Hub (512Hz ECG), Zone 2, Spatial Grappling 3D
├── 02_ai_models_and_inference/       # prima.cpp PRP (:8082), llama.cpp (:8083), Petals DHT, Exo P2P, GGUF Vault, lauburu-tui
├── 03_biometrics_and_telemetry/      # Movesense BLE, Pan-Tompkins QRS DSP, PTT Blood Pressure, DFA-alpha1
├── 04_data_and_memory/               # PySpark Crawlers, 24/7 LoRA Datasets, Qdrant Vector DB, Google Drive Sync
├── 05_agents_and_swarms/             # Screen Lens Swarm Client, Tri-Orchestrator AI Debate, CodeClash SWE Arena
├── 06_scripts_and_tooling/           # Universal SSH Daemons, ADB Keepalive, WoL Resurrection, Figma MCP Bridge
├── 07_docs_and_architecture/         # Architecture Indexes, Whitepapers, Gemini Notebook/Spark Context Pack
├── obsidian_vault/                   # Canonical Obsidian Knowledge Graph, APPS_AND_FEATURES, Swarm Logs
└── teamwork_projects/                # 32 Active Federated Projects (software_dev, internet_training, etc.)
```

---

## 🛑 8. Core Operating Invariants for Gemini Spark / NotebookLM
When responding to directives or analyzing code in the Lauburu Monorepo:
1. **Rule #0 (Zero-Mock Data):** Strictly forbid placeholder, dummy, or fake arrays. Telemetry must reflect live hardware or clean `--` waiting states.
2. **Local AI Hierarchy:** Always prioritize `prima.cpp` (Port `:8082`) as primary master, `llama.cpp` (Port `:8083`) with `Qwen 3.8 Max 27B Abliterated` as fallback, and `SmolLM2` for the GL.iNet router.
3. **Storage Health (Rule 6.3):** Confirm Tri-Vault storage layers are healthy and verify host NVMe maintain $\ge 5.0\text{ GB}$ free disk space.
