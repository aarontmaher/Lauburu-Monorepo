---
title: "Google Pixel 10 Pro XL Movesense Bluetooth Terminal Installation"
tags: [pixel, movesense, bluetooth, terminal, termux, tri_proof]
author: "Aaron (Sovereign Lead) & Antigravity Swarm Orchestrator"
date: "2026-09-13"
---

# 📱 Google Pixel 10 Pro XL Movesense Bluetooth Terminal Installation

- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[MOVESENSE_DONGLE_HANDOVER_E2E_SPEC]]
- [[AUTONOMOUS_HEADLESS_MESH_WORKER_SPEC]]

---

## 1. Executive Summary

The **Movesense Connected Bluetooth Terminal** has been installed, configured, and verified on the **Google Pixel 10 Pro XL (Layer 6 Edge Node)**.

This deployment provides:
1. **Interactive Bubble Tea TUI Terminal**: Runs directly in Termux or via home screen widgets.
2. **512Hz Medical Biometrics & Pan-Tompkins QRS DSP**: Displays real-time heart rate, R-R intervals, RMSSD, and DFA-alpha1.
3. **Nordic UART Service (NUS) & GATT Integration**: Directly scans and connects to Movesense sensor (`261030002013`, MAC: `74:92:BA:11:36:D6`).
4. **Kai Morich Macro Shortcuts**: M1 (`status`), M2 (`telemetry`), M3 (`ram`), M4 (`movesense`/`bicep`) with strict CRLF (`\r\n`) anti-staircasing.
5. **Android System Integration**: Direct launch via `movesense-terminal`, Termux home screen widgets, and native APK package installers staged in `/sdcard/Download/`.

---

## 2. Deployed Artifacts & Paths on Pixel

| Component | Pixel Device Path | Permissions | Role |
| :--- | :--- | :--- | :--- |
| **Terminal Launcher** | `/data/data/com.termux/files/usr/bin/movesense-terminal` | `rwxr-xr-x` | Main wrapper CLI for interactive and headless modes |
| **Sovereign Mesh Worker** | `/data/data/com.termux/files/usr/bin/lauburu` | `rwxr-xr-x` | Native Go binary (`lauburu_android` ARM64 PIE) |
| **Home Screen Widget** | `~/.shortcuts/Movesense_BT_Terminal` | `rwx------` | One-tap launch from Termux Widget |
| **Shell Shortcut** | `~/.shortcuts/Movesense_BT_Terminal.sh` | `rwx------` | Shell link for terminal execution |
| **BLE Scanner Task** | `~/.shortcuts/tasks/Movesense_BLE_Scan.sh` | `rwx------` | Quick BLE peripheral discovery |
| **Live Stream Task** | `~/.shortcuts/tasks/Movesense_Live_Stream.sh` | `rwx------` | Background 512Hz biometrics ANSI stream tailer |
| **Sensor Status Task** | `~/.shortcuts/tasks/Movesense_Status.sh` | `rwx------` | Instant sensor readiness check |
| **Native APK Installer** | `/sdcard/Download/Serial_Bluetooth_Terminal.apk` | `rw-rw----` | Kai Morich Serial Bluetooth Terminal APK |
| **Lauburu IDE APK** | `/sdcard/Download/Lauburu_BT_Terminal_IDE.apk` | `rw-rw----` | Custom Flutter Bluetooth Terminal IDE APK |

---

## 3. Empirical Tri-Proof Verification Matrix

Verified by `tests/test_pixel_movesense_terminal_installation.py`:

```
test_01_remote_binary_and_execution:  PASS (Exit Code 0)
test_02_remote_ble_scan_execution:    PASS (Exit Code 0)
test_03_shortcuts_and_widgets_integrity: PASS (Exit Code 0)
test_04_cryptographic_parity:        PASS (Exit Code 0)
  • movesense-terminal SHA: 659dffa9fa1dfd99...
  • lauburu binary SHA:     7f2ecf944bfe5ace...
test_05_staged_apk_installers:        PASS (Exit Code 0)
test_06_host_sanctuary:               PASS (Exit Code 0, Free RAM: 6.96 GB >= 4.8 GB)
```

---

## 4. How to Use on the Pixel 10 Pro XL

### Option A: From Android Home Screen (Termux Widget)
- Tap the **`Movesense_BT_Terminal`** icon on the Termux widget to launch the full interactive Bluetooth terminal directly.
- Tap **`Movesense_BLE_Scan`** to scan for sensor advertising.
- Tap **`Movesense_Status`** to see sensor connection, battery level, and placement.

### Option B: From Termux Command Line
```bash
# Launch interactive Movesense Bluetooth Terminal
movesense-terminal

# Standalone BLE discovery scan
movesense-terminal --scan

# Live 512Hz biometrics ANSI monitor
movesense-terminal --live

# Check Movesense sensor connection status
movesense-terminal --status
```
