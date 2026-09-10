---
title: "Federated Device Specialist Network & Data Specialization Matrix"
tags: [federated_mesh, hardware_roles, data_specialization, tb4, jupyterlab, seaweedfs, tri_vault]
---

# 💻 Federated Device Specialist Network & Data Specialization Matrix

> **Active Computing Mesh:** 4 / 5 Computers Online  
> **Shared Data Fabric:** `SeaweedFS DFS (:8888) + Tailscale WireGuard + Git Worktrees`

---

## 🏛️ 1. Computer & Laptop Specialization Matrix

| Node & Device | Hardware & OS | Shared Data Roles | Specialized Local Competencies |
|---|---|---|---|
| **L1_Mac_Mini_Host**<br>`Apple M4 Pro Mac Mini (24GB Unified RAM)`<br>IP: `127.0.0.1` | Tier-1 Master Host<br>*macOS Sequoia (Darwin ARM64)* | • Tri-Vault Obsidian Sync<br>• Master Leaderboard<br>• LoRA Compaction | • Master Prompt Ingestion & Memory Governor (Hard Cap: 20.0 GB)<br>• Hardware Watchdog Timer Starvation Prevention (Swap < 500 MB)<br>• Universal Web-TUI Portal & 120 FPS PTY WebSocket Streamer (:8088)<br>• Real-Time Mesh Live Console (:18805) |
| **L5_MacBook_Air_Worker**<br>`Apple M4 MacBook Air (16GB Unified RAM)`<br>IP: `100.93.158.96` | Tier-1 Headless Worker<br>*macOS Sequoia (Darwin ARM64)* | • 89.54 GB Model Vault Sync<br>• Obsidian Notebooks Mirror<br>• Subagent Workspaces | • 24/7 Headless Clamshell Worker (pmset sleep disabled)<br>• JupyterLab Server (:8889) & Reactive Marimo Engine<br>• Frontier 80B/72B Model Staging Vault (/Users/aaronmaher/models/)<br>• Headless Chrome DevTools MCP & Browser-Use Automation<br>• Apple Silicon Metal Performance Shaders (MPS) LoRA Trainer |
| **L2_MacBook_Pro_TB4**<br>`Apple M-Series MacBook Pro (16GB Unified RAM)`<br>IP: `100.103.212.21` | Tier-1 TB4 DMA Co-Processor<br>*macOS Sequoia (Darwin ARM64)* | • TB4 DMA Tensor Activations<br>• Metal Weight Cache<br>• Logits Streaming | • 10Gbps Thunderbolt 4 PCIe DMA Bridge (0.277ms Latency)<br>• Dedicated Metal GPU RPC Worker (:50052)<br>• Output Logits & Softmax Calculation Vault<br>• High-Throughput Model Sharding Ring Node |
| **L3_Linux_Head_Node**<br>`AMD Ryzen 7 5700U Linux Server (16GB RAM)`<br>IP: `100.101.39.98` | Tier-2 Big Data & Container Hub<br>*Debian GNU/Linux 12 (x86_64)* | • SeaweedFS Lakehouse<br>• PySpark Monorepo Index<br>• Qdrant Vector DB | • SeaweedFS Master (:9333) and Filer (:8888) DFS Service<br>• Native Docker Engine & LobeHub Docker MCP (:2375)<br>• Qdrant Vector DB (:6333) 3,100+ AST Chunk Index<br>• Apache Ray Cluster Worker & PySpark Lakehouse Pipelines<br>• 512Hz Movesense GATT DSP Signal Processing Hub |
| **L4_Debian_Linux_Tablet**<br>`Debian Linux Touch Tablet (8GB RAM)`<br>IP: `100.81.92.125` | Tier-3 Mobile Edge & TUI Client<br>*Debian GNU/Linux (aarch64)* | • Live Telemetry Mirror<br>• Bedside TUI Stream<br>• Micro-Benchmark Log | • Bedside Touch-Optimized TUI Terminal<br>• Low-Power BLE Movesense GATT Ingestion<br>• Qwen 2.5 0.5B Read-Only AST Syntax Linter<br>• Petals Secondary DHT Edge Worker |

---

## 🔄 2. Data Specialization vs. Shared Fabric Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FEDERATED MULTI-DEVICE DATA FABRIC                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. SHARED DATA FABRIC (All Nodes Sync)                                      │
│    • Monorepo ASTs, Git worktrees, Obsidian Knowledge Graph (5,339 notes)  │
│    • Champion Genetic Genomes (JSON Ledger) & 24/7 LoRA SFT/DPO Datasets    │
│    • SeaweedFS Global Object Store (http://100.101.39.98:8888)              │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. SPECIALIZED LOCAL DATA STREAMS (Device-Specific Isolation)               │
│    • Mac Mini (L1): Port 8088/18805 PTY sockets, watchdog swap metrics      │
│    • MacBook Air (L5): 89.54 GB GGUF Binaries, JupyterLab Kernels (:8889)   │
│    • MacBook Pro (L2): TB4 PCIe DMA Ring activations & Metal GPU logits     │
│    • Linux Head (L3): Qdrant vector index chunks & raw Docker containers    │
│    • Linux Tablet (L4): Touch TUI frame buffers & low-power GATT BLE logs   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---
- Links: [[Index]] | [[00_MASTER_INFRASTRUCTURE_TOPOLOGY]] | [[DEVICE_ROLES_AND_OPENWRT_GLINET_OPTIMIZATION]]
