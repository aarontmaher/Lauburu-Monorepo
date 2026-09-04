# 🧠 Lauburu AI Monorepo — Canonical Architecture & Unified Storage Hub (1.701 TB)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       LAUBURU MESH UNIFIED ARCHITECTURE                     │
│               1.701 TB SeaweedFS DFS  •  108 GB Pooled RAM (82.8 GB VRAM)    │
│            10Gbps Thunderbolt 4  •  Tri-Vault Synchronization Layer          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 📖 Overview
The **Lauburu Monorepo** is the canonical source code, model inference, biometrics, and AI orchestration repository for the **Lauburu Mesh Ecosystem**. The workspace is distributed across a **7-layer physical hardware mesh** interconnected via a **10Gbps Thunderbolt 4 DMA bridge (0.277ms RTT)** and an encrypted **Tailscale WireGuard mesh**, unified on top of a **1.701 TB SeaweedFS Distributed Object & File System** mounted at `/Users/aaron/DFS_UNIFIED`.

---

## 🏛️ 1. Canonical Tri-Vault Storage Architecture

All state, telemetry, training runs, and architectural whitepapers are synchronized across three persistent storage vaults:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TRI-VAULT STORAGE SYNCHRONIZATION                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. OBSIDIAN VAULT (Human & Semantic Knowledge Core)                         │
│    • Path: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/        │
│    • Managed via: Obsidian MCP Pro (41 graph traversal tools, Wikilinks)   │
│    • Content: System specifications, live debate transcripts, audit logs.  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. PYSPARK & BIG DATA LAKE (High-Throughput Computation & Datasets)         │
│    • Paths: /Users/aaron/DFS_UNIFIED/lora_datasets/ & 04_data_and_memory/   │
│    • Engine: PySpark, Delta Lake (delta-rs), Qdrant Vector DB, Parquet      │
│    • Content: 3,100+ code file AST crawls, 435K+ LOC index, 24/7 DPO LoRA   │
│      instruction pairs, 512Hz raw ECG streams.                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. GITHUB REPOSITORY & WORKTREES (Canonical Source Code & Version Control)  │
│    • Repo: aarontmaher/Lauburu-Monorepo (Host: /Users/aaron/DFS_UNIFIED)    │
│    • Managed via: gh CLI, Git Worktrees, Automated Multi-Tier CI Test Suites│
│    • Content: Microservices, client apps, container definitions, drivers.   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🌐 2. 7-Layer Physical Mesh Hardware Matrix

The distributed hardware mesh pools **108.0 GB RAM (82.8 GB Usable AI VRAM)** across 7 physical nodes:

| Layer | Node Name | Network Role | Local IP | Tailscale / Bridge IP | RAM / AI Cap | Key Roles & Protocols |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `Mac_Node` | Primary Host & Memory Governor | `192.168.8.230` | `100.119.199.76` | 24.0 GB (21.6 GB AI) | Apple M4 Pro Mac Mini. Prompt Ingestion & Memory Governor. Dynamic Cap: 90%. |
| **L2** | `MacBook_Pro` | Metal GPU RPC & Storage Vault | `192.168.8.127` | `100.103.212.21` (TB4: `169.254.187.138`) | 16.0 GB (14.0 GB AI) | **10Gbps Thunderbolt 4 Bridge (0.277ms RTT)**, 285 GB SSD Model Vault. Dynamic Cap: 90%. |
| **L3** | `Linux_Head_Node` | Gateway Ingress & Compute Hub | `192.168.8.224` | `100.101.39.98` | 16.0 GB (13.8 GB AI) | AMD Ryzen 7 5700U, Docker Hub, SeaweedFS Master/Filer & Ray. Dynamic Cap: 80%. |
| **L4** | `Linux_Tablet` | Mobile Linux Compute & Touch DSP | DHCP | `100.81.92.125` | 8.0 GB (6.5 GB AI) | Debian Linux Tablet, secondary Petals worker, biometrics display. Dynamic Cap: 75%. |
| **L5** | `MacBook_Air` | Secondary High-Speed Metal Worker | `192.168.8.222` | `100.93.158.96` | 16.0 GB (14.0 GB AI) | Apple M4 MacBook Air, Metal Performance Shaders, LoRA Distillation. Dynamic Cap: 90%. |
| **L6** | `Pixel_10_Pro_XL` | 8K Vision Stream & Edge TPU | DHCP | `100.73.38.87` | 16.0 GB (12.5 GB AI) | Google Tensor G5, Edge TPU, 8K Digital PTZ, UWB 3D Positioning. Dynamic Cap: 85%. |
| **L7** | `Samsung_S20` | Dedicated Automated UI Tester | DHCP | `100.84.40.95` | 12.0 GB (9.0 GB AI) | Samsung Exynos 990, Router USB ADB default target for OpenClaw UI. Dynamic Cap: 75%. |
| **GW** | `GL.iNet Router` | Core Gateway & Hardware USB Bridge | `192.168.8.1` | `100.122.185.123` | Embedded | GL-MT3600BE-a0f-MLO. Hardware USB ADB daemon & kmwan multi-WAN failover. |

---

## 📁 3. Canonical Monorepo Directory Layout (13 Canonical Pillars)

All repository code is organized into 13 numbered canonical pillars, ensuring strict separation of concerns:

```
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/
├── 00_core_infrastructure/           # Master SeaweedFS, Docker, Tailscale, daemons, launchd units
├── 01_apps/                          # Client applications (Port 4000 Hub, Movesense Hub, Zone 2, Quartz)
├── 02_ai_models_and_inference/       # llama.cpp RPC (8081-8085), Petals, Exo, GGUF Vault, Prima.cpp
├── 03_biometrics_and_telemetry/      # Movesense 512Hz ECG, Pan-Tompkins QRS, PTT BP, DFA-alpha1
├── 04_data_and_memory/               # PySpark Data Lake, 24/7 LoRA datasets, Qdrant Vector DB
├── 05_agents_and_swarms/             # Tri-Orchestrator Soul, Genetic MoE Engine, Antigravity Skills
├── 06_scripts_and_tooling/           # Autonomous network self-healing, global NAS mounting, ADB daemons
├── 07_docs_and_architecture/         # Architecture whitepapers, hardware topologies, spec sheets
├── 08_business_and_commerce/         # Shopify Storefront GraphQL, Subscriptions, CAC/LTV modeling
├── 09_app_store_and_release/         # Signed Android APKs, Play Store & Apple App Store release manifests
├── 10_spatial_grappling_kinematics/  # 955-Node Spatial OPML trees, 3D tatami world models, kinematics
├── 11_security_and_governance/       # Hardware isolation, SSH/RPC socket encryption, Cloudflare HMAC
├── 12_continuous_lora_evolution/     # 24/7 LoRA harvesting, DARE-TIES weight merging, MLX backprop
├── obsidian_vault/                   # Canonical Obsidian Knowledge Graph (Tri-Vault Layer 1)
└── tests/                            # Multi-tier verification test suites & regression benchmarks
```

---

## 🧹 4. Legacy Root Directory Consolidation Plan (README Mode)

To maintain backward compatibility while organizing the repository, legacy root directories will transition via non-destructive symlinks:

| Legacy Root Directory | Canonical Destination | Consolidation & Symlink Policy |
| :--- | :--- | :--- |
| `00_SYSTEM_DASHBOARDS/` | [00_core_infrastructure/dashboards](file:///Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure) & [01_apps](file:///Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps) | Consolidate system monitoring UI and Prometheus/Grafana configs. |
| `ai_debate/` | [05_agents_and_swarms/ai_debate](file:///Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/ai_debate) | Consolidated; maintain symlink `ai_debate -> 05_agents_and_swarms/ai_debate`. |
| `apps/` | [01_apps](file:///Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps) | Merge residual apps; replace with symlink `apps -> 01_apps`. |
| `core/` | [00_core_infrastructure](file:///Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure) | Merge system configs; replace with symlink `core -> 00_core_infrastructure`. |
| `docs/` | [07_docs_and_architecture](file:///Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/07_docs_and_architecture) | Consolidate specifications; replace with symlink `docs -> 07_docs_and_architecture`. |
| `filerldb2/` | [00_core_infrastructure/seaweedfs/filerldb2](file:///Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure) | Move SeaweedFS local leveldb database out of git root into infrastructure data. |
| `Installed_Apps/` | [01_apps/installed](file:///Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps) | Catalog installed tooling binaries and runtime wrappers. |
| `lora_datasets/` | [04_data_and_memory/lora_datasets](file:///Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory) | Maintain symlink pointing to high-capacity DFS dataset pool. |
| `pyspark_analytics/` | [04_data_and_memory/pyspark_analytics](file:///Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory) | Consolidate AST indexers and Parquet crawlers into data pillar. |
| `scripts/` | [06_scripts_and_tooling](file:///Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling) | Consolidate operational scripts; maintain symlink `scripts -> 06_scripts_and_tooling`. |
| `self_healing_hub/` | [06_scripts_and_tooling/network/self_healing_hub](file:///Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling) | Integrate into Nomad Courier self-healing daemon hierarchy. |
| `webapp/` | [01_apps/webapp](file:///Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps) | Web dashboard frontend; maintain symlink `webapp -> 01_apps/webapp`. |

---

## 🤖 5. Designated Optimal Local AI Storage & Uptime Governor

Based on empirical benchmarks conducted on local model weights on Apple Silicon Metal GPU (see [07_AUTONOMOUS_STORAGE_GOVERNOR_AND_UPTIME_SPEC.md](file:///Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/07_docs_and_architecture/07_AUTONOMOUS_STORAGE_GOVERNOR_AND_UPTIME_SPEC.md)), the project employs a **Dual-Tier Local AI Model Architecture**:

### 5.1 Tier 1: Reflex Sentinel & Uptime Maintainer
- **Assigned Model:** **`qwen2.5-coder-7b-instruct-q4_k_m.gguf`** (Port `8081`)
- **VRAM Footprint:** 4.4 GB (<20% of Host M4 Pro AI VRAM, leaving 17+ GB for dev/inference)
- **Performance:** **43.6 tok/s**, Time-to-First-Token **65ms**, native JSON tool-calling grammar.
- **Continuous Tasks:**
  1. 60s health pulse on SeaweedFS Master (`9333`), Filer (`8888`), Volume (`8080`), WebDAV (`7333`).
  2. Proactive FUSE mount validation for `/Users/aaron/DFS_UNIFIED`.
  3. Automatic process resurrection (`weed server`, `weed mount`) and Samba service restarts upon drop.
  4. Tri-Vault disk headroom enforcement (maintaining $\ge$ 5.0 GB free disk).

### 5.2 Tier 2: Deep Semantic Reorganizer & AST Crawler
- **Assigned Model:** **`qwen2.5-coder-32b-instruct-q4_k_m.gguf`** (19 GB) or **`Mistral-Nemo-Instruct-2407-abliterated`** (128k context)
- **Topology Placement:** Offloaded across the **10Gbps Thunderbolt 4 bridge** to Layer 2 (`MacBook_Pro`) or executed on L1 during idle windows.
- **Continuous Tasks:**
  1. Semantic deduplication and SHA-256 integrity verification across the 1.701 TB store.
  2. AST parsing of 3,100+ monorepo code files to update Wikilink graphs in `obsidian_vault`.
  3. Generating self-documenting `.md` manifests for new directories.

---

## ⚡ 6. Network Combined Storage Management (`/Users/aaron/DFS_UNIFIED`)

### 6.1 Cluster Ports & Endpoints
- **SeaweedFS Master:** `127.0.0.1:9333` (gRPC: `19333`)
- **SeaweedFS Filer:** `127.0.0.1:8888` / `8088` (gRPC: `18888`)
- **SeaweedFS Volume Server:** `127.0.0.1:8080` (gRPC: `18080`)
- **WebDAV Gateway:** `127.0.0.1:7333` (Direct HTTP/Finder access)
- **Samba SMB3:** `100.101.39.98:445` (Apple VFS Fruit extensions)
- **Local FUSE Mount:** `/Users/aaron/DFS_UNIFIED` (Logical Capacity: 1.701 TB)

### 6.2 Autonomous Keepalive Daemon
Managed 24/7 by [nomad_courier_self_healer.py](file:///Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/nomad_courier_self_healer.py):
```bash
# Execute single health & mount verification cycle:
python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/nomad_courier_self_healer.py --once

# Inspect live status telemetry:
cat /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/network/nomad_self_healer_status.json
```

---

## 🛠️ 7. Operational Runbook & Common CLI Workflows

### 7.1 Verify Mesh AI Inference Servers
```bash
curl -s http://127.0.0.1:8081/health && echo "Qwen Coder 7B Sentinel (8081): ONLINE"
curl -s http://127.0.0.1:8083/health && echo "DeepSeek Coder / Devil's Advocate (8083): ONLINE"
```

### 7.2 Run Storage Headroom & Genetic Evolution Optimizer
```bash
python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/storage/nomad_genetic_storage_optimizer.py
```

### 7.3 Execute Tri-Vault Pre-Flight Self-Healing
```bash
# 1. Ensure vault directories exist
mkdir -p /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault /Users/aaron/DFS_UNIFIED/lora_datasets /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory

# 2. Release stale git index locks
[ -f "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.git/index.lock" ] && rm -f "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.git/index.lock"
```

---

## 📋 8. Compliance & Governance Invariants
1. **Rule #0 Zero-Mock Mandate:** No simulated, mocked, or placeholder data. Telemetry originates exclusively from live BLE sensors, live network sockets, and authentic hardware.
2. **Dynamic RAM Governance:** Host Mac Mini M4 Pro RAM allocation must remain $\le 90\%$ (21.6 GB AI cap).
3. **Continuous DPO LoRA Serialization:** All self-healing actions, debate verdicts, and storage reorganizations are serialized to `data/lora_datasets/` for 24/7 background learning.
