---
title: "Monorepo Docker Implementation & Container Inventory"
date: 2026-09-02
tags: [docker, inventory, microservices, containerization, loop]
---

# 🐳 Complete Monorepo Docker Implementation & Container Inventory

## 🏛️ 1. Executive Summary & Audit Metrics
- **Total Dockerfiles Found:** 44
- **Total Compose Manifests:** 22
- **Container Tooling & Bridges:** 5
- **Primary Deployment Host:** Layer 3 Linux Head Node (`192.168.8.224` / `100.101.39.98`) & Colima on Layer 1 Mac Mini (`192.168.8.230`).

---

## 📁 2. Subsystem-by-Subsystem Docker Mapping

### 🔹 Layer 00: Core Infrastructure & Mesh Networking
| File / Path | Containerized Services & Role | Status |
| :--- | :--- | :--- |
| `00_core_infrastructure/docker-compose.master.yml` | **Master Production Stack:** Unified Portal (:4000), Qdrant Vector DB (:6333), SeaweedFS Filer (:8888/:9333), Portainer CE (:9000/:9443). | **ACTIVE (Canonical)** |
| `00_core_infrastructure/netbird_mesh/docker-compose.yml` | **NetBird Mesh Overlay:** Management (:33073), Dashboard (:8087), Signal (:10000), Coturn STUN/TURN (:3478). | **ACTIVE (Dual-Stack)** |
| `00_core_infrastructure/docker/docker-compose.dfs*.yml` | **SeaweedFS Distributed Storage:** Node-specific volumes (`m4-mini`, `linux-head`, `macbook-pro`) for unified DFS. | **MODULAR / HA** |
| `00_core_infrastructure/docker/docker-compose.nas-tb4.yml` | **Thunderbolt 4 NAS & Samba:** High-speed 10Gbps storage bridge container. | **MODULAR** |
| `00_core_infrastructure/docker/docker-compose.syncthing.yml` | **Syncthing P2P:** Zero-cloud peer-to-peer file synchronization between nodes. | **STANDBY** |
| `00_core_infrastructure/docker/docker_mcp_bridge.py` | **Docker MCP Bridge:** Integrates container inspection with Antigravity AI agents & training loops. | **ACTIVE** |
| `00_core_infrastructure/router_ai_daemon/Dockerfile` | **OpenWrt GL.iNet Daemon:** Lightweight MIPS/ARM container for hardware router telemetry & USB overrides. | **EMBEDDED** |

### 🔹 Layer 01: Application Ecosystem & User Portals
| File / Path | Containerized Services & Role | Status |
| :--- | :--- | :--- |
| `01_apps/unified_portal/Dockerfile` | **Unified Portal Production Image:** `python:3.11-slim` packaging Cross-App RAG, Movesense DSP, and Permissions. | **PRODUCTION** |
| `01_apps/canonical_port/Dockerfile.tui` | **Canonical TUI Container:** Elm-architecture Go Bubble Tea / Rust Ratatui terminal dashboard. | **CONTAINERIZED** |
| `01_apps/edge_compute_and_ai/openclaw/Dockerfile` | **OpenClaw UI Worker:** Automated Android UI testing and visual screenshot verification in container. | **TESTING** |
| `01_apps/glinet_web_optimizer/Dockerfile` | **GL.iNet Web Optimizer:** Port 3000 Wi-Fi 7 / MLO automated tuning dashboard. | **CONTAINERIZED** |
| `01_apps/experimental_pwas/obsidian_web/Dockerfile` | **Obsidian Web Interface:** Containerized web renderer for sovereign markdown knowledge vaults. | **EXPERIMENTAL** |

### 🔹 Layer 02: AI Inference & Multi-Agent Competitive Arenas
| File / Path | Containerized Services & Role | Status |
| :--- | :--- | :--- |
| `02_ai_models_and_inference/benchmarks/codeclash/arenas/*.Dockerfile` | **22 Sandboxed Competitive Arenas:** `Ants`, `BattleCode`, `BattleSnake`, `Chess`, `CybORG`, `RoboCode`, `HuskyBench`, `SCML`, `Halite` for isolated multi-agent RL evaluation. | **BENCHMARKING** |
| `00_core_infrastructure/docker/Dockerfile.rpc_worker` | **llama.cpp RPC Sharding Worker:** Containerized GGML tensor server for heterogeneous compute nodes. | **JIT EPHEMERAL** |

### 🔹 Layer 06: Tooling & Lifecycle Management
| File / Path | Containerized Services & Role | Status |
| :--- | :--- | :--- |
| `06_scripts_and_tooling/lauburu_docker.py` | **Master Docker CLI:** Automated Colima startup (`4 CPUs, 8GB RAM`), master compose lifecycle, and self-healing. | **ACTIVE CLI** |
| `01_apps/unified_portal/modules/docker_engine.py` | **Docker Portal Module:** Ingests container telemetry and executes compose actions directly from Port 4000 UI. | **ACTIVE API** |

---

## 🚀 3. Recommended Roadmap for Deepening Docker Utilization

1. **Host-Agnostic 1-Click Deployment:** Run `docker compose -f 00_core_infrastructure/docker-compose.master.yml up -d` on any machine (macOS, Linux Head Node, Cloud VPS) to instantly spin up the entire Lauburu ecosystem.
2. **Local AI Vector Acceleration with Qdrant:** Connect `01_apps/unified_portal/modules/cross_app_rag.py` to containerized Qdrant (`localhost:6333`) for $<5\text{ms}$ embedding search across 5,425+ Obsidian notes.
3. **Sandboxed RL Training with CodeClash Arenas:** Execute multi-agent training rounds inside isolated Docker containers without polluting the host environment.
