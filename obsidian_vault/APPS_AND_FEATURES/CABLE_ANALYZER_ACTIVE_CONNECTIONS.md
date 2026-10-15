---
title: "Cable & Mesh Analyzer Lauburu — Active Connections Subsystem (2026)"
tags: [lauburu, active_connections, bluetooth, ssh, tailscale, wifi_mlo, usb, thunderbolt, zero_mock]
---

# 🔗 Cable & Mesh Analyzer Lauburu — Active Connections Subsystem

## 1. Architectural Overview
The **Active Connections Subsystem** (`01_apps/network_cable_analyzer/backend/probes/active_connections_probe.py`) provides real-time, empirical, zero-mock discovery and telemetry across all 6 core physical and logical transport layers of the Lauburu 7-layer mesh:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 6-LAYER ACTIVE NETWORK CONNECTION MATRIX                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. 📶 BLUETOOTH (Layer 0 IP-Less Foundation)                                │
│    • Kernel Probes: blueutil, lsof -i :4005, Darwin CoreBluetooth sysctl    │
│    • Active Links: Pixel 10 Pro XL, Samsung S20+, Magic Keyboard, Linux Mini│
│    • Bandwidth: 2.0–3.0 Mbps (EDR/BLE 5.3) | Protocol: RFCOMM / SPP / HID   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. 🔒 SSH (Encrypted Point-to-Point Node Tunnels)                           │
│    • Kernel Probes: lsof -i :22 -i :8022, ps -Ao pid,args                   │
│    • Active Links: Established sessions to Linux Mini & Termux daemons      │
│    • Ciphers: OpenSSH ChaCha20-Poly1305, AES-256-GCM, Ed25519 authentication│
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. 🛡️ TAILSCALE (WireGuard Overlay & Direct P2P)                            │
│    • Kernel Probes: tailscale status --json                                 │
│    • Active Peers: MacBook Pro, Linux Mini, Pixel, S20+, Sentinel, Router   │
│    • Protocol: WireGuard Noise_IK / ChaCha20-Poly1305                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. 📡 WI-FI MULTI-BAND & WI-FI 7 MLO (2.4GHz / 5GHz 160M / 6GHz 320M)      │
│    • Kernel Probes: airport -I, ipconfig getsummary en1, system_profiler    │
│    • Active Link: GL-MT3600BE-a0f-MLO (Channel 44, 160MHz width, MCS 11)   │
│    • Security: WPA3 SAE (Personal) | PHY: 802.11ax / 802.11be MLO Capable   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 5. 🔌 USB PERIPHERALS & BUS TOPOLOGY                                        │
│    • Kernel Probes: ioreg -p IOUSB -w0 -l, adb devices -l                   │
│    • Active Links: Apple USB2 Hub (480M), Apple USB3 Gen2 Hub (10G),        │
│      2.4G RF Receiver (12M), Samsung S20+ ADB Daemon (480M cable bottleneck)│
├─────────────────────────────────────────────────────────────────────────────┤
│ 6. ⚡ THUNDERBOLT 4 / USB4 PCIE DMA RING BRIDGE                              │
│    • Kernel Probes: ifconfig bridge0, ping6 -c 1 fe80::...%bridge0          │
│    • Active Links: bridge0 active members (en2, en3, en4)                   │
│    • Bandwidth: 40.0 Gbps | Measured Link Latency: 0.198–0.205 ms RTT       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. API Endpoints
- `GET /api/connections/active`: Consolidated telemetry across all 6 categories.
- `GET /api/connections/{category}`: Filtered category telemetry (`bluetooth`, `ssh`, `tailscale`, `wifi`, `usb`, `thunderbolt`).

## 3. UI/UX Features
- **Header Stat Chip:** Real-time counter of active links (`stat-active-conns`).
- **Dedicated Sidebar Tab:** `🔗 Links` tab (`#tab-btn-connections`, `#tab-content-connections`).
- **Interactive Category Filter:** Filter by All, Bluetooth, SSH, Tailscale, Wi-Fi 7, USB, and Thunderbolt.
- **Connection Cards:** Displays transport, endpoint, bandwidth rate, signal/RTT latency, protocols, and authentic diagnostic descriptions.

## 4. Verification Proofs
- **Proof 1 (Actuation):** Pytest 29/29 tests passed (Exit Code 0).
- **Proof 2 (Line-by-Line):** Exact SHA256 checksums documented in `walkthrough.md`.
- **Proof 3 (Visual):** Visual screen capture verified in `lauburu_cable_analyzer_active_connections_verified.png`.
