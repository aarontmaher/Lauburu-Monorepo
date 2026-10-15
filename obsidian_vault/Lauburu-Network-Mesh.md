---
tags: [network, dashboard, lauburu, mesh, self-healing, thunderbolt, 8_node]
title: Lauburu Network Mesh Status
updated: "2026-10-12T10:10:00+11:00"
---

# Lauburu Network Mesh Topology & Self-Healing Routes

## Overview
The **Lauburu Mesh Ecosystem** aggregates an **8-node compute mesh + core gateway router** across heterogeneous physical silicon, pooling **139.0 GB RAM (108.4 GB AI VRAM)**. The mesh utilizes a multi-layered connectivity architecture to ensure high availability and self-healing. When upstream DNS (`oauth2.googleapis.com`) or cloud APIs fail, the mesh gracefully falls back to local subnets, peer-to-peer tunnels, and physical tethers to remain operational at **$0 cloud spend**.

## Topology & Network Interfaces (Host L1 Mac Mini M4 Pro)
| Connection Type | Interface | Subnet / IP | Role | Status |
| --- | --- | --- | --- | --- |
| **Ethernet** | `en0` | `192.168.8.230/24` | High-speed LAN uplink to GL-BE14000 gateway | **ACTIVE (PROBED)** |
| **Wi-Fi** | `en1` | `192.168.8.143/24` | Primary wireless interface to GL-BE14000 | **ACTIVE (PROBED)** |
| **Thunderbolt 4** | `bridge0` | `10.0.0.2/24` (Peer `10.0.0.8`) | **40 Gb/s PCIe DMA to L8 `lauburu` (0.38 ms RTT)** | **ACTIVE (PROBED)** |
| **Tailscale** | `utun4` / VPN | `100.119.199.76` | Overlay zero-trust WireGuard mesh across all 8 nodes | **ACTIVE (PROBED)** |
| **Bluetooth PAN / Layer 0** | Bluetooth Graph | RFCOMM / L2CAP / BNEP | IP-less control plane, BLE magic packets, and WoL | **ACTIVE (PROBED)** |

## Self-Healing & Fallback Routes

### 1. Tier 0: Direct Thunderbolt 4 DMA Link (`10.0.0.0/24`)
- **Peers:** L1 Mac Mini M4 Pro (`10.0.0.2`) $\longleftrightarrow$ L8 Linux Mini Hub `lauburu` (`10.0.0.8`).
- **Performance:** 40 Gbps line rate, ~0.38 ms average round-trip time.
- **Role:** High-throughput Tensor Parallelism (TP), GGUF model vault synchronization, and zero-latency inter-node memory pooling.

### 2. Tier 1: Wired Switch & Gateway Backplane (GL-BE14000)
- **WAN Uplink:** Wired 2.5GbE Port (`eth2`) directly to NBN NTD (`100.90.9.130`, 12 ms RTT to 1.1.1.1, 0% packet loss).
- **LAN Port 1:** Mac Mini host connection (`192.168.8.230`).
- **LAN Port 2:** Linux Tablet (`debian-1`, `192.168.8.176`, 0.95 ms RTT).
- **USB ADB Bus:** Direct hardware bridge to mobile edge nodes (Pixel 10 Pro XL, Samsung S20+).

### 3. Tier 2: Wireless & Overlay Mesh
- **Wi-Fi 7 MLO:** Primary high-speed wireless for MacBook Air M4 (`192.168.8.248`) and Pixel 10 Pro XL (`192.168.8.213`).
- **Wi-Fi 5 (802.11ac):** Dedicated link for Intel MacBook Pro L2 (`192.168.8.127`, RTT ~6.5 ms).
- **Tailscale WireGuard (`100.x.x.x`):** Encrypted fallback and remote mesh overlay across all 8 nodes and router (`100.70.123.123`).

### 4. Layer 0: Omnipresent Bluetooth Graph (IP-less Control Plane)
- **Trigger:** Complete loss of Wi-Fi, Ethernet, and Tailscale overlays.
- **Action:** The mesh drops into Layer 0 Bluetooth RFCOMM/L2CAP serial bridges. Magic packets, WoL resurrection commands, and Screen Lens control payloads transmit over raw Bluetooth serial pairings.

## Connectivity Flow

```mermaid
graph TD
    subgraph External Infrastructure
    NBN[NBN NTD Fiber WAN]
    TS[Tailscale DERP Relay]
    end

    subgraph Core Gateway
    GW["GL-BE14000 Router (192.168.8.1 / 100.70.123.123)"]
    end

    subgraph Compute Backbone [Tier 0: 40 Gb/s TB4]
    L1["L1: Mac Mini M4 Pro (10.0.0.2)"] <===>|"40 Gbps TB4 Bridge (0.38ms RTT)"| L8["L8: Linux Mini lauburu (10.0.0.8)"]
    end

    subgraph Wired LAN [Tier 1]
    GW <-->|"eth2 2.5G WAN (12ms)"| NBN
    GW <-->|"1000baseT LAN Port 1"| L1
    GW <-->|"1000baseT LAN Port 2"| L4["L4: Linux Tablet (.116)"]
    end

    subgraph Wireless & Overlay [Tier 2]
    GW -.->|"Wi-Fi 7 / Tailscale"| L5["L5: MacBook Air M4 (.248)"]
    GW -.->|"Wi-Fi 7 / Tailscale"| L6["L6: Pixel 10 Pro XL (.213)"]
    GW -.->|"Wi-Fi 5 / Tailscale"| L2["L2: MacBook Pro Intel (.127)"]
    GW -.->|"Wi-Fi / Tailscale"| L3["L3: Linux Head Node (.225)"]
    GW -.->|"USB ADB / Wi-Fi"| L7["L7: Samsung S20+ (.157)"]
    end

    subgraph Control Plane [Layer 0: Bluetooth Graph]
    L1 -.-|"Bluetooth Serial / WoL"| L2
    L1 -.-|"Bluetooth Serial (-28 dBm)"| L3
    L1 -.-|"BLE GATT 512Hz ECG"| MOVESENSE["Movesense Medical Sensor"]
    end
```
