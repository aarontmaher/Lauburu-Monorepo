---
title: "Lauburu Cable Analyzer: Reconnect via Bluetooth Protocol & All-Laptop / Mac Mini Wake Engine"
tags: [lauburu, bluetooth, reconnect, mesh, cable_analyzer, zero_mock, wol, adb, blueutil, all_laptops, mac_mini, port4005, port4007]
date: 2026-09-09
status: ACTIVE_PRODUCTION
---

# 📲 Lauburu Cable Analyzer: Reconnect via Bluetooth Protocol & All-Laptop / Mac Mini Wake Engine

## 🏛️ 1. Executive Summary & Full-Mesh Wake Architecture

The **Reconnect via Bluetooth** subsystem is an authentic, zero-mock hardware actuation feature embedded into the **Lauburu Cable & Mesh Analyzer** (Port 4007). It bridges user interactions from the web dashboard directly to the **Bluetooth Serial Terminal Daemon** on Port 4005 (`06_scripts_and_tooling/bluetooth_serial_terminal_daemon.py`), initiating a 3-tier cascade to restore degraded or standby mesh links across the entire physical mesh.

Crucially, **Stage 1 (Bluetooth Proximity Wake)** is not restricted to mobile nodes; it explicitly targets **ALL the laptops and the Mac Mini host too**, executing parallel connection pulses via CoreBluetooth / `blueutil`:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 3-STAGE CASCADING MESH RECONNECT PIPELINE                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ STAGE 1: BLUETOOTH PROXIMITY WAKE (CoreBluetooth / RFCOMM / blueutil)       │
│   • Actuates native Darwin Bluetooth radio across ALL LAPTOPS & MAC MINI:   │
│     - Mac Mini M4 Pro (L1 Host): Controller Self-Affirmation (blueutil     │
│       --power 1) & PCIe radio beacon (1c-f6-4c-81-0b-28)                   │
│     - MacBook Pro M4 (L2 Laptop): 2c-ca-16-08-c0-27 (Metal GPU & SSD Vault)│
│     - Linux Head Node (L3 Laptop): 00-41-0e-14-28-44 (AMD Ryzen 7 5700U)   │
│     - MacBook Air M4 (L5 Laptop): dc-29-55-d6-fc-0b (Secondary Metal Node) │
│     - Pixel 10 Pro XL (L6 Mobile): 30-e0-44-6d-18-ec (Tensor G5 Edge TPU)  │
│     - Samsung S20+ (L7 Mobile): 5c-cb-99-05-81-41 (ADB UI Test Target)     │
│     - Movesense 512Hz ECG Sensor: GATT BLE proximity reconnection          │
├─────────────────────────────────────────────────────────────────────────────┤
│ STAGE 2: WAKE-ON-LAN LAYER 2 ETHERNET BROADCAST (UDP Port 9 / Port 7)       │
│   • Dispatches 06_scripts_and_tooling/mesh/canonical_network_resurrection_engine.py magic packets to: │
│     - MacBook Pro M4 (L2) - a4:83:e7:d1:7c:82 (10Gbps TB4 Bridge)          │
│     - Linux Head Node (L3) - 00:41:0e:14:28:43 (Ryzen Compute Hub)         │
│     - MacBook Air M4 (L5) - 66:74:75:d8:16:fb (Metal Worker)               │
│     - Host Mac Mini (L1) - 1c:f6:4c:7d:d7:0a (Host Node)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ STAGE 3: ADB KEEPALIVE & DISPLAY WAKE INJECTION (USB + Wi-Fi ADB)           │
│   • Executes Android Debug Bridge wake sequence:                            │
│     - adb shell input keyevent 224 (KEYCODE_WAKEUP)                         │
│     - adb shell termux-wake-lock (Doze mode bypass for 24/7 workers)        │
│     - Dynamic port verification across L6 (:42601) and L7 USB serial        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ 2. High-Speed Parallel Execution Matrix

To prevent sequential connection timeout bottlenecks (which would require 12+ seconds sequentially), Stage 1 executes all peer proximity pulses concurrently using Python `concurrent.futures.ThreadPoolExecutor(max_workers=5)`:

| Device | Mesh Layer | Hardware Type | Bluetooth MAC | Proximity Wake Protocol | Live Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Mac Mini M4 Pro** | **L1** | Host Desktop | `1c-f6-4c-81-0b-28` | Controller Power Assertion (`blueutil --power 1`) | **CONTROLLER ACTIVE** |
| **MacBook Pro Vault** | **L2** | Laptop Computer | `2c-ca-16-08-c0-27` | CoreBluetooth ACL Pulse (`blueutil --connect`) | **PULSE DISPATCHED** |
| **Linux Head Node** | **L3** | Laptop Computer | `00-41-0e-14-28-44` | BNEP / RFCOMM Connect (`blueutil --connect`) | **CONNECTED** (-39 dBm) |
| **MacBook Air M4** | **L5** | Laptop Computer | `dc-29-55-d6-fc-0b` | CoreBluetooth ACL Pulse (`blueutil --connect`) | **PULSE DISPATCHED** |
| **Pixel 10 Pro XL** | **L6** | Mobile Phone | `30-e0-44-6d-18-ec` | GATT ACL Pulse (`blueutil --connect`) | **CONNECTED** (0 dBm) |
| **Samsung Galaxy S20+** | **L7** | Mobile Phone | `5c-cb-99-05-81-41` | GATT ACL Pulse (`blueutil --connect`) | **CONNECTED** (0 dBm) |

---

## 💻 3. API Endpoints & Backend Implementation

### 3.1 Backend Probe: `backend/probes/bt_terminal_probe.py`
- **Function:** `reconnect_via_bluetooth() -> Dict[str, Any]`
- **Parser:** `parse_bluetooth_wake_events(raw_output)` extracts structured telemetry for all laptops and the Mac Mini.
- **Payload Structure:**
```json
{
  "status": "reconnection_completed",
  "command": "reconnect",
  "duration_ms": 7614.55,
  "bluetooth_wake_events": [
    {
      "device": "Host Mac Mini M4 Pro (L1)",
      "mac": "1c-f6-4c-81-0b-28",
      "status": "CONTROLLER ACTIVE (Power: ON)",
      "tier": "Line 1 Bluetooth Controller"
    },
    {
      "device": "MacBook Pro Vault (L2 Laptop)",
      "mac": "2c-ca-16-08-c0-27",
      "status": "PULSE DISPATCHED",
      "tier": "Line 1 Bluetooth Proximity Wake"
    },
    {
      "device": "Linux Head Node (L3 Laptop)",
      "mac": "00-41-0e-14-28-44",
      "status": "CONNECTED",
      "tier": "Line 1 Bluetooth Proximity Wake"
    },
    {
      "device": "MacBook Air M4 (L5 Laptop)",
      "mac": "dc-29-55-d6-fc-0b",
      "status": "PULSE DISPATCHED",
      "tier": "Line 1 Bluetooth Proximity Wake"
    },
    {
      "device": "Pixel 10 Pro XL (L6 Mobile)",
      "mac": "30-e0-44-6d-18-ec",
      "status": "CONNECTED",
      "tier": "Line 1 Bluetooth Proximity Wake"
    },
    {
      "device": "Samsung Galaxy S20+ (L7 Mobile)",
      "mac": "5c-cb-99-05-81-41",
      "status": "CONNECTED",
      "tier": "Line 1 Bluetooth Proximity Wake"
    }
  ],
  "reconnected_devices": [
    {"device_name": "Mac Mini M4 Pro (L1)", "connected_via": "192.168.8.155 | 100.119.199.76"},
    {"device_name": "Linux Head Node (L3)", "connected_via": "100.101.39.98 | 192.168.8.224"}
  ]
}
```

### 3.2 Server Endpoints: `backend/server.py`
- `POST /api/bluetooth/reconnect` & `GET /api/bluetooth/reconnect`
- Invalidates topology cache (`force=True`) and re-probes dynamic IPs (`find_dynamic_mesh_ips(force=True)`).
- Returns the complete wake event ledger with all laptops, Mac Mini, and active cables.

---

## 🖥️ 4. Frontend Controls & User Interaction

1. **Header Action Bar:**
   - Dedicated button: `<button class="btn btn-bluetooth" id="btn-reconnect-bt" title="Line 1 Bluetooth Proximity Wake across all laptops (MBP L2, Linux L3, MBA L5), Mac Mini (L1 Host), and mobile mesh">`
   - Real-time loading indicator: `⏳ Reconnecting...` during parallel wake execution.
2. **Terminal Tab Quick Actions (`📟 BT Terminal`):**
   - Quick action bar:
     - `📲 Reconnect via Bluetooth` (with tooltip documenting all laptops & Mac Mini)
     - `📊 Status`
     - `⚡ Telemetry`
     - `🧹 Clear`
   - Terminal window auto-scrolls to display the full wake cascade log.

---

## 🛡️ 5. Empirical Tri-Proof Verification Gate (Rule #1 & #5)

### Proof 1: Actuation & Test Suite Pass
- Automated Test Suite: `pytest tests/test_probes.py`
- Result: **`9 passed in 17.40s (Exit Code 0)`**
- Tested:
  - `test_cable_probe_fields_and_integrity()`
  - `test_local_macos_ram_and_ane()`
  - `test_all_devices_ram_npu_aggregation()`
  - `test_speed_probe_throughput_and_latencies()`
  - `test_bluetooth_terminal_and_local_ai()`
  - `test_full_mesh_topology_assembly()`
  - `test_neo_bridge_recommendations()`
  - `test_dynamic_ip_finder()`
  - `test_bluetooth_reconnect()` (asserts wake events for all laptops & Mac Mini)

### Proof 2: Line-by-Line Cryptographic SHA256 Checksums
| Component | File Path | SHA256 Checksum |
| :--- | :--- | :--- |
| **BT Terminal Daemon** | `06_scripts_and_tooling/bluetooth_serial_terminal_daemon.py` | `a9e4c1dd2178d09b4b7a8f0ba5802c9478c9fdc6342037eec7e465fc7e02cb8f` |
| **WoL Manager** | `06_scripts_and_tooling/mesh/canonical_network_resurrection_engine.py` | `2a4632151efbcdf1a64a501dede0c0520cc710bb924aefd461617bb849fb119b` |
| **BT Network Healer** | `06_scripts_and_tooling/canonical_network_resurrection_engine.py` | `c8d5e88036b76c988ecb63551110bd022c9bfe9964b95835402a6b48cf9fcdd4` |
| **Neo Autonomous Healer** | `06_scripts_and_tooling/automation/neo_autonomous_mesh_healer.py` | `647e156cbc6467c820d2ed1d56c3d19f98da9c49c9f993f6fa3e0184936d3f24` |
| **BT Terminal Probe** | `01_apps/lauburu_cable_analyzer/backend/probes/bt_terminal_probe.py` | `03ec5bc098220f83ba5a39ae8c7f327c1f2dab197da891e0d4f414150cd4d5d6` |
| **Frontend HTML** | `01_apps/lauburu_cable_analyzer/frontend/index.html` | `3fcc3dba99cf736e1554591e3541718b7410c350b88970ae620863bfde933f4b` |
| **Frontend JS** | `01_apps/lauburu_cable_analyzer/frontend/app.js` | `6098f15dd1097776e63f36059e2836c6f2ade02dc1dbe6519b2beda2343f7f45` |
| **Pytest Suite** | `01_apps/lauburu_cable_analyzer/tests/test_probes.py` | `09e291f8c841fdbf49087c92032765d9d98f433023c921b1987836d229b1b064` |
| **Visual Artifact** | `lauburu_all_laptops_mac_mini_bluetooth_wake_verified.png` | `dbde868d7750fa3322ce03164de69b3a94ea577fa3fb6d0454ce584ccf611abf` |

### Proof 3: Visual Verification
- Verified via Chrome DevTools MCP screen capture:
  - File: `lauburu_all_laptops_mac_mini_bluetooth_wake_verified.png`
  - SHA256: `dbde868d7750fa3322ce03164de69b3a94ea577fa3fb6d0454ce584ccf611abf`
  - Verified UI elements: Header button title, active BT Terminal stream, dynamic nodes graph with active links to all laptops and Mac Mini.

---

## 🔗 Related Wikilinks
- [[LAUBURU_CABLE_MESH_ANALYZER_ARCHITECTURE]]
- [[DYNAMIC_IP_FINDER_NETWORK_CABLES]]
- [[BLUETOOTH_KEYRING_OMNITERMINAL_INTEGRATION_VERIFIED]]
- [[SOVEREIGN_BLUETOOTH_TERMINAL_IDE_2026]]
- [[Index]]
