---
title: "Lauburu Full-Network Lens TUI Specification & Architecture"
tags: [lauburu, rust, ratatui, whatcable, wireshark, mesh, network_lens]
---

# ⚡ Lauburu Full-Network, Thermal, Battery & Cable Lens (`lauburu_network_lens` v3.0)

A native, high-performance, immediate-mode Rust terminal analyzer integrating reverse-engineered **WhatCable** (physical port/cable/e-marker inspection, 240W PD, and data speeds), **Wireshark** (live packet and socket dissection), **Thermal & Battery Power Monitoring**, and **Ethernet 40Gbps DMA Transfer Speed Capabilities** across all 7 layers of the Lauburu AI Mesh.

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
| **L1** | `Mac Mini M4 Pro Host` | `192.168.8.143` / `.230` | 40Gbps TB4 (`bridge0`) + 1GbE | 40.0 Gbps | **0.05 ms** | 86 | Master Governor, Screen Lens Core |
| **L8** | `Linux Mini (lauburu)` | `10.0.0.8` (TB) / `.242` | **40Gbps TB4 Bridge (`bridge0`)** | 40.0 Gbps | **0.38 ms** | 48 | GGUF Model Vault Hub, High-RAM Compute |
| **L2** | `Intel MacBook Pro` | `10.0.0.4` / `192.168.8.127` | **40Gbps TB4 Bridge (`bridge0`)** | 40.0 Gbps | **4.67 ms (LAN)** | 34 | Screen Lens Teacher Target & Storage Vault |
| **L1b** | `Mac Mini M2 Pro` | `10.0.0.3` / `192.168.8.114` | **40Gbps TB4 Bridge (`bridge0`)** | 40.0 Gbps | **0.43 ms (TB)** | 24 | Secondary Mac Compute Worker |
| **L3** | `Linux Head Node` | `192.168.8.225` / TS `100.101.39.98` | 1GbE LAN / Wi-Fi + BT (-28 dBm) | 1.0 Gbps | **5.50 ms** | 398 | Ingress Gateway, Docker Hub, Ray Head |
| **L4** | `Linux Tablet` | `192.168.8.176` / TS `100.99.210.89` | Wired Port 2 on Router | 1.0 Gbps | **0.95 ms** | 16 | Touch DSP & Bedside TUI Terminal |
| **L5** | `MacBook Air M4` | `192.168.8.248` / TS `100.121.202.34` | Wi-Fi 7 MLO (5GHz / 6GHz) | 1.2 Gbps | **12.00 ms** | 28 | Metal LoRA Distillation Worker |
| **L6** | `Pixel 10 Pro XL` | `192.168.8.213` / TS `100.114.215.68` | Wi-Fi 7 MLO / USB-C PD | 1.2 Gbps | **9.20 ms** | 18 | Edge TPU Vision & Spatial UWB |
| **L7** | `Samsung Galaxy S20+` | `192.168.8.130` / TS `100.78.206.96` | USB ADB Bridge (Port 5039 / 5555) | 866 Mbps | **11.20 ms** | 14 | OpenClaw UI Test Automation |
| **GW** | `GL.iNet GL-BE14000` | `192.168.8.1` / TS `100.70.123.123` | 2.5GbE WAN (`eth2` to NBN NTD) | 2.5 Gbps | **12.00 ms** | 92 | Core Gateway, 2.5G NBN WAN, USB ADB |
| **AP** | `TP-Link VX230v` | `192.168.8.2` | 1GbE LAN Bridge (AP Mode) | 1.8 Gbps | Standby | 22 | Secondary Wi-Fi 6 AX AP |

---

## 🚀 3. Execution & Keybindings

### Run Interactive TUI:
```bash
cd /Volumes/Lauburu-Monorepo/01_apps/rust_network_analyzer
cargo run --release
```

### Run Instant Headless Snapshot:
```bash
/Volumes/Lauburu-Monorepo/01_apps/rust_network_analyzer/target/release/lauburu_network_lens --snapshot
```

### Keyboard Navigation:
* `Tab` / `1`–`5`: Switch between Full-Mesh, WhatCable, Wireshark, AI Matrix, and Multi-WAN lenses.
* `r`: Trigger immediate concurrent multi-node hardware re-probe.
* `q` / `Esc`: Graceful shutdown.

---
[[CANONICAL_PROJECT_AND_STORAGE_RULE]] | [[TP_LINK_AND_GLINET_ROUTER_CONFIGURATION_GUIDE]] | [[Index]]
