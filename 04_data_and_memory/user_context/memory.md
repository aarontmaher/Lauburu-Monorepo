# 🧠 MEMORY.MD — Canonical Hardware, Network & Monorepo State

> *"Persistent, verified ground truth for the 7-Layer Lauburu Mesh Ecosystem."*

---

## 📍 1. Physical Environment & Network Topology

- **Property Address:** 12 Martin Street, St Kilda VIC 3182 (Apartment building / MDU).
- **WAN Backhaul:** FTTB (Fibre to the Building) delivered via VDSL2 over copper telephone line.
- **Modem Router:** TP-Link VX230v (authenticates Origin broadband credentials over VDSL2).
- **Core Gateway Router:** GL.iNet Beryl 7 (`GL-MT3600BE`, `192.168.8.1`, Tailscale `100.122.185.123`).
  - **Port 1 (2.5G WAN 🌐):** Connected to TP-Link LAN port.
  - **Port 2 (1G LAN 🖧):** Connected to 5-port Gigabit switch distributing LAN to all local nodes.
  - **Subnet:** `192.168.8.0/24`. Tailscale WireGuard Overlay: `100.64.0.0/10`.

---

## 🖥️ 2. The 7-Layer Physical Mesh Hardware Matrix

| Layer | Device Name | Primary OS | RAM / AI Cap | Network Protocols & IPs | Strategic Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `Mac_Node` (Mini M4 Pro) | macOS 15 Darwin | 24.0 GB (1.09 GB free) | `192.168.8.230`, `100.119.199.76`, TB4: `169.254.187.1` | **Memory Governor & Prompt Ingestion**. Fills last ($\ge 9.6\text{ GB}$ headroom target). |
| **L2** | `MacBook_Pro` (Vault) | macOS 15 Darwin | 16.0 GB (14.0 GB AI) | `192.168.8.127`, `100.103.212.21`, **TB4: `169.254.187.138`** | **10Gbps TB4 Bridge (0.204ms RTT)**, 285 GB SSD Model Vault. Primary compute fill. |
| **L3** | `Linux_Mini` | Ubuntu / Debian | 16.0 GB (13.8 GB AI) | `192.168.8.224`, `100.101.39.98` | Intel 2018 Mac Mini (Linux) (16T), Docker Hub, Petals DHT, Apache Ray worker. |
| **L4** | `Linux_Tablet` | Debian Linux | 8.0 GB (6.5 GB AI) | DHCP, `100.81.92.125` | Touch DSP, mobile compute worker, lightweight telemetry. |
| **L5** | `MacBook_Air` | macOS Darwin | 16.0 GB (14.0 GB AI) | `192.168.8.222`, `100.93.158.96`, TB4: `169.254.187.96` | Apple M4, Metal Performance Shaders, background LoRA distillation. |
| **L6** | `Pixel_10_Pro_XL` | Android 15 | 16.0 GB (3.83 GB free) | USB ADB `5B080DLCQ001LQ`, `100.73.38.87` | Google Tensor G5, Edge TPU, 188 GB UFS, **Shizuku Binder IPC (`uid=2000`)**. |
| **L7** | `Samsung_S20` | Android 13 | 12.0 GB (4.45 GB free) | Tailscale ADB `100.84.40.95:5555`, `100.99.123.58` | Samsung Exynos 990, 66 GB storage, dedicated automated UI test runner. |
| **GW** | `GL.iNet Router` | OpenWrt 24 | Embedded MIPS | `192.168.8.1`, `100.122.185.123` | Core Gateway, kmwan failover, USB ADB hardware bridge daemon. |

---

## 🏛️ 3. Canonical Tri-Vault Storage Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. OBSIDIAN KNOWLEDGE VAULT                                                 │
│    • Path: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/        │
│    • 5,862 Markdown notes, graph links, continuous debate consensus logs.   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. PYSPARK & DATA LAKEHOUSE                                                 │
│    • Path: /Users/aaron/DFS_UNIFIED/lora_datasets/ & 04_data_and_memory/    │
│    • Continuous 24/7 LoRA datasets (VLA, UI/UX ELO, Polyglot, Claude CoT).  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. GITHUB MONOREPO & WORKTREES                                              │
│    • Path: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/                       │
│    • 202,209 indexed files across 9 canonical subsystems.                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔌 4. Active Ports & Services Matrix

- **Port 8081:** Qwen 3.8 Max Dense (`PRIMA_LEGACY_URL`)
- **Port 8082:** Distributed Pipelined-Ring Parallelism (`PRIMA_RING_URL`)
- **Port 8083:** Huihui Qwen 3.8 Max Abliterated (`PRIMA_PROXY_URL`)
- **Port 18802:** Self-Healing Hub & Wake-on-LAN REST API daemon
- **Port 4000:** Lauburu Web UI Hub
- **Port 2222:** Pixel 10 Pro XL USB Reverse SSH Forwarding (`adb reverse tcp:2222 tcp:22`)
