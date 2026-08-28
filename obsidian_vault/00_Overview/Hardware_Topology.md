---
title: "Hardware Topology & Multi-Interface Link Matrix"
updated: "2026-08-27"
tags: [topology, hardware, network, interfaces, latency]
---

# Hardware Topology & Multi-Interface Link Matrix

## 📋 Physical & Overlay Link Topologies
Documents the physical network wiring, Thunderbolt 4 DMA bridges, Wi-Fi 7 radio parameters, and Tailscale WireGuard mesh routing across all devices.

## 🌐 Interface Matrix
- **Thunderbolt 4 Bridge (`bridge0`):** `169.254.187.138` (0.277ms latency, ~2,800 MB/s throughput)
- **Local Ethernet / Wi-Fi LAN:** `192.168.8.0/24` (Sub-millisecond local routing)
- **Tailscale Mesh Overlay:** `100.64.0.0/10` (End-to-end encrypted WireGuard)

## 🔗 Knowledge Graph Connections
- **Master Index:** [[Index]]
- **Hardware Matrix:** [[7_DEVICE_MESH_AND_VRAM_POOL]]
- **Bonding Engine:** [[SPEEDIFY_MULTIPATH_TUN_TAP_BONDING_ENGINE]]
