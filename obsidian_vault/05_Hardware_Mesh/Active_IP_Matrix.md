---
title: "Lauburu Mesh: Canonical Active IP Matrix & Transport Topology"
tags: [network, mesh, transport, tailscale, ip_table, obsidian_canonical]
updated: "2026-09-08T09:51:50+10:00"
total_nodes: 8
active_overlay_nodes: 8
truth_audited: true
audit_swarm_verified: "2026-09-08"
audit_swarm_engine: "local_llamacpp_rpc+cloud_frontier"
mesh_topology_version: "8-node-verified"
canonical_source: true
---

# 🌐 Canonical Mesh Topology & Active IP Table

| Layer | Node Alias | Hostname | Tailscale IP | LAN IP | Direct / Fallback IP | Port | Protocol / User | Status & Telemetry |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GW** | `router` | `gl-mt3600be` | `100.122.185.123` | `192.168.8.1` | USB: `Lauburu-Router-BT` (hci0 `8C:86:DD:00:26:41`) | 22 | OpenSSH (`root`) | 🟢 Active (Bluetooth 5.1 SPP/RFCOMM Gateway, RTT 2.7ms) |
| **L1** | `mac-mini` | `aarons-mac-mini` | `100.119.199.76` | `192.168.8.155` | TB4: `169.254.224.29` | 22 | OpenSSH (`aaron`) | 🟢 Active (Host Sanctuary Preserved, BT Terminal Port 4005) |
| **L2** | `macbook-pro` | `aarons-macbook-pro` | `100.103.212.21` | `192.168.8.128` | TB4: `169.254.187.138` | 22 | OpenSSH (`aaronmaher`) | 🟢 Active (SSH Verified, RTT 6.25ms) |
| **L3** | `linux` | `linux-1` | `100.101.39.98` | `192.168.8.224` | - | 22 | OpenSSH (`linux`) | 🟢 Active (SSH Verified, Kernel 7.0.0, RTT 7.20ms) |
| **L4** | `linux-tablet`| `desktop-q4si00p` | `100.81.92.125` (needs login) | `192.168.8.173` | - | 22 | OpenSSH (`aaron`) | 🟢 Active (Debian 13, RTT 4.6ms, SSH Verified) |
| **L5** | `macbook-air` | `macbook-1` | `100.121.202.34` | `192.168.8.222` | - | 22 | OpenSSH (`aaronmaher`) | 🟢 Active (Direct Tailscale & LAN RTT 4.9ms, Port 22 Open) |
| **L6** | `pixel` | `pixel-10-pro-xl` | `100.73.38.87` | `192.168.8.145` | Wireless ADB: `192.168.8.145:5555` / `100.73.38.87:5555` | 8022 / 5555 | Termux / PRoot AGY / Shizuku | 🟢 Active (Wireless ADB & Shizuku Server PID 14947 Active, Doze Whitelisted, RTT 3.1ms) |
| **L7** | `s20` | `aarons-s20-1` | `100.84.40.95` | `192.168.8.135` | Wireless ADB: `192.168.8.135:5555` / `100.84.40.95:5555` | 8022 / 5555 | Termux / ADB Shell / Shizuku | 🟢 Active (Wireless ADB & Shizuku Linked, Doze Whitelisted, RTT 7.0ms) |

---

## ⚡ Thunderbolt 4 PCIe DMA Bridge (`bridge0`)
- **Status:** ACTIVE
- **Host Link-Local IP:** `169.254.224.29`
- **Peer Slices:** MacBook Pro M1 Max (`169.254.187.138`), sub-millisecond tensor transport.
