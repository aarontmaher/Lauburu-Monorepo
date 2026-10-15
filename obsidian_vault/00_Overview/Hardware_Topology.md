---
title: "Hardware Topology & Multi-Interface Link Matrix"
updated: "2026-10-12"
tags: [topology, hardware, network, interfaces, latency]
---

# Hardware Topology & Multi-Interface Link Matrix

## 📋 Physical & Overlay Link Topologies
Documents the physical network wiring, Thunderbolt 4 DMA bridges, Wi-Fi 7 radio parameters, Layer 0 Bluetooth lifeline, and Tailscale WireGuard mesh routing across all 8 hardware nodes.

## 🌐 Interface Matrix
- **Thunderbolt 4 Bridge (`bridge0`):** `10.0.0.2` (L1 Host) ↔ `10.0.0.8` (L8 `lauburu`, 40 Gb/s, 0.38ms RTT avg, ~2,800 MB/s throughput). L2 MacBook Pro is unlinked from TB and operates over LAN/Tailscale.
- **Local Ethernet / Wi-Fi LAN:** `192.168.8.0/24` (GL-BE14000 Gateway at `192.168.8.1`, Port 2 wired to L4 tablet at `192.168.8.176`, L1 wired `192.168.8.230` / Wi-Fi `192.168.8.143`)
- **Tailscale Mesh Overlay:** `100.64.0.0/10` (End-to-end encrypted WireGuard)
- **Layer 0 Bluetooth Mesh:** Persistent IP-less RFCOMM/BLE serial control plane across all 8 nodes

## 🔗 Knowledge Graph Connections
- **Master Index:** [[Index]]
- **Hardware Matrix:** [[7_DEVICE_MESH_AND_VRAM_POOL]]
- **Bonding Engine:** [[SPEEDIFY_MULTIPATH_TUN_TAP_BONDING_ENGINE]]
