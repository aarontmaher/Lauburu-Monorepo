---
title: "Speedify Multi-Path Bonding & Tailscale WireGuard Reverse-Engineering Whitepaper"
tags: [speedify, tailscale, wireguard, channel_bonding, reverse_engineering, zero_mock, openwrt]
date: 2026-08-29
---

# ⚡ Speedify Channel Bonding & Tailscale WireGuard Reverse-Engineering

## 1. Native Multi-WAN Channel Bonding Engine (`lauburu_bond`)
### 1.1 Architectural Objectives
- Aggregates Wi-Fi 7 (`wlan0`), 1GbE Ethernet (`eth0`), and USB 5G Tethering (`usb0`) into a unified virtual interface (`bond0`).
- Memory footprint: $<5\text{ MB}$ RAM RSS (vs. 65MB proprietary closed-source daemon).
- Forward Error Correction (FEC): XOR parity packet generation across consecutive stripe bursts.
- Link Estimation: Exponentially Weighted Moving Average (EWMA) of RTT, jitter, and packet loss.

```
       ┌──────────────────────────────────────────────────┐
       │     Application Layer / Raw Socket Streams       │
       └────────────────────────┬─────────────────────────┘
                                │
               ┌────────────────▼────────────────┐
               │    lauburu_bond Bonding Engine  │
               │   • Sequence Tagging (32-bit)   │
               │   • Dynamic Capacity Estimator  │
               │   • FEC XOR Parity Generator    │
               └────┬───────────┬───────────┬────┘
                    │           │           │
           ┌────────▼────┐ ┌────▼───────┐ ┌─▼───────────┐
           │ Wi-Fi 7 WAN │ │  1GbE WAN  │ │ USB 5G WAN  │
           │   (wlan0)   │ │   (eth0)   │ │   (usb0)    │
           └─────────────┘ └────────────┘ └─────────────┘
```

## 2. Kernel WireGuard Mesh Agent (`lauburu_tailscale`)
### 2.1 Architectural Objectives
- Replaces 40MB Go `tailscaled` daemon with lightweight C control agent ($<2\text{ MB}$ RSS).
- Direct interface with Linux Kernel WireGuard module (`wg0` / `ts0`).
- Automated subnet route advertisement and Firewall4 (`fw4`) zone binding.

## 3. Related Knowledge Graph Links
- [[DOM_GLINET_LUCI_DEV_PIPELINE]]
- [[OPENWRT_AST_TAXONOMY]]
- [[Index]]
