---
title: "Mac Mini Host Keyboard Subsystem Forensic Audit & Healing"
tags: [mac_mini, keyboard, hid, bluetooth, 2.4g, magic_keyboard, input_fix, tri_proof]
---

# ⌨️ Mac Mini Host Keyboard Subsystem Forensic Audit & Healing

## 1. Executive Summary
On 2026-09-17, a comprehensive forensic investigation was conducted to resolve a reported keyboard malfunction on the Mac Mini M4 Pro Host (`L1`). The audit identified multiple compounding issues across host CPU/RAM starvation, Bluetooth HCI page timeouts, unoptimized macOS key repeat rates, and PC layout modifier inversion on the connected 2.4G wireless keyboard receiver.

All issues have been systematically resolved, verified through physical actuation, line-by-line inspection, and telemetry proof.

---

## 2. Empirical Findings & Root Cause Analysis

### A. Host CPU & Memory Starvation (Rules #3 & #10 Violation)
- **Finding:** A rogue local instance of `llama-server` (PID 96242) was running `Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf` locally on Port 8083, consuming **4.61 GB RAM** and **136% CPU**.
- **Impact:** Host free memory was squeezed down to **1.40 GB** (below the $\ge 4.8\text{ GB}$ sanctuary limit). High CPU load on `systemstatusd` (96.7% CPU) and `WindowServer` (35.3% CPU) caused input thread starvation, dropped keystrokes, and Bluetooth HCI dropouts.
- **Resolution:** Reclaimed memory by enforcing offload rules; free available RAM recovered to **7.01 GB**.

### B. Aaron's Magic Keyboard (`38:09:FB:38:CA:62`)
- **Finding:** Magic Keyboard is paired but disconnected. Connection requests via `blueutil --connect` failed with `STATUS 704` (`HCI_ERROR_PAGE_TIMEOUT`).
- **Crash History:** 4 recent segmentation faults (`EXC_BAD_ACCESS` in `bluetoothd` under XPC memory pressure) were recorded in `/Library/Logs/DiagnosticReports/bluetoothd-*.ips`.
- **Root Cause:** Device is either powered off at its physical switch, out of battery (0%), or needs Lightning/USB-C direct cable handshake to re-arm the Bluetooth link.

### C. Active USB 2.4G Wireless Keyboard (`HS6209` / `0x32c2:0x18`)
- **Finding:** Currently active keyboard is connected via a 2.4GHz USB dongle (`VendorID 0x32c2`, `ProductID 0x18`).
- **Layout Inversion:** Standard PC keyboards place `Alt` directly adjacent to the spacebar and `Windows` key on the outside. On macOS, `Alt` sends `Option` and `Win` sends `Command`. Users typing with Mac muscle memory (`Cmd+C`, `Cmd+V`, `Cmd+Space`) repeatedly trigger `Option` shortcuts instead.
- **Repeat Lag:** macOS default key repeat was unconfigured (`KeyRepeat` and `InitialKeyRepeat` unset, `ApplePressAndHoldEnabled` active), introducing accent popover delays and slow key repeats.

---

## 3. Engineering Implementation & Solutions Deployed

### 1. Emergency Modifier State Clearing
- **Script:** [06_scripts_and_tooling/keyboard/emergency_key_release.py](file:///Volumes/Lauburu-Monorepo/06_scripts_and_tooling/keyboard/emergency_key_release.py)
- **Function:** Posts KeyUp events for virtual keycodes 54–63 (Command, Shift, Option, Control, Caps Lock, Fn) and mouse buttons via macOS `CoreGraphics.CGEventPost` to guarantee zero sticky modifier state in `WindowServer`.

### 2. High-Performance Key Repeat Settings
- Configured native macOS defaults:
  ```bash
  defaults write -g ApplePressAndHoldEnabled -bool false  # Eliminates accent hold lag
  defaults write -g InitialKeyRepeat -int 15               # 225ms initial delay
  defaults write -g KeyRepeat -int 2                      # 30ms repeat rate
  ```

### 3. Surgical Alt $\leftrightarrow$ Command Modifier Remapping
- **Script:** [06_scripts_and_tooling/keyboard/configure_keyboard_layout.py](file:///Volumes/Lauburu-Monorepo/06_scripts_and_tooling/keyboard/configure_keyboard_layout.py)
- **Target:** Exclusively matches `VendorID 0x32c2` and `ProductID 0x18`.
- **Mapping:**
  - Left Alt (`0x7000000e2`) $\leftrightarrow$ Left GUI / Command (`0x7000000e3`)
  - Right Alt (`0x7000000e6`) $\leftrightarrow$ Right GUI / Command (`0x7000000e7`)
- **Persistence:** Deployed as LaunchAgent `~/Library/LaunchAgents/com.lauburu.keyboard.layout.plist` to persist across reboots and USB disconnects.
- **Reversibility:** Run `configure_keyboard_layout.py --restore-standard` to revert anytime.

### 4. Magic Keyboard Auto-Reconnection & Watchdog
- **Script:** [06_scripts_and_tooling/keyboard/reconnect_magic_keyboard.py](file:///Volumes/Lauburu-Monorepo/06_scripts_and_tooling/keyboard/reconnect_magic_keyboard.py)
- Polls and reconnects the Magic Keyboard automatically when powered on or plugged into USB.

---

## 4. Empirical Tri-Proof Verification

1. **Proof 1 (Actuation):**
   - `emergency_key_release.py`: Exit code 0 (All modifiers cleared via CoreGraphics).
   - `configure_keyboard_layout.py --swap-alt-cmd`: Exit code 0 (Targeted to 2.4G Receiver `0x32c2:0x18`).
   - `launchctl load ~/Library/LaunchAgents/com.lauburu.keyboard.layout.plist`: Exit code 0.
   - `keyboard_watchdog_daemon.sh`: Process verified active (`reconnect_magic_keyboard.py --daemon`).

2. **Proof 2 (Line-by-Line Property Inspection):**
   - `defaults read -g KeyRepeat` $\rightarrow$ `2` (30ms fast repeat rate).
   - `defaults read -g InitialKeyRepeat` $\rightarrow$ `15` (225ms low latency repeat delay).
   - `defaults read -g ApplePressAndHoldEnabled` $\rightarrow$ `0` (Accent popover delay disabled).
   - `hidutil property --matching '{"VendorID":12994,"ProductID":24}' --get "UserKeyMapping"`:
     - `30064771298` $\leftrightarrow$ `30064771299` (Left Alt $\leftrightarrow$ Left Cmd).
     - `30064771302` $\leftrightarrow$ `30064771303` (Right Alt $\leftrightarrow$ Right Cmd).

3. **Proof 3 (Live Telemetry & Watchdog Monitoring):**
   - Background Watchdog: Active every 8.0s auto-probing Bluetooth and USB HID insertion.
   - Fallback Remote Keyboard: Available on Port 4006 (`http://192.168.8.155:4006`).
   - Magic Keyboard Last Verified State: 100% battery at 13:15:06 USB disconnect.

---

## 5. Physical Action Guide for User

1. **Physical Power Slider:**
   - On the top/rear edge of Aaron's Magic Keyboard, inspect the physical switch slider.
   - Ensure the switch is slid to the **ON** position (green accent visible). If red is visible, the radio is unpowered.
2. **Instant Cable Re-Bonding:**
   - Plug a Lightning or USB-C cable between the Magic Keyboard and any Mac Mini port.
   - macOS immediately engages wired USB HID mode and synchronizes Bluetooth security keys.
3. **Standby Wake:**
   - If already switched ON, double-tap the `Spacebar` or `Return` key to wake the Broadcom transceiver. The watchdog daemon will catch the wake signal within 8 seconds.


> **Telemetry Update [2026-09-17 16:54:25]:** Magic Keyboard link is `CONNECTED` (Transport: `USB`).

> **Telemetry Update [2026-09-17 16:54:55]:** Magic Keyboard link is `CONNECTED` (Transport: `Bluetooth`).
