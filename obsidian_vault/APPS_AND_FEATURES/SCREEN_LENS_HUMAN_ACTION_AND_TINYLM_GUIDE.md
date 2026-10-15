---
title: "Screen Lens Event-Driven Human Action Sentinel & TinyLM Raw Telemetry Engine"
tags: [screen_lens, sentinel, human_action, tinylm, raw_telemetry, zero_mock, mesh]
date: 2026-10-02
status: PRODUCTION_ACTIVE
---

# 👁️ Screen Lens Event-Driven Human Action Sentinel & TinyLM Raw Telemetry Engine

## 1. Architectural Overview

The **Screen Lens Sovereign** subsystem integrates dual high-performance components to transform Screen Lens from a static periodic polling loop into a responsive, ground-truth-grounded perceptual core:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│             DUAL SCREEN LENS SOVEREIGN ENGINES (PORT 3035 & 3036)           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. EVENT-DRIVEN HUMAN ACTION SENTINEL                                       │
│    • Discovery: Discovers approved devices (macOS Accessibility, ADB)       │
│    • Ingestion: Quartz / ctypes CoreGraphics, LaunchServices lsappinfo,     │
│      and Android ADB getevent stream                                        │
│    • Latency: Micro-debounced (~60ms) immediate trigger on human action     │
│    • Governance: Enters QUIESCENT_STANDBY when idle (>5.0s) to spare RAM/CPU│
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. TINYLM RAW TELEMETRY & MULTIMODAL GROUND-TRUTH FUSION                    │
│    • Terminal Stream: Sub-10ms ingestion of raw ANSI stream (Movesense BLE, │
│      serial daemons, terminal error exit codes)                             │
│    • Sockets & Latencies: Real-time scan of 11 canonical mesh ports and     │
│      ICMP RTTs to Gateway (0.68ms) and L3 Linux Mini (6.0ms)                │
│    • Darwin Mach RAM: vm_stat & sysctl accounting per Rule 1 & Rule 3       │
│    • Discrepancy Gate: Detects divergences between visual OCR and raw truth │
│    • Dataset Harvest: Continuously appends verified traces to PySpark lake  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Multi-Device Human Action Sentinel

### 2.1 Device Approval Matrix
The sentinel automatically audits all connected devices before initiating monitoring:
- **macOS Host (L1_Mac_Node):** Checked via Darwin `ApplicationServices.AXIsProcessTrusted()` and ScreenCaptureKit authorization.
- **Android Peripherals (L6 Pixel 10 Pro XL, L7 Samsung S20+):** Discovered via `adb devices -l` and authorization states.

### 2.2 Event Interception & Zero-Polling Law (Rule 3)
- Physical mouse movements, clicks, and window drags are detected via pure `ctypes` CoreGraphics C syscalls (`CGEventCreate`, `CGEventGetLocation`, `CGEventSourceButtonState`).
- Active frontmost application switches are tracked via Darwin Launch Services (`/usr/bin/lsappinfo front`), strictly adhering to the Zero-`osascript` Polling Law to eliminate WindowServer event thread locks.
- Physical touches and hardware buttons on Android devices are monitored via asynchronous pipe readers streaming `adb shell getevent -q -l`.

### 2.3 Quiescent Standby Power Management
- When no human interaction occurs for $>5.0$ seconds, the sentinel transitions from `ACTIVE_INTERACTION` to `QUIESCENT_STANDBY`.
- Polling overhead drops to sub-millisecond sleep intervals, preserving Mac Mini host memory headroom ($\ge 4.8\text{ GB}$ buffer).
- Any incoming touch, mouse click, or keypress instantly awakens the pipeline, triggering an immediate Screen Lens frame capture.

---

## 3. TinyLM Raw Telemetry Engine & Ground-Truth Fusion

### 3.1 Raw Telemetry Channels
1. **Raw Terminal Stream:** Ingests live streams from `/tmp/bluetooth_terminal_stream.ansi` and terminal command outputs, stripping ANSI color codes, checking exit codes, and flagging warnings/errors.
2. **Network Mesh Sockets:** Verifies active listeners across canonical mesh ports (`3035, 3036, 3037, 4000, 4003, 4005, 4006, 8081, 8082, 8083, 18802`) and measures physical ICMP RTTs.
3. **Darwin Mach Kernel RAM:** Extracts App Memory, Wired Memory, Compressed Memory, and Memory Pressure Level directly from kernel Mach syscalls.

### 3.2 Fused Ground-Truth Evaluation
TinyLM executes a sub-10ms micro-inference fusing visual OCR data with raw device telemetry:
- **Visual vs Terminal:** Checks whether UI error messages match actual terminal exit codes, or whether UI claims "Connected" when raw sockets are dropped.
- **Visual vs RAM:** Detects UI slowdowns originating from kernel memory pressure levels rather than application bugs.
- **Verdict Scoring:** Computes `fused_accuracy_score` ($0.0$ to $1.0$) and categorizes state into `VERIFIED_ALIGNED` or `DISCREPANCY_FLAGGED`.
- **LoRA Lake Distillation:** Records discrepancy traces into `/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl` for continuous model fine-tuning.

---

## 4. REST API & Web Dashboard Integration

### 4.1 Endpoints on Port 3036
- `GET /api/human_action`: Returns live sentinel state (`ACTIVE_INTERACTION` vs `QUIESCENT_STANDBY`), idle duration, approval matrix, and the recent human interactions buffer.
- `POST /api/human_action`: Ingests human interaction events from external nodes or devices.
- `GET /api/tinylm_telemetry`: Returns current fused ground-truth evaluation, raw terminal snippet, raw kernel memory metrics, network port health, peer RTTs, and flagged discrepancies.

### 4.2 Web Dashboard (Port 3036)
- **Human Action Sentinel Card:** Displays live state badge, idle timer, connected device approval badges, and dynamic scrolling event feed.
- **TinyLM Raw Telemetry Card:** Displays ground-truth alignment score, Darwin Mach memory breakdown, active socket matrix, and live terminal text preview.

---

## 5. Verification & Service Operations

```bash
# Check Sentinel & TinyLM live telemetry via curl
curl -s http://127.0.0.1:3036/api/human_action | python3 -m json.tool
curl -s http://127.0.0.1:3036/api/tinylm_telemetry | python3 -m json.tool

# Restart Screen Life Companion Daemon
bash 01_apps/screen_lens/screen_life_companion/screen_life_daemon.sh restart

# Check logs
tail -n 30 /Volumes/Lauburu-Monorepo/logs/screen_life_companion.log
```
