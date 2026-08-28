---
title: "multi-wan-accelerator — Multi-WAN & Multi-Transport Speedup Engine"
updated: "2026-08-27"
tags: [multi_wan, transport, channel_bonding, 10gbe, tb4, speedify, tailscale]
---

# multi-wan-accelerator — Multi-WAN & Multi-Transport Speedup Engine

## 📋 Scope & High-Throughput Aggregation
Governs simultaneous packet-level channel bonding, intelligent multi-path routing, and failover across the physical and wireless network interfaces in the Lauburu Mesh.

## 🚀 Aggregated Transport Interfaces
1. **10Gbps Thunderbolt 4 Bridge (`bridge0`):**
   - Direct point-to-point PCIe DMA bridge (`169.254.187.138`) delivering **0.277ms RTT** and up to 40 Gbps aggregate bandwidth for distributed AI tensor sharding.
2. **1GbE Dedicated Ethernet (`eth0` / `en0`):**
   - High-reliability local wired backhaul for SeaweedFS storage replication and cluster management.
3. **Wi-Fi 7 / MLO Wireless Link:**
   - Multi-Link Operation interface connected to the core GL.iNet router (`192.168.8.1`).
4. **Tailscale WireGuard Encrypted Mesh:**
   - Global L3 overlay (`100.x.x.x`) providing zero-trust routing across roaming nodes.
5. **Emergency Cellular Fallback:**
   - Android Wi-Fi Hotspot and Bluetooth PAN tethering profiles for outage survivability.

## ⚙️ Channel Bonding & Multipath Engine
- Utilizes Speedify TUN/TAP packet-level aggregation to combine interfaces, dynamically adjusting packet distribution based on real-time jitter and loss.

## 🔗 Knowledge Graph Connections
- **Master Index:** [[Index]]
- **Specifications:** [[SPEEDIFY_MULTIPATH_TUN_TAP_BONDING_ENGINE]], [[LIGHTWEIGHT_WIREGUARD_DERP_MESH_SPEC]]
- **Mesh Governance:** [[swarm]], [[7_DEVICE_MESH_AND_VRAM_POOL]]
