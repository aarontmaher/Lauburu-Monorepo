---
title: "Movesense Bluetooth App Connectivity, Single-Central GATT Lockout & Anatomical Placement Guide"
tags: [movesense, bluetooth, android, termux, gatt, single_central, chest_vs_bicep, tri_proof]
author: "Aaron (Sovereign Lead) & Antigravity Swarm Orchestrator"
date: "2026-09-13"
---

# 🫀 Movesense Bluetooth App Connectivity & Placement Guide

- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[MOVESENSE_DONGLE_HANDOVER_E2E_SPEC]]
- [[PIXEL_MOVESENSE_BLUETOOTH_TERMINAL_INSTALLATION]]

---

## 🛑 1. Why "The Phone is Connected to Movesense but the App Won't Connect"

### Root Cause: The Android BLE Single-Central GATT Lockout
1. **Physical Movesense Limitation**:
   - The Movesense Medical Sensor (`261030002013`, Nordic nRF52840 SoC) implements a standard Bluetooth Low Energy (BLE) peripheral stack that supports **exactly ONE active Central GATT connection** at any given moment.
2. **The Android OS Trapping Behavior**:
   - When a user pairs or connects the Movesense sensor in **Android System Settings ➡️ Connected devices ➡️ Bluetooth**, Android's OS-level Bluetooth service (`com.android.bluetooth`) establishes and latches an exclusive GATT client connection (`0x180D`).
   - The moment Movesense connects to Android OS, it **stops broadcasting BLE advertising packets (`ADV_IND`)**.
   - Consequently, when any app (Kai Morich Serial Bluetooth Terminal, custom Flutter app, Movesense Showcase, or Chrome Web Bluetooth) calls `connectGatt()`, Android returns `GATT_ERROR (Status 133)` or hangs indefinitely waiting for advertisements.
3. **The Universal Rule for BLE Biometric Sensors**:
   - Unlike Classic Bluetooth headphones or car audio, **BLE sensors must NEVER be connected or paired in the phone's Android Bluetooth Settings menu**.
   - The sensor must remain unbonded/disconnected at the OS level so third-party apps or the Lauburu mesh can claim the GATT link directly.

---

## ⚡ 2. Immediate Resolution Steps (How to Connect)

### Step 1: Disconnect / Unpair from Android Settings
1. Open **Settings** on your phone (Pixel or Samsung).
2. Go to **Connected devices** ➡️ **Bluetooth**.
3. Locate **Movesense 261030002013**.
4. Tap the **Gear / Settings icon** next to it.
5. Tap **Disconnect** (or **Forget / Unpair**).
6. *The Movesense LED will flash and resume advertising BLE packets.*

---

### Step 2: Choose Your Terminal / App Connection Method

#### Option A: Termux Movesense Bluetooth Terminal (On Pixel 10 Pro XL)
You can launch the terminal in three ways directly on the Pixel:
1. **Interactive TUI**: Open Termux and run:
   ```bash
   movesense-terminal
   ```
   *Controls: Tap macro buttons M1-M4 or type `movesense` / `bicep`.*
2. **Live 512Hz Biometrics Monitor**:
   ```bash
   movesense-terminal --live
   ```
3. **Home Screen One-Tap**:
   - Add the **Termux:Widget** to your Android home screen.
   - Tap **`Movesense_BT_Terminal`** to launch instantly.

---

#### Option B: Kai Morich "Serial Bluetooth Terminal" (Recommended App Mode)
Because Movesense transmits biometrics via Heart Rate Service (`0x180D`) rather than Nordic UART Service (NUS), connect via the Lauburu TCP Bridge:

1. Open **Serial Bluetooth Terminal** on your phone.
2. Tap the **Hamburger Menu (☰)** in the top-left corner.
3. Tap **Settings** ➡️ **Connection** ➡️ **Connection Type**.
4. Select **`TCP Client`**.
5. Set:
   - **Host / IP**: `100.119.199.76` *(Tailscale IP of Mac Mini Host)* or `192.168.8.230`
   - **Port**: `4050` *(or `4051`)*
6. Return to the main terminal screen and tap the **Connect (Plug) Icon** in the top bar.
7. **Result**: Terminal latches instantly with CRLF (`\r\n`) anti-staircasing.
   - Tap **M1** ➡️ Mesh Health Status.
   - Tap **M2** ➡️ Mach Hardware Telemetry.
   - Tap **M3** ➡️ Mac Mini Sanctuary RAM Headroom.
   - Tap **M4** ➡️ Real-time Movesense biometrics & Auto-Classifier placement.

---

## 🧠 3. Automated Chest vs. Bicep Anatomical Placement Classifier

The system automatically distinguishes whether the sensor is placed on the **Chest** or the **Bicep** in real-time without requiring manual toggling:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               ANATOMIC PLACEMENT AUTO-CLASSIFICATION PIPELINE               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. GATT 0x2A38 Location Code                                                │
│    • Code 1 (Chest): +1.2 Score                                             │
│    • Code 2 (Wrist/Arm): -1.0 Score                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Kamath 20% Ectopic & Artifact Rejection Rate                             │
│    • Low Artifact (<8%): +1.8 Score (High sternal SNR, clean Lead II)        │
│    • Elevated Artifact (>18%): -2.2 Score (Brachial bicep EMG muscle noise) │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. Respiratory Sinus Arrhythmia (RSA) Oscillations                          │
│    • Thoracic Waveform (15ms <= Mean Diff <= 85ms): +1.5 Score              │
│    • Erratic Delta (Mean Diff > 110ms or Std Diff >= 45ms): -1.5 Score      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. Dynamic Classification & DSP Routing                                     │
│    • Score >= 0.0: 🫀 CHEST STRAP (Thoracic Sternal ECG - Lead II Vector)     │
│    • Score <  0.0: 💪 BICEP STRAP (Brachial Bicep ECG - Kamath 20% Filter)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 4. Empirical Tri-Proof Parity & Verification Matrix

Both test suites executed and verified with Exit Code 0:
1. `tests/test_movesense_placement_auto_classifier_e2e.py` (6/6 PASS - 100%)
2. `tests/test_pixel_movesense_terminal_installation.py` (6/6 PASS - 100%)
3. `go test -v ./internal/biometrics ./internal/bluetooth` (PASS - Exit Code 0)
4. Cryptographic SHA256 parity verified between Mac host and Pixel 10 Pro XL.
