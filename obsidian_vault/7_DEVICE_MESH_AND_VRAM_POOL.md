---
title: "8-Node Mesh Hardware Topology & 108.4 GB AI VRAM Pooling Matrix"
updated: "2026-10-14"
tags: [hardware, mesh, vram, topology, nodes, rpc_sharding]
---

# 8-Node Mesh Hardware Topology & 108.4 GB AI VRAM Pooling Matrix

## 📋 Pooled Hardware Overview
The Lauburu Mesh aggregates **139.0 GB Physical RAM (108.4 GB Usable AI VRAM)** across 8 heterogeneous physical compute layers and 1 embedded gateway router.

## 🖥️ Node Matrix & Network Allocation
| Layer | Node Name | Hardware Specs | Local IP | Tailscale IP | Usable AI VRAM | Key Protocols |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `Mac_Node` | Apple M4 Pro Mac Mini (24 GB) | `192.168.8.143` / `.230` | `100.119.199.76` | **19.2 GB** | Prompt Ingestion & Memory Governor |
| **L8** | `Linux_Mini (lauburu)` | Intel Core i7-8700B (32 GB) | `10.0.0.8` (TB) / `.242` | `100.121.247.8` | **27.2 GB** | **40Gbps TB4 Bridge (0.14ms probed RTT)**, Model Vault GGUF Hub |
| **L1b** | `MacMini_M2` | Apple M2 Pro Mac Mini (16 GB) | `10.0.0.3` (TB) / `.114` | `100.104.128.34` | **13.6 GB** | **40Gbps TB4 Bridge (27.4ms RTT)**, Secondary Inference Node |
| **L2** | `MacBook_Pro` | Intel Core i7-9750H (16 GB) | `10.0.0.4` (TB) / `.127` | `100.103.212.21` | **14.0 GB** | Screen Lens Sovereign Teacher Target (TB unlinked, Wi-Fi 5 / Tailscale) |
| **L3** | `Linux_Head_Node` | AMD Ryzen 7 5700U (15 GB) | `192.168.8.225` | `100.101.39.98` | **12.0 GB** | Docker Hub, SeaweedFS DFS (:8888), Qdrant Vector DB |
| **L4** | `Linux_Tablet` | Debian Linux Tablet (8 GB) | `192.168.8.116` (Port 2) | `100.80.64.5` | **6.0 GB** | Touch DSP & Bedside TUI Terminal |
| **L5** | `MacBook_Air` | Apple M4 (16 GB) | `192.168.8.248` | `100.121.202.34` | **14.0 GB** | Metal Shaders & LoRA Distillation |
| **L6** | `Pixel_10_Pro_XL` | Google Tensor G5 (16 GB) | `192.168.8.213` | `100.114.215.68` | **13.6 GB** | Edge TPU & 8K Vision Stream, Termux SSH (:8022) |
| **L7** | `Samsung_S20` | Samsung Exynos 990 (12 GB) | `192.168.8.157` | `100.84.40.95` | **9.0 GB** | Router USB ADB UI Testing Target |
| **GW** | `GL.iNet Router` | GL-BE14000 (2.0 GB) | `192.168.8.1` | `100.70.123.123` | Embedded | 2.5G NBN WAN (`eth2`), USB ADB Bridge |

## 🔗 Knowledge Graph Connections
- **Master Index:** [[Index]]
- **Governance:** [[device-hardware-governor]], [[multi-wan-accelerator]], [[swarm]]
- **Compute:** [[02_ai_models_and_inference]], [[TERMIUS_TUI_UNIFIED_AI_SHARDING_SPEC]]
