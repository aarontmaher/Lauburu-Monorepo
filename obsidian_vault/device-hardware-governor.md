---
title: "device-hardware-governor — Adaptive Device Hardware Capabilities & RAM Governor"
updated: "2026-10-14"
tags: [governor, hardware, ram, vram, limits, thermal, telemetry]
---

# device-hardware-governor — Adaptive Device Hardware Capabilities & RAM Governor

## 📋 Scope & Responsibility
The **Device Hardware Capabilities Governor** continuously monitors host and peripheral hardware thermals, CPU load, and RAM/VRAM utilization across all 7 physical mesh layers to prevent Out-Of-Memory (OOM) panics and thermal throttling.

## ⚙️ Hardware Limits & Dynamic Safety Caps
| Layer | Node | Physical RAM | AI VRAM Cap | Dynamic Cap % | Operating Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `Mac_Node` (M4 Pro) | 24.0 GB | 19.2 GB | **80%** (>=4.8 GB Free) | Primary Host & Memory Governor (Rule 3) |
| **L8** | `Linux_Mini (lauburu)` | 32.0 GB | 25.6 GB | **80%** | 40Gbps TB4 DMA Bridge (0.14ms probed RTT), GGUF Model Vault Hub |
| **L1b** | `MacMini_M2` (M2 Pro) | 16.0 GB | 13.6 GB | **85%** | 40Gbps TB4 DMA Bridge (0.43ms RTT), Secondary Compute Node |
| **L2** | `MacBook_Pro` (Intel i7) | 16.0 GB | 14.0 GB | **90%** | 40Gbps TB4 DMA Bridge (`10.0.0.4`), Teacher Target & Automation |
| **L3** | `Linux_Head_Node` (5700U)| 15.0 GB | 12.0 GB | **80%** | Docker Hub, Ray cluster, First-Offload Target (Rule 10) |
| **L4** | `Linux_Tablet` | 8.0 GB | 6.0 GB | **75%** | Mobile Linux Compute & Touch DSP |
| **L1a / L5** | `MacBook_Air` (M4) | 16.0 GB | 14.0 GB | **90%** | Metal Worker & LoRA Distillation |
| **L6** | `Pixel_10_Pro_XL` | 16.0 GB | 13.6 GB | **85%** | Edge TPU & 8K Vision Stream, Termux SSH (:8022) |
| **L7** | `Samsung_S20` | 12.0 GB | 9.0 GB | **75%** | Dedicated Automated UI Tester |
| **GW** | `GL.iNet Router` | 2.0 GB | N/A | Embedded (1.38 GB Free) | Core Gateway, 2.5G NBN WAN (`eth2`), USB ADB Bridge |

## 🛡️ Governance Policies
1. **Dynamic Offloading:** If Host Mac RAM exceeds 80% (or available free buffer drops below 4.8 GB), background batch compute and APIs are automatically offloaded over 40Gbps TB4 to L8 (`lauburu`), L1b (`MacMini_M2`), or L2 (`MacBook_Pro`), or over LAN/Tailscale to L3 (`Linux_Head_Node`).
2. **Android Keepalive:** Maintains `termux-wake-lock` and battery optimization whitelists to ensure 24/7 background worker stability.
3. **Headroom Invariant:** Enforces $\ge 10.0\text{ GB}$ free NVMe disk space at all times.

## 🔗 Knowledge Graph Connections
- **Master Index:** [[Index]]
- **Hardware Matrix:** [[7_DEVICE_MESH_AND_VRAM_POOL]]
- **Mesh Governance:** [[swarm]], [[ai-debate]]
