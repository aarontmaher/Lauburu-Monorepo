---
title: "01 Apps and Portal Catalog — Master Endpoints, Web-TUIs & Interactive Studios"
tags: [apps, portals, catalog, endpoints, tui, voila, seaweedfs, live_console, tri_vault]
---

# 🌐 01 Apps and Portal Catalog — Master Endpoints & Interactive Studios

- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- [[CANONICAL_APPS_OVERVIEW]]
- [[00_MASTER_INFRASTRUCTURE_TOPOLOGY]]
- [[VOILA_PORT_8890_MASTER_CYBER_STUDIO]]
- [[03_MOVESENSE_512HZ_ECG_DSP_PIPELINE]]
- [[04_PYSPARK_AND_LORA_DATA_LAKE]]

---

## 🏛️ 1. Master Endpoints & Port Architecture Matrix

Under **Rule #0 (Zero-Mock & Zero-Simulated Data Mandate)**, every portal, TUI, and dashboard connects directly to live hardware sockets, physical BLE sensors, kernel syscalls, or renders unambiguous zero-mock standby states.

| Port / Endpoint | Service Name | Host / Layer | Technology Stack | Operational Role & Capabilities | Empirical Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`http://127.0.0.1:8890/`** | **Voilà Master Cyber Studio** | `L1 Mac Mini M4 Pro` | Python 3.13, Voilà 0.5.8, ipywidgets, Plotly | **12-Tab SSoT Studio**: Cyber IDE, 14-Port Matrix 2x2 multiplexer, Multi-TUI, 7-Layer Radar, 512Hz ECG DSP, 955-Node BJJ OPML, CoreWar Arena, 1-Click Optimizer, Monorepo AST Scanner, AI Swarm Bridge, AI Training & ELO Progression, Canonical Mesh Arch. | **● LIVE** (HTTP 200, Tornado 6.5.8) |
| **`http://100.119.199.76:18805/`** | **Real-Time Mesh Live Console** | `L1 Mac Mini M4 Pro` | Python 3, FastAPI, Uvicorn (`ai_mesh_live_monitor.py`) | Real-time live command console, genetic radar gauges, model download speedometers, and multi-device telemetry watchdog. | **STANDBY** (Process idle; start via `python3 00_core_infrastructure/ai_mesh_live_monitor.py`) |
| **`http://100.119.199.76:8088/`** | **Universal Web-TUI Portal** | `L1 Mac Mini M4 Pro` | Python 3, aiohttp, xterm.js, WebSocket PTY (`serve_web_tui.py`) | **8 TUI Micro-Dashboards**: Canonical Command Center (`:8088/canonical`), Movesense Readiness (`:8088/readiness`), 3D Grappling (`:8088/grappling`), Combat Arena (`:8088/arena`), ELO Leaderboard (`:8088/leaderboard`), SmolAgents Duel (`:8088/smolagents`), Storefront (`:8088/store`), Streamer Root (`:8088`). | **STANDBY** (Process idle; start via `python3 01_apps/canonical_port/tui/serve_web_tui.py`) |
| **`http://100.93.158.96:8890/`** | **MacBook Air Voila Studio** | `L5 MacBook Air M4` | Python 3, Voilà, JupyterLab (`100.93.158.96`) | Distributed secondary notebook execution node & Metal Performance Shaders worker for remote telemetry offload. | **STANDBY** (Host in battery DarkWake/sleep state; WoL target) |
| **`http://100.101.39.98:8888/`** | **SeaweedFS Distributed Filer** | `L3 Linux Head Node` | Go, SeaweedFS 30GB v3.79 (`100.101.39.98`) | Distributed high-throughput blob & POSIX filesystem filer for Big Data Lake, LoRA checkpoints, and Parquet ECG streams. | **● LIVE** (HTTP 200, SeaweedFS 3.79) |
| **`http://127.0.0.1:3000/`** | **Zone 2 Cardiovascular Trainer** | `L1 Mac Mini M4 Pro` | Next.js 14 RSC, React 18/19, Web Bluetooth | Real-time aerobic lipid oxidation corridor tracking, DFA-alpha1 LT1 (0.75) trend charts, WCAG AA live announcer. | **● LIVE** (HTTP 200, Next.js) |
| **`http://127.0.0.1:4000/`** | **Movesense 512Hz Unified Hub** | `L1 Mac Mini M4 Pro` | Rust Axum 0.7, Tokio, Flutter UI, `btleplug` | Clinical 512Hz Pan-Tompkins ECG DSP, Kamath 20% filter, PTT blood pressure, 7-node speedway, 3D tatami kinematics. | **● LIVE** (HTTP 200, Rust Axum) |
| **`http://127.0.0.1:4002/`** | **Screen Lens Marimo Studio** | `L1 Mac Mini M4 Pro` | Python 3, Marimo reactive notebook server | Headless local AI Neo integration, interactive reactive cells, Stage 4 Human Sovereign Approval Banner. | **STANDBY** (On-demand reactive) |
| **`http://127.0.0.1:4003/`** | **Screen Lens Live MJPEG Stream** | `L1 Mac Mini M4 Pro` | Python 3, CoreGraphics ctypes (<1ms) | Continuous zero-mock 10–15 FPS multipart live screen broadcast (`/stream.mjpg`) under Rule #7. | **STANDBY** (On-demand streamer) |
| **`http://127.0.0.1:4004/`** | **Omnichannel Knowledge Hub** | `L1 Mac Mini M4 Pro` | Python 3, HTTPServer, AST indexer | 4-stream cross-indexer, sub-150ms search across Obsidian vault, chat transcripts, and token budgets. | **STANDBY** (On-demand explorer) |
| **`http://127.0.0.1:18802/`** | **Self-Healing Hub & WoL Engine** | `L1 Mac Mini M4 Pro` | Python 3, FastAPI, Wake-on-LAN | 5-tier self-healing daemon, RFC 792 magic packets (UDP 7/9), mesh node resurrection, process watchdog. | **● LIVE** (HTTP 200, FastAPI) |

---

## 🖥️ 2. Deep-Dive: Universal Web-TUI Portal (`:8088`)

The **Universal Web-TUI Portal** (`01_apps/canonical_port/tui/serve_web_tui.py`) uses a high-concurrency `aiohttp` server and asynchronous pseudoterminals (`pty.openpty()`) to stream native terminal interfaces directly to web browsers via WebSockets and xterm.js at 120 FPS.

### 2.1 The 8 Specialized TUI Applications
1. **`🏛️ Canonical Port 9-Screen Command Center (:8088/canonical)`**:
   - Source: `01_apps/canonical_port/tui/canonical_tui.py`
   - Tier: Operator & Developer
   - Features: Full 14-port status matrix, RAM headroom gauges, Tailscale ping latency grid, active process inspector.
2. **`💓 Movesense Readiness & Cardio Coach (:8088/readiness)`**:
   - Source: `01_apps/biometrics/movesense_readiness_tui.py`
   - Tier: User & Athlete
   - Features: Live 512Hz ASCII ECG oscilloscope, real-time BPM, RMSSD parasympathetic recovery gauge, Zone 2 DFA-alpha1 corridor indicator.
3. **`🥋 3D Spatial Grappling Kinematics (:8088/grappling)`**:
   - Source: `01_apps/spatial_and_3d/spatial_grappling_3d/presentation/tui.py`
   - Tier: User & Athlete
   - Features: 3,044-node OPML knowledge graph traversal, joint torque limits (Armbar 45 N·m, Heel Hook 38/55 N·m), submission danger states.
4. **`⚔️ Lauburu Combat Arena & Swarm Game (:8088/arena)`**:
   - Source: `01_apps/canonical_port/tui/tui_live_arena_dev.py`
   - Tier: User & Developer
   - Features: CoreWar CodeClash arena, redcode warrior duels, Bradley-Terry ELO ratings, real-time memory core visualization.
5. **`🏆 Universal Live Leaderboard (:8088/leaderboard)`**:
   - Source: `01_apps/canonical_port/tui/serve_web_tui.py`
   - Tier: Global NOC
   - Features: Real-time ELO rankings across all 16 local and cloud models (SmolLM2 135M at 2292 ELO up to Combined Apex Swarm at 2915 ELO).
6. **`🤖 SmolAgents Python Duel Sandbox (:8088/smolagents)`**:
   - Source: `01_apps/canonical_port/tui/serve_web_tui.py`
   - Tier: Developer & Operator
   - Features: Isolated Python execution sandbox for autonomous code execution benchmarking without host corruption.
7. **`🛍️ Headless Storefront & Membership Tiers (:8088/store)`**:
   - Source: `01_apps/commerce_and_business/storefront_membership_tui.py`
   - Tier: Commerce & Business
   - Features: Shopify Storefront GraphQL customer account query, subscription tiers ($29 Pro / $99 Gym Master), token allowance verification.
8. **`⚡ Universal Streamer Root (:8088)`**:
   - Source: `01_apps/canonical_port/tui/serve_web_tui.py`
   - Tier: Master Switchboard
   - Features: Unified launcher to select and hot-swap between any of the 7 active TUI sessions.

---

## ⚡ 3. Deep-Dive: Real-Time Live Command Console (`:18805`)

The **Real-Time Live Command Console** (`00_core_infrastructure/ai_mesh_live_monitor.py`) is an ultra-lightweight FastAPI daemon operating on Port 18805 designed for live operations monitoring:
- **Low Memory Footprint**: Uses pure Python standard library and FastAPI/Uvicorn (<25 MB RAM).
- **Genetic Radar**: Tracks generational mutation rates, token compression ratios, and speculative drafting accuracy.
- **Model Download Gauges**: Visualizes live model pull progress, quantization benchmarks, and shard allocations.
- **Auto-Refresh**: 2000ms WebSocket/HTTP polling loop with zero mock data.

---

## 📡 4. Deep-Dive: Distributed Storage Layer (`:8888` & `:9333`)

The **SeaweedFS Distributed Storage Cluster** (`100.101.39.98:8888`) operates on the L3 Linux Head Node:
- **SeaweedFS Filer (:8888)**: Exposes a unified POSIX-like namespace over HTTP/REST and WebDAV.
- **SeaweedFS Master Raft (:9333)**: Governs volume assignment and replication across physical drives.
- **Role in Tri-Vault Storage**: Serves as the primary blob store for 512Hz raw biometrics, Parquet datasets, and 24/7 LoRA checkpoints, keeping heavy bulk storage off the primary Mac Mini SSD.

---

- Links: [[Index]] | [[VOILA_PORT_8890_MASTER_CYBER_STUDIO]] | [[00_MASTER_INFRASTRUCTURE_TOPOLOGY]] | [[CANONICAL_APPS_OVERVIEW]]
