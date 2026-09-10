---
title: "Voilà Port 8890 Master Cyber Studio — 12-Tab SSoT Master Interactive Console"
tags: [voila, studio, cyber_ide, 14_port_matrix, dsp, bjj_opml, corewar, ast, tri_vault, zero_mock]
---

# 🌌 Voilà Port 8890 Master Cyber Studio — 12-Tab SSoT Master Console

- [[Index]]
- [[01_APPS_AND_PORTAL_CATALOG]]
- [[CANONICAL_APPS_OVERVIEW]]
- [[00_MASTER_INFRASTRUCTURE_TOPOLOGY]]
- [[03_MOVESENSE_512HZ_ECG_DSP_PIPELINE]]
- [[04_PYSPARK_AND_LORA_DATA_LAKE]]

---

## 🏛️ 1. Overview & Operational Architecture

The **Voilà Master Cyber Studio** (`http://127.0.0.1:8890/`) is the Single Source of Truth (SSoT) master interactive execution environment of the Lauburu Monorepo. Built inside `01_apps/notebooks/00_lauburu_global_master_project.ipynb` and served via Voilà 0.5.8 on Tornado, it unifies the entire multi-surface ecosystem into 12 glassmorphic, interactive operational domains.

- **Primary URL**: `http://127.0.0.1:8890/` (Local Host M4 Mini)
- **Secondary Peer URL**: `http://100.93.158.96:8890/` (MacBook Air M4 remote worker)
- **Engine**: Python 3.13 ipykernel + Voilà + ipywidgets 8.1.5 + Plotly + Headless Matplotlib Agg
- **Visual Design**: Master Cyber Dark Theme (`#020617`), cyan glassmorphic glow borders, responsive flex tabs.
- **Rule #0 Zero-Mock Enforcement**: Every tab executes live system calls, POSIX file probes, socket connect tests, or OPML XML tree parses.

---

## 📑 2. Comprehensive 12-Tab Feature Specification

### Tab 1: 📂 1. Custom Cyber IDE & SeaweedFS Distributed Storage
- **Role**: In-browser code navigation, inspection, editing, and sandbox execution.
- **Components**:
  - **Directory Navigator**: Live directory tree browsing across all monorepo subsystems (`00_core_infrastructure` through `12_continuous_lora_evolution`).
  - **SeaweedFS Client Binding**: Dual-mode file operations — POSIX local filesystem with automatic fallback to distributed SeaweedFS Filer (`http://100.101.39.98:8888`).
  - **Pre-Loaded Code Templates**:
    1. *512Hz Pan-Tompkins ECG DSP Pipeline*
    2. *14-Port Socket Prober & Latency*
    3. *7-Layer Tailscale & TB4 Mesh Ping*
    4. *SeaweedFS Distributed Filer Query*
    5. *Monorepo Polyglot AST Scanner*
  - **Action Toolbar**: `[Enter Dir]`, `[Up Dir]`, `[Refresh]`, `[New File]`, `[Save File]`, `[Run in Sandbox]`, `[Clear Console]`.
  - **Output Pane**: Real-time stdout/stderr stream from sandbox execution.

### Tab 2: 🌐 2. 14-Port Sovereign Mesh Matrix (2x2 Quad / Split / Solo)
- **Role**: Live service orchestration and interactive iframe multiplexer.
- **Live Monitored Ports**:
  - **Web & Portals (3)**: `:3000` (Zone 2 Endurance), `:4000` (Movesense ECG Hub), `:8890` (Voilà Master Studio).
  - **Distributed AI Inference (4)**: `:8081` (prima.cpp Master), `:8082` (prima.cpp PRP Ring), `:8083` (Devil's Advocate 27B), `:8084` (llama.cpp Worker 4).
  - **TUIs & Workbenches (2)**: `:8088` (Universal Web-TUI Portal), `:8889` (JupyterLab Master IDE).
  - **Infrastructure & Storage (5)**: `:8888` (SeaweedFS Filer), `:9000` (AI Budget Proxy), `:9333` (SeaweedFS Master Raft), `:18802` (Self-Healing Hub), `:18805` (Real-Time Live Command Console).
- **Layout Presets**: Full Stack Quad, AI Cluster Quad, Ops Grid Quad, Storage Quad.
- **Dynamic Viewports**: 2x2 Quad, 1x2 Split, 1x1 Solo with selectable pane heights (380px, 520px, 750px).
- **Embedded Iframes**: Interactive live browser views directly into active ports.

### Tab 3: 🖥️ 3. Multi-TUI Suite (Port 8088 Streamer)
- **Role**: WebSocket PTY bridge for terminal apps rendered at 120 FPS.
- **Active Dashboards**:
  - `🏛️ Canonical Port 9-Screen Command Center (:8088/canonical)`
  - `💓 Movesense Readiness & Cardio Coach (:8088/readiness)`
  - `🥋 3D Spatial Grappling Kinematics (:8088/grappling)`
  - `⚔️ Lauburu Combat Arena & Swarm Game (:8088/arena)`
  - `🏆 Universal Live Leaderboard (:8088/leaderboard)`
  - `🤖 SmolAgents Python Duel Sandbox (:8088/smolagents)`
  - `🛍️ Headless Storefront & Membership Tiers (:8088/store)`
- **Shortcuts**: `[Tab]` Cycle Views, `[r]` Re-balance Shards, `[o]` Optimize Mesh, `[q]` Quit.

### Tab 4: 📡 4. 7-Layer Mesh Physical Radar (82.8 GB Pooled VRAM)
- **Role**: Dynamic latency and RAM governor dashboard for the 7 physical hardware layers.
- **Hardware Topology**:
  - `L1 Mac_Node (Host M4 Mini)`: `100.119.199.76:8082` | 24G RAM (21.6G AI) | Cap: 90%
  - `L2 MacBook_Pro (x86_64)`: `100.103.212.21:50053` | 16G RAM (14.0G AI) | Cap: 90% | 40 Gbps TB4 PHY DMA (0.27ms RTT)
  - `L3 Linux_Head_Node (Ryzen 7)`: `100.101.39.98:50052` | 16G RAM (13.8G AI) | Cap: 80%
  - `L4 Linux_Tablet (Debian Touch)`: `100.81.92.125:22` | 8G RAM (6.5G AI) | Cap: 75%
  - `L5 MacBook_Air (M4 Metal)`: `100.93.158.96:8081` | 16G RAM (14.0G AI) | Cap: 90%
  - `L6 Pixel_10_Pro_XL (Tensor G5)`: `100.73.38.87:8022` | 16G RAM (12.5G AI) | Cap: 85%
  - `L7 Samsung_S20 (Automated Tester)`: `100.84.40.95:8022` | 12G RAM (9.0G AI) | Cap: 75%
  - `GW GL.iNet Router (Hardware Gateway)`: `100.122.185.123:80` | Embedded

### Tab 5: 🫀 5. 512Hz ECG DSP & Pan-Tompkins QRS Detector
- **Role**: Medical-grade digital signal processing visualizer.
- **Interactive Controls**: Real-time noise slider ($0.0 - 1.0$), compute pipeline trigger.
- **Visual Waveforms (Plotly)**:
  - Raw ECG (512Hz single-lead microvolts)
  - 4th-order Butterworth Bandpass Filtered (5–15 Hz)
  - Energy Envelope (Moving Window Integration / MWI)
  - Real-time detected heart rate (BPM) and RR interval segmentation.

### Tab 6: 🥋 6. 955-Node BJJ Spatial Grappling Hierarchy
- **Role**: Biomechanical kinetic mindmap explorer and submission tree.
- **Data Sources**:
  - `mindomo_final copy.opml` (955 Canonical Nodes)
  - `grappling.opml` (3,044 Extended Nodes)
  - `mindomo_Grappling Mind Map 2.opml` (3,723 Deep Nodes)
- **Features**: Real-time XML tree parsing, live substring search filter, technique category inspection (Collar Tie, Outside Tie, Underhook, 2-on-1, Snatch Single, Ankle Pick, Rear Body Lock, Front Headlock).

### Tab 7: ⚔️ 7. CoreWar CodeClash Master Arena (4096-Cell Core)
- **Role**: Assembly memory arena duel simulator and autonomous redcode tournament.
- **Warriors**: `lauburu_champion`, `silk_replicator`, `dwarf_bomber`, `imp_ring`, `qwen_anti_silk_hunter`, `stone_bomber`, `vampire_pit`.
- **Engine**: 4096-cell circular core PMARS emulator.
- **Tournament**: 50-round matches updating Bradley-Terry ELO ratings live in the table.

### Tab 8: ⚡ 8. 1-Click Multi-Domain System Self-Healing
- **Role**: Automated execution of 5-tier self-healing protocols.
- **Actions**: Cleans stale `.git/index.lock`, restores disk headroom ($\ge 10$ GB free), recovers Obsidian `Index.md`, checks PySpark datasets, cleans orphan memory sockets.

### Tab 9: 📊 9. Real-Time Monorepo AST & Polyglot LOC Scanner
- **Role**: Live codebase inventory across all 12 domains.
- **Metrics**: Recursively analyzes 71,453 files and 28,780,005 lines of code, breaking down files and LOC for `00_core_infrastructure` (9,631 files / 3.97M LOC), `01_apps` (36,356 files / 15.91M LOC), `02_ai_models` (13,543 files / 4.12M LOC), `05_agents` (11,551 files / 4.66M LOC), etc.

### Tab 10: 🤖 10. AI Swarm Bridge (Antigravity ◄──► Local Qwen)
- **Role**: Bidirectional co-programming channel between cloud Antigravity IDE and Sovereign Local AI (Qwen 3.8 Max / Qwen MoE 80B).
- **Ports**: Connected via `:18803` and `:8083`.
- **Queues**: Real-time inbox task queue and outbox completed diff queue.

### Tab 11: 📈 11. AI Training & ELO Progression Tracker
- **Role**: Tracking 24/7 continuous DPO and LoRA distillation trajectories.
- **Key Metrics**:
  - Total Harvested Pairs: **93,142 Pairs**
  - Neo 12B BFCL Accuracy: **98.48%**
  - Step Loss: $0.485 \rightarrow 0.370 \rightarrow 0.284$ (Step 8,500)
  - Apex Swarm ELO: **2,915.0 ELO** ($0.00 cloud spend)
  - 16-Model ELO Ladder: From SmolLM2 135M (2292) to Combined Apex Team (2915).

### Tab 12: 🏛️ 12. Canonical Mesh Architecture & Tri-Vault Storage
- **Role**: Interactive master whitepaper summarizing the entire ecosystem.
- **Panels**: Pooled Physical RAM (108.0 GB), Usable AI VRAM (82.8 GB), Thunderbolt 4 RTT (0.277 ms), Dynamic Host Cap ($\le 90\%$, $\ge 9.6$ GB buffer), Tri-Vault synchronization contracts.

---

- Links: [[Index]] | [[01_APPS_AND_PORTAL_CATALOG]] | [[CANONICAL_APPS_OVERVIEW]]
