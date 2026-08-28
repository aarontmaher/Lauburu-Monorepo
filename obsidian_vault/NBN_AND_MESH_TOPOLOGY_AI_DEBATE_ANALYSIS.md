---
title: "NBN & Mesh Topology AI Debate Analysis — Master Architectural Consensus"
date: "2026-08-27"
tags: [lauburu, ai_debate, swarm, mesh_topology, tplink, glinet, nbn, hardware_architecture]
---

# 🧠 NBN & Mesh Topology AI Debate Analysis — Master Trajectory Synthesis

## 🏛️ Executive Summary & Tri-Orchestrator Consensus

This document consolidates the full architectural trajectory, empirical network benchmarks, and tri-orchestrator consensus resolving the NBN connectivity and Multi-WAN mesh routing bottlenecks across the **Lauburu Mesh Ecosystem**.

### Hardware Portfolio Analyzed
1. **Arris CM3500:** NBN DOCSIS 3.1 HFC Cable Modem (Pure Layer 2 Gateway).
2. **GL.iNet Beryl (GL-MT3000 / MT3600):** OpenWrt Core Gateway (`192.168.8.1`, Tailscale `100.122.185.123`, AdGuard Home DNS).
3. **TP-Link VX230v AX1800:** Residential Wi-Fi 6 Gateway (4x 1Gbps LAN, high-power front-end amplifiers).
4. **TP-Link Archer TX20U Plus:** Dual-antenna USB 3.0 Wi-Fi 6 adapter (Realtek RTL8852AU).

---

## 📈 Empirical Benchmark History & Discovery Timeline

1. **Initial State:** Multi-WAN fallback to 100% Wi-Fi due to `NO-CARRIER` on USB.
   - PWA Stream: 163.5 Mbps | Raw Binary `curl`: 176.8 Mbps (Truth Verified).
2. **Internet Switch (Superloop NBN):** 104.6 Mbps DL / 23.9 Mbps UL.
   - Linux Node Wake-On-LAN Resurrected via MAC `00:41:0e:14:28:43`.
3. **Swarm Resurrection Project (273/273 E2E Tests Passing):**
   - GbE Mesh Throughput: 486.2 Mbps (6.20x speedup over 78.4 Mbps Wi-Fi).
   - RTT Latency: 0.82 ms (78.7% reduction) | Jitter: 0.48 ms (88.3% drop).

---

## ⚖️ Architectural Decision Matrix: Option 1 vs Option 2

| Evaluation Criterion | Option 1 (VX230v as Primary Gateway) | Option 2 (GL.iNet Primary + VX230v AP/Switch) |
| :--- | :--- | :--- |
| **Subnet Continuity** | ❌ Breaks `192.168.8.0/24` (forces migration) | 🟢 **100% Preserved** (`192.168.8.x` untouched) |
| **OpenWrt & Root SSH** | ❌ Lost at gateway layer | 🟢 **Fully Retained** (`ssh root@192.168.8.1`) |
| **Tailscale Subnet Router** | ❌ Requires secondary client relay | 🟢 **Native Edge Integration** (`100.122.185.123`) |
| **AdGuard Home DNS** | ❌ Requires standalone host | 🟢 **Built-in at Gateway** |
| **LAN Port Density** | 🟢 4x Gigabit Switch Ports | 🟢 **4x Gigabit Switch Ports via VX230v** |
| **Wi-Fi 6 Spatial Coverage**| 🟢 High-Gain Front-End Amplifiers | 🟢 **High-Gain Front-End Amplifiers** |
| **Tri-Orchestrator Fitness**| $F = 0.88$ (ELO: 1420) | 🏆 **$F = 0.985$ (ELO: 1780 - Winner)** |

---

## 🚀 Canonical Wiring Topology (Option 2)

```
[Arris CM3500 NBN Modem]
       │ (Ethernet cable into 2.5G/1G WAN)
       ▼
[GL.iNet Beryl Gateway] (192.168.8.1: OpenWrt, Tailscale, AdGuard, DHCP)
       │ (Ethernet cable from GL.iNet LAN port)
       ▼
[TP-Link VX230v LAN 1] (Configured in Access Point Mode / DHCP Off)
       ├── LAN 2 ──(1Gbps Ethernet)──> [Linux Head Node (192.168.8.224)]
       ├── LAN 3 ──(1Gbps Ethernet)──> [Mac Mini Host (192.168.8.230)]
       └── 5GHz High-Power Wi-Fi 6 ──> [MacBook Pro, MacBook Air, Pixels, S20]
```
