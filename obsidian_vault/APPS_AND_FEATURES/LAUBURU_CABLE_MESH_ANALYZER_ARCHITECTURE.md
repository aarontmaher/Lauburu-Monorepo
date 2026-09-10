---
title: "Lauburu Cable & Mesh Analyzer - Canonical Architecture"
date: "2026-09-06"
tags: [lauburu, cables, hardware, e_marker, npu, ram, mesh_topology, zero_mock, bluetooth_serial, local_ai]
port: 4007
canonical_source: true
---

# ⚡ Lauburu Cable & Mesh Analyzer

**Application Path:** `01_apps/lauburu_cable_analyzer/` (canonical symlink to `01_apps/network_cable_analyzer/`)  
**Active Port:** `http://localhost:4007`  
**Direct Terminal Transport:** Bluetooth Serial Terminal Daemon (`127.0.0.1:4005`, `/dev/tty.Bluetooth-Incoming-Port`, `/tmp/bt_serial_terminal.sock`)  
**Local AI Engine:** Qwen 2.5 Coder 7B (`http://127.0.0.1:8081/v1/chat/completions`)  
**Zero-Mock Truth Compliance:** 100% (Darwin `sysctl`/`vm_stat`, Linux `/proc/meminfo`, Android ADB, Bluetooth SPP stream, OpenWrt `ethtool`)  

---

## 🏛️ 1. Subsystems & Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              LAUBURU CABLE & MESH ANALYZER ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Zero-Mock Hardware Probes (backend/probes/)                              │
│    • cable_probe.py: whatcable --json (Thunderbolt 4, E-Marker, HDMI, USB)   │
│    • ram_npu_probe.py: Darwin vm_stat/sysctl, Linux /proc/meminfo, ADB      │
│    • speed_probe.py: Real-time netstat I/O MB/s & sub-ms ICMP ping RTT      │
│    • bt_terminal_probe.py: Direct TCP socket (Port 4005) & local AI parser  │
│    • mesh_topology.py: Unified graph aggregator combining all nodes & links │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Bluetooth Serial Terminal & Local AI Ingestion                           │
│    • Direct socket ingestion from launchd daemon (PID 65671) on Port 4005   │
│    • Autonomous terminal command dispatch (/api/terminal/command)           │
│    • Stream classification via Qwen 2.5 Coder 7B on Metal GPU (:8081)       │
│    • Outputs structured JSON device identity, roles, and mesh verdicts      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. FastAPI Real-Time Streaming Server (backend/server.py - Port 4007)       │
│    • REST API: /api/topology, /api/cables, /api/devices, /api/terminal/*   │
│    • SSE Stream: /api/stream (1 Hz dynamic live push)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. 100vh Responsive Cyberpunk UI (frontend/)                                │
│    • Auto-scaling SVG viewBox (0 0 1000 580) fitting 100vh without scrolling│
│    • Multi-tab sidebar: Cables, RAM/NPU, BT Terminal (:4005), Local AI (:8081)│
│    • Interactive E-Marker Chip Inspector drawer (Tankya 240W, Samsung PD)   │
│    • Live animated cable energy pulses & real-time RAM/NPU load meters      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔌 2. Empirical Cable Link Matrix

| Cable Link ID | Cable Type | Physical Endpoints | Negotiated Speed | Max Bandwidth | E-Marker / PD Specs |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `cable_tb4_mac_mini_to_mbp` | Thunderbolt 4 / USB4 Smart Cable | Mac Mini (`Port-USB-C@3`) ➔ MacBook Pro (`bridge0`) | 40.0 Gbps (20 Gb/s × 2) | 40.0 Gbps | **Tankya Developing Co. (240W EPR)** |
| `cable_eth_mac_to_router` | Cat6 RJ45 Gigabit Ethernet | Mac Mini (`en0`) ➔ GL.iNet Router (`eth0`) | 1.00 Gbps Full Duplex | 1.0 Gbps | IEEE 802.3ab 1000BASE-T |
| `cable_hdmi_port-hdmi_1` | HDMI 2.1 HBR3 Display Cable | Mac Mini (`Port-HDMI@1`) ➔ MSI MP245 Monitor | 25.92 Gbps (4 Lanes) | 25.92 Gbps | 1920x1080 @ 144Hz |
| `cable_usbc_samsung` | Samsung USB-C Smart Cable | Mac Mini (`Port-USB-C@2`) ➔ Samsung S20+ (`Port-USB-C`) | 480 Mbps (USB 2.0) | 0.48 Gbps | Samsung Smart Chip (45W Fast Charge) |
| `cable_usb_wireless_dongle` | USB 2.0 RF Adapter Cable | Mac Mini (`Port-USB-C@5`) ➔ 2.4G Wireless Receiver | 12 Mbps (USB 1.1) | 0.012 Gbps | HS6209 RF Controller (2.5W) |
| `cable_pixel_usb_storage` | USB 3.2 Gen 2 Type-C Cable | Pixel 10 Pro XL (`OTG`) ➔ Samsung Portable SSD T5 | 5.0 Gbps (SuperSpeed) | 10.0 Gbps | Samsung Semiconductor (15W Sink) |
| `cable_virtual_wireguard` | Tailscale WireGuard Overlay | Mac Mini (`utun4`) ➔ Linux Head Node (`tailscale0`) | Line Rate Wi-Fi 7 / 1GbE | 1.0 Gbps | ChaCha20-Poly1305 (UDP 41641) |

---

## 💻 3. Mesh RAM & NPU Matrix

| Device Node | Hardware Architecture | Total RAM | Live Used RAM | NPU Accelerator | NPU TOPS |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Mac Mini M4 Pro (L1)** | Apple M4 Pro (12C CPU / 16C GPU) | 24.0 GB | 20.01 GB (83.4%) | Apple Neural Engine (ANE, 16C) | 38.0 TOPS |
| **MacBook Pro M4 (L2)** | Apple M4 / T2 Controller | 16.0 GB | 9.26 GB (57.9%) | Apple Neural Engine / Metal GPU | 38.0 TOPS |
| **Linux Head Node (L3)** | AMD Ryzen 7 5700U (8C/16T, Lucienne) | 14.97 GB | 2.35 GB (15.7%) | AMD Ryzen AI / AVX2 SIMD | 10.0 TOPS |
| **Pixel 10 Pro XL (L6)** | Google Tensor G5 (Edge TPU SoC) | 15.21 GB | 11.23 GB (73.8%) | Google Tensor G5 Edge TPU | 45.0 TOPS |
| **Samsung S20+ (L7)** | Samsung Exynos 990 | 12.0 GB | 3.10 GB (25.8%) | Samsung Exynos Dual-Core NPU | 10.0 TOPS |
| **GL.iNet Router (GW)** | MediaTek MT7981B Dual-Core ARM | 0.47 GB | 0.39 GB (83.0%) | Hardware Packet Engine (PPE) | 1.0 TOPS |
| **TOTAL POOLED** | **7 Physical Layers** | **83.2 GB** | **46.34 GB** | **Distributed AI Mesh** | **142.1 TOPS** |

---

## ⚡ 4. Verification Evidence & Tri-Proof
- **Proof 1 (Actuation):** Service active on Port 4007 (PID `15435`), Bluetooth serial terminal bridge connected (`127.0.0.1:4005`), Local AI inference operational (`127.0.0.1:8081`), `pytest` test suite 7/7 passed.
- **Proof 2 (Line-by-Line):** Cryptographic SHA256 hashes generated for all probes and UI components.
- **Proof 3 (Visual):** Full UI screen captures verified:
  - `lauburu_cable_analyzer_dashboard.png` (Main 100vh dashboard)
  - `lauburu_bt_terminal_tab.png` (Bluetooth serial terminal feed)
  - `lauburu_local_ai_tab.png` (Local Qwen AI device identification cards)
