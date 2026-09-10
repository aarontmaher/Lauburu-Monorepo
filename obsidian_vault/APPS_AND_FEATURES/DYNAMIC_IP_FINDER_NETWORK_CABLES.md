---
title: "Lauburu Dynamic IP Finder & Real-Time Mesh Cable Telemetry"
tags: [lauburu, dynamic_ip, network_cables, mesh, zero_mock, tailscale, arp, adb, dhcp]
date: 2026-09-07
status: ACTIVE_PRODUCTION
---

# 🌐 Lauburu Dynamic IP Finder & Real-Time Mesh Cable Telemetry

## 🏛️ 1. Executive Summary & Problem Context
In dynamic multi-device edge networks, IP assignments and debugging ports change automatically across DHCP lease renewals, router reboot cycles, and wireless debugging handshakes:
- **Android Wireless Debugging Ports**: The Pixel 10 Pro XL dynamically shifts listening TCP ports (e.g. rotating from `:36815` to `:42601`).
- **USB vs. TCP Transport Transitions**: Samsung Galaxy S20+ dynamically toggles between USB serial (`R3CN40CJJ1R`) and Wi-Fi ADB.
- **Dynamic DHCP Leases**: The router (`192.168.8.1`) issues renewed IP leases to mobile nodes (e.g. Linux Tablet at `192.168.8.190`, Samsung S20 at `192.168.8.214`).
- **Thunderbolt 4 Bridge Link-Local**: The high-speed 10Gbps TB4 DMA bridge assigns dynamic link-local IPv4 addresses on `bridge0` (`169.254.215.118`).
- **Tailscale WireGuard Mesh**: Peers can authenticate on new overlay addresses (e.g. MacBook Air M4 on `100.121.202.34`, Linux Tablet on `100.118.79.63`).

To eliminate stale hardcoded fallback addresses and maintain continuous 100% authentic telemetry without mock data (Cardinal Rule #0), the **Dynamic IP Finder Engine** was designed and integrated into `01_apps/network_cable_analyzer`.

---

## ⚡ 2. 5-Stage Multi-Source Discovery Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 DYNAMIC IP FINDER HEURISTIC PIPELINE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. KERNEL DARWIN INTERFACES (ifconfig en1, en0, bridge0, utun4)             │
│    • Resolves Host Mac Mini M4 Pro Local IPs and Bridge Subnets             │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. NUMERIC ARP CACHE (arp -an)                                              │
│    • Instant (<2ms) MAC-to-IP resolution without DNS stalls                 │
│    • Identifies bridge0 Link-Local endpoint (169.254.215.118)               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. ROUTER DHCP LEASES (ssh root@192.168.8.1 'cat /tmp/dhcp.leases')         │
│    • Resolves dynamic device hostnames to DHCP IPs and MAC addresses        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. TAILSCALE STATUS JSON (tailscale status --json)                          │
│    • Extracts Tailscale IPs (100.x.y.z), CurAddr endpoints, and Online states│
├─────────────────────────────────────────────────────────────────────────────┤
│ 5. ADB DEVICE TABLE (adb devices -l)                                        │
│    • Resolves USB serials (R3CN40CJJ1R) and dynamic wireless ports (:42601) │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 3. Discovered Live Mesh Matrix (Empirical Proof)

| Layer | Node Name | Dynamic LAN IP | Tailscale IP | TB4 / ADB Target | Discovery Source | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `Mac Mini M4 Pro` | `192.168.8.155` | `100.119.199.76` | TB4: `169.254.195.35` | `kernel_darwin` | **ONLINE** |
| **L2** | `MacBook Pro M4` | `192.168.8.128` | `100.103.212.21` | TB4: `169.254.215.118` | `arp_bridge0` | **ONLINE** |
| **L3** | `Linux Head Node` | `192.168.8.225` | `100.101.39.98` | SSH: `linux` | `tailscale_peer` | **ONLINE** |
| **L4** | `Linux Tablet` | `192.168.8.190` | `100.118.79.63` | SSH: `tablet` | `tailscale_peer` | *STANDBY* |
| **L5** | `MacBook Air M4` | `192.168.8.222` | `100.121.202.34` | TB4: `169.254.187.139`| `tailscale_peer` | *STANDBY* |
| **L6** | `Pixel 10 Pro XL` | `192.168.8.145` | `100.73.38.87` | ADB: `192.168.8.145:42601` | `tailscale_peer` | **ONLINE** |
| **L7** | `Samsung S20+` | `192.168.8.214` | `100.84.40.95` | ADB USB: `R3CN40CJJ1R` | `tailscale_peer` | **ONLINE** |
| **GW** | `GL.iNet Router` | `192.168.8.1` | `100.122.185.123` | SSH: `root@192.168.8.1` | `tailscale_peer` | **ONLINE** |

---

## 🛡️ 4. Performance & Caching Guarantees
- **Lookup Latency**: ~200 ms for full 5-stage synthesis across all 8 nodes.
- **TTL Caching**: 10.0 seconds default TTL preventing CLI process thrashing during 1 Hz SSE streaming.
- **Fail-Safe Fallback**: If a peripheral node is in deep sleep, gracefully displays authentic `--` standby metrics without synthetic numbers.

## 🔗 Related Knowledge Links
- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
