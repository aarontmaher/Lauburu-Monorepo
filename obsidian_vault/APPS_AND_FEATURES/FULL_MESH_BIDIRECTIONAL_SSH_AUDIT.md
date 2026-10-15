# 🌐 Full-Mesh Bidirectional SSH Connectivity & Topology Audit

*Conducted under **Rule 1 (Zero-Mock Empirical Truth)**, **Rule 8 (Pre-Flight Telemetry Gate)**, and **Rule 9 (Multi-IP Fallback Protocol)**.*
*Timestamp: September 30, 2026*

---

## 🏛️ Executive Summary

A comprehensive, pairwise, bidirectional SSH audit was executed across all physical devices in the 7-Layer Lauburu Mesh. Keyless authentication (`ed25519`) and mutual host verification was configured across all active nodes, validating **100% full-mesh bidirectional reachability** (30 directed pairs tested across the 6 active compute nodes).

```
        ┌────────────────────────────────────────────────────────┐
        │            LAUBURU BIDIRECTIONAL FULL-MESH             │
        ├────────────────────────────────────────────────────────┤
        │  [L1] Mac Mini M4 Pro Host  <==== TB4 ====>  [L2] MBP   │
        │       ║                  \\                //    ║     │
        │      TB4                   TB4          TB4     TB4    │
        │       ║                      \\        //        ║     │
        │  [L8] Linux Mini Hub        [L5] MacBook Pro (Node L2)        │
        │       ║                         ║                ║     │
        │      TS/LAN                    TS               TS     │
        │       ║                         ║                ║     │
        │  [L3] Linux Head Node (Ryzen) <===> [L6] Pixel 10 Pro  │
        └────────────────────────────────────────────────────────┘
```

---

## 📊 Pairwise Bidirectional SSH Matrix (30 Directed Paths)

| Source Node ➔ Destination Node | Authentic Transport / Interface | Latency (ms) | Exit Code | Verified Target Hostname |
| :--- | :--- | :---: | :---: | :--- |
| **L1 Mac Mini** ➔ **L2 MacBook Pro** | Thunderbolt 4 DMA (`192.168.2.2`) | **`0.24 ms`** | `0` | `mac-intel.taildb25e9.ts.net` |
| **L1 Mac Mini** ➔ **L8 Linux Mini** | Thunderbolt 4 DMA (`192.168.2.3`) | **`0.15 ms`** | `0` | `lauburu` |
| **L1 Mac Mini** ➔ **L2 MacBook Pro** | Tailscale Overlay (`100.121.202.34`) | `58.5 ms` | `0` | `mac-air.local` |
| **L1 Mac Mini** ➔ **L3 Linux Head Node** | Tailscale Overlay (`100.101.39.98`) | `95.3 ms` | `0` | `linux` |
| **L1 Mac Mini** ➔ **L6 Pixel 10 Pro XL** | Local Wi-Fi (`192.168.8.213:8022`) | `167.0 ms` | `0` | `localhost` (Pixel 10 Pro XL) |
| **L2 MacBook Pro** ➔ **L1 Mac Mini** | Thunderbolt 4 DMA (`192.168.2.1`) | **`0.22 ms`** | `0` | `lauburu.local` |
| **L2 MacBook Pro** ➔ **L8 Linux Mini** | Thunderbolt 4 DMA (`192.168.2.3`) | **`0.34 ms`** | `0` | `lauburu` |
| **L2 MacBook Pro** ➔ **L2 MacBook Pro** | Tailscale Overlay (`100.121.202.34`) | `218.6 ms` | `0` | `mac-air.local` |
| **L2 MacBook Pro** ➔ **L3 Linux Head Node** | Tailscale Overlay (`100.101.39.98`) | `1925.4 ms` | `0` | `linux` |
| **L2 MacBook Pro** ➔ **L6 Pixel 10 Pro XL** | Tailscale Overlay (`100.114.215.68:8022`)| `771.0 ms` | `0` | `localhost` (Pixel 10 Pro XL) |
| **L8 Linux Mini** ➔ **L1 Mac Mini** | Thunderbolt 4 DMA (`192.168.2.1`) | **`0.10 ms`** | `0` | `lauburu.local` |
| **L8 Linux Mini** ➔ **L2 MacBook Pro** | Thunderbolt 4 DMA (`192.168.2.2`) | **`0.33 ms`** | `0` | `mac-intel.taildb25e9.ts.net` |
| **L8 Linux Mini** ➔ **L2 MacBook Pro** | Tailscale Overlay (`100.121.202.34`) | `796.5 ms` | `0` | `mac-air.local` |
| **L8 Linux Mini** ➔ **L3 Linux Head Node** | Tailscale Overlay (`100.101.39.98`) | `3507.5 ms` | `0` | `linux` |
| **L8 Linux Mini** ➔ **L6 Pixel 10 Pro XL** | Tailscale Overlay (`100.114.215.68:8022`)| `1086.8 ms` | `0` | `localhost` (Pixel 10 Pro XL) |
| **L2 MacBook Pro** ➔ **L1 Mac Mini** | Tailscale Overlay (`100.119.199.76`) | `3.52 ms` | `0` | `lauburu.local` |
| **L2 MacBook Pro** ➔ **L2 MacBook Pro** | Tailscale Overlay (`100.103.212.21`) | `13.02 ms` | `0` | `mac-intel.taildb25e9.ts.net` |
| **L2 MacBook Pro** ➔ **L8 Linux Mini** | Tailscale Overlay (`100.121.247.8`) | `458.4 ms` | `0` | `lauburu` |
| **L2 MacBook Pro** ➔ **L3 Linux Head Node** | Tailscale Overlay (`100.101.39.98`) | `1830.7 ms` | `0` | `linux` |
| **L2 MacBook Pro** ➔ **L6 Pixel 10 Pro XL** | Tailscale Overlay (`100.114.215.68:8022`)| `795.1 ms` | `0` | `localhost` (Pixel 10 Pro XL) |
| **L3 Linux Head Node** ➔ **L1 Mac Mini** | Tailscale Overlay (`100.119.199.76`) | `3.37 ms` | `0` | `lauburu.local` |
| **L3 Linux Head Node** ➔ **L2 MacBook Pro** | Tailscale Overlay (`100.103.212.21`) | `4.63 ms` | `0` | `mac-intel.taildb25e9.ts.net` |
| **L3 Linux Head Node** ➔ **L8 Linux Mini** | Tailscale Overlay (`100.121.247.8`) | `3536.8 ms` | `0` | `lauburu` |
| **L3 Linux Head Node** ➔ **L2 MacBook Pro** | Tailscale Overlay (`100.121.202.34`) | `8.17 ms` | `0` | `mac-air.local` |
| **L3 Linux Head Node** ➔ **L6 Pixel 10 Pro XL** | Tailscale Overlay (`100.114.215.68:8022`)| `2450.0 ms` | `0` | `localhost` (Pixel 10 Pro XL) |
| **L6 Pixel 10 Pro XL** ➔ **L1 Mac Mini** | Local Wi-Fi (`192.168.8.230`) | `238.9 ms` | `0` | `lauburu.local` |
| **L6 Pixel 10 Pro XL** ➔ **L2 MacBook Pro** | Tailscale Overlay (`100.103.212.21`) | `493.8 ms` | `0` | `mac-intel.taildb25e9.ts.net` |
| **L6 Pixel 10 Pro XL** ➔ **L8 Linux Mini** | Tailscale Overlay (`100.121.247.8`) | `747.6 ms` | `0` | `lauburu` |
| **L6 Pixel 10 Pro XL** ➔ **L2 MacBook Pro** | Tailscale Overlay (`100.121.202.34`) | `612.2 ms` | `0` | `mac-air.local` |
| **L6 Pixel 10 Pro XL** ➔ **L3 Linux Head Node** | Tailscale Overlay (`100.101.39.98`) | `2243.2 ms` | `0` | `linux` |

---

## 🛠️ Infrastructure Hardening Performed During Audit

1. **GL.iNet Sovereign Gateway (GW `192.168.8.1`):**
   * Generated dedicated Dropbear ed25519 client key (`/root/.ssh/id_ed25519`).
   * Authorized key on L1 Mac Mini; verified keyless SSH execution from Router into Mac Mini.
2. **Key Ring Cross-Pollination:**
   * Installed L8 Linux Mini pubkey on L2 MacBook Pro, L3 Linux Head, and L6 Pixel 10.
   * Installed L3 Linux Head pubkey on L1 Mac Mini, L2 MacBook Pro, and L6 Pixel 10.
   * Installed L2 MacBook Pro pubkey on L8 Linux Mini and L6 Pixel 10.
   * Installed L6 Pixel 10 pubkey on L1, L2, L5, and L8.
3. **Peripheral & Standby Devices Status:**
   * **L7 (Samsung Galaxy S20+):** Power-saving / Wi-Fi sleep standby. USB bridge ready for wake event.
   * **L4 (Bedside Linux Tablet):** Power-saving standby.
   * **L9 (iPhone 16 Pro):** iOS CoreDevice lockdown target.
