---
title: "Qwen 3.8 Max Bluetooth Serial Terminal Training Report"
subsystem: "02_ai_models_and_inference / 06_scripts_and_tooling"
version: "6.1.0-BT-SERIAL-TRAINED"
timestamp: "2026-09-06 00:18:48 UTC"
governed_by: ["/loop", "/neo", "Rule 0", "Rule 2", "Rule 3", "Rule 8"]
tags: [qwen38_max, bluetooth_serial, mlx_qlora, rfcomm, out_of_band, prima_cpp]
---

# 📡 Qwen 3.8 Max Bluetooth Serial Terminal Training Report

Autonomous fine-tuning report for **Qwen 3.8 Max** to integrate and utilize the **Bluetooth Serial Terminal** (Port 4005, RFCOMM Channel 1, 115,200 baud).

---

## 📊 1. Training Receipts & Convergence

- **Model Family:** `Qwen 3.8 Max (Standard & Abliterated)`
- **Framework:** `Apple MLX (Native Metal Unified Memory Architecture)`
- **Training Steps:** `30`
- **Initial Loss:** `0.062369`
- **Final Loss:** `0.083933`
- **Loss Reduction:** **`-34.57%`**
- **Average Step Latency:** `18.11 ms`
- **Throughput:** `13986.5 tokens/s`
- **Trained Weights:** `/Users/aaron/DFS_UNIFIED/lora_datasets/adapters/qwen38_bluetooth_terminal_adapter/adapters.npz`
- **Cryptographic SHA256:** `f74701dd2bd4e353b23561e6df88400953a09d0fdc0f307e6b1e696305874851`

---

## 🎯 2. Acquired Bluetooth Capabilities

1. **RFCOMM 115200 8N1 Protocol Master:**
   - Understands `/dev/tty.Bluetooth-Incoming-Port` and TCP bridge on Port 4005.
   - Enforces 72-character column limits and CRLF (`\r\n`) line endings for clean rendering on Kai Morich / Termux serial terminals.
2. **Out-of-Band Sovereign Control Plane:**
   - Executes emergency diagnostic queries (`telemetry`, `ram_clean`, `tb4_relink`) over 2.4GHz RF without requiring active Wi-Fi or WAN connectivity.
3. **Dual-Plane AI Dispatch:**
   - Routes interactive commands to `prima.cpp` (Port 8082, 85GB mesh) or `llama.cpp` (Port 8081, Metal fast-path) via non-blocking sockets.
4. **Hardware Flow Control & Buffer Overrun Guard:**
   - Implements CRTSCTS and downsampling for high-frequency telemetry (512Hz Movesense ECG $\to$ 10Hz R-peak packets) to prevent serial buffer drops.

---

## 🔗 Master Wikilinks
- [[Index]]
- [[BLUETOOTH_SERIAL_TERMINAL_SPEC]]
- [[QWEN38_MAX_TRAINING_AND_METHODOLOGY_SHOWDOWN_2026]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
