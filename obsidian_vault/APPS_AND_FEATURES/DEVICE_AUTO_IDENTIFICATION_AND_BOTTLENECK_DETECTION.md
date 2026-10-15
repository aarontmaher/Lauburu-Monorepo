---
title: "Dynamic Device Auto-Identification, Hardware Capabilities Matrix & Intelligent Bottleneck Detection"
tags: [lauburu, cables, hardware, bottleneck, bluetooth, auto_identification, mesh]
created: 2026-09-10
---

# 🔍 Dynamic Device Auto-Identification, Capabilities & Bottleneck Analysis

## 🏛️ 1. Architecture Overview

The **Lauburu Cable & Mesh Analyzer** on **Port 4007** (`http://localhost:4007`) provides real-time, zero-mock device auto-identification, physical bottleneck diagnostics, and optimal transfer method calculations, anchored permanently to a foundational Bluetooth control-plane link.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│             INTELLIGENT DEVICE AUTO-IDENTIFICATION & BOTTLENECK ENGINE      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. DYNAMIC DEVICE AUTO-IDENTIFICATION                                       │
│    • Darwin System Profiler (`SPThunderboltDataType`): Maps physical socket │
│      receptacles directly to remote node IDs (`Receptacle 3` ➔ MBP L2,      │
│      `Receptacle 1` ➔ MBA L5) without hardcoded port assumptions.           │
│    • OpenWrt dnsmasq Lease Engine: Actively probes IP responsiveness        │
│      (`is_ip_alive()`) to bypass stale DHCP lease collisions.               │
│    • WhatCable E-Marker Decoders: Inspects SOP' VDM cable identity and      │
│      active USB device vendor strings.                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. PERMANENT BLUETOOTH FOUNDATION ANCHOR                                    │
│    • IOBluetooth / RFCOMM / `blueutil`: Anchors every mesh node to its      │
│      Bluetooth MAC address (e.g. S20+ `5c-cb-99-05-81-41`, Linux Head Node  │
│      `00-41-0e-14-28-44`, Host Controller `1c-f6-4c-81-0b-28`).            │
│    • Provides 100% reliable out-of-band proximity, wake, and control plane. │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. HARDWARE CAPABILITIES MATRIX PROFILING                                   │
│    • Evaluates maximum supported PHY speed across all 8 mesh layers:         │
│      - L1 Mac Mini M4 Pro: 80/120 Gbps TB5 / 40 Gbps TB4                   │
│      - L2 Intel MacBook Pro: 40 Gbps TB4 / 10 Gbps USB 3.2 Gen 2               │
│      - L3 Linux Head Node: 1 Gbps Ethernet / Wi-Fi 5                        │
│      - L6 Pixel 10 Pro XL: Wi-Fi 7 MLO (5.8 Gbps) / 10 Gbps USB 3.2 Gen 2   │
│      - L7 Samsung Galaxy S20+: 5.0 Gbps USB 3.2 Gen 1 / 1.2 Gbps Wi-Fi 6    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. INTELLIGENT BOTTLENECK & OPTIMAL TRANSFER CALCULATION                    │
│    • Identifies link speed mismatches: S_negotiated < min(S_dev, S_host)    │
│    • Flags Charge-Only USB 2.0 throttling on SuperSpeed devices.             │
│    • Recommends optimal wireless vs. wired alternative routes + multipliers.│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ 2. Bottleneck Detection Rules & Real-World Findings

### Case Study: Samsung Galaxy S20+ (L7) USB 2.0 Charge Throttling
- **Device Capabilities:** Supports USB 3.2 Gen 1 (5.0 Gbps SuperSpeed) and Wi-Fi 6 (1.2 Gbps).
- **Physical Link State:** Connected via USB-C to `Port-USB-C@2` negotiating at **480 Mbps** (High Speed USB 2.0).
- **Diagnostic Verdict:** `⚠️ WARNING: Charge-Only / USB 2.0 Throttling`.
- **Optimal Transfer Recommendation:** **Wi-Fi 6 (1.2 Gbps)** is **2.5x faster** than the current cable link. For maximum speed, connect a rated USB 3.2 Gen 1 cable (**10.4x faster**).

### Case Study: Intel MacBook Pro (L2) Thunderbolt 4 Peak Throughput
- **Device Capabilities:** Supports 40.0 Gbps Thunderbolt 4 / PCIe Gen 3 Tunneling.
- **Physical Link State:** Negotiated at **40.0 Gbps** via Tankya 240W EPR smart cable on `Port-USB-C@3`.
- **Diagnostic Verdict:** `✅ OPTIMAL: Operating at peak link capacity (PCIe DMA bridge0)`.
- **Latency:** 0.99 ms RTT.

---

## 🔗 3. Canonical Wikilinks
- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[LAUBURU_CABLE_MESH_ANALYZER_ARCHITECTURE]]
- [[LAUBURU_CABLE_ANALYZER_SYSTEM_AUDIT]]
- [[DYNAMIC_IP_FINDER_NETWORK_CABLES]]
- [[BLUETOOTH_RECONNECT_CABLE_ANALYZER]]
