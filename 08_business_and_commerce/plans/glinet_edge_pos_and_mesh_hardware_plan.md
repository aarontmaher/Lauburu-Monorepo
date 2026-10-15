# 🌐 GL.iNet Edge POS Gateway & Hardware Mesh Infrastructure Plan

**System Subsystem:** `00_core_infrastructure/network/glinet_pos_gateway`  
**Target Hardware:** GL.iNet GL-MT3600BE (Wi-Fi 7 Core) / Beryl AX (GL-MT3000 Travel Retail)  
**Operating System:** OpenWrt 24.x (LuCI + Custom Kernel Modules)  
**Primary Architect:** Cloud Frontier Architect (`Opus_Architect`) & Local Network Specialist  

---

## 🏛️ 1. Executive Summary & Retail Objective
GL.iNet routers serve as the physical network foundation of the Lauburu Ecosystem (`192.168.8.1`). Beyond standard routing, this plan turns the GL.iNet router into a **Sovereign Pop-Up Retail & Edge Device Controller**:
1. **Zero-Trust Pop-Up Retail:** Operates an air-gapped, offline-capable Wi-Fi & Ethernet mesh for pop-up gyms, BJJ competitions, and retail stands without relying on commercial venue Wi-Fi.
2. **Hardware USB-over-IP (`usbip`) Bridge:** Exposes the router's physical USB port over the network, allowing L1 Mac Mini and L3 Linux Node to control connected Android edge devices (Pixel 10, Samsung S20) via ADB even when Wi-Fi sleeps or Doze mode activates.
3. **Local Storefront Caching:** Buffers MedusaJS / Shopify POS transactions locally on the router's internal flash/microSD when 4G/5G cell links drop.

---

## ⚙️ 2. Hardware Topology & Electrical Isolation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GL.iNET RETAIL EDGE GATEWAY TOPOLOGY                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. GL.iNet Gateway (`192.168.8.1` / Tailscale `100.122.185.123`)            │
│    • WAN: 5G Mobile Tethering / Venue Ethernet / Wi-Fi Repeater             │
│    • LAN (Subnet 192.168.8.x): Mac Mini (10GbE), POS Terminals, Card Reader │
│    • USB Port: Connected to Powered 4-Port USB Hub (5V/3A)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Powered USB Hub & Edge Device Isolation (Rule #0 Electrical Gate)        │
│    • Port 1: Pixel 10 Pro XL (Tensor G5 Edge TPU Barcode & Vision Scanner) │
│    • Port 2: Samsung Galaxy S20 (Automated POS UI Tester & SMS Dispatch)   │
│    • Port 3: Thermal Receipt Printer (ESC/POS via USB Raw)                  │
│    • Requirement: Must use powered hub; router port alone drops under 2A.   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 3. Software Architecture & OpenWrt Configuration

### A. USB-over-IP (`usbip`) Daemon
Enables remote ADB actuation from L1 Mac Mini without USB cables directly attached to the host:
```bash
# On GL.iNet Router (SSH root@192.168.8.1):
opkg update
opkg install kmod-usbip kmod-usbip-server usbip

# Bind Pixel 10 (Bus 1-1.2):
usbip list -p -l
usbip bind -b 1-1.2
usbipd -D
```
*On Mac Mini Host (L1):* Screen Lens connects to `192.168.8.1:3240` to attach the phone directly to macOS `adb`.

### B. Offline POS Order Buffering Daemon
A lightweight Python/Lua daemon on the router listens on `http://192.168.8.1:8088/api/pos/transact`:
- Stores transactions in SQLite database on USB flash drive (`/mnt/sda1/pos_buffer.db`).
- Synchronizes with MedusaJS v2 on L3 Linux Head Node as soon as upstream cell connection returns.

---

## 💰 4. Bill of Materials (BOM) & Unit Economics

| Item | Model / Specification | Unit Cost (AUD) | Role |
| :--- | :--- | :--- | :--- |
| **Edge Router** | GL.iNet GL-MT3000 (Beryl AX) | $139.00 | Mobile retail router & Tailscale node |
| **Powered USB Hub** | Anker 4-Port USB 3.0 (5V/3A) | $29.95 | Prevents USB power drops on ADB |
| **OTG Host Cable** | Right-Angle USB-C 10Gbps | $14.50 | Phone connection to hub |
| **MicroSD Storage** | SanDisk Extreme 128GB A2 | $28.00 | Local POS offline transaction buffer |
| **Total Hardware Cost** | — | **$211.45 AUD** | Replaces $1,200+ proprietary POS hubs |

---

## 🚀 5. Actionable Implementation Checklist (Pull the Trigger)
- [x] Research OpenWrt `usbip` compatibility on MediaTek MT7981B.
- [ ] Deploy `glinet_usbip_daemon.sh` to `/etc/init.d/usbipd` on GL.iNet router.
- [ ] Connect powered USB hub and verify Pixel 10 ADB enumeration over IP.
- [ ] Test simulated 4G disconnect: verify POS transactions buffer to local SQLite.
