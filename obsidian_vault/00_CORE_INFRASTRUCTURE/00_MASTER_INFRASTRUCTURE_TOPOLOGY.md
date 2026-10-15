---
title: "00 Core Infrastructure: 7-Layer Mesh & Physical Hardware Matrix"
tags: [infrastructure, mesh, tailscale, hardware, ports]
---

# 🌐 00 Core Infrastructure: 7-Layer Physical Mesh Topology

Governs the pooled **139.0 GB RAM (108.4 GB Usable AI VRAM)** across 8 physical compute nodes and 1 gateway router:

| Layer | Node Name | Network Role | IP Address | Dynamic Cap | Assigned Responsibilities |
|---|---|---|---|---|---|
| **L1** | `Mac_Node` | Host & Memory Governor | `192.168.8.143` / `100.119.199.76` | 19.2 GB (80%, >=4.8GB free) | Master Prompt Ingestion, Screen Lens, & Memory Governor |
| **L1a / L5** | `MacBook_Air` | Metal Worker & LoRA Distillation | `192.168.8.248` / `100.121.202.34` | 14.4 GB (90%) | Metal Performance Shaders, LoRA Training, & JupyterLab |
| **L1c / L2** | `MacBook_Pro_16` | Model Vault & x86_64 Worker | `10.0.0.4` / `192.168.8.127` / `100.103.212.21` | 14.4 GB (90%) | Intel i7 Model Vault (TB 40 Gb/s Receptacle 3, MTU 9000, LAN/Tailscale) |
| **L1b** | `MacMini_M2` | Secondary Compute Node | `10.0.0.3` / `192.168.8.114` / `100.104.128.34` | 13.6 GB (85%) | Apple M2 Pro, Mac14,12 (TB 40 Gb/s Receptacle 2, 0.43ms RTT) |
| **L3** | `Linux_Head_Node` | Gateway Ingress & Compute Hub | `192.168.8.225` / `100.101.39.98` | 12.0 GB (80%) | AMD Ryzen 7 5700U, Docker Hub, Ray cluster, Local AI Offload |
| **L4** | `Linux_Tablet` | Mobile Linux & TUI Terminal | `192.168.8.176` / `100.99.210.89` | 6.0 GB (75%) | Debian Linux (`debian-1`), Bedside Client, Touch DSP |
| **L6** | `Pixel_10_Pro_XL`| 8K Vision Stream & Edge TPU | `192.168.8.213` / `100.114.215.68` | 13.6 GB (85%) | Google Tensor G5, Edge TPU, Shizuku rish & 8K Video Stream |
| **L7** | `Samsung_S20` | Dedicated Automated UI Tester| `192.168.8.130` / `100.78.206.96` | 9.0 GB (75%) | Exynos 990, ADB Automated Mobile UI Testing |
| **L8** | `Linux_Mini` | Central Hub & High-RAM Compute | TB `10.0.0.8` / `100.121.247.8` | 25.6 GB (80%) | `lauburu` Intel i7-8700B, Ubuntu 24.04 (32GB RAM), 40 Gb/s TB Link |
| **GW** | `GL.iNet Router`| Core Gateway & USB Bridge | `192.168.8.1` / `100.70.123.123` | 1.38 GB free (2 GB RAM) | GL-BE14000 (OpenWrt), 2.5G NBN eth2 WAN, USB Hardware ADB Bus |

---

### ⚡ Probed Thunderbolt 4 Fabric Topology
Mac mini M4 Pro (L1) provides three discrete Thunderbolt buses, all three physically active at 40 Gb/s on `bridge0`:
1. **Receptacle 1 (Bus 0) $\longleftrightarrow$ `lauburu` (L8):** **40 Gb/s** (`bridge0` IP `10.0.0.8`, ~0.38 ms avg RTT)
2. **Receptacle 2 (Bus 1) $\longleftrightarrow$ `mac-mini-m2` (L1b):** **40 Gb/s** (`bridge0` IP `10.0.0.3`, ~0.43 ms avg RTT)
3. **Receptacle 3 (Bus 2) $\longleftrightarrow$ `MacBook Pro 16"` (L2):** **40 Gb/s** (`bridge0` IP `10.0.0.4`, MTU 9000, ~4.67 ms LAN fallback)

---
- Links: [[Index]] | [[NETWORK_CONNECTIVITY_GRAPH]] | [[02_PRIMA_CPP_FULL_NETWORK_SHARDING]] | [[01_APPS_AND_PORTAL_CATALOG]]
