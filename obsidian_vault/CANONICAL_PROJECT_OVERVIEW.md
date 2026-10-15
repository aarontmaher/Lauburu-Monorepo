---
title: "Lauburu Mesh Ecosystem: Canonical Master Project & Architecture Overview"
tags: [lauburu, canonical, architecture, 7_layer_mesh, tri_vault, zero_mock, ram_governor]
version: "2.0.0-SOVEREIGN-MESH-2026"
updated: "2026-09-04"
author: "worker_gen24_1"
---

# 🧠 Lauburu Mesh Ecosystem: Canonical Master Project & Architecture Overview

**Document Classification:** Canonical Monorepo Architecture Specification (Requirement 1)  
**Governing Laws:** Rule 0 & Rule 0.1 Zero-Mock Empirical Truth Verification | Dynamic RAM Sanctuary  
**Related Canonical Notes:** [[Index]], [[CANONICAL_PROJECT_AND_STORAGE_RULE]], [[00_MASTER_INFRASTRUCTURE_TOPOLOGY]], [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]], [[STORAGE_ARCHITECTURE_CONTEXT_MAP]], [[CANONICAL_AI_DEVELOPMENT_AND_RUNTIME_ARCHITECTURE]], [[LENS_AI_CANONICAL_OVERVIEW]]

---

## 🏛️ 1. Master Architectural Overview of the Lauburu Mesh Ecosystem

The **Lauburu Mesh Ecosystem** is a distributed, sovereign, local-first artificial intelligence, medical-grade biometrics, and autonomous multi-agent swarm platform. Designed for complete privacy, high-throughput model inference, and continuous self-improvement at **$0 recurring cloud spend**, the ecosystem pools compute, memory, and storage across seven heterogeneous physical hardware layers and an embedded infrastructure gateway router.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                LAUBURU MESH ECOSYSTEM: MASTER ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                 TIER 0: TRI-ORCHESTRATOR SWARM GOVERNOR                                 │
│          Proxy Port 8082 (:8089/:8085) ◄───► Abliterated Devil's Advocate (Port 8083)           │
│                     ▲                                           ▲                                       │
│                     │       40Gbps Thunderbolt 4 Link (0.38ms)  │                                       │
│                     ▼                                           ▼                                       │
│    ┌──────────────────────────────────┐        ┌──────────────────────────────────┐                     │
│    │     LAYER 1: MAC MINI M4 PRO     │        │     LAYER 8: LAUBURU LINUX HUB   │                     │
│    │  Host Memory Governor & Prompts  │◄──────►│   Intel i7-8700B Ubuntu 32GB RAM │                     │
│    │   24.0 GB RAM (>=4.8 GB Free)    │        │   40Gbps TB (10.0.0.8, 0.38ms)   │                     │
│    └──────────────────────────────────┘        └──────────────────────────────────┘                     │
│                     ▲                                           ▲                                       │
│                     │ WireGuard Mesh (Tailscale) / 1GbE LAN     │                                       │
│                     ▼                                           ▼                                       │
│    ┌──────────────────────────────────┐        ┌──────────────────────────────────┐                     │
│    │   LAYER 3: LINUX HEAD NODE       │        │     LAYER 1a / 5: MACBOOK AIR M4 │                     │
│    │   AMD Ryzen 7 5700U Compute Hub  │        │   Secondary Metal & Distillation │                     │
│    │   15.0 GB RAM (12.0 GB AI)       │        │   16.0 GB RAM (14.0 GB AI)       │                     │
│    └──────────────────────────────────┘        └──────────────────────────────────┘                     │
│                     ▲                                           ▲                                       │
│                     ▼                                           ▼                                       │
│    ┌──────────────────────────────────┐        ┌──────────────────────────────────┐                     │
│    │    LAYER 4: LINUX TABLET         │        │    LAYER 6: PIXEL 10 PRO XL      │                     │
│    │  Debian Bedside TUI & Touch DSP  │        │  Tensor G5 TPU, 8K Video & UWB   │                     │
│    │    8.0 GB RAM (6.0 GB AI)        │        │    16.0 GB RAM (12.5 GB AI)      │                     │
│    └──────────────────────────────────┘        └──────────────────────────────────┘                     │
│                     ▲                                           ▲                                       │
│                     ▼                                           ▼                                       │
│    ┌──────────────────────────────────┐        ┌──────────────────────────────────┐                     │
│    │    LAYER 7: SAMSUNG S20          │        │    GATEWAY: GL.iNET GL-BE14000   │                     │
│    │  Exynos 990 Dedicated UI Tester  │◄──────►│  Wi-Fi 7 / 2.5G NBN eth2 WAN     │                     │
│    │    12.0 GB RAM (9.0 GB AI)       │        │  2 GB RAM (1.38 GB Free)         │                     │
│    └──────────────────────────────────┘        └──────────────────────────────────┘                     │
│                     ▲                                                                                   │
│                     ▼                                                                                   │
│    ┌──────────────────────────────────┐                                                                 │
│    │    LAYER 2: MACBOOK PRO INTEL i7 │ (TB4 40 Gb/s; Wi-Fi 192.168.8.127 / TS 100.103.212.21)          │
│    │    16.0 GB RAM (Model Vault)     │                                                                 │
│    └──────────────────────────────────┘                                                                 │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                  TRI-VAULT STORAGE PERSISTENCE LAYER                                    │
│   1. Obsidian Vault (5,425+ Notes)  │  2. PySpark / Data Lake (154MB DPO)  │  3. GitHub Canonical Repo  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 Core Architectural Principles
1. **Local AI First**: All primary inference, agent coordination, and biometrics digital signal processing (DSP) execute on local silicon across Apple Silicon Metal Performance Shaders, AMD x86_64, and Android Google Tensor TPUs. Cloud LLMs serve strictly as shadow teachers, reasoning benchmarks, or rate-limited verification judges.
2. **Zero-Simulation Mandate (Rule 0 / Rule 0.1)**: Simulated arrays, synthetic timestamps, fake benchmark runs, and dummy placeholders are strictly prohibited across all code, tests, and documentation. Every metric originates from verified kernel syscalls, physical sensors, or live network sockets.
3. **Tri-Vault Knowledge Persistence**: Every decision, architectural diff, debate verdict, and sensor stream is continuously written to the Obsidian Semantic Vault, the PySpark Data Lake, and canonical Git worktrees.
4. **Sub-Millisecond Inter-Device DMA**: Nodes communicate over a tiered network fabric combining a 40Gbps Thunderbolt direct memory access (DMA) bridge to L8 `lauburu` (~0.38ms round-trip latency), a 1GbE Ethernet backplane, and a zero-trust Layer 3 WireGuard mesh (Tailscale).

---

## 🌐 2. 7-Layer Physical Mesh Topology & Hardware Matrix

The Lauburu Mesh pools **139.0 GB Physical RAM (108.4 GB Usable AI VRAM)** across eight distinct physical compute nodes and one dedicated gateway router:

| Layer | Node Identifier | Hardware Specifications | Network Interfaces (Local / Tailscale) | Total Physical RAM | Usable AI Capacity | Dynamic RAM Cap | Primary Roles & Kernel Capabilities |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `Mac_Node` | Apple M4 Pro Mac Mini<br>(12-Core CPU, 16-Core GPU, 16-Core ANE) | `192.168.8.143` (Wi-Fi)<br>`192.168.8.230` (LAN)<br>`100.119.199.76` | **24.0 GB** | **19.2 GB AI** | **80% Hard Cap**<br>(Min Free: $\ge 4.8\text{ GB}$) | **Host Memory Governor & Master Controller**:<br>Prompt ingestion, subagent orchestrator, Darwin Mach kernel memory guardian, Screen Lens live streamer. |
| **L2** | `MacBook_Pro` | Intel Core i7 MacBook Pro<br>(6-Core i7-9750H, 16 GB RAM) | TB `10.0.0.4` (40 Gb/s)<br>`192.168.8.127`<br>`100.103.212.21` | **16.0 GB** | **14.0 GB AI** | **90% Hard Cap** | **Metal GPU RPC & Model Vault**:<br>285 GB SSD GGUF model vault, TB4 40 Gb/s link (MTU 9000), secondary Metal worker via LAN / Tailscale. |
| **L1b** | `MacMini_M2` | Apple M2 Pro Mac Mini<br>(10-Core CPU, 16-Core GPU) | TB `10.0.0.3` (40 Gb/s)<br>`192.168.8.114`<br>`100.104.128.34` | **16.0 GB** | **13.6 GB AI** | **85% Hard Cap** | **Secondary Compute Worker**:<br>TB4 40 Gb/s bridge to L1 (0.43ms RTT), local inference & AST validation. |
| **L3** | `Linux_Head_Node` | AMD Ryzen 7 5700U<br>(8-Core / 16-Threads, 15 GB RAM) | `192.168.8.225`<br>`100.101.39.98` | **15.0 GB** | **12.0 GB AI** | **80% Hard Cap** | **Gateway Ingress & Compute Hub**:<br>Docker Engine daemon, Ray Head cluster, Petals DHT bootstrap, SeaweedFS DFS, Local AI offload. |
| **L4** | `Linux_Tablet` | Debian Linux Tablet (`debian-1`)<br>(x86_64 / ARM64 Hybrid) | `192.168.8.116`<br>`100.80.64.5` | **8.0 GB** | **6.0 GB AI** | **75% Hard Cap** | **Mobile Linux Compute & Touch DSP**:<br>Bedside interactive TUI terminal, secondary worker, lightweight biometrics telemetry collector. |
| **L5 / L1a** | `MacBook_Air` | Apple M4 MacBook Air<br>(10-Core CPU, 10-Core GPU, 16-Core ANE) | `192.168.8.248`<br>`100.121.202.34` | **16.0 GB** | **14.0 GB AI** | **90% Hard Cap** | **Secondary Metal Worker & Distillation**:<br>Metal Performance Shaders worker, 24/7 LoRA adapter fine-tuning, offloaded headless Chromium/Playwright QA tester. |
| **L6** | `Pixel_10_Pro_XL` | Google Tensor G5<br>(Edge TPU, Android 15, Termux) | `192.168.8.213`<br>`100.114.215.68` | **16.0 GB** | **12.5 GB AI** | **85% Hard Cap** | **8K Vision Stream & Edge TPU**:<br>8K Digital PTZ video ingestion, Ultra-Wideband (UWB) spatial tracking, Shizuku rish privileged shell. |
| **L7** | `Samsung_S20` | Samsung Exynos 990<br>(Mali-G77 MP11, Android 13, Termux) | `192.168.8.157`<br>`100.84.40.95` | **12.0 GB** | **9.0 GB AI** | **75% Hard Cap** | **Dedicated UI Automation Tester**:<br>Dedicated OpenClaw automated mobile UI tester, ADB target on port 5039. |
| **L8** | `Linux_Mini` | `lauburu` Intel Core i7-8700B<br>(Ubuntu 24.04 Linux, 32 GB RAM) | TB `10.0.0.8`<br>`192.168.8.242`<br>`100.121.247.8` | **32.0 GB** | **25.6 GB AI** | **80% Hard Cap** | **Thunderbolt Central Hub & Compute**:<br>**40Gbps Thunderbolt bridge (0.38ms RTT)**, Docker Hub, Ray cluster, High-RAM microservices. |
| **GW** | `GL.iNet Router` | GL.iNet GL-BE14000<br>Wi-Fi 7 BE14000 MLO, OpenWrt | `192.168.8.1`<br>`100.70.123.123`<br>WAN: `eth2` (2.5G NBN) | **2.0 GB** | **Embedded**<br>(1.38 GB Free) | **OpenWrt** | **Core Gateway & Hardware USB Bridge**:<br>2.5G wired NBN WAN, Hardware USB ADB bus daemon, Port 18802 C Sentinel daemon, WoL relay. |
| **NET** | **8 Nodes + 1 GW** | **Aggregated Mesh Totals** | **Multi-Subnet Fabric** | **139.0 GB** | **108.4 GB AI** | **Dynamic** | **Pooled Heterogeneous Mesh Compute** |

---

## ⚡ 3. Dynamic RAM Governor & Host Memory Sanctuary

The Lauburu Mesh implements a mathematical, hardware-enforced memory governance invariant designed to prevent host kernel memory exhaustion, out-of-memory (OOM) process panics, and disk-thrashing swap states.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 DYNAMIC RAM GOVERNOR ALLOCATION SCHEDULER                               │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. REAL PHYSICAL RAM INVARIANT:                                                                         │
│    Calculations compute strictly against 100% REAL PHYSICAL RAM (139.0 GB Mesh, 40.0 GB Active M4 Silicon).│
│    Zero simulated headroom masks or artificial scaling multipliers are permitted in memory telemetry.   │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. PERIPHERAL NODES FILL FIRST:                                                                         │
│    Layer 2 (MBP: 16 GB) ──► Layer 5 (MBA: 16 GB) ──► Layer 3 (Linux: 16 GB) ──► Layer 6 (Pixel: 16 GB)│
│    All peripheral devices fill to their dynamic caps before the Mac Mini host accepts model weights.     │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. HOST MAC MINI SANCTUARY & EARLY-FULL CEILING:                                                        │
│    • Total Host RAM: 24.0 GB                                                                            │
│    • Early-Full Ceiling: 80% allocation (19.2 GB maximum active AI footprint)                           │
│    • Guaranteed Sanctuary Buffer: >= 4.8 GB of UNTOUCHED physical RAM reserved at all times.            │
│    • Purpose: Prompt ingestion, Apple Neural Engine (ANE) caching, TUI rendering, subagent spawning.   │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. RULE 7.1 ACTIVE HOST MEMORY EVACUATION:                                                              │
│    • Trigger Threshold: Free RAM < 4.8 GB OR Total Host Utilization > 80%.                              │
│    • Automated Evacuation Actions:                                                                      │
│      1. Darwin vm_stat inactive page trimming.                                                          │
│      2. Transmit RFC 792 Wake-on-LAN resurrection magic packets to sleeping peripheral nodes.           │
│      3. Shift active KV cache layers across 40Gbps TB4 DMA bridge to Linux Mini Hub (lauburu, L8).      │
│      4. Append Rule #8 structured failure-to-training LoRA pair to continuous_lora_dataset.jsonl.       │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. ZERO-SWAP INVARIANT:                                                                                 │
│    Active Darwin swap usage on the Mac Mini host must never exceed 500 MB. Swap accumulation > 500 MB   │
│    immediately triggers hard model layer eviction to peripheral nodes.                                  │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 6. SUB-MICROSECOND DIRECT MACH KERNEL AUDITING:                                                         │
│    Audited via native C11 binary (01_apps/screen_lens/c_core/darwin_ram_auditor.c).                     │
│    Direct host_statistics64() Mach syscall execution latency: 6.00 microseconds (0.006 ms).             │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Mathematical Allocation Formulas
For any global model context and parameter weight tensor $W$ requiring total memory $M_{\text{req}}$, allocation follows the constrained linear program:

$$M_{\text{host}} \le \min\left(0.60 \times M_{\text{host\_total}}, M_{\text{host\_total}} - 9.6\text{ GB}\right) = 14.4\text{ GB}$$

$$M_{\text{peripherals}} = \sum_{i \in \{L2, L3, L4, L5, L6, L7\}} \min\left(\text{Cap}_i \times M_i, M_{\text{free}, i}\right)$$

$$M_{\text{total\_allocatable}} = M_{\text{host}} + M_{\text{peripherals}} \le 82.8\text{ GB}$$

If $M_{\text{req}} > M_{\text{peripherals}}$, host memory is consumed up to $14.4\text{ GB}$. Any excess tensor weights stream across the 40Gbps Thunderbolt 4 DMA bridge using `prima.cpp` Pipelined-Ring Parallelism (PRP).

---

## 🏛️ 4. Tri-Vault Storage Hierarchy & Synchronization

The Tri-Vault storage architecture guarantees bit-for-bit durability, high-throughput training dataset harvesting, and immediate semantic graph retrieval:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   TRI-VAULT STORAGE SYNCHRONIZATION                                     │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. OBSIDIAN KNOWLEDGE VAULT (Human & Semantic Knowledge Core)                                           │
│    • Path: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/                                     │
│    • Scope: 5,425+ Markdown notes, YAML frontmatter, KaTeX equations, bidirectional Wikilinks.          │
│    • Tooling: Managed via obsidian-mcp-pro (41 native tools for graph traversal and note manipulation).  │
│    • Master Entry: Index.md linking [[CANONICAL_PROJECT_AND_STORAGE_RULE]], [[00_MASTER_INFRASTRUCTURE_│
│      TOPOLOGY]], [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]], and [[LENS_AI_CANONICAL_OVERVIEW]].      │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. PYSPARK & BIG DATA LAKE (High-Throughput Computation & Datasets)                                     │
│    • Paths: /Users/aaron/DFS_UNIFIED/lora_datasets/ and 04_data_and_memory/                             │
│    • Engine: Apache PySpark (pyspark), Delta Lake, Parquet columnar tables, Qdrant Vector DB (Port 6333)│
│    • Continuous Dataset: continuous_lora_dataset.jsonl (154 MB active live stream, 76,000+ records).    │
│    • Telemetry Stream: 512Hz Pan-Tompkins ECG streams, Movesense BLE telemetry, Darwin memory traces.   │
│    • Sinks: tri_vault_sink.py enforcing POSIX atomic file persistence (os.replace + os.fsync).          │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. GITHUB MONOREPO & WORKTREES (Canonical Source Code & Version Control)                                │
│    • Repository: aarontmaher/Lauburu-Monorepo (Local Root: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo)   │
│    • Tooling: Git 2.44+, Git Worktrees, gh CLI, pre-commit AST verification gates.                      │
│    • Scope: Production applications (01_apps/), core infrastructure (00_core_infrastructure/),           │
│      native C11 engines, Docker compose clusters, and multi-tier CI test suites.                        │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ DFS COLD TIER: Google Drive Cloud Sync                                                                  │
│    • Path: /Volumes/Google Drive/My Drive/Lauburu_AI_Memory/ (Automated periodic mirror).                │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Mandatory Pre-Flight Storage Health Invariant (Rule 5.1 & 5.2)
Before any agent executes code edits, runs refactors, or commits architectural decisions, it must verify the storage health invariant ($< 3\text{ ms}$ fast-path check):
1. `obsidian_vault/` exists, and `Index.md` is non-empty with valid master Wikilinks.
2. `lora_datasets/` and `04_data_and_memory/` exist and are writable; host preserves $\ge 10.0\text{ GB}$ free disk space ($\ge 5.0\text{ GB}$ hard operational limit).
3. `.git/index.lock` is absent and git worktrees are free of unmerged conflicts.
4. If unhealthy, the agent automatically executes self-healing protocols (`mkdir -p`, `rm -f .git/index.lock`, `find ... -name "__pycache__" -delete`).

---

## 🛡️ 5. Rule 0.1 Zero-Mock Empirical Truth Enforcement

The cornerstone of the Lauburu engineering methodology is **Cardinal Law #1**: absolute zero tolerance for simulated data, synthetic benchmarks, mocked arrays, or hallucinated victories.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 MANDATORY TRI-PROOF VERIFICATION GATE                                   │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Any claim of task completion, bug resolution, or optimization MUST provide empirical Tri-Proof:        │
│                                                                                                         │
│ 1. PROOF 1: PHYSICAL ACTUATION                                                                          │
│    • Operating system process exit code: Exit Code 0.                                                   │
│    • Verified device touch event (ADB tap/swipe on Layer 6/7 or macOS accessibility click).            │
│    • Live socket state verification (curl HTTP 200, TCP handshake).                                     │
│                                                                                                         │
│ 2. PROOF 2: LINE-BY-LINE AUDIT & CHECKSUM                                                               │
│    • Line-by-line inspection with exact byte counts and line numbers.                                   │
│    • Cryptographic SHA256 checksum of modified or generated files.                                     │
│    • Direct AST syntax verification without runtime stubbing.                                           │
│                                                                                                         │
│ 3. PROOF 3: VISUAL SCREEN CAPTURE                                                                       │
│    • Authentic pixel-level screen capture (.png / .jpg) saved to disk and visually inspected.           │
│    • Continuous 10–15 FPS multipart MJPEG stream broadcast on Port 4003 (zero static PNG placeholders). │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 5.1 Empirical Kernel & DSP Latency Benchmarks
Zero-mock compliance is demonstrated by actual verified latencies audited directly on host and edge hardware:

| Subsystem Component | Implementation File | Verification Method | Empirical Verified Latency | Speedup vs Baseline |
| :--- | :--- | :--- | :--- | :--- |
| **XNU Mach Kernel Memory Audit** | `01_apps/screen_lens/c_core/darwin_ram_auditor.c` | Native C11 binary calling `host_statistics64` | **6.00 µs** (0.0060 ms) | **1200x faster** than Python `subprocess` |
| **Pan-Tompkins QRS ECG DSP** | `01_apps/screen_lens/c_core/movesense_dsp.c` | Native C11 binary filtering 5,000 ECG samples | **66.0 µs** (0.0660 ms) | **300x faster** than SciPy / NumPy |
| **AST Token Compression Engine** | `01_apps/screen_lens/c_core/ast_compressor.c` | Native C11 binary stripping whitespace/comments | **8.50 µs** (0.0085 ms) | **250x faster** than Python AST parser |
| **Consistent Hash Storage Ring** | `01_apps/screen_lens/c_core/lauburu_pooled_storage.c` | Native C11 1.0MB block dispersal & reassembly | **1.30 ms** dispersal<br>**0.22 ms** reassembly | **Bit-for-bit SHA256 match** (Fletcher32) |
| **Thunderbolt 4 DMA RPC Ping** | TB4 Bridge to L8 lauburu (`10.0.0.8` / `bridge0`) | ICMP and raw TCP socket ping to L8 hub | **0.38 ms** RTT (40 Gb/s) | **36x lower latency** than Wi-Fi 7 |

### 5.2 Rule 5 Victory-Word Interceptor & RAM Slashing
Under `lens_tri_proof_interceptor.py`, any utterance of victory keywords (`success`, `confirmed`, `complete`, `completed`, `resolved`, `passed`, `verified`, `fixed`, `done`, `working`) by any subagent or AI model triggers an automatic verification trap.
- If the assertion lacks accompanied physical proof (actuation, line audit, visual frame), the assertion is rejected and marked `UNVERIFIED`.
- The `lens_accuracy_weighted_ram_governor.py` automatically slashes the offending model's allocated context window and VRAM allocation by 25–50%, reallocating that memory headroom to the Sovereign Auditor.

---

## 📁 6. Canonical Monorepo Directory Hierarchy & Subsystem Map

The monorepo organizes code into ten modular, strictly governed pillars:

```text
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/
├── 00_core_infrastructure/           # Self-Healing Sentinel (Port 18802), SeaweedFS DFS, Docker Compose, Tailscale
├── 01_apps/                          # Production Applications:
│   ├── screen_lens/                  # Sovereign Multimodal VLA, MJPEG Stream (:4003), Omnichannel Hub (:4004)
│   ├── movesense_hub/                # Medical-grade 512Hz ECG, Pan-Tompkins QRS DSP, PTT Blood Pressure
│   ├── zone2_trainer/                # DFA-alpha1 cardiovascular endurance engine & HR recovery
│   ├── spatial_grappling_3d/         # 955-node OPML kinematics tree, 3D tatami world model, joint torque
│   └── portal_hub/                   # Port 4000 unified multi-view web dashboard & service registry
├── 02_ai_models_and_inference/       # Distributed Inference Engines:
│   ├── prima_cpp/                    # Primary Pipelined-Ring Parallelism over 40Gbps TB4 DMA Bridge
│   ├── llama_cpp_rpc/                # Resilient RPC fallback sharding (:8081 - :8084)
│   ├── petals_dht/                   # Heterogeneous distributed DHT layer swarming
│   ├── exo_p2p/                      # Dynamic peer-to-peer model discovery and pipeline rings
│   └── model_vault_gguf/             # Quantized GGUF model vault (Q4_K_M, IQ2_XXS, Huihui Abliterated)
├── 03_biometrics_and_telemetry/      # Movesense BLE sensor daemons, raw ADC byte unpackers, ECG streams
├── 04_data_and_memory/               # PySpark crawlers, Delta Lake, Qdrant Vector DB, continuous_lora_dataset.jsonl
├── 05_agents_and_swarms/             # Tri-Orchestrator AI Debate Council, Genetic MoE Engine, Truth Audit
├── 06_scripts_and_tooling/           # Universal SSH daemons, ADB keepalive, WoL resurrection, Figma MCP bridge
├── 07_docs_and_architecture/         # Master architecture specifications, whitepapers, canonical overviews
├── obsidian_vault/                   # Canonical Obsidian Knowledge Graph (5,425+ notes, MCP Pro, Wikilinks)
└── teamwork_projects/                # Federated project workspaces (software_dev, internet_training, etc.)
```

---

## 📋 7. Summary of Canonical Operating Rules (Rules 0–13)

| Rule # | Title | Core Invariant & Enforcement Mechanism |
| :--- | :--- | :--- |
| **Rule 0** | Zero-Mock Mandate | Zero fake arrays, simulated telemetry, or synthetic timestamps. All metrics must originate from authentic hardware sensors or kernel syscalls. |
| **Rule 0.1** | Definitive Tri-Proof | Every completed task requires actuation proof (Exit Code 0), line-by-line audit with SHA256 checksums, and visual screen proof. |
| **Rule 1** | Local AI First | Prioritize local quantized models over 40Gbps TB4 DMA before falling back to cloud APIs. |
| **Rule 2** | Tri-Vault Sync | Synchronize all architectural decisions and training pairs across Obsidian, PySpark, and GitHub. |
| **Rule 3** | Host Sanctuary | Mac Mini M4 Pro host strictly preserves $\ge 4.8\text{ GB}$ free physical RAM ($\le 80\%$ utilization); peripheral nodes fill first. |
| **Rule 4** | Untouched Baseline | Production code (`01_apps/`, `00_core_infrastructure/`) remains 100% untouched during autonomous model experiments; experiments run in `sandbox_evolution/`. |
| **Rule 5** | Victory Interceptor | Automatic interception of victory words; unverified victory claims trigger immediate RAM slashing. |
| **Rule 6** | Cloud Quota Pacing | Dynamic pacing of free cloud quotas (Google AI Studio 1,500 RPD, NVIDIA NIM 2,000 RPD, xAI 1,000 RPD, Cloudflare 800 RPD); 4-tier graduated autonomy. |
| **Rule 7** | Live Screen Broadcast | Continuous 10–15 FPS HTTP multipart MJPEG streaming on Port 4003 (`/stream.mjpg`); no static PNG masquerading as live stream. |
| **Rule 7.1**| Host RAM Evacuation | If Host Mac Mini free RAM drops below 5.0 GB or utilization exceeds 85%, instantly execute memory trimming and TB4 DMA offload to MBP/MBA. |
| **Rule 8** | Failure-to-Training | Every solved bug or system fault must be serialized as an instruction-thought-action pair in `continuous_lora_dataset.jsonl` for continuous local AI fine-tuning. |
| **Rule 9** | Container Acceleration | macOS Docker runtimes must use `vmType: vz` and `mountType: virtiofs` (1,420 MB/s read throughput); Colima VM strictly capped at $\le 8.0\text{ GB}$ RAM. |
| **Rule 10**| Dual-Ring Sandbox | Sub-1B models execute in isolated Ring 0 containers (512 MB cap, 5s watchdog); Ring 1 Qwen MoE gatekeeper audits outputs before host commit. |
| **Rule 11**| Pre-Training Consensus| LoRA adapter fine-tuning requires Tri-Orchestrator consensus ($\Phi \ge 0.95$) and Aaron's explicit sovereign approval before touching weights. |
| **Rule 12**| Context Compression | Large contexts (>32K tokens) require AST pre-compression (60-75% token reduction) and Q4_0 KV cache quantization. |
| **Rule 13**| Visual Aesthetics | Web/Electron dashboards follow Linear Bento Minimalism ($\ge 2450$ ELO); TUIs follow 120 FPS Cyberpunk Phosphor styling ($\ge 2380$ ELO). |

---

## 🔗 8. Bidirectional Navigation & Master Index
- Return to Master Knowledge Vault: [[Index]]
- Review Canonical Storage & Tooling Matrix: [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- Review Master Network Topology & IP Allocations: [[00_MASTER_INFRASTRUCTURE_TOPOLOGY]]
- Review Monorepo 5M LOC AST Crawl Index: [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- Review Screen Lens Sovereign AI Subsystem: [[LENS_AI_CANONICAL_OVERVIEW]]
