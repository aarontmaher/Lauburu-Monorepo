---
title: Mesh Topology & All-Device Connection Audit
date: 2026-09-14
tags: [mesh, network, audit, topology, zero_mock, physical_hardware]
---

# 🌐 Mesh Topology & All-Device Connection Audit (Empirical Tri-Proof)

## 📊 1. Multi-Transport Device Verification Matrix

| Physical Node | Physical Role | Hardware Silicon | Wired / TB Link (RTT) | Wi-Fi IP / Band (RTT) | Tailscale IP (RTT) | Auth / Protocol | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1 Mac Mini** | Primary Host & Memory Governor | Apple M4 Pro (24 GB) | `192.168.8.230` (10GbE, 0.04ms) / `169.254.189.217` | `192.168.8.155` (Wi-Fi 7 MLO, 2401.9 Mbps) | `100.119.199.76` | Local / Darwin | **ONLINE** |
| **L2 MacBook Pro** | Metal GPU RPC & SSD Vault | Intel Core i7 (16 GB) | `169.254.44.77` (TB4 DMA, 0.399ms) | `192.168.8.128` (Wi-Fi 5, 866.7 Mbps, 1.98ms) | `100.103.212.21` (3.15ms) | SSH `aaronmaher` | **ONLINE** |
| **L1a MacBook Air** | Metal Performance Shaders | Apple M4 (16 GB) | `169.254.76.5` (TB4 DMA, 0.451ms) | `192.168.8.248` (Wi-Fi 7 MLO, 2401.9 Mbps, 3.12ms) | `100.121.202.34` | SSH `aaronmaher` | **ONLINE** |
| **L3 Linux Head Node** | Compute Hub & Docker Gateway | AMD Ryzen 7 5700U (16 GB) | `192.168.8.225` (1GbE/WoL, 3.16ms) | `192.168.8.183` (Wi-Fi 5, 433.3 Mbps) | `100.101.39.98` (7.80ms) | SSH `linux` | **ONLINE** |
| **L6 Pixel 10 Pro XL** | Edge TPU & 8K Digital PTZ | Google Tensor G5 (16 GB) | N/A (USB Available) | `192.168.8.145` (Wi-Fi 7 MLO, 1441.3 Mbps, 5.13ms) | `100.73.38.87` (119ms) | Termux SSH (8022) | **ONLINE** |
| **L7 Samsung S20+** | Automated UI Tester & ADB | Samsung Exynos 990 (12 GB) | USB-C Tether (`rndis0`) | `192.168.8.118` (Wi-Fi 6, 2161.3 Mbps, 3.54ms) | `100.78.206.96` (5.98ms) | Termux SSH (8022) / ADB | **ONLINE** |
| **L4 Lenovo Idea Tab** | Mobile Compute & Touch DSP | MediaTek ARM (8 GB) | N/A | `192.168.8.190` (Wi-Fi, 390.0 Mbps, 275ms) | `100.81.92.125` | Wi-Fi / Ping | **ONLINE** |
| **GW GL.iNet Router** | Core Gateway & Hardware Bridge | MT3600BE Wi-Fi 7 Gateway | `192.168.8.1` (0.729ms) | Tri-Band (2.4GHz, 5GHz, MLO) | `100.122.185.123` (4.10ms) | Root SSH `root` | **ONLINE** |
| **Linux Mini (lauburu)** | Dedicated Linux Intel Node | Intel Core i7 2018 Mini (32 GB) | TB3 Bus 1 20 Gb/s (`fe80::1082:a3ff:fe9e:ae71%bridge0`, 0.411ms) | TP-Link AX Wi-Fi (`2357:013f` RTL8852AU Driver Ready) | `100.115.233.33` | Thunderbolt IPv6 | **LINK UP** |

## 🛠️ 2. TP-Link Extender & Linux Mini Driver Resolution

1. **Kernel Driver Patch & Installation:**
   - **Hardware ID:** `Bus 001 Device 013: ID 2357:013f TP-Link 802.11ac/ax WLAN Adapter`
   - **Underlying Chipset:** Realtek RTL8852AU (Wi-Fi 6 AX)
   - **Driver Build:** Compiled `/usr/src/morrownr-rtw89` on Linux 6.8.0-41-generic kernel with backports:
     - `core.c:3948`: `ieee80211_iterate_stations_atomic`
     - `phy.c:844`: `ieee80211_iterate_stations_atomic`
     - `usb.c:760`: `skb_queue_purge(&rtwusb->tx_queue[i])`
   - **Module & Firmware Installed:**
     - `/lib/modules/6.8.0-41-generic/extra/rtw89/rtw89_8852au_git.ko`
     - `/lib/firmware/rtw89/rtw8852a_fw-1.bin.zst`
   - **Conflict Elimination:** Purged conflicting `88x2bu.ko` and blacklisted `88x2bu` in `/etc/modprobe.d/blacklist-88x2bu.conf`.

2. **Router Static Reservations:**
   - `tplink-extender-bridge`: MAC `98:fc:84:e6:e2:12` -> `192.168.8.176`
   - `mac_mini_eth`: MAC `1c:f6:4c:7d:d7:0a` -> `192.168.8.230`
   - `linux_head_node_wol`: MAC `00:41:0e:14:28:43` -> `192.168.8.225`
