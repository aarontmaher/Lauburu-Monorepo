---
title: "device-hardware-governor — Adaptive Device Hardware Capabilities & RAM Governor"
updated: "2026-08-27"
tags: [governor, hardware, ram, vram, limits, thermal, telemetry]
---

# device-hardware-governor — Adaptive Device Hardware Capabilities & RAM Governor

## 📋 Scope & Responsibility
The **Device Hardware Capabilities Governor** continuously monitors host and peripheral hardware thermals, CPU load, and RAM/VRAM utilization across all 7 physical mesh layers to prevent Out-Of-Memory (OOM) panics and thermal throttling.

## ⚙️ Hardware Limits & Dynamic Safety Caps
| Layer | Node | Physical RAM | AI VRAM Cap | Dynamic Cap % | Operating Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `Mac_Node` (M4 Pro) | 24.0 GB | 21.6 GB | **90%** | Primary Host & Memory Governor |
| **L2** | `MacBook_Pro` (TB4) | 16.0 GB | 14.0 GB | **90%** | Metal GPU RPC & Storage Vault |
| **L3** | `Linux_Head_Node` | 16.0 GB | 13.8 GB | **80%** | Docker Hub & Petals Bootstrap |
| **L4** | `Linux_Tablet` | 8.0 GB | 6.5 GB | **75%** | Mobile Linux Compute & Touch DSP |
| **L5** | `MacBook_Air` (M4) | 16.0 GB | 14.0 GB | **90%** | Metal Worker & LoRA Distillation |
| **L6** | `Pixel_10_Pro_XL` | 16.0 GB | 12.5 GB | **85%** | Edge TPU & 8K Vision Stream |
| **L7** | `Samsung_S20` | 12.0 GB | 9.0 GB | **75%** | Dedicated Automated UI Tester |
| **GW** | `GL.iNet Router` | Embedded | N/A | Embedded | Core Gateway & USB ADB Bridge |

## 🛡️ Governance Policies
1. **Dynamic Offloading:** If Host Mac RAM exceeds 90%, background batch compute is automatically sharded over 10Gbps TB4 to peripheral nodes.
2. **Android Keepalive:** Maintains `termux-wake-lock` and battery optimization whitelists to ensure 24/7 background worker stability.
3. **Headroom Invariant:** Enforces $\ge 10.0\text{ GB}$ free NVMe disk space at all times.

## 🔗 Knowledge Graph Connections
- **Master Index:** [[Index]]
- **Hardware Matrix:** [[7_DEVICE_MESH_AND_VRAM_POOL]]
- **Mesh Governance:** [[swarm]], [[ai-debate]]
