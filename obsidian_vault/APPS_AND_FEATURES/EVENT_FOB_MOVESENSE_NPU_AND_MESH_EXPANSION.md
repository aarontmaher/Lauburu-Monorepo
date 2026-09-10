---
title: "Event Fob Dispatcher, Movesense Bicep ECG, NPU Telemetry & Mesh Topology Expansion"
tags: [lauburu, keyring, movesense, ecg, npu, tailscale, cloudflare, ai_debate]
created: 2026-09-05T09:25:00+10:00
---

# 🛰️ Event Fob Dispatcher, Movesense Bicep ECG, NPU Telemetry & Mesh Expansion

## 1. What is an Event Fob Dispatcher?
The **Event Fob Dispatcher** (`KeyFobMacroDispatcher` in `src/omniterminal/macro_dispatcher.py`) is an out-of-band, event-driven hardware bridge connecting physical Bluetooth Low Energy (BLE) key fobs directly to POSIX/PTY process signals and terminal macros.

### Architecture:
```
┌────────────────────────┐        BLE GATT Notification        ┌─────────────────────────────┐
│ Physical Key Ring Fob  │ ─────────────────────────────────> │ Local BLE Ingress Daemon    │
│ (Tile / Nut / nRF52840)│   (0x9D410002 / Simple Key 0xFFE1) │ (/tmp/keyring_ble.sock)     │
└────────────────────────┘                                     └──────────────┬──────────────┘
                                                                              │
                                                                       IPC JSON Frame
                                                                              ▼
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│ Event Fob Dispatcher (Temporal Debounce & Click Classifier)                                 │
├────────────────────────────────────────────────────────────────────────────────────────────┤
│ • Single Click (<300ms):    Toggle Hands-Free STT Voice Pair-Programming Engine            │
│ • Double Click (400ms win): Interrupt Foreground Shell Session (SIGTSTP / Safe Interrupt)  │
│ • Triple Click (600ms win): Summon Dual-Plane AI Debate Co-Pilot (Port 8081 vs Port 8083)  │
│ • Long Press (>=1500ms):    Instant Terminal Lockout Canvas (Zero-Trust RSSI Screen Freeze)│
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Movesense ECG Deep Research, Google Movement & Bicep Prototyping

### A. Python on Movesense & Whiteboard API
- Movesense sensors run on Nordic nRF52832 / nRF52840 microcontrollers (ARM Cortex-M4F @ 64MHz).
- Open-source Python integration uses the **Movesense Whiteboard Protocol** over BLE GATT Nordic UART Service (NUS). Real-time 512Hz ECG streams and 9-DOF IMU arrays are streamed and parsed with zero cloud reliance.

### B. Google Movement & Sensor Foundation Models
- **Google Research SensorFM (2026) & SensorLM (2025):** Pre-trained on >1 trillion minutes of multimodal wearable sensor data (ECG, IMU, PPG, polysomnography).
- **Google Movement / MediaPipe:** Python toolboxes for biomechanical motion tracking, tremor analysis, and kinematic joint estimation.
- **Integration:** Movesense 512Hz raw acceleration + ECG can be fed directly into local 1D CNN / SensorFM embeddings to quantify cardiovascular strain during grappling and conditioning.

### C. 1-Wire Smart Accessory Interface
- The back of the Movesense sensor contains an accessory bus supporting Maxim **1-Wire EEPROM (`DS28E07`)**.
- When snapped into an accessory, the sensor queries the 1-Wire ID to automatically detect the cable/strap type and configure the ADC / AFE sampling parameters.

### D. Developing an ECG-Capable Bicep Strap
- **The Challenge:** Traditional ECG measures the cardiac vector across the chest ($\sim 1.0 - 1.5$ mV). On the upper bicep, cardiac electrical amplitude drops to $\sim 0.15 - 0.25$ mV and is contaminated by biceps/triceps electromyography (EMG) during muscle activation.
- **The Engineering Solution:**
  1. **Electrode Topology:** Dual Ag/AgCl conductive silicone pads positioned longitudinally along the medial bicep groove ($\ge 6\text{ cm}$ separation) facing the thoracic cavity.
  2. **AFE Analog Gain Boost:** Reconfigure the MAX30003 Analog Front End via `/Meas/ECG/Config` from standard $20\text{ V/V}$ to $80\text{ V/V}$ or $160\text{ V/V}$.
  3. **Real-time DSP Filtering:** 4th-order Butterworth bandpass ($0.8 - 35\text{ Hz}$) + 50Hz IIR notch filter + dynamic Pan-Tompkins derivative squaring.
  4. **Automated Prototype Pipeline:** Parametric 3D snap bracket (OpenSCAD/CadQuery) + conductive textile strap specs connected to JLCPCB/PCBWay automated fabrication script. Aaron reviews the spec, issues "buy it", and a prototype is ordered.

---

## 3. NPU Telemetry Integration in the 10Gbps TB4 DMA Console
NPU telemetry across the 7 mesh layers:
1. **L1 (Mac Mini M4 Pro):** Apple Neural Engine (ANE) power (mW) and active duty cycle via Darwin `powermetrics` / `ioreg`.
2. **L6 (Pixel 10 Pro XL):** Google Tensor G5 Edge TPU inference frequency and duty cycle via Shizuku `rish` sysfs nodes (`/sys/class/edgetpu/`).
3. **L3 (Linux Head Node):** AMD Ryzen NPU driver metrics (`/sys/class/accel/`).
Integrated directly into `omniterminal` Console TUI alongside the Multi-WAN bonded bandwidth gauges.

---

## 4. Zero-Touch Bluetooth Node Recruitment: Feasibility & Protocol
- **Security Reality:** Modern OSes (iOS, Android, macOS, Windows) strictly prohibit arbitrary silent remote code execution over unauthenticated Bluetooth.
- **Feasible Sovereign Architecture:**
  1. **Pre-Authorized BLE Provisioning:** Known mesh nodes (Android phones/tablets running Termux, Raspberry Pis) run the lightweight Lauburu BLE edge daemon. When in proximity, the Mac Mini connects via BLE GATT, exchanges WireGuard keys and task payloads, and recruits the node.
  2. **WebBluetooth / WebGPU Browser Node (Zero Installation):** Any device opening a local URL becomes an instant WebAssembly/WebGPU compute worker via WebSockets, executing matrix math in the browser with zero installation.

---

## 5. Tailscale vs Cloudflare vs VPS Headscale AI Debate

### Tri-Orchestrator Verdict (Port 8081, Port 8083 Abliterated Devil's Advocate, Cloud Shadow):
- **Cloudflare Zero Trust (Tunnels + WARP):**
  - *Strengths:* World-class public ingress, zero exposed router ports, DDoS protection, edge auth.
  - *Devil's Advocate Flaw:* All traffic routes through Cloudflare edge data centers, adding 15–40ms RTT latency. Completely incompatible with sub-millisecond local tensor sharding (which requires $\le 1.0$ ms). Lacks raw Layer 3 UDP packet encapsulation for BLE/multicast.
- **Tailscale:**
  - *Strengths:* Direct peer-to-peer WireGuard connections (TB4 at 0.27ms, Wi-Fi 7 at 2ms). DERP relays used strictly as fallback.
  - *Drawback:* Uses Tailscale Inc.'s proprietary coordination server.
- **The Optimal Sovereign Solution: Self-Hosted Headscale on a \$5/mo VPS:**
  - Runs the open-source Tailscale control server (Headscale) on a VPS.
  - All devices run native Tailscale clients pointed to `headscale.lauburu.local`.
  - Full WireGuard P2P performance + 100% data sovereignty + $0 recurring vendor lock-in.
- **MCP over WebSockets/TLS:**
  - Operates at Layer 7 (Application RPC). Runs on top of the WireGuard/Tailscale overlay to securely share AI tools across the mesh.

---

## 6. Shell Errors Diagnosed & Fixed

| Error Reported | Root Cause | Resolution |
| :--- | :--- | :--- |
| `omniterminal telemetry`: `No module named 'src'` | Relative import resolution in `sentinel/__init__.py` | Fixed with `sys.path` bootstrap. Verified `Exit Code 0`. |
| `pytest -v`: `No module named pytest` | Shell alias `pytest="python3 -m pytest"` invoked experimental `python@3.14` | Symlinked `/Users/aaron/.local/bin/python3` to `/Users/aaron/.venv/bin/python3`. Verified `pytest 9.1.1` `Exit Code 0`. |
| `python3 -m src.omniterminal.main --console`: `No module named 'omniterminal'` | Absolute import in `omniterminal/__init__.py` & missing `main.py` | Converted to relative imports, created `main.py`, wired into wrapper. Verified `Exit Code 0`. |
| `python tests/...`: `No such file or directory` | Executed from `$HOME` instead of monorepo root | Run from `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`. |
| `npm run build`: `ENOENT: package.json` | Executed from `$HOME` instead of app folder | Run from specific app directory (`01_apps/...`). |

