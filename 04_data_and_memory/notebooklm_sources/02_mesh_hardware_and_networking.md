# 🌐 Source 2: 8-Node Hardware Mesh Network Topology & Dynamic RAM Governance
*Generated for Google NotebookLM & Gemini Spark | Monorepo Canonical Source*
*Compilation Timestamp: 2026-10-14T14:16:14.829967+00:00*

---

## 1. Hardware Matrix (139.0 GB RAM / 108.4 GB Usable AI VRAM Pool)

| Layer | Node Name | Network Role | Local IP | Tailscale IP | Dynamic RAM Ceiling | Hardware & Capabilities |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `Mac_Node` | Primary Host & Memory Governor | `192.168.8.230` | `100.119.199.76` | **80%** (19.2 GB AI) | Apple M4 Pro Mac Mini. Primary controller, memory governor (>=4.8 GB free buffer). |
| **L2** | `MacBook_Pro` | Model Vault & Automation Target | `192.168.8.127` | `100.103.212.21` | **90%** (14.0 GB AI) | Intel Core i7-9750H, 16 GB, LAN Wi-Fi 5 (~6.5ms RTT, unlinked TB), 285 GB SSD vault. |
| **L8** | `Linux_Mini_lauburu` | 40Gbps TB4 DMA Bridge & Sharded GGUF | TB `10.0.0.8` | `100.121.247.8` | **80%** (25.6 GB AI) | Intel Core i7-8700B, 32 GB RAM, 40Gbps TB4 DMA bridge (0.38ms RTT), Ubuntu 24.04. |
| **L3** | `Linux_Head_Node` | Gateway Ingress & Compute Hub | `192.168.8.225` | `100.101.39.98` | **80%** (12.0 GB AI) | AMD Ryzen 7 5700U, 15 GB RAM, Docker Engine, Ray Head, BT paired (-28 dBm). |
| **L4** | `Linux_Tablet` | Mobile Compute & Touch DSP | `192.168.8.116` | `100.80.64.5` | **75%** (6.0 GB AI) | Debian Linux Tablet, Port 2 Router wired link, lightweight biometrics telemetry. |
| **L5** | `MacBook_Air` | Metal LoRA Distillation & Worker | `192.168.8.248` | `100.121.202.34` | **90%** (14.0 GB AI) | Apple M4 MacBook Air, Metal Performance Shaders, LoRA fine-tuning & distillation. |
| **L6** | `Pixel_10_Pro_XL` | 8K Vision Stream & Edge TPU | `192.168.8.213` | `100.114.215.68` | **85%** (13.6 GB AI) | Google Tensor G5, Edge TPU, 8K Digital PTZ, Termux SSH :8022. |
| **L7** | `Samsung_S20` | Dedicated Automated UI Tester | `192.168.8.157` | `100.84.40.95` | **75%** (9.0 GB AI) | Samsung Exynos 990, 12 GB RAM, Termux UI Tester & ADB target. |
| **GW** | `GL-BE14000` | Core Gateway & 2.5G NBN WAN | `192.168.8.1` | `100.70.123.123` | Embedded (2.0 GB) | GL-BE14000 Core Gateway, 2.5G NBN WAN on eth2, USB ADB bridge. |

---

## 2. Core Infrastructure Subsystem
# 00_core_infrastructure — Core Mesh Infrastructure & Containerization

## Scope & Responsibility
Houses all clustering, storage aggregation, network routing, and container definitions powering the 7-device mesh.

## Components
1. **SeaweedFS Cluster:** Master, Filer, and Volume servers aggregating NVMe and SSD storage across all nodes into `/mnt/dfs_unified` (1.701 TB).
2. **Samba Gateway (Containerized):** `dperson/samba` container providing SMB3 with Apple VFS Fruit extensions for macOS Finder and iOS clients.
3. **Tailscale Mesh Overlay:** Encrypted WireGuard overlay connecting all 7 devices across cellular, Wi-Fi, and Ethernet transports.
4. **Systemd Service Units:** Daemons for auto-mounting, keep-alives, and automatic crash recovery.
5. **Docker Compose Stacks:** Declarative container configurations for MinIO, Apache Ray, Portainer, and microservices.

## Key Ports & Endpoints
- SeaweedFS Master: `100.101.39.98:9333` (gRPC: `19333`)
- SeaweedFS Filer: `100.101.39.98:8888` (gRPC: `18888`)
- SeaweedFS Volume Server: `100.101.39.98:8080` (gRPC: `18080`)
- Samba SMB3: `100.101.39.98:445` & `139`


---
## 🤖 Assigned Subsystem Specialist AI
- **Specialist Agent:** `spec-00-core-infrastructure`
- **Assigned Model Tier:** `Qwen 2.5 Coder 32B (Q4_K_M) / Hermes 3 8B`
- **Skill Definition:** `05_agents_and_swarms/antigravity_skills/spec-00-core-infrastructure/SKILL.md`
- **Governance Mandate:** Continuous recursive optimization of this subsystem's documentation, contracts, and test integrity.
