---
title: "Mobile Charging, Device & Network Apps Clean-Room Reverse Engineering & Feature Integration"
tags: [reverse_engineering, mobile_apps, usb_c, battery_charging, ookla_jitter, cpdt_benchmark, tplink_portscan, pixel10, samsung_s20, lauburu_mesh, cable_analyzer]
date: "2026-09-11"
---

# 📱 Mobile Charging, Device & Network Analysis Apps Clean-Room Reverse Engineering

## Executive Overview

In compliance with the **Sovereign Closed-Source Reverse Engineering AI Protocol** and the **Tri-Vault Storage Architecture**, this whitepaper documents the complete clean-room reverse engineering, feature distillation, sandbox extraction, and sovereign deletion of charging, device, and network analysis applications across both mobile nodes in the Lauburu Mesh:
- **Pixel 10 Pro XL (Layer 6)**
- **Samsung Galaxy S20+ (Layer 7)**

All target binaries have been securely backed up in the isolated evolution sandbox, disassembled, analyzed for architectural design patterns, and distilled into production zero-mock probes within the **Lauburu Cable & Mesh Analyzer (`01_apps/network_cable_analyzer` on Port 4007)**. Following empirical verification and user alignment via the `/grill-me` protocol, all non-essential consumer apps have been uninstalled from both phones, recovering hundreds of megabytes while preserving essential developer infrastructure.

---

## 🏛️ Tri-Vault Architectural Linkages
- Master Knowledge Graph: [[Index]]
- Project Rules: [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- Monorepo Deep Index: [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- Cable & Mesh Analyzer: [[LAUBURU_CABLE_MESH_ANALYZER_ARCHITECTURE]]
- WhatCable & Shark Wire Reverse Engineering: [[APPS_AND_FEATURES/REVERSE_ENGINEERING_WHATCABLE_AND_SHARKWIRE]]
- Device Auto-Identification: [[APPS_AND_FEATURES/DEVICE_AUTO_IDENTIFICATION_AND_BOTTLENECK_DETECTION]]

---

## 🔍 Quarantined Sandbox Backups & Deletion Audit Matrix

All APKs were pulled live via ADB into the isolated sandbox quarantine directories:
- Pixel 10 Pro XL: `01_apps/screen_lens/sandbox_evolution/reverse_engineering/mobile_apps/`
- Samsung Galaxy S20+: `01_apps/screen_lens/sandbox_evolution/reverse_engineering/mobile_apps/samsung_s20/`

### 1. Pixel 10 Pro XL (Layer 6)

| Package Identifier | Application Name | APK Size | SHA256 Checksum (Prefix) | Architectural Classification | Device Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `nl.nordicnode.usbctest` | USB-C Test | 7.07 MB | `554fcdf6...` | USB-C Power & Microamp Meter | **Uninstalled (Verified)** |
| `org.zwanoo.android.speedtest` | Ookla Speedtest | 27.21 MB | `4191eb5e...` | Dynamic TCP & Jitter Benchmark | **Uninstalled (Verified)** |
| `com.tplink.networktoolsbox` | TP-Link Network Tools Box | 54.19 MB | `a57311e3...` | Concurrent Port & ARP Discovery | **Uninstalled (Verified)** |
| `com.Saplin.CPDT` | Cross Platform Disk Test | 8.31 MB | `c25bf9d7...` | Cache-Purged Direct Disk/RAM I/O | **Uninstalled (Verified)** |
| `cn.trinea.android.developertools` | Dev Tools (Android) | 10.71 MB | `c698666e...` | Sysprops, Package & HW Inspector | **Uninstalled (Verified)** |
| `no.nordicsemi.android.mcp` | nRF Connect for Mobile | 13.80 MB | `5e15d188...` | BLE GATT / Advertising Dissector | **PRESERVED (Dev Tool)** |
| `com.cac.bluetoothmanager` | Bluetooth Manager | 19.90 MB | `b0f67568...` | Bluetooth Profile & RSSI Monitor | **Uninstalled (Verified)** |
| `moe.zhs.caffeine` | Caffeine | 6.69 MB | `a82a8f58...` | Android WakeLock Governor | **PRESERVED (Dev Tool)** |
| `xyz.goodcloud.glinet` | GL.iNet GoodCloud | 44.90 MB | `4ad409a8...` | Mesh Router Cloud Control | **PRESERVED (Dev Tool)** |
| `com.glinet.kvm` | GL.iNet KVM | 5.77 MB | `52b034c3...` | Hardware KVM Video Streamer | **PRESERVED (Dev Tool)** |
| `com.google.ai.edge.gallery` | AI Edge Gallery | 14.58 MB | `ad5bd025...` | On-Device TFLite / LLM Harness | **Uninstalled (Verified)** |

### 2. Samsung Galaxy S20+ (Layer 7)

| Package Identifier | Application Name | APK Size | SHA256 Checksum (Prefix) | Architectural Classification | Device Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `com.ttec.fastcharging` | Fast Charging | 21.11 MB | `923c0dea...` | Battery Status & Charging Monitor | **Uninstalled (Verified)** |
| `com.wifiset.wifiset` | WiFi Settings | 13.68 MB | `a16b0850...` | WLAN Config & Network Scanner | **Uninstalled (Verified)** |
| `com.sdcard.usbbackup` | SD Card & USB Backup | 33.35 MB | `0eff7dc3...` | Mass Storage Backup / Sync | **Uninstalled (Verified)** |
| `com.cac.bluetoothmanager` | Bluetooth Manager | 19.90 MB | `b0f67568...` | BT Profile & RSSI Analyzer | **Uninstalled (Verified)** |
| `otgconnector...` | OTG Connector & Checker | 16.60 MB | `644d5019...` | USB OTG Host / Device Probe | **Uninstalled (Verified)** |
| `eyalin.mydevicedetailsheb` | My Device Details | 22.82 MB | `a71dfa7e...` | Hardware Sensor & Spec Audit | **Uninstalled (Verified)** |
| `de.kai_morich.serial_bluetooth_terminal` | Serial BT Terminal | 1.68 MB | `cf7aedea...` | Serial RFCOMM / BLE Terminal | **PRESERVED (Core Tool)** |
| `com.vrem.wifianalyzer` | WiFiAnalyzer | 2.65 MB | `4384e4dd...` | Open-Source Wi-Fi RF Spectrum | **PRESERVED (Core Tool)** |

---

## 🛠️ Reverse Engineering Deep Dives & Key Architectural Findings

### 1. USB-C Test & Fast Charging (`nl.nordicnode.usbctest`, `com.ttec.fastcharging`)
- **Mechanism:** Interrogates `android.os.BatteryManager` via `BATTERY_PROPERTY_CURRENT_NOW` (reporting instantaneous microamps $I_{\mu\text{A}}$) and `Intent.ACTION_BATTERY_CHANGED` for `EXTRA_VOLTAGE` ($V_{\text{mV}}$).
- **Extracted Power Formula:**
  $$\text{Current (A)} = \frac{|\text{microamps}|}{1,000,000}$$
  $$\text{Power (W)} = V_{\text{volts}} \times I_{\text{amps}}$$
- **Lauburu Integration:** Implemented in `probe_mobile_battery_charging()` in `network_diagnostics.py`. Polls real-time ADB `/sys/class/power_supply/battery/current_now` and `dumpsys battery`.

### 2. Ookla Speedtest (`org.zwanoo.android.speedtest`)
- **Mechanism:** Implements RFC 3550 interarrival jitter variance over consecutive RTT samples:
  $$J_i = J_{i-1} + \frac{|D(i-1, i)| - J_{i-1}}{16}$$
  where $D(i-1, i) = \text{RTT}_i - \text{RTT}_{i-1}$.
- **Lauburu Integration:** Implemented in `run_ping_test()` in `network_diagnostics.py`. Calculates discrete interarrival jitter variance and empirical packet loss percentages across mesh links.

### 3. TP-Link Network Tools Box (`com.tplink.networktoolsbox`)
- **Mechanism:** Concurrent non-blocking socket connections with configurable millisecond timeout (`SocketChannel.connect()`) across well-known administrative ports.
- **Lauburu Integration:** Implemented in `run_mesh_port_scan()` using Python's `concurrent.futures.ThreadPoolExecutor(max_workers=10)` to scan all 9 canonical mesh services in $\le 50\text{ ms}$.

### 4. Cross Platform Disk Test (`com.Saplin.CPDT`)
- **Mechanism:** Directly tests unbuffered storage throughput by executing synchronous POSIX file flushes (`fsync()`) on random non-compressible byte blocks, deliberately bypassing the OS page cache. Evaluates RAM copy throughput by memory-copying dense byte arrays.
- **Lauburu Integration:** Implemented in `run_storage_memory_benchmark()` in `network_diagnostics.py`. Empirically tests host NVMe sequential write/read throughput via `os.fsync()` and Apple Silicon Unified Memory Architecture (UMA) RAM copy bandwidth (measuring 53.23 GB/s).

---

## 💻 Cable & Mesh Analyzer Production Integration (Port 4007)

All reverse-engineered capabilities have been directly wired into the Cable & Mesh Analyzer web application:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 LAUBURU CABLE & MESH ANALYZER (PORT 4007)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. REST Endpoints (server.py):                                              │
│    • GET /api/diagnostics/ping?host=<ip>&count=4                            │
│    • GET /api/diagnostics/port_scan?host=<ip>                               │
│    • GET /api/diagnostics/benchmark                                         │
│    • GET /api/diagnostics/power_delivery?device=<adb_target>                │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Frontend Diagnostics Suite (index.html & app.js):                        │
│    • "🩺 Diag" Tab in Sidebar                                               │
│    • Real-time ICMP Ping & RFC 3550 Jitter Inspector Card                   │
│    • Mesh Service Port Scanner with millisecond socket latency indicators   │
│    • CPDT Disk & RAM Benchmark Card with UMA bandwidth ratings              │
│    • USB-C Power Delivery & Battery Card (Voltage, Current, Watts, Temp)    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. Automated Verification (tests/test_probes.py):                           │
│    • 16/16 Unit Tests Passing (100% Exit Code 0)                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛡️ Tri-Proof Empirical Verification Gate

1. **Proof 1 (Actuation):**
   - Pixel 10 Pro XL: `adb uninstall` succeeded with Exit Code 0 for 7 packages.
   - Samsung S20+: `adb uninstall` succeeded with Exit Code 0 for 6 packages.
   - Unit tests: `pytest 01_apps/network_cable_analyzer/tests/test_probes.py` exited with 16 passed in 24.10s (Exit Code 0).
2. **Proof 2 (Line-by-Line Inspection & Cryptographic Hashes):**
   - 19 APK binaries quarantined in `sandbox_evolution/reverse_engineering/mobile_apps/` with full SHA256 specs.
   - Zero synthetic mocks in `network_diagnostics.py`.
3. **Proof 3 (Visual Verification):**
   - Live Headless Chrome capture saved to disk:
     `lauburu_cable_analyzer_diagnostics_tab_active.png` (391,178 bytes).
