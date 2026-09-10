---
title: "Sovereign Bluetooth Key Ring & Omni Terminal Integration (VICTORY CONFIRMED)"
tags: [omniterminal, bluetooth_keyring, ble, life360_disintermediated, zero_mock, movesense_ecg, shizuku, ai_debate, tri_vault]
created: 2026-09-05
status: VICTORY_CONFIRMED
tests_passing: "339/339"
exit_code: 0
---

# 🛰️ Sovereign Bluetooth Key Ring & Omni Terminal Integration — Canonical Blueprint

- **Project Root:** `/Users/aaron/teamwork_projects/bluetooth_keyring_omniterminal`
- **Audit Verdict:** **VICTORY CONFIRMED** by `teamwork_preview_victory_auditor`
- **Total Test Suite:** **339 / 339 Tests Passing** (Exit Code 0 in 4.10s)
  - Unit Tests: 117 / 117
  - E2E Tests: 156 / 156
  - Adversarial & Stress Tests: 66 / 66
- **Integrity Status:** 0 AST Mock Violations across all 21 production files (6,232 LOC in `src/`).
- **Cloud Spend:** **$0/month** (Life360 cloud telemetry completely bypassed).
- **Master Index Link:** [[Index]] | [[CANONICAL_PROJECT_AND_STORAGE_RULE]] | [[AI_DEBATE_BLUETOOTH_KEYRING_AND_OMNITERMINAL_EXPANSION]]

---

## 🏛️ 1. Subsystem R1: Sovereign BLE Key Ring Driver (`src/keyring_ble/`)

| Feature | Implementation Detail | Empirical Verification |
| :--- | :--- | :--- |
| **Passive 0xFEED Sniffing** | Listens for Tile/Life360 advertisements (`0xFEED` service UUID) without active connection. | Preserves 12+ month CR2032 battery life; zero battery drain. |
| **GATT Buzzer Actuation** | Connects on-demand and writes command `0x9d410002` to play high-decibel alert chime. | `<500ms` latency; disconnects immediately after actuation. |
| **Reverse-Ring Button** | Listens for physical button press notifications from the key fob. | Emits authentic event captured by Omniterminal event loop. |
| **2D WLS Multilateration** | Weighted least-squares RSSI multilateration across Mac, Linux, and Android nodes. | Kalman-filtered; reports room-level proximity with `--` waiting states. |

---

## 🖥️ 2. Subsystem R2: Omni Terminal Core & PTY Macros (`src/omniterminal/`)

- **CLI Commands:**
  - `omniterminal ring-keys`: Triggers physical key ring buzzer alert.
  - `omniterminal proximity --watch`: Real-time room proximity and RSSI stream.
  - `omniterminal beacon-status`: Displays battery, firmware, and node visibility matrix.
- **Out-of-Band PTY Macro Dispatcher:**
  - Single-Click: Toggles speech-to-text (STT) hands-free voice coding.
  - Double-Click: Emits `SIGTSTP` emergency screen clear and safe-state.
  - Long-Press: Triggers modal security lock.
- **Proximity Auto-Lock State Machine:**
  - 20 dB hysteresis (-85 dBm lock / -65 dBm unlock) with 5.0s grace period and $K=3$ median filter.
  - Auto-locks terminal sessions when keys leave room perimeter; unlocks with PIN override or biometric touch.

---

## 🫀 3. Subsystem R3: Omni Terminal Feature Ecosystem (`src/omniterminal/ecosystem/`)

1. **Movesense 512Hz ECG HUD (`movesense_hud.py`):**
   - Medical-grade Pan-Tompkins QRS DSP with IIR 50Hz notch filter and Kamath outlier filtering.
   - Calculates real-time BPM, RMSSD, DFA-$\alpha_1$, and PTT blood pressure.
   - Throttles cognitive load when HRV detects fatigue.
2. **Rootless Android Shizuku Remote (`shizuku_remote.py`):**
   - Direct execution via `rish` on Pixel 10 Pro XL (L6) and Samsung S20 (L7).
   - 80% battery charging clamps, Doze mode whitelist regex validation, and automated 5G cellular hotspot failover.
3. **Dual-Plane Local AI Debate Co-Pilot (`ai_debate_copilot.py`):**
   - Side-by-side terminal pane comparing Port 8081 (Qwen Coder) against Port 8083 (Abliterated Devil's Advocate) before running shell commands or git commits.
4. **Multi-WAN & 10Gbps Thunderbolt 4 Telemetry (`multiwan_telemetry.py`):**
   - Live hardware counter monitoring `bridge0` (0.27ms RTT), `en0`, `en1`, and Tailscale WireGuard.
