---
title: "TP-Link & GL.iNet Router Master Configuration Guide"
date: "2026-09-02"
tags: [lauburu, router_settings, tplink, vx230v, glinet, openwrt, dhcp, mesh_topology, mac_air]
---

# 🌐 TP-Link & GL.iNet Router Master Configuration Guide

## 🏛️ 1. Executive Summary & Architecture Consensus

This canonical specification resolves the **TP-Link VX230v AX1800** and **GL.iNet GL-MT3600BE** routing, switching, and Wi-Fi configuration across the **7-Layer Lauburu Mesh Ecosystem**.

Based on empirical benchmarks and the **Tri-Orchestrator AI Debate Consensus** (`[[NBN_AND_MESH_TOPOLOGY_AI_DEBATE_ANALYSIS]]`), the network operates in a **Single Flat Subnet (`192.168.8.0/24`)**:
* **GL.iNet GL-MT3600BE** (`192.168.8.1`, Tailscale `100.122.185.123`): **Primary OpenWrt Master Gateway**, WAN routing, DHCP Server, AdGuard Home DNS, Tailscale Subnet Router.
* **TP-Link VX230v AX1800** (`192.168.8.2`): **Access Point (AP) / 4-Port 1Gbps Switch**, DHCP **DISABLED**, Wi-Fi 6 AX high-power coverage.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CANONICAL TOPOLOGY WIRING                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  [Arris CM3500 NBN DOCSIS 3.1 Modem]                                        │
│         │ (Ethernet cable into 2.5G/1G WAN port eth0)                       │
│         ▼                                                                   │
│  [GL.iNet GL-MT3600BE Gateway] (192.168.8.1 / OpenWrt DHCP Master)          │
│         │ (Ethernet cable from GL.iNet LAN port eth1)                       │
│         ▼                                                                   │
│  [TP-Link VX230v LAN 1] (Access Point Mode / DHCP Off / IP 192.168.8.2)     │
│         ├── LAN 2 ──(1Gbps Eth)──> [Linux Head Node (192.168.8.224)]       │
│         ├── LAN 3 ──(1Gbps Eth)──> [Mac Mini Host L1 (192.168.8.230)]      │
│         ├── LAN 4 ──(1Gbps Eth)──> [MacBook Pro L2 (192.168.8.127)]        │
│         └── 5GHz High-Power AX ──> [MacBook Air L5, Pixels, S20/S22]        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 💻 2. Mac Air Antigravity Chats & Role Analysis

From deep trajectory analysis across the Antigravity session transcripts and slash commands (`/goal`, `/boost`, `/loop`, `/ai-debate`):

1. **Hardware Isolation Policy:**
   - **Layer 5 (MacBook Air M4, `192.168.8.222` / `100.93.158.96`):** Dedicated manual AI execution node and UI/UX testing ground.
   - All interactive Chrome browsing, Lens visual auditing, and manual AI tasks are routed to **MacBook Air** and **Samsung S20** to ensure the Mac Mini Host (`Mac_Node`, `192.168.8.230`) remains unblocked for high-throughput orchestration and governance.
2. **Local AI Model Hosting on Mac Air:**
   - Runs local Apple Silicon Metal GPU inference (Qwen-VL, MLX LoRA distillation) and hosts web dashboards / JupyterLab notebooks at `http://100.93.158.96:8890` (and port `8889` / `8866`).
3. **Storage & Headroom:**
   - Cleared and verified for synchronous MLX LoRA weight hot-swapping under `/loop`.

---

## ⚙️ 3. TP-Link VX230v Step-by-Step Configuration Settings (`http://tplinkmodem.net/`)

When accessing the TP-Link VX230v administration interface (`http://tplinkmodem.net` or `http://192.168.8.2` / factory `http://192.168.1.1`):

### 3.0 Domain Access & Redirect Mechanism (`http://tplinkmodem.net/`)
* **How It Works:** The URL `http://tplinkmodem.net/` is the factory DNS intercept domain embedded in TP-Link DSL/VDSL/Ethernet routers.
* **Direct Access:** Connect an Ethernet cable from your computer (e.g. MacBook Air or Mac Mini) directly to **LAN Port 1** of the TP-Link VX230v (or connect to factory Wi-Fi `TP-Link_XXXX`), then navigate to `http://tplinkmodem.net/`.
* **Static Access (Post-Setup):** Once configured, the management interface is accessible directly at `http://192.168.8.2` within the flat mesh subnet.

### 3.1 Operation Mode
* Navigate to **Advanced $\to$ Operation Mode** (or **Quick Setup**).
* Select: **Access Point (AP) Mode** (or Bridge Mode).
* *Effect:* Automatically disables NAT, firewall routing, and WAN routing, turning the device into a high-performance Layer 2 switch and Wi-Fi 6 AP.

### 3.2 LAN TCP/IP Settings
* Navigate to **Advanced $\to$ Network $\to$ LAN**.
* **IP Address:** `192.168.8.2` (or `192.168.8.254`)
* **Subnet Mask:** `255.255.255.0`
* **Default Gateway:** `192.168.8.1`
* **Primary DNS:** `192.168.8.1` (GL.iNet AdGuard Home)
* **Secondary DNS:** `1.1.1.1` (Cloudflare DNS)

### 3.3 DHCP Server (CRITICAL)
* Navigate to **Advanced $\to$ Network $\to$ DHCP Server**.
* **DHCP Server:** **DISABLED / OFF** (Checkbox unchecked).
* *Rationale:* Prevents DHCP collision, IP address duplication, and split-brain subnet routing.

### 3.4 Wireless Wi-Fi 6 (AX) Settings
* Navigate to **Wireless $\to$ Wireless Settings**:
  * **2.4 GHz Band:**
    * **Network Name (SSID):** `GL-MT3600BE-a0f`
    * **Security:** WPA2/WPA3-Personal (Mixed)
    * **Password:** `goldfighting1`
    * **Channel:** Auto (or fix to Channel 1, 6, or 11 away from GL.iNet)
    * **Channel Width:** 20/40 MHz
  * **5 GHz Band:**
    * **Network Name (SSID):** `GL-MT3600BE-a0f` (or `GL-MT3600BE-a0f-MLO`)
    * **Security:** WPA2/WPA3-Personal (Mixed)
    * **Password:** `goldfighting1`
    * **Channel:** 149, 153, 157, or 161 (Non-overlapping with GL.iNet channel 36-48)
    * **Channel Width:** 80 MHz / 160 MHz (Wi-Fi 6 AX enabled)
  * **Advanced Wireless Features:**
    * **802.11k/v Fast Roaming:** **Enabled**
    * **OFDMA / MU-MIMO:** **Enabled**
    * **Beamforming:** **Enabled**

---

## 🛡️ 4. GL.iNet Core Gateway (GL-MT3600BE) Configuration

The GL.iNet router hosts OpenWrt and manages all static IP allocations:

### 4.1 Master Static DHCP Reservations Matrix

| Node / Device | Hardware Layer | MAC Address | Canonical IP | Interface / Role |
| :--- | :--- | :--- | :--- | :--- |
| **GL.iNet Gateway** | `GW` | `94:83:c4:d3:4a:10` | `192.168.8.1` | Core Router & Subnet Gateway |
| **TP-Link VX230v** | `AP/SW` | *Configured Static* | `192.168.8.2` | Wi-Fi 6 AP & 4x GbE Switch |
| **Mac Mini M4 Pro** | `L1 (Eth)` | `1c:f6:4c:7d:d7:0a` | `192.168.8.230` | Host & Memory Governor |
| **Mac Mini M4 Pro** | `L1 (Wi-Fi)` | `1c:f6:4c:7c:dc:5f` | `192.168.8.155` | Secondary Wi-Fi Link |
| **MacBook Pro M4** | `L2` | `36:7e:4d:07:b2:c0` | `192.168.8.127` | Metal GPU RPC & Storage |
| **Linux Head Node** | `L3 (Eth)` | `00:e0:4c:68:03:c8` | `192.168.8.224` | Gateway Ingress & Compute |
| **Linux Head Node** | `L3 (WoL)` | `00:41:0e:14:28:43` | `192.168.8.224` | Wake-on-LAN Hardware NIC |
| **MacBook Air M4** | `L5` | `66:74:75:d8:16:fb` | `192.168.8.222` | Manual AI & UI/UX Specialist |
| **Pixel 10 Pro XL** | `L6` | `66:00:88:ca:e8:3b` | `192.168.8.145` | Vision Stream & Edge TPU |
| **Samsung S20** | `L7` | `0a:8f:1b:f1:c8:17` | `192.168.8.214` | Automated UI/UX Tester |
| **TP-Link Extender** | `EXT` | `98:fc:84:e6:e2:12` | `192.168.8.116` | Layer 2 Client Bridge |

### 4.2 Dynamic DHCP Pool
* **Start:** `192.168.8.100`
* **Limit:** `150` (Pool: `.100` – `.200`)
* **Lease Time:** `12h`

---

## 🛠️ 5. Automation & Self-Healing Tooling

The configuration is synchronized and verified via automated monorepo scripts:

```bash
# 1. Autonomous TP-Link Setup, Discovery & Verification Suite
python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/autotplink_setup.py

# 2. Live HTTP Endpoint & Subnet Diagnostic Optimizer
python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/tplink_modem_optimizer.py

# 3. Apply canonical DHCP reservations and verify mesh ping RTT
python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/configure_mesh_router_topology.py

# 4. Run real-hardware router RAM and daemon governance
python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/hybrid_router_mesh_governor.py

# 5. Run full network system settings benchmark
python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/system_settings_optimizer.py --benchmark
```

---
[[CANONICAL_PROJECT_AND_STORAGE_RULE]] | [[NBN_AND_MESH_TOPOLOGY_AI_DEBATE_ANALYSIS]] | [[Index]]
