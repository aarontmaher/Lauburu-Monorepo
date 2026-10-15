---
title: "Thunderbolt Mesh & General Network Sovereign Status"
updated: 2026-09-14 14:52:34
tags: [thunderbolt, mesh_network, sovereign_governor, zero_mock]
---

# ⚡ Thunderbolt & Network Sovereign Telemetry

- **Mac Mini Host Virtual Bridge:** `bridge0` (MTU 9000, Status: active)
- **Linux Mini TB3 Link:** `3.665 ms RTT` via `169.254.65.244` (20 Gb/s PHY)
- **Route Integrity:** Removed rogue default gateway via thunderbolt0; restored enp4s0 primary.

## 🔌 Thunderbolt Fabric Matrix
| Bus | Connected Device | Link Speed | Status | RTT |
| :--- | :--- | :--- | :--- | :--- |
| **Bus 0** | MacBook Air | 40 Gb/s | Standby | -- |
| **Bus 1** | Linux Mini (`lauburu`) | 20 Gb/s | ACTIVE | `3.665 ms` |
| **Bus 2** | MacBook Pro | 40 Gb/s | ACTIVE | `None ms` |

## 🌐 General Mesh Ingress
| Node | Local IP | Port | Status | RTT |
| :--- | :--- | :--- | :--- | :--- |
| **GL.iNet Router** | 192.168.8.1 | 22 | ONLINE | `2.819 ms` |
| **Linux Laptop** | 192.168.8.225 | 22 | ONLINE | `5.205 ms` |
| **Linux Mini** | 192.168.8.238 | 22 | ONLINE | `2.569 ms` |
| **Pixel 10 Pro XL** | 192.168.8.145 | 8022 | ONLINE | `8.929 ms` |
| **Samsung S20+** | 192.168.8.118 | 8022 | ONLINE | `6.002 ms` |
