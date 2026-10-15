---
title: "Federated Device Specialist Network & Data Specialization Matrix"
tags: [federated_mesh, hardware_roles, data_specialization, tb4, jupyterlab, seaweedfs, tri_vault]
---

# 💻 Federated Device Specialist Network & Data Specialization Matrix

> **Active Computing Mesh:** Multi-Node Heterogeneous Mesh (L1-L8 + Gateway)  
> **Shared Data Fabric:** `SeaweedFS DFS (:8888) + Tailscale WireGuard + Git Worktrees`

---

## 🏛️ 1. Computer & Laptop Specialization Matrix

| Node & Device | Hardware & OS | Shared Data Roles | Specialized Local Competencies |
|---|---|---|---|
| **L1_Mac_Mini_Host**<br>`Apple M4 Pro Mac Mini (24GB Unified RAM)`<br>LAN: `192.168.8.143` / `192.168.8.230`<br>Tailscale: `100.119.199.76` | Tier-1 Master Host<br>*macOS Sequoia (Darwin ARM64)* | • Tri-Vault Obsidian Sync<br>• Master Leaderboard<br>• LoRA Compaction | • Master Prompt Ingestion & Memory Governor (Hard Cap: 20.0 GB)<br>• Hardware Watchdog Timer Starvation Prevention (Swap < 500 MB)<br>• Universal Web-TUI Portal & 120 FPS PTY WebSocket Streamer (:8088)<br>• Real-Time Mesh Live Console (:18802) |
| **L1a_MacBook_Air_Worker (L5)**<br>`Apple M4 MacBook Air (16GB Unified RAM)`<br>LAN: `192.168.8.248`<br>Tailscale: `100.121.202.34` | Tier-1 Headless Worker<br>*macOS Sequoia (Darwin ARM64)* | • Model Vault Sync<br>• Obsidian Notebooks Mirror<br>• Subagent Workspaces | • 24/7 Headless Clamshell Worker (pmset sleep disabled)<br>• JupyterLab Server (:8889) & Reactive Marimo Engine<br>• Frontier Model Staging Vault (/Users/aaronmaher/models/)<br>• Headless Chrome DevTools MCP & Browser-Use Automation<br>• Apple Silicon Metal Performance Shaders (MPS) LoRA Trainer |
| **L8_Linux_Mini (lauburu)**<br>`Intel Core i7-8700B Linux Mini (32GB RAM)`<br>TB4: `10.0.0.8` (RTT 0.38ms)<br>LAN: `192.168.8.242`<br>Tailscale: `100.121.247.8` | Tier-1 TB4 DMA Co-Processor<br>*Ubuntu 24.04 LTS (x86_64)* | • TB4 DMA Tensor Activations<br>• Model Vault GGUF Hub<br>• High-Throughput Sharding | • **40Gbps Thunderbolt to L1** (`bridge0` IP `10.0.0.8`, 0.38ms RTT)<br>• Model Vault GGUF Storage (`/home/linuxmini/model_vault_gguf/`)<br>• Large-Scale Model Sharding & Glances v4 (:61208)<br>• High-Throughput Linux Compute & Build Node |
| **L1c_MacBook_Pro (L2)**<br>`Intel Core i7-9750H MacBook Pro (16GB RAM)`<br>LAN: `192.168.8.127`<br>Tailscale: `100.103.212.21` | Tier-2 Desktop Automation Worker<br>*macOS (x86_64)* | • Desktop Automation Target<br>• Screen Lens Teacher<br>• Logits Streaming | • Unlinked from Thunderbolt (communicates over LAN/Tailscale)<br>• Authorized Screen Lens Sovereign Teacher target (AppleScript / osascript)<br>• Headless Secondary Test Node & Glances v4 (:61208) |
| **L3_Linux_Head_Node**<br>`AMD Ryzen 7 5700U Mini PC (15GB RAM)`<br>LAN: `192.168.8.225`<br>Tailscale: `100.101.39.98` | Tier-2 Big Data & Container Hub<br>*Ubuntu / Debian (x86_64)* | • SeaweedFS Lakehouse<br>• PySpark Monorepo Index<br>• Qdrant Vector DB | • SeaweedFS Master (:9333) and Filer (:8888) DFS Service<br>• Native Docker Engine & LobeHub Docker MCP (:2375)<br>• Qdrant Vector DB (:6333) AST Chunk Index<br>• Apache Ray Cluster Worker & PySpark Lakehouse Pipelines<br>• Bluetooth RFCOMM connected to L1 (-28 dBm) |
| **L4_Debian_Linux_Tablet**<br>`Debian Linux Touch Tablet (8GB RAM)`<br>LAN: `192.168.8.176` (Port 2)<br>Tailscale: `100.99.210.89` | Tier-3 Mobile Edge & TUI Client<br>*Debian GNU/Linux (x86_64/aarch64)* | • Live Telemetry Mirror<br>• Bedside TUI Stream<br>• Micro-Benchmark Log | • Bedside Touch-Optimized TUI Terminal<br>• Low-Power BLE Movesense GATT Ingestion<br>• Qwen 2.5 0.5B Read-Only AST Syntax Linter<br>• Wired Ethernet via Router Port 2 (0.95ms RTT) |

---

## 🔄 2. Data Specialization vs. Shared Fabric Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FEDERATED MULTI-DEVICE DATA FABRIC                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. SHARED DATA FABRIC (All Nodes Sync)                                      │
│    • Monorepo ASTs, Git worktrees, Obsidian Knowledge Graph                 │
│    • Champion Genetic Genomes (JSON Ledger) & 24/7 LoRA SFT/DPO Datasets    │
│    • SeaweedFS Global Object Store (http://100.101.39.98:8888)              │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. SPECIALIZED LOCAL DATA STREAMS (Device-Specific Isolation)               │
│    • Mac Mini (L1): Port 8088/18802 PTY sockets, watchdog swap metrics      │
│    • Linux Mini (L8): 40Gbps TB4 DMA Tensor bridge (10.0.0.8, 0.38ms RTT)   │
│    • MacBook Air (L5): Model Staging Vault, JupyterLab Kernels (:8889)      │
│    • MacBook Pro (L2): Desktop automation target & Screen Lens Teacher (LAN)│
│    • Linux Head (L3): Qdrant vector index chunks & raw Docker containers    │
│    • Linux Tablet (L4): Touch TUI frame buffers & low-power GATT BLE logs   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---
- Links: [[Index]] | [[00_MASTER_INFRASTRUCTURE_TOPOLOGY]] | [[DEVICE_ROLES_AND_OPENWRT_GLINET_OPTIMIZATION]]
