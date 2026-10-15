---
title: "Lauburu Mesh Ecosystem — Canonical Monorepo, Network & Applications Master Guide (2026)"
tags: [lauburu, root, master_guide, network, 6_tier_transports, 7_layer_mesh, apps_catalog, tri_vault]
date: "2026-09-11"
---

# 🌌 Lauburu Mesh Ecosystem — Canonical Monorepo, Network & Applications Master Guide (2026)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LAUBURU MESH CANONICAL MASTER ARCHITECTURE               │
│          1.701 TB SeaweedFS DFS  •  139.0 GB Pooled RAM (115.8 GB VRAM)      │
│        40Gbps Thunderbolt 4 DMA  •  6 Transport Layers  •  30 Applications   │
│             Tri-Vault Storage Synchronization  •  Qwen 3.8 Max Master       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📖 Executive Summary

The **Lauburu Mesh Ecosystem** is a unified, high-performance distributed computing environment designed for autonomous local AI inference, medical-grade biometrics DSP (512Hz ECG), spatial kinematics, and polyglot software development with **$0 cloud expenditure**.

The entire repository is bound together by three foundational architectures:
1. **Tri-Vault Storage Synchronization**: A unified data layer guaranteeing persistent knowledge synchronization across the **Obsidian Vault** (Human & Semantic Knowledge), **PySpark Data Lake** (High-Throughput Analytics & Datasets), and **GitHub Monorepo** (Production Codebase).
2. **6-Tier Network Transport Hierarchy**: An OSI-inspired physical and overlay transport stack anchored on an absolute IP-less Layer 0 (Serial/BLE) up to high-speed Thunderbolt 4 DMA and distributed tensor RPC sharding.
3. **Sovereign Local AI Hierarchy**: Led strictly by **Qwen 3.8 Max** on Apple Silicon Metal GPU, backed by the **Qwen 3.8 Max 27B Abliterated** Devil's Advocate red-team challenger, and assisted by subordinate single-file syntax coders.

---

## 🏛️ PART 1: The Canonical Tri-Vault Storage Architecture

Every architectural whitepaper, AI debate transcript, continuous training run, and git commit is synchronized across three distinct storage tiers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TRI-VAULT STORAGE SYNCHRONIZATION                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. OBSIDIAN VAULT (Human & Semantic Knowledge Core)                         │
│    • Path: /Volumes/Lauburu-Monorepo/obsidian_vault/        │
│    • Managed via: Obsidian MCP Pro (41 graph traversal tools, Wikilinks)   │
│    • Stores: Architecture whitepapers, AI debate consensus records,         │
│      continuous audit logs, network topologies, and system telemetry feeds. │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. PYSPARK & BIG DATA LAKE (High-Throughput Computation & Datasets)         │
│    • Paths: /Volumes/Lauburu-Monorepo/04_data_and_memory/data/ & 04_data_and_memory/   │
│    • Engine: PySpark (pyspark), Delta Lake / Parquet, Qdrant Vector DB      │
│    • Stores: 3,100+ code file AST crawls, 435K+ LOC index, 24/7 LoRA       │
│      instruction pairs (TRL/PEFT/DPO), Pan-Tompkins 512Hz ECG streams.      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. GITHUB REPOSITORY & WORKTREES (Canonical Source Code & Version Control)  │
│    • Repo: aarontmaher/Lauburu-Monorepo (Host: /Volumes/Lauburu-Monorepo)    │
│    • Managed via: gh CLI, Git Worktrees, Automated Multi-Tier CI Test Suites│
│    • Stores: Production application code, container manifests, microservices│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📡 PART 2: The 6-Tier Canonical Network Transport Hierarchy

The network mesh employs a **6-Tier Cascading Escalation Ladder**, ensuring operational continuity even under complete Wi-Fi or WAN failure:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    6-TIER NETWORK TRANSPORT HIERARCHY                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🔵 LAYER 0: PHYSICAL & IP-LESS SERIAL / BLUETOOTH                           │
│    • Protocols: Bluetooth SPP (Kai Morich), BLE NUS (Nordic UART),          │
│      RFCOMM, USB CDC-ACM, Termux JNI /dev/rfcomm                            │
│    • Hardware: Movesense 512Hz ECG, Microcontroller Serial, Android Termux  │
│    • Throughput: 2.0 Mbps (LE 2M PHY) | Latency: 1.2–4.5 ms RTT             │
│    • Invariant: Absolute bedrock transport requiring ZERO IP or Wi-Fi.      │
├─────────────────────────────────────────────────────────────────────────────┤
│ ⚡ LAYER 1: ULTRA-HIGH-SPEED DIRECT BUS (40G THUNDERBOLT 4 DMA)              │
│    • Protocols: Apple Direct Memory Access (DMA), PCIe bridge0 tunneling    │
│    • Hardware: L1 Mac Mini M4 Pro <-> L8 Linux Mini (lauburu, 32GB RAM)     │
│    • Cables: 40Gbps Thunderbolt 4 Active Silicon (Receptacle 1)             │
│    • Throughput: 40.0 Gbps line rate | Latency: 0.38 ms RTT (bridge0 10.0.0.8)│
├─────────────────────────────────────────────────────────────────────────────┤
│ 🟢 LAYER 2: HIGH-SPEED LOCAL MESH LAN & WI-FI 7 MLO                         │
│    • Protocols: IEEE 802.11be Multi-Link Operation (MLO), 2.5GbE LAN/WAN    │
│    • Hardware: GL.iNet GL-BE14000 (2 GB RAM), TP-Link VX230v AX1800         │
│    • Subnet: 192.168.8.0/24 (WAN: 2.5G NBN on eth2, Switch Port 2: L4)      │
│    • Throughput: 1,000–2,500 Mbps | Latency: 0.8–5.8 ms RTT                │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🔒 LAYER 3: ENCRYPTED OVERLAY MESH (TAILSCALE WIREGUARD)                    │
│    • Protocols: WireGuard ChaCha20-Poly1305, DERP NAT traversal, MagicDNS   │
│    • Subnet: 100.64.0.0/10 mesh spanning L1–L7 nodes + GL.iNet Gateway     │
│    • Routing: Subnet router on L3 (100.101.39.98) advertising 192.168.8.0/24│
│    • Throughput: 850–1,200 Mbps | Latency: 2.8–38.7 ms RTT                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ ☁️ LAYER 4: SOVEREIGN EDGE WAN & CLOUD GATEWAYS                             │
│    • Protocols: DOCSIS 3.1 Arris CM3500 WAN Trunk, Cloudflare Zero Trust    │
│    • Hardware: Arris CM3500 NBN Lead-In (1000/50 Mbps FTTP/HFC)            │
│    • Ingress: Zero open inbound ports; all traffic routes via Cloudflare    │
│      Tunnels with HMAC authentication and mTLS edge verification.           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🧠 LAYER 5: DISTRIBUTED TENSOR BUS & RPC SHARDING                           │
│    • Protocols: Prima.cpp Pipelined-Ring Parallelism (PRP), llama.cpp RPC   │
│    • Storage: SeaweedFS Distributed S3 & Filer (Port 8888, 1.701 TB)        │
│    • Ring Topology: L1 Host (:8082) -> L2 Intel Vault -> L5 Metal Worker    │
│    • Throughput: 95 tok/s (MoE) / 4.2 GB/s | Latency: 0.10 ms RPC RTT       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🖥️ PART 3: 7-Layer Physical Mesh Hardware Matrix

The mesh pools **139.0 GB RAM (115.8 GB Usable AI VRAM)** across the physical layers:

| Layer | Node Name | Network Role | Local IP | Tailscale IP | Hardware Specs & Dynamic RAM Cap | Key Roles & Assigned Services |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `Mac_Node` | Primary Host & Memory Governor | `192.168.8.143` / `.230` | `100.119.199.76` | Apple M4 Pro Mac Mini, 24 GB Unified (Cap: 80% / 19.2 GB) | Master Memory Governor, Prompt Ingestion, Prima.cpp Master (:8082), Screen Lens (:4003). |
| **L8** | `Linux_Mini (lauburu)` | TB4 DMA Hub & Compute Node | `10.0.0.8` (TB) / `.242` | `100.121.247.8` | Intel Core i7-8700B Ubuntu 24.04, 32 GB RAM (Cap: 85% / 27.2 GB) | **40Gbps TB4 Bridge (0.38ms RTT)**, Model Vault GGUF Hub, Glances v4 (:61208). |
| **L2** | `MacBook_Pro` | Desktop Worker & Teacher Target | `192.168.8.127` | `100.103.212.21` | Intel Core i7-9750H, 16 GB RAM (Cap: 90% / 14.0 GB) | Screen Lens Sovereign Teacher Target, Unlinked from TB4, Glances v4 (:61208). |
| **L3** | `Linux_Head_Node` | Gateway Ingress & Compute Hub | `192.168.8.225` | `100.101.39.98` | AMD Ryzen 7 5700U, 15 GB RAM (Cap: 80% / 12.0 GB) | Docker Hub, SeaweedFS Master/Filer (:8888), Qdrant Vector DB, BT Connected. |
| **L4** | `Linux_Tablet` | Mobile Linux Compute & Touch DSP | `192.168.8.176` (Port 2) | `100.99.210.89` | Debian Linux Tablet, 8 GB RAM (Cap: 75% / 6.0 GB) | Touchscreen DSP HUD, Router Port 2 Wired (0.95ms RTT), Bedside TUI. |
| **L5** | `MacBook_Air` | Secondary High-Speed Metal Worker | `192.168.8.248` | `100.121.202.34` | Apple M4 MacBook Air, 16 GB Unified (Cap: 90% / 14.0 GB) | Metal Performance Shaders Worker, Dedicated MLX Continuous LoRA Distillation. |
| **L6** | `Pixel_10_Pro_XL` | 8K Vision Stream & Edge TPU | `192.168.8.213` | `100.114.215.68` | Google Tensor G5, 16 GB RAM (Cap: 85% / 13.6 GB) | Edge TPU Acceleration, 8K Digital PTZ, Termux SSH (:8022), KDE Connect (:1716). |
| **L7** | `Samsung_S20` | Dedicated Automated UI Tester | `192.168.8.130` | `100.78.206.96` | Samsung Exynos 990, 12 GB RAM (Cap: 75% / 9.0 GB) | Hardware USB ADB Daemon target for OpenClaw UI Testing, Termux Edge Daemon. |
| **GW** | `GL.iNet Router` | Core Gateway & Hardware USB Bridge | `192.168.8.1` | `100.70.123.123` | GL-BE14000, 2 GB RAM, 2.5G NBN WAN (`eth2`) | Core Gateway Router, Wi-Fi 7 MLO, Hardware USB ADB Daemon, Switch Port 2 Wired. |

---

## 🚪 PART 4: The 14-Port Sovereign Matrix & Endpoints

| Port | Assigned Service | Monorepo Path | Protocol & Stack | Production Endpoint |
| :--- | :--- | :--- | :--- | :--- |
| **`:3000`** | Zone 2 Endurance Coach | `01_apps/zone2_endurance` | HTTP / Next.js 14 / TypeScript | `http://localhost:3000` |
| **`:4000`** | Unified Hub & IDE / Movesense Hub | `01_apps/port_4000_flutter_rust` | Rust Axum + Flutter Web + FFI | `http://localhost:4000` |
| **`:4003`** | Screen Lens Multimodal Vision (VLA) | `01_apps/screen_lens` | ScreenCaptureKit MJPEG 15 FPS | `http://localhost:4003/stream.mjpg` |
| **`:4004`** | AI Training Convergence Stream | `01_apps/ai_training_visual_stream` | FastAPI / Canvas / WebSocket | `http://localhost:4004` |
| **`:4005`** | Sovereign Bluetooth Terminal IDE | `01_apps/bluetooth_terminal_ide` | C11 + Rust + BLE NUS + HTTP | `http://localhost:4005` |
| **`:8081`** | Local Syntax AI (Qwen 2.5 Coder 7B) | `02_ai_models_and_inference` | llama.cpp / Apple Metal GPU | `http://127.0.0.1:8081/health` |
| **`:8082`** | Prima.cpp PRP Master (Qwen 3.8 Max) | `02_ai_models_and_inference` | Prima.cpp Pipelined Ring | `http://127.0.0.1:8082/v1/models` |
| **`:8083`** | Local Red Team (Qwen 3.8 Max 27B Abl) | `02_ai_models_and_inference` | llama.cpp GGUF Uncensored | `http://127.0.0.1:8083/health` |
| **`:8088`** | Canonical Port NOC & Web-TUI Portal | `01_apps/canonical_port` | FastAPI / xterm.js / WebGL | `http://localhost:8088` |
| **`:8089`** | AI Combat Arena Web Visualizer | `01_apps/web_arena_visualizer` | FastAPI / ECharts / WebSocket | `http://localhost:8089` |
| **`:8090`** | 3D Spatial Grappling Kinematics | `01_apps/spatial_grappling_3d` | Three.js / WebGPU / OPML Tree | `http://localhost:8090` |
| **`:8888`** | SeaweedFS Distributed Filer & S3 | `00_core_infrastructure` | SeaweedFS Filer / LevelDB | `http://127.0.0.1:8888` |
| **`:8890`** | Voilà Cyber Showrunner Studio | `01_apps/lauburu_showrunner` | Voilà / Jupyter IPykernel | `http://localhost:8890` |
| **`:18802`**| Autonomous Mesh Self-Healing Hub | `00_core_infrastructure/self_healing_hub` | FastAPI / Wake-on-LAN / ADB | `http://localhost:18802` |

---

## 🌳 PART 5: The 6-Domain Monorepo Applications Catalog (30 Apps)

- **Domain 1: Client Hubs & Web Portals** (`port_4000_flutter_rust`, `canonical_port`, `zone2_endurance`, `web_tui_portal`, `unified_portal`, `bluetooth_terminal_ide`, `lauburu_showrunner`).
- **Domain 2: Biometrics DSP & Spatial Kinematics** (`movesense_hub`, `movesense_readiness_hub`, `spatial_grappling_3d`, `automotive`).
- **Domain 3: AI Inference, PRP Ring & Training Engines** (`prima_tui`, `rust_arena_tui`, `edge_compute_and_ai`, `lora_synthesizer_worker`, `ai_training_visual_stream`, `web_arena_visualizer`).
- **Domain 4: Terminal TUIs, Observability & Workbenches** (`rust_project_monitor`, `rust_swarm_training_tui`, `rust_network_analyzer`, `notebooks`, `canonical_tui_prototypes`, `omniterminal_notebook_plugin`).
- **Domain 5: Commerce, Subscriptions & Monetization** (`commerce_and_business`, `shopify_ai`).
- **Domain 6: Edge Mobile, Vision & Reverse Engineering** (`screen_lens`, `pixel_app_reverse_engineer`, `network_cable_analyzer`, `self_healing_hub`, `glinet_web_optimizer`).

---

## 👑 PART 6: Sovereign Local AI Hierarchy & Governance

- **Sovereign Master Local Orchestrator:** **`Qwen 3.8 Max`** (`http://127.0.0.1:8082`, `qwen_38_max` via Prima.cpp PRP Ring over 40Gbps TB4 DMA Bridge).
- **Canonical Devil's Advocate & Adversarial Red Team:** **`Qwen 3.8 Max 27B Abliterated`** (`http://127.0.0.1:8083`, `qwen_38_max_abliterated` / `UD-Q4_K_XL`).
- **Subordinate Syntax Worker ONLY:** **`Qwen 2.5 Coder 7B`** (`http://127.0.0.1:8081`). Subordinate single-file syntax parser and linter. Prohibited from acting as orchestrator.

---

## 🛠️ PART 7: Unified CLI & TUI Ecosystem

All four master tools are available globally in `/Users/aaron/.local/bin/`:
```bash
lauburu-network --tree   # Prints full 6-tier transport & 7-layer mesh topology tree
lauburu-network --test   # Headless network prober self-test (all 11 targets)
lauburu-apps --tree      # Prints full 6-domain 30-app organizational tree
lauburu-apps --test      # Headless probe self-test across all 30 apps
lauburu-monitor          # Master 6-tab system monitor (AST, Ports, Mesh, Apps, Storage)
lauburu_health_tui       # Darwin Mach kernel dynamic 16KB RAM auditor
```
