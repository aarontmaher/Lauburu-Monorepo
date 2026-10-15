---
title: "Thunderbolt & Mesh Network Sovereign Governor Telemetry"
updated: 2026-09-14T10:44:34Z
tags: [lauburu, thunderbolt, network, screen_lens, qwen_duo, self_healing]
---

# ⚡ Thunderbolt & Mesh Network Sovereign Lens Dashboard

*Last Updated: `2026-09-14T10:44:34Z` | Governed by **Screen Lens Sovereign & Qwen Duo***

## 🔌 1. Physical Thunderbolt Bus Topology (Mac Mini M4 Pro Host)

| Bus / Receptacle | Physical PHY Speed | Connected Peer | Hardware Status | Direct Interface |
| :--- | :--- | :--- | :--- | :--- |
| **Bus 0 (Port 1)** | `40 Gb/s` | MacBook Pro (Node L2) (`Mac16,12`) | `Link Status: 0x2 (Active)` | `en4` -> `bridge0` |
| **Bus 1 (Port 2)** | `20 Gb/s` | Linux Mini (`lauburu`) | `Link Status: 0x2 (Active)` | `en3` -> `bridge0` |
| **Bus 2 (Port 3)** | `40 Gb/s` | MacBook Pro Intel (`MacBookPro16,1`) | `Link Status: 0x2 (Active)` | `en2` -> `bridge0` |

---

## 🚀 2. Live Thunderbolt DMA Peer Latencies vs Network Fallbacks

| Node Name | Role | Direct TB Latency | LAN Latency | Tailscale Latency | DMA Speedup | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`L2_MacBook_Pro`** | Metal GPU RPC & Storage Vault | `--` | `57.15 ms` | `3.68 ms` | **`Baseline`** | 🟡 LAN FALLBACK |
| **`L5_MacBook_Air`** | Secondary High-Speed Metal Worker | `--` | `107.65 ms` | `4.52 ms` | **`Baseline`** | 🟡 LAN FALLBACK |
| **`L8_Linux_Mini`** | Gateway Ingress & 10M Drafter Vault | `--` | `--` | `--` | **`Baseline`** | 🔴 OFFLINE |

---

## 🌐 3. General Mesh Network & Gateway Ingress

| Node Name | Network Role | LAN IP | LAN RTT | Tailscale IP | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`L3_Linux_Laptop`** | 1M Router AI Compute Hub | `192.168.8.225` | `2.87 ms` | `100.101.39.98` | 🟢 ACTIVE |
| **`GW_Router`** | Core Gateway & Hardware USB Bridge | `192.168.8.1` | `0.92 ms` | `100.122.185.123` | 🟢 ACTIVE |

---

## 🛡️ 4. Autonomous Self-Healing & Integrity Log

- **Linux Mini Route Guard:** `verified_healthy` (Success: `True`)
- **Bridge0 MTU:** `9000` (Jumbo Frames Verified)
- **Zero-Mock Verification Gate:** Empirical hardware telemetry collected via Darwin Mach kernel syscalls and TCP connect timestamps.
