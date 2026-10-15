---
title: "Lauburu Mesh: Canonical Active IP Matrix & Transport Topology"
tags: [network, mesh, transport, tailscale, ip_table, obsidian_canonical]
updated: "2026-10-12T10:10:00+11:00"
total_nodes: 10
active_overlay_nodes: 9
canonical_source: true
truth_audited: true
audit_swarm_verified: "2026-10-12"
audit_swarm_engine: "screen_lens_mesh_telemetry+empirical_probe"
mesh_topology_version: "10-node-probed-2026-10-12"
---

# 🌐 Canonical Mesh Topology & Active IP Table (Probed 2026-10-12)

| Layer | Node Alias | Hostname / Model | Tailscale IP | LAN IP (Wi-Fi/Ethernet) | Direct DMA / Thunderbolt / USB | Hardware MAC | SSH/API Port | Keepalive / Live Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `Mac_Node` | Mac mini M4 Pro (Mac16,11) | `100.119.199.76` | `192.168.8.143` (Wi-Fi) / `192.168.8.230` (LAN) | TB `bridge0`: `10.0.0.2` | `1c:f6:4c:7d:d7:0a` | 22 | Host Governor / **ONLINE (0.15ms)** |
| **L1a / L5** | `MacBook_Air` | Mac16,12 (MacBook Air M4) | `100.121.202.34` | `192.168.8.248` | - | `fe:6e:09:2c:3b:dc` | 22 | Metal Worker / **ONLINE (5.3ms TS / 24.7ms LAN)** |
| **L1b** | `MacMini_M2` | Mac mini (M2 Pro, Mac14,12) | `100.104.128.34` | `192.168.8.114` | TB Receptacle 2: `10.0.0.3` (40 Gb/s) | `36:d5:c0:8:3e:c0` | 22 | Secondary Mac / **ONLINE (0.43ms TB / 27ms LAN)** |
| **L1c / L2** | `MacBook_Pro` | MacBookPro16,1 (2019 i7) | `100.103.212.21` | `192.168.8.127` | TB Receptacle 3: `10.0.0.4` (40 Gb/s) | `82:e6:6d:c0:a4:01` | 22 | Model Vault / **ONLINE (4.67ms LAN / 40 Gbps TB)** |
| **L3** | `Linux_Head_Node` | AMD Ryzen 7 5700U | `100.101.39.98` | `192.168.8.225` | BT: `-28 dBm` | `00:41:0e:14:28:43` | 22 | `systemd` / **ONLINE (5.5ms TS / 13.8ms LAN)** |
| **L4** | `Linux_Tablet` | Debian Linux (`debian-1`) | `100.99.210.89` | `192.168.8.176` (Port 2 LAN) | BT: `00:00:00:00:5a:ad` | `98:fc:84:e6:e2:12` | 22 | Active Compute / **ONLINE (~92ms TS)** |
| **L6** | `Pixel_10_Pro_XL` | Pixel 10 Pro XL (Tensor G5) | `100.114.215.68` | `192.168.8.213` | BT: `30-e0-44-6d-18-ec` | `26:cc:79:f2:90:76` | 8022 | `termux-wake-lock` / **ONLINE (69ms TS)** |
| **L7** | `Samsung_S20` | Galaxy S20+ 5G (Exynos 990) | `100.78.206.96` | `192.168.8.130` | BT: `5c:cb:99:05:81:41` | `1e:8f:6d:0a:8e:0b` | ICMP / 5039 | UI Tester / **STANDBY (Paired BT)** |
| **L8** | `Linux_Mini` | `lauburu` (Intel Ubuntu 24.04, 32GB) | `100.121.247.8` | `192.168.8.242` | TB Receptacle 1: `10.0.0.8` (40 Gb/s) | `12:82:a3:9e:ae:71` | 22 | Docker Hub / **ONLINE (0.38ms TB / 2.95ms TS)** |
| **GW** | `GLiNet_Router` | GL.iNet GL-BE14000 (OpenWrt) | `100.70.123.123` | `192.168.8.1` | WAN `eth2` (NBN 2.5G) | `1c:f6:4c:7d:d7:0a` (LAN bridge) | 22 | Native Root / **ONLINE (3.05ms TS / 3.18ms LAN)** |

---

## 🚀 Live Transport Health Summary (Audit: 2026-10-12)
- **Thunderbolt 4 DMA Fabric (`bridge0`):**
  - **L1 ↔ L8 (`lauburu`):** **0.38 ms avg RTT** at **40 Gb/s** (`10.0.0.8`, Receptacle 1, Bus 0).
  - **L1 ↔ L1b (`Mac mini M2 Pro`):** **0.43 ms avg RTT** at **40 Gb/s** (`10.0.0.3`, Receptacle 2, Bus 1).
  - **L1 ↔ L2 (`MacBook Pro 16"`):** **40 Gb/s linked** (`10.0.0.4`, MTU 9000, Receptacle 3, Bus 2).
  - All three physical Thunderbolt buses on L1 are active at 40 Gb/s bridging into `10.0.0.0/24`.
- **Local Area Network (GL-BE14000 2.5GbE / Wi-Fi 7):**
  - Gateway router uptime: load average 0.82.
  - WAN: **Active on eth2** (2.5G port connected to NBN), 0.0% packet loss to 1.1.1.1 (12ms avg).
- **Encrypted Tailscale Overlay (`100.x.x.x`):**
  - All compute nodes maintaining direct WireGuard peer connections.
- **Storage Substrate (SeaweedFS):**
  - Endpoints on Ports 8085 / 8087, verified active.
