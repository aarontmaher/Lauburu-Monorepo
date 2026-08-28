---
title: "7-Device Mesh Hardware Topology & 82.8 GB VRAM Pooling Matrix"
updated: "2026-08-27"
tags: [hardware, mesh, vram, topology, nodes, rpc_sharding]
---

# 7-Device Mesh Hardware Topology & 82.8 GB VRAM Pooling Matrix

## 📋 Pooled Hardware Overview
The Lauburu Mesh aggregates **108.0 GB Physical RAM (82.8 GB Usable AI VRAM)** across 7 physical compute layers and 1 gateway node.

## 🖥️ Node Matrix & Network Allocation
| Layer | Node Name | Hardware Specs | Local IP | Tailscale IP | Usable AI VRAM | Key Protocols |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `Mac_Node` | Apple M4 Pro Mac Mini (24 GB) | `192.168.8.230` | `100.119.199.76` | **21.6 GB** | Prompt Ingestion & Memory Governor |
| **L2** | `MacBook_Pro` | Apple M3/M4 Pro (16 GB) | `192.168.8.127` | `100.103.212.21` (TB4: `169.254.187.138`) | **14.0 GB** | 10Gbps TB4 Bridge (0.277ms RTT), GGUF Vault |
| **L3** | `Linux_Head_Node` | AMD Ryzen 7 5700U (16 GB) | `192.168.8.224` | `100.101.39.98` | **13.8 GB** | Docker Hub, Petals DHT Bootstrap |
| **L4** | `Linux_Tablet` | Debian Linux Tablet (8 GB) | DHCP | `100.81.92.125` | **6.5 GB** | Mobile Compute & Lightweight DSP |
| **L5** | `MacBook_Air` | Apple M4 (16 GB) | `192.168.8.222` | `100.93.158.96` | **14.0 GB** | Metal Shaders & LoRA Distillation |
| **L6** | `Pixel_10_Pro_XL` | Google Tensor G5 (16 GB) | DHCP | `100.73.38.87` | **12.5 GB** | Edge TPU & 8K Vision Stream |
| **L7** | `Samsung_S20` | Samsung Exynos 990 (12 GB) | DHCP | `100.84.40.95` | **9.0 GB** | Router USB ADB UI Testing Target |
| **GW** | `GL.iNet Router` | GL-MT3600BE-a0f-MLO | `192.168.8.1` | `100.122.185.123` | Embedded | Core Gateway & USB ADB Daemon |

## 🔗 Knowledge Graph Connections
- **Master Index:** [[Index]]
- **Governance:** [[device-hardware-governor]], [[multi-wan-accelerator]], [[swarm]]
- **Compute:** [[02_ai_models_and_inference]], [[TERMIUS_TUI_UNIFIED_AI_SHARDING_SPEC]]
