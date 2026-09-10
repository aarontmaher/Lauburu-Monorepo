---
title: "Lauburu Monorepo - Hierarchical Project Taxonomy Map"
tags: [lauburu, taxonomy, architecture, subsystems, dev_historian]
updated: "2026-09-01 15:31:05 UTC"
canonical_source: true
---

# 🗺️ Lauburu Monorepo — Canonical Project Taxonomy Map
> Continuously updated by `lauburu-dev-historian` on 2026-09-01 15:31:05 UTC.

- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]

---

## 🏛️ Subsystem Hierarchy & Core Modules

### 📦 `00_core_infrastructure/`
- **Description**: Core Infrastructure (SeaweedFS, Docker, Tailscale, Self-Healing Hub)
- **Total Indexed Files**: 44505

### 📦 `01_apps/`
- **Description**: User Applications & Client Ecosystems (Automotive Android Auto, Screen Lens, Zone 2)
- **Total Indexed Files**: 104565

### 📦 `02_ai_models_and_inference/`
- **Description**: Distributed AI Inference Mesh (llama.cpp RPC, Petals DHT, Exo P2P, prima.cpp)
- **Total Indexed Files**: 41992

### 📦 `03_biometrics_and_telemetry/`
- **Description**: Biometrics & Sensor DSP (Movesense 512Hz ECG, Pan-Tompkins, PTT BP)
- **Total Indexed Files**: 28

### 📦 `04_data_and_memory/`
- **Description**: Data Lake & Knowledge Memory (PySpark Crawlers, 24/7 LoRA Datasets, Qdrant)
- **Total Indexed Files**: 1737

### 📦 `05_agents_and_swarms/`
- **Description**: Agent Swarms & Tri-Orchestrator Governance (AI Debate Council, Genetic MoE)
- **Total Indexed Files**: 25698

### 📦 `06_scripts_and_tooling/`
- **Description**: Tooling & Hardware Automation (Universal SSH, ADB Keepalive, WoL Daemon)
- **Total Indexed Files**: 447

### 📦 `07_docs_and_architecture/`
- **Description**: Canonical Architecture & RFC Whitepapers
- **Total Indexed Files**: 154

### 📦 `obsidian_vault/`
- **Description**: Obsidian Knowledge Vault (Tri-Vault Human & Semantic Core)
- **Total Indexed Files**: 5415

---
## 🌐 Active Compute Nodes & Sharding Roles
- **L1 Mac Mini M4 Pro**: Host Controller, Memory Governor, Screen Lens Host (:3035)
- **L2 MacBook Pro M1 Max**: Metal GPU RPC Shard (:8081), 285 GB Model Vault
- **L3 Linux Head Node**: Gateway Ingress, Docker Engine, Ray Cluster (:8082)
- **L5 MacBook Air M2**: Manual AI Task Worker, Active Screen Lens (:3035)
- **L6 Pixel 10 Pro XL**: Android Auto In-Car Voice Coding Host, 24/7 Mobile Screen Lens (:3035)
- **L7 Samsung Galaxy S20+**: Automated UI Testing & ADB Target (:5555)

