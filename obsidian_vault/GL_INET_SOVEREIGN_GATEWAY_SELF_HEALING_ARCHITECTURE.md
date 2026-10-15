---
title: "GL.iNet Sovereign Gateway Autonomous Mesh & Daemon Self-Healing Architecture"
tags: [lauburu, router, openwrt, self_healing, wake_on_lan, ssh, mesh_watchdog, llamacpp, petals, exo, seaweedfs, docker]
date: "2026-08-27"
---

# 🛡️ GL.iNet Sovereign Gateway Autonomous Mesh & Daemon Self-Healing Architecture

## 1. Overview & Physical Ground Truth

The **GL.iNet GL-BE14000 Router** (`100.70.123.123` / `192.168.8.1`) functions as the **Tier-0 Sovereign Gateway** of the 8-Layer Physical Mesh. Because it is physically connected to mains power, WAN (2.5G NBN on `eth2`), and local Ethernet/Wi-Fi 7, it serves as the ultimate out-of-band watchdog that **never sleeps** and maintains autonomous resurrection capabilities across the entire ecosystem.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              GL.iNET TIER-0 AUTONOMOUS SELF-HEALING ARCHITECTURE            │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. HARDWARE LAYER & WATCHDOG RUNNER                                         │
│    • Hardware: GL.iNet GL-BE14000 (MediaTek Filogic Quad-Core, 2 GB RAM)   │
│    • Daemon: /usr/bin/router_mesh_watchdog.sh (POSIX Shell, <4.0 MB RAM)    │
│    • Service: /etc/init.d/router_mesh_watchdog (OpenWrt procd, START=99)    │
│    • Crontab: /etc/crontabs/root (* * * * * execution)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. HARDWARE RESURRECTION MATRIX                                             │
│    • Layer 1 (Mac Mini Host): aaron@100.119.199.76 / WoL 1C:F6:4C:7D:D7:0A  │
│    • Layer 8 (Linux Mini): linuxmini@100.121.247.8 / TB 10.0.0.8            │
│    • Layer 2 (MacBook Pro): aaronmaher@100.103.212.21 / WoL 98:FC:...       │
│    • Layer 3 (Linux Head Node): linux@100.101.39.98 / WoL 00:41:0E:14:28:43 │
│    • Layer 4 (Linux Tablet): debian@100.99.210.89 / Router Port 2 (0.95ms)   │
│    • Layer 5 (MacBook Air): aaronmaher@100.121.202.34                       │
│    • Layer 6 (Pixel 10 Pro XL): u0_a363@100.114.215.68:8022 (Termux)       │
│    • Layer 7 (Samsung S20+): u0_a420@100.78.206.96:8022 & USB ADB           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. AUTONOMOUS DAEMON SELF-HEALING MATRIX                                    │
│    • AI Inference: llama.cpp / llama-server (:8090), proxies (:8081,:8082)  │
│    • Containers: Docker / Colima service restarts on Linux and Mac          │
│    • Storage: SeaweedFS Filer (8888), Master (9333), FUSE remounts          │
│    • Edge Ingress: Cloudflare Tunnel (cloudflared), Tailscale overlay       │
│    • Memory Graph: Qdrant Vector DB (6333), Self-Healing Hub (18802)        │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. Live Verification Matrix

All hardware targets have been verified with **zero-password Dropbear SSH & Hardware USB ADB** from the router:

| Node | User & IP | Port | Protocol | Live Status |
| :--- | :--- | :--- | :--- | :--- |
| **L1 Mac Mini** | `aaron@100.119.199.76` | 22 | SSH ED25519 / WoL | ✅ **ONLINE** |
| **L8 Linux Mini (lauburu)** | `linuxmini@100.121.247.8` | 22 | SSH ED25519 / TB4 (`10.0.0.8`) | ✅ **ONLINE** |
| **L2 MacBook Pro** | `aaronmaher@100.103.212.21` | 22 | SSH ED25519 / WoL | ✅ **ONLINE** |
| **L3 Linux Head Node** | `linux@100.101.39.98` | 22 | SSH ED25519 / WoL | ✅ **ONLINE** |
| **L4 Linux Tablet** | `100.99.210.89` (`192.168.8.176`) | 22 | SSH ED25519 / Port 2 Wired | ✅ **ONLINE** |
| **L5 MacBook Air** | `aaronmaher@100.121.202.34` | 22 | SSH ED25519 / WoL | ✅ **ONLINE** |
| **L6 Pixel 10 Pro XL** | `u0_a363@100.114.215.68` | 8022 | SSH ED25519 | ✅ **ONLINE** |
| **L7 Samsung S20+** | `u0_a420@100.78.206.96` | 8022 | SSH ED25519 & USB ADB | ✅ **ONLINE** |

Live Telemetry Feed: `http://100.70.123.123/mesh_status.json`
