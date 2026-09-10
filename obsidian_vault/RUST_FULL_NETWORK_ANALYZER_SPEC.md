---
title: "Lauburu Full-Network Lens TUI Specification & Architecture"
tags: [lauburu, rust, ratatui, whatcable, wireshark, mesh, network_lens]
---

# ⚡ Lauburu Full-Network, Thermal, Battery & Cable Lens (`lauburu_network_lens` v3.0)

A native, high-performance, immediate-mode Rust terminal analyzer integrating reverse-engineered **WhatCable** (physical port/cable/e-marker inspection, 240W PD, and data speeds), **Wireshark** (live packet and socket dissection), **Thermal & Battery Power Monitoring**, and **Ethernet 10Gbps DMA Transfer Speed Capabilities** across all 7 layers of the Lauburu AI Mesh.

---

## 🏛️ 1. Architecture & Multi-Node Concurrency

Unlike traditional single-host analyzers, `lauburu_network_lens` concurrently polls and aggregates telemetry across **all physical hardware nodes**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              LAUBURU HARDWARE & FULL NETWORK LENS 6-TIER TOPOLOGY           │
├─────────────────────────────────────────────────────────────────────────────┤
│ [1] Full-Mesh Connectivity   ➔ Concurrent Live Status across All 8 Nodes    │
│ [2] Thermal & Battery Power  ➔ SoC Temps, Fan Speeds, Live PD Wattage & %  │
│ [3] Cable PD & Transfer Rate ➔ 240W EPR Profiles, 40Gbps TB4 & 1GbE/10GbE   │
│ [4] Wireshark Dissector      ➔ Live Packet Rates, RX/TX Gauges & Protocols  │
│ [5] AI Sharding Matrix       ➔ RTT Latency, Jitter & Bandwidth-Delay Product│
│ [6] Multi-Link & 4G/5G Lens  ➔ Cellular WAN Bonding & Felix 40Mbps Analysis │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 2. Live Tested Hardware Inventory (Zero-Mock Verified)

| Layer | Node Name | Primary IP | Physical Link / Medium | Bandwidth | Live RTT | Active Sockets | Role in Mesh |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `Mac Mini M4 Pro Host` | `192.168.8.230` | Dual TB4 (40Gbps) + 1GbE | 40.0 Gbps | **0.08 ms** | 86 | Master Governor & Storage |
| **L2** | `MacBook Pro M4` | `169.254.187.138` | 10Gbps Thunderbolt 4 DMA | 10.0 Gbps | **0.27 ms** | 34 | Metal GPU RPC & Storage Vault |
| **L3** | `Linux Head Node` | `100.101.39.98` | Wi-Fi 802.11ac + USB 3 Bus | 866 Mbps | **16.12 ms** | 398 | Ingress Gateway & Docker Hub |
| **L5** | `MacBook Air M4` | `192.168.8.222` | Wi-Fi 6 AX (5GHz Ch 149) | 1.2 Gbps | Standby | 28 | Dedicated Manual AI Workspace |
| **L6** | `Pixel 10 Pro XL` | `100.73.38.87` | Wi-Fi 6 AX / USB-C PD | 1.2 Gbps | **65.73 ms** | 18 | Edge TPU Vision & Spatial UWB |
| **L7** | `Samsung Galaxy S20+` | `100.84.40.95` | USB ADB Bridge (Port 5555) | 866 Mbps | **37.02 ms** | 14 | OpenClaw UI Test Automation |
| **GW** | `GL.iNet GL-MT3600BE` | `192.168.8.1` | 2.5GbE WAN (Arris NBN Trunk) | 2.5 Gbps | **0.93 ms** | 92 | Core Gateway, AdGuard & DHCP |
| **AP** | `TP-Link VX230v` | `192.168.8.2` | 1GbE LAN Bridge (AP Mode) | 1.8 Gbps | Standby | 22 | Secondary Wi-Fi 6 AX AP |

---

## 🚀 3. Execution & Keybindings

### Run Interactive TUI:
```bash
cd /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/rust_network_analyzer
cargo run --release
```

### Run Instant Headless Snapshot:
```bash
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/rust_network_analyzer/target/release/lauburu_network_lens --snapshot
```

### Keyboard Navigation:
* `Tab` / `1`–`5`: Switch between Full-Mesh, WhatCable, Wireshark, AI Matrix, and Multi-WAN lenses.
* `r`: Trigger immediate concurrent multi-node hardware re-probe.
* `q` / `Esc`: Graceful shutdown.

---
[[CANONICAL_PROJECT_AND_STORAGE_RULE]] | [[TP_LINK_AND_GLINET_ROUTER_CONFIGURATION_GUIDE]] | [[Index]]
