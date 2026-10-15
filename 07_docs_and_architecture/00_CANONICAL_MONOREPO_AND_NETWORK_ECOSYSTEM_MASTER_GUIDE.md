# 🌌 Lauburu Mesh Ecosystem — Canonical Monorepo, Network & Applications Master Guide (2026)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LAUBURU MESH CANONICAL MASTER ARCHITECTURE               │
│          1.701 TB SeaweedFS DFS  •  109.0 GB Pooled RAM (91.4 GB VRAM)       │
│        10Gbps Thunderbolt 4 DMA  •  6 Transport Layers  •  30 Applications   │
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
│    • Path: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/        │
│    • Managed via: Obsidian MCP Pro (41 graph traversal tools, Wikilinks)   │
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

### Pre-Flight Storage Invariants
- Host disk headroom must strictly preserve $\ge 10.0\text{ GB}$ free disk space.
- `obsidian_vault/Index.md` must remain populated with canonical master Wikilinks.
- `.git/index.lock` must be cleared before modifying code.

---

## 📡 PART 2: The 6-Tier Canonical Network Transport Hierarchy

The network mesh does not rely solely on traditional Wi-Fi or internet connectivity. It employs a **6-Tier Cascading Escalation Ladder**, ensuring operational continuity even under complete Wi-Fi or WAN failure:

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
│ ⚡ LAYER 1: ULTRA-HIGH-SPEED DIRECT BUS (10G/40G THUNDERBOLT 4 DMA)         │
│    • Protocols: Apple Direct Memory Access (DMA), PCIe bridge0 tunneling    │
│    • Hardware: L1 Mac Mini M4 Pro <-> L2 MacBook Pro <-> L5 MacBook Air     │
│    • Cables: 40Gbps Lintes 240W Certified & Tankya 240W Active Silicon      │
│    • Throughput: 40.0 Gbps line rate (4.2 GB/s DMA) | Latency: 0.27 ms RTT  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🟢 LAYER 2: HIGH-SPEED LOCAL MESH LAN & WI-FI 7 MLO                         │
│    • Protocols: IEEE 802.11be Multi-Link Operation (MLO), Realtek 2.5GbE    │
│    • Hardware: GL.iNet Beryl 7 (GL-MT3600BE), TP-Link VX230v AX1800, Netgear│
│    • Subnet: 192.168.8.0/24 (DHCP pool: .100–.250, Static: .1–.99)         │
│    • Throughput: 1,000–2,500 Mbps | Latency: 1.5–5.8 ms RTT                │
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

The mesh pools **109.0 GB RAM (91.4 GB Usable AI VRAM)** across 7 physical layers, governed by dynamic hardware limits:

| Layer | Node Name | Network Role | Local IP | Tailscale IP | Hardware Specs & Dynamic RAM Cap | Key Roles & Assigned Services |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `Mac_Node` | Primary Host & Memory Governor | `192.168.8.230` | `100.119.199.76` | Apple M4 Pro Mac Mini, 24 GB Unified (Cap: 90% / 21.6 GB) | Master Memory Governor, Prompt Ingestion, Prima.cpp Master (:8082), Screen Lens (:4003). |
| **L2** | `MacBook_Pro` | Metal GPU RPC & Storage Vault | `192.168.8.127` | `100.103.212.21` | Intel Core i7, 16 GB RAM (Cap: 90% / 14.0 GB), TB4: `169.254.187.138` | 10Gbps TB4 DMA Bridge (0.27ms RTT), 285 GB SSD Model Storage Vault, Secondary Worker. |
| **L3** | `Linux_Mini` | Gateway Ingress & Compute Hub | `192.168.8.224` | `100.101.39.98` | Intel 2018 Mac Mini (Linux), 16 GB RAM (Cap: 80% / 13.8 GB) | Docker Hub, SeaweedFS Master/Filer (:8888), Subnet Router, Petals DHT Bootstrap. |
| **L4** | `Linux_Tablet` | Mobile Linux Compute & Touch DSP | DHCP | `100.81.92.125` | Debian Linux Tablet, 8 GB RAM (Cap: 75% / 6.5 GB) | Touchscreen DSP HUD, Secondary Petals Worker, Bedside Biometrics Visualizer. |
| **L5** | `MacBook_Air` | Secondary High-Speed Metal Worker | `192.168.8.222` | `100.121.202.34` | Apple M4 MacBook Air, 16 GB Unified (Cap: 90% / 14.0 GB) | Metal Performance Shaders Worker, Dedicated MLX Continuous LoRA Distillation. |
| **L6** | `Pixel_10_Pro_XL` | 8K Vision Stream & Edge TPU | DHCP | `100.73.38.87` | Google Tensor G5, 16 GB RAM (Cap: 85% / 12.5 GB), Titan M2 | Edge TPU Acceleration, 8K Digital PTZ, UWB 3D Spatial Tracking, PRoot Linux. |
| **L7** | `Samsung_S20` | Dedicated Automated UI Tester | DHCP | `100.84.40.95` | Samsung Exynos 990, 12 GB RAM (Cap: 75% / 9.0 GB) | Hardware USB ADB Daemon target for OpenClaw UI Testing, Termux Edge Daemon. |
| **GW** | `GL.iNet Router` | Core Gateway & Hardware USB Bridge | `192.168.8.1` | `100.122.185.123` | MediaTek MT7988A, Wi-Fi 7 MLO (GL-MT3600BE) | Core Router, AdGuard Home DNS, Hardware USB ADB Daemon, kmwan Multi-WAN. |
| **AP** | `TP-Link Router` | Dedicated High-Throughput AP | `192.168.8.2` | `192.168.8.119` | TP-Link VX230v AX1800 AP (Cat6 RJ45 Trunk) | Dedicated 5.0 GHz AP, Wi-Fi 6 Backhaul for Mobile Nodes. |
| **MO** | `Arris Modem` | NBN WAN Physical Lead-In | `192.168.100.1`| `192.168.100.1` | Arris CM3500 DOCSIS 3.1 NBN Trunk | High-Speed Gigabit WAN PHY Termination (1000/50 Mbps NBN). |
| **EX** | `TP-Link Extender`| Bedside Mesh Range Extender | `192.168.8.116`| `192.168.8.116` | TP-Link RE305 AC1200 Dual-Band Extender | Extends coverage to L4 Bedside Tablet and mobile BLE sensors. |

---

## 🚪 PART 4: The 14-Port Sovereign Matrix & Endpoints

All core monorepo applications bind to strictly allocated ports to eliminate port collisions and ensure predictable process orchestration:

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

## 🔌 PART 5: Physical Cabling, Interfaces & GaN Power Matrix

To achieve ultra-low tensor sharding latencies ($0.27\text{ ms}$) without thermal or electrical degradation, all physical interconnects adhere to certified specifications:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHYSICAL CABLE & BUS SPECIFICATIONS                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. 40Gbps Thunderbolt 4 DMA Bus:                                            │
│    • L1 Mac Mini <-> L2 MacBook Pro: Lintes 240W Certified TB4 (0.8m)       │
│    • L1 Mac Mini <-> L5 MacBook Air: Tankya 240W E-Marker TB4 (1.0m)        │
│    • Bridge Interface: bridge0 (Darwin arm64 PCIe tunneling, MTU 9000)      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. 2.5GbE / 1GbE Physical Ethernet:                                         │
│    • Arris CM3500 Modem <-> GL.iNet Beryl 7 2.5G WAN: Cat7 Shielded (1.5m) │
│    • GL.iNet 2.5G LAN <-> TP-Link AX1800 WAN: Cat6a UTP (2.0m)              │
│    • TP-Link LAN <-> Linux Head Node L3: RTL8153 Gigabit USB 3.0 (1.0m)     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. Clean GaN Dual-Rail Power Distribution:                                  │
│    • Rail A (Stationary): AU 240V Mains -> 140W GaN Hub (L1 Mac Mini + L3)  │
│    • Rail B (Peripherals): 100W GaN PD Hub (L2 MacBook Pro + L5 MacBook Air)│
│    • Mobile PD: 65W GaN Multi-Port (L6 Pixel 10 Pro + L7 Samsung S20)       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🌳 PART 6: The 6-Domain Monorepo Applications Catalog (30 Apps)

All 30 active applications across `01_apps/` are categorized into 6 functional domains:

### 🚀 Domain 1: Client Hubs & Web Portals
1. **`port_4000_flutter_rust`** (Port 4000/4001): Rust Axum backend + Flutter Web IDE with hands-free voice coding and live compiler checks.
2. **`canonical_port`** (Port 8088): 9-Screen operations console monitoring 7 physical mesh nodes, pooled RAM, and blackboard stores.
3. **`zone2_endurance`** (Port 3000): Real-time DFA-alpha1 aerobic threshold (LT1/LT2) metabolic coach with auditory pacing.
4. **`web_tui_portal`** (Port 8088): High-throughput WebGL terminal streaming engine delivering zero-latency multi-console switching.
5. **`unified_portal`** (Port 4000): Centralized reverse proxy and single sign-on router aggregating client applications.
6. **`bluetooth_terminal_ide`** (Port 4005): Clean-room SPP/BLE NUS terminal emulator and hardware bridge connecting serial microcontrollers.
7. **`lauburu_showrunner`** (Port 8890): Multi-screen presentation engine streaming interactive biometrics, 3D tatami kinematics, and live AI debates.

### 🩺 Domain 2: Biometrics DSP & Spatial Kinematics
8. **`movesense_hub`** (Port 4000): Authentic 512Hz single-lead ECG streamer with Pan-Tompkins QRS bandpass filtering and HRV RMSSD calculation.
9. **`movesense_readiness_hub`**: Continuous pulse transit time (PTT) blood pressure estimator and autonomic readiness score calculator.
10. **`spatial_grappling_3d`** (Port 8090): 3,044-node martial art spatial kinematics tree mapped to a 10m x 10m tatami world model.
11. **`automotive`**: Automotive heads-up display and hands-free voice coding service streaming biometric strain and code diffs to car HUD.

### 🧠 Domain 3: AI Inference, PRP Ring & Training Engines
12. **`prima_tui`** (Port 8082): Ring memory parallelism coordinator sharding 27B/72B LLM tensor layers across 3 Macs over 10Gbps TB4 DMA.
13. **`rust_arena_tui`**: Autonomous model tournament engine executing 1.4M+ head-to-head architectural debates between local and cloud models.
14. **`edge_compute_and_ai`** (Port 8081): Multi-device tensor streaming daemon routing syntax completion to Qwen 2.5 Coder 7B on Metal GPU.
15. **`lora_synthesizer_worker`**: Continuous instruction pair harvester serializing validated code diffs and debate verdicts into the PySpark Lake.
16. **`ai_training_visual_stream`** (Port 4004): Real-time loss convergence visualizer plotting gradient descent trajectories and DPO margins.
17. **`web_arena_visualizer`** (Port 8089): Live head-to-head AI combat arena UI rendering real-time deliberation rounds and consensus scoring.

### 🖥️ Domain 4: Terminal TUIs, Observability & Workbenches
18. **`rust_project_monitor`** (`lauburu-monitor`): Master 6-tab system overview monitoring the 14-port matrix, 7-layer mesh, monorepo AST, and Tri-Vault.
19. **`rust_swarm_training_tui`** (`lauburu_health_tui`): Darwin Mach memory auditor with dynamic 16KB page size detection and mesh snapshot probing.
20. **`rust_network_analyzer`** (`lauburu-network`): Physical link throughput and latency meter benchmarking 40Gbps TB4 DMA and Wi-Fi 7.
21. **`notebooks`** (Port 8888): Interactive biometrics DSP plotting, PySpark data exploration, and reactive Python visual notebooks across the mesh.
22. **`canonical_tui_prototypes`**: Polyglot terminal user interface showroom demonstrating Elm-architecture, reactive CSS/TCSS, and immediate-mode renderers.
23. **`omniterminal_notebook_plugin`**: IPython / JupyterLab telemetry HUD injecting real-time Darwin RAM headroom, TB4 link status, and GPU load.

### 🛍️ Domain 5: Commerce, Subscriptions & Monetization
24. **`commerce_and_business`**: Athlete membership subscriptions ($9/$29/$99/mo), Movesense HR+ medical sensor bundles, and Storefront GraphQL sync.
25. **`shopify_ai`**: Autonomous inventory manager, margin optimizer, and crowdsourced compute token validator ($0 free lifetime tier).

### 📱 Domain 6: Edge Mobile, Vision & Reverse Engineering
26. **`screen_lens`** (Port 4003): Autonomous screen observing companion streaming 10–15 FPS MJPEG with speculative token reduction.
27. **`pixel_app_reverse_engineer`**: Sovereign reverse engineering sandbox extracting proprietary BLE sensor protocols and generating clean-room specs.
28. **`network_cable_analyzer`**: Low-level hardware link diagnostic verifying 40Gbps Thunderbolt 4 cabling, Lintes 240W cables, and Realtek 2.5GbE PHY.
29. **`self_healing_hub`** (Port 18802): Autonomous mesh self-healing daemon broadcasting RFC 792 WoL magic packets, ADB power pinning, and Termux wake-locks.
30. **`glinet_web_optimizer`**: Autonomous gateway daemon managing GL.iNet Beryl 7 fan PWM curves, kmwan multi-WAN load balancing, and ADB USB overrides.

---

## 🏛️ PART 7: The 13 Canonical Monorepo Subsystems

The monorepo code is partitioned into 13 numbered pillars ensuring strict domain encapsulation:

```
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/
├── 00_core_infrastructure/           # Master SeaweedFS, Docker Compose, Tailscale, self-healing hub
├── 01_apps/                          # All 30 applications across the 6 canonical domains
├── 02_ai_models_and_inference/       # Prima.cpp PRP ring, llama.cpp RPC, GGUF vault, Petals DHT
├── 03_biometrics_and_telemetry/      # Movesense 512Hz ECG, Pan-Tompkins QRS, PTT BP, DFA-alpha1
├── 04_data_and_memory/               # PySpark Data Lake, Delta Lake, 24/7 LoRA datasets, Qdrant
├── 05_agents_and_swarms/             # Tri-Orchestrator debate engine, Genetic MoE router, ELO ladder
├── 06_scripts_and_tooling/           # Autonomous network self-healing, global NAS mounting, ADB daemons
├── 07_docs_and_architecture/         # Architecture whitepapers, hardware topologies, spec sheets
├── 08_business_and_commerce/         # Shopify Storefront GraphQL, Subscriptions, CAC/LTV modeling
├── 09_app_store_and_release/         # Signed Android APKs, Play Store & Apple App Store release manifests
├── 10_spatial_grappling_kinematics/  # 3,044-Node Spatial OPML trees, 3D tatami world models, kinematics
├── 11_security_and_governance/       # Hardware isolation, SSH/RPC socket encryption, Cloudflare HMAC
├── 12_continuous_lora_evolution/     # 24/7 LoRA harvesting, DARE-TIES weight merging, MLX backprop
└── obsidian_vault/                   # Canonical Obsidian Knowledge Graph (Tri-Vault Layer 1)
```

---

## 👑 PART 8: Sovereign Local AI Hierarchy & Governance

All AI execution across the 7-layer mesh adheres strictly to the **Qwen 3.8 Max Sovereign Invariant**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SOVEREIGN LOCAL AI HIERARCHY MATRIX                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 👑 1. SOVEREIGN MASTER LOCAL ORCHESTRATOR & DEFAULT PROJECT MODEL:          │
│    • Model: Qwen 3.8 Max 27B Abliterated (qwen_38_max_abliterated)          │
│    • Endpoint: http://127.0.0.1:8082 | Transport: 10Gbps TB4 DMA Bridge     │
│    • Status: Rule 15 Dynamic ELO Incumbent (#1 Rank: 1734 ELO). Bound to    │
│      Screen Lens Sovereign (/screen-lens-sovereign) multimodal vision.      │
│    • Role: Sole, exclusive local orchestrator leading all debate consensus, │
│      architectural resolution, and master multi-agent coordination.         │
├─────────────────────────────────────────────────────────────────────────────┤
│ ⚔️ 2. CANONICAL DEVIL'S ADVOCATE & ADVERSARIAL RED TEAM:                    │
│    • Model: Qwen 3.8 Max (qwen_38_max)                                      │
│    • Endpoint: http://127.0.0.1:8083 | Weights: Qwen3.8-Max-Q4_K_M.gguf     │
│    • Role: Uncensored adversarial challenger red-teaming every proposed     │
│      refactor, architectural decision, and tool modification.               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🛠️ 3. SUBORDINATE SYNTAX WORKER ONLY:                                       │
│    • Model: Qwen 2.5 Coder 7B (qwen2.5-coder-7b-instruct-q4_k_m.gguf)       │
│    • Endpoint: http://127.0.0.1:8081 | Transport: Apple Metal GPU           │
│    • Invariant: Strictly a subordinate fast single-file syntax parser and    │
│      linter. PROHIBITED from acting as orchestrator or leading debates.     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ PART 9: CLI & TUI Operational Tooling Catalog

The monorepo provides a suite of compiled, zero-mock native tools in `/Users/aaron/.local/bin/`:

### 1. `lauburu-network` (Master Network Orchestrator)
- **Binary:** `/Users/aaron/.local/bin/lauburu-network`
- **Source:** `01_apps/rust_network_analyzer/`
- **Commands:**
  ```bash
  lauburu-network         # Interactive 120 FPS dual-pane network TUI
  lauburu-network --tree  # Prints full ANSI 6-tier transport & mesh tree
  lauburu-network --test  # Fast headless network prober self-test
  lauburu-network --json  # Dumps structured JSON network telemetry
  ```

### 2. `lauburu-apps` (Master Applications Orchestrator)
- **Binary:** `/Users/aaron/.local/bin/lauburu-apps`
- **Source:** `01_apps/rust_apps_orchestrator/`
- **Commands:**
  ```bash
  lauburu-apps            # Interactive 120 FPS application lifecycle manager
  lauburu-apps --tree     # Prints 6-domain 30-app organizational tree
  lauburu-apps --test     # Headless probe self-test across all 30 apps
  lauburu-apps --json     # Dumps structured JSON applications state
  ```

### 3. `lauburu-monitor` (Master Monorepo Observability Workbench)
- **Binary:** `/Users/aaron/.local/bin/lauburu-monitor`
- **Source:** `01_apps/rust_project_monitor/`
- **Commands:**
  ```bash
  lauburu-monitor         # Interactive 6-tab system monitor (AST, Ports, Mesh, Apps, Pillars, Vault)
  lauburu-monitor --test  # Headless full-monorepo AST and mesh verification test
  ```

### 4. `lauburu_health_tui` (Mach Kernel Memory & Swarm Health Lens)
- **Binary:** `/Users/aaron/.local/bin/lauburu_health_tui`
- **Source:** `01_apps/rust_swarm_training_tui/`
- **Commands:**
  ```bash
  lauburu_health_tui            # Interactive RAM and swarm health TUI
  lauburu_health_tui --snapshot # One-shot authentic Mach RAM & mesh probe
  ```
