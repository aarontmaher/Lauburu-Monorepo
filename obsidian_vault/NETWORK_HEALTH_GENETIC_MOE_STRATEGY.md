---
title: "Network Health Genetic MoE Strategy & Bottleneck Matrix"
tags: [lauburu, network_health, genetic_moe, lo_ra, topology_optimizer]
updated_at: "2026-09-07T05:54:00.822087+00:00Z"
---

# 🧠 Network Health Genetic MoE Strategy & Physical Wiring Matrix

This document defines the mathematical models, edge AI training datasets, and physical wiring optimizations for the **Lauburu 7-Layer AI Mesh**.

---

## 🏛️ 1. The Three Macs Canonical Layer Hierarchy
- **L1 (Primary Host & Memory Governor):** `Mac Mini M4 Pro` (24GB RAM, Dual 40Gbps TB4, 1GbE Physical NIC).
- **L8 (TB4 DMA Co-Processor & GGUF Storage Vault):** `Linux Mini (lauburu)` (32GB RAM, Intel Core i7-8700B, 40Gbps TB4 DMA Bridge, 0.38ms RTT, IP `10.0.0.8`).
- **L2 (Desktop Automation Worker):** `Intel MacBook Pro` (16GB RAM, macOS, unlinked from TB4, connects via LAN Wi-Fi / Tailscale `100.103.212.21`).
- **L3 (Gateway Ingress & Big Data / Docker Hub):** `Linux Head Node` (15GB RAM, AMD Ryzen 7 5700U, LAN `192.168.8.225`, Tailscale `100.101.39.98`).
- **L4 (Lightweight Biometrics & Touch DSP):** `Linux Tablet Bedside` (8GB RAM, wired Ethernet via Router Port 2, 0.95ms RTT).
- **L5 (Dedicated Metal Worker & LoRA Distillation):** `MacBook Air M4` (16GB RAM, Tailscale `100.121.202.34`, MLX LoRA).
- **L6 (8K Vision Stream & Edge TPU):** `Pixel 10 Pro XL` (16GB RAM, Tensor G5, Tailscale `100.114.215.68`).
- **L7 (Automated UI Tester & ADB Bridge):** `Samsung Galaxy S20+` (12GB RAM, Exynos 990, Tailscale `100.78.206.96`).
- **GW (Core WAN Gateway & Security):** `GL.iNet GL-BE14000` (2 GB RAM, 2.5GbE WAN `eth2`, LAN `192.168.8.1`, Tailscale `100.70.123.123`).
- **AP (Secondary High-Bandwidth Wi-Fi 6 AP):** `TP-Link VX230v` (512MB RAM, UNII-3 Ch 149-161).

---

## 🏎️ 2. Active Bottlenecks & Self-Healing Action Feedback

| ID | Component | Hardware Limit | Active Link | Impact & Solution |
| :--- | :--- | :--- | :--- | :--- |
| `BN-01-MACMINI-ETH` | **Mac Mini M4 Pro (L1) Physical Ethernet** | `10GbE / 1GbE Physical NIC (10,000 Mbps capable)` | `1000baseT (1,000 Mbps Full Duplex)` | Use TB4 DMA for inter-Mac AI sharding; keep en0 for general Internet/LAN |
| `BN-02-L8-TB4-SPEED` | **Linux Mini (L8) Thunderbolt 4 Bridge** | `40 Gbps Thunderbolt 4 to L1 (Receptacle 1)` | `40.0 Gbps (bridge0 IP 10.0.0.8, 0.38ms RTT)` | Hardware link is active and verified; L2 MBP is currently unlinked on LAN |
| `BN-03-MBA-FALLBACK` | **MacBook Air M4 (L5) Connection State** | `Apple Silicon M4 (16GB RAM)` | `Tailscale WireGuard (100.121.202.34, 12ms RTT) / LAN Wi-Fi` | Stable headless worker; can be plugged into TB4 for ultra-low latency bursts |
| `BN-04-ROUTER-RAM-OFFLOAD` | **GL.iNet GL-BE14000 (2 GB RAM) vs TP-Link VX230v (512MB RAM)** | `Combined 2.5 GB Router RAM + Wi-Fi 7 MLO Radios` | `GL.iNet handles WAN 2.5G (eth2), Tailscale, ADB, and LAN routing (1.38 GB free)` | Primary default route is eth2 wired NBN (12ms latency, 0% packet loss) |
| `BN-05-LINUX-WIFI-FALLBACK` | **Linux Head Node (AMD Ryzen 7 5700U / L3)** | `15 GB RAM, AMD Ryzen 7 5700U` | `LAN 192.168.8.225 / Tailscale 100.101.39.98 (6.4ms RTT)` | Docker engine, SeaweedFS DFS, Qdrant vector index |

---

## 🔋 3. Multi-Port Power Strip & AC Mains Monitoring
- **Main AC Wall Outlet:** 240V AC Mains (Australian AS/NZS 3112 10A / 2,400W Maximum Rating).
- **10-Port GaN Charging Station:** 240W Total PD (Single Port 140W EPR).
- **Live Mesh Draw:** ~168.5W Total Active Computing Power across all 7 physical layers.
