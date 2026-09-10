---
title: "00 Core Infrastructure: 7-Layer Mesh & Physical Hardware Matrix"
tags: [infrastructure, mesh, tailscale, hardware, ports]
---

# 🌐 00 Core Infrastructure: 7-Layer Physical Mesh Topology

Governs the pooled **108.0 GB RAM (82.8 GB Usable AI VRAM)** across 7 physical layers:

| Layer | Node Name | Network Role | IP Address | Dynamic Cap | Assigned Responsibilities |
|---|---|---|---|---|---|
| **L1** | `Mac_Node` | Host & Memory Governor | `127.0.0.1` (`100.119.199.76`) | 20.0 GB (83%) | Master Prompt Ingestion & Port 8088 Portal |
| **L2** | `MacBook_Pro_16` | TB3 Storage Vault & x86_64 Host | `100.103.212.21` (TB: `169.254.215.118`) | 16.0 GB (4G AMD 5300M) | Dual 40G/20G TB3 DMA Ring (0.54ms RTT) |
| **L3** | `Linux_Head_Node` | Gateway Ingress & Docker | `100.101.39.98` | 12.8 GB (80%) | SeaweedFS DFS (:8888), Ray Engine & Qdrant |
| **L4** | `Linux_Tablet` | Mobile Linux & TUI Terminal | `100.81.92.125` | 5.5 GB (68%) | Dedicated TUI Bedside Client & Qwen 1.5B |
| **L5** | `MacBook_Air` | Metal Worker & Model Vault | `100.93.158.96` (TB4: `169.254.136.148`) | 13.5 GB (84%) | JupyterLab (:8889), Qwen 80B/72B Vault |
| **L6** | `Pixel_10_Pro_XL`| 8K Vision Stream & Edge TPU | `100.73.38.87` | 12.5 GB (78%) | Gemini Nano 3B & 8K Digital PTZ Camera |
| **L7** | `Samsung_S20` | Dedicated Automated UI Tester| `100.84.40.95` | 8.5 GB (70%) | SmolLM2-1.7B Termux UI Automation |
| **GW** | `GL.iNet Router`| Core Gateway & USB Bridge | `192.168.8.1` | 28 MB (5%) | SmolLM2-135M Keepalive Sentinel (:18802) |

---

### ⚡ Triangular 3-Node Thunderbolt Full-Mesh Topology
All three Apple Silicon/Metal compute nodes form a dedicated zero-switch, point-to-point DMA ring:
1. **Mac Mini M4 Pro $\longleftrightarrow$ MacBook Pro:** 40 Gb/s (0.54 ms avg RTT)
2. **Mac Mini M4 Pro $\longleftrightarrow$ MacBook Air:** 40 Gb/s (0.48 ms avg RTT)
3. **MacBook Pro $\longleftrightarrow$ MacBook Air:** 20 Gb/s (0.61 ms avg RTT)

---
- Links: [[Index]] | [[NETWORK_CONNECTIVITY_GRAPH]] | [[02_PRIMA_CPP_FULL_NETWORK_SHARDING]] | [[01_APPS_AND_PORTAL_CATALOG]]
