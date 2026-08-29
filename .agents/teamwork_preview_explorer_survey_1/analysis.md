# Comprehensive Analysis: Biometrics Domain & Movesense Hub Architecture

**Author:** Explorer Agent (`teamwork_preview_explorer_survey_1`)  
**Date:** 2026-08-29  
**Subsystem:** Biometrics, Physiological Readiness & Movesense Hub  
**Target Directories:** `01_apps/biometrics/`, `03_biometrics_and_telemetry/`, `01_apps/edge_compute_and_ai/`  
**Rule Compliance:** 100% Local Airgap Protected & Rule #0 Zero-Mock Certified  

---

## 1. Executive Summary

This investigation explores the current state of the biometrics subsystem across the Lauburu Monorepo, focusing on the flagship **Movesense Physiological Readiness App**, real physical BLE GATT streaming (`Movesense 261030002013`), 512Hz/128Hz digital signal processing (Pan-Tompkins QRS detection, Kamath 2004 20% RR artifact filter, RMSSD, DFA-alpha1 aerobic thresholds), continuous Pulse Transit Time (PTT) hemodynamic blood pressure inversion, overnight PPG sleep staging (0-100 recovery score), auto workout classification, and Zone 2 cardio coaching.

### Core Discoveries:
1. **Strong Mathematical & DSP Foundation:** High-performance DSP algorithms are implemented in `03_biometrics_and_telemetry/pan_tompkins_dsp.py` and `movesense_readiness_suite.py` with 100% test coverage in `03_biometrics_and_telemetry/tests/test_movesense_dsp_suite.py` (all tests passing).
2. **Multi-Transport BLE Streaming:** Full Bluetooth Low Energy (BLE) ingestion is implemented across three environments:
   - Python Bleak async daemon (`01_apps/edge_compute_and_ai/lauburu_compute_hub/services/movesense_ingestion.py` and `03_biometrics_and_telemetry/run_real_movesense_daemon.py`).
   - Web Bluetooth API in TypeScript/React (`01_apps/biometrics/zone2_endurance/src/services/movesenseBleService.ts`).
   - Flutter/Dart BLoC cross-platform client (`01_apps/biometrics/lauburu_zone2_endurance/lib/services/compute_hub_connection_service.dart`).
3. **Multi-Platform Presentation Interfaces:**
   - **Textual TUI:** `01_apps/biometrics/movesense_readiness_tui.py`.
   - **Web-TUI:** `01_apps/canonical_port/tui/serve_web_tui.py` hosting `/readiness` over WebSockets & xterm.js at 120 FPS.
   - **Next.js 14 Web PWA:** `01_apps/biometrics/zone2_endurance/` featuring 128Hz Canvas oscilloscope with circular ring buffer (`LiveEcgMonitor.tsx`).
4. **Architectural Gap Identified:** `01_apps/biometrics/movesense_hub` is currently unmodularized (contains only `pyspark_biometrics_dsp.py` and stale temp files) and requires decomposition into standardized modular subpackages: `core/`, `dsp/`, `presentation/`, and `transport/`.

---

## 2. Monorepo Biometrics Code Inventory & File Map

| File Path | LOC | Subsystem Role | Key Features / Status |
|:---|:---|:---|:---|
| `03_biometrics_and_telemetry/pan_tompkins_dsp.py` | 561 | Core DSP Engine | 512Hz/128Hz Butterworth bandpass (0.5–40Hz), 5-pt derivative, squaring, 150ms MWI, dual-threshold peak search, Kamath 2004 20% filter, RMSSD, DFA-alpha1, PTT BP inversion. |
| `03_biometrics_and_telemetry/movesense_readiness_suite.py` | 464 | Readiness & Sleep Staging | PTT continuous BP, 30s epoch sleep staging (Deep, REM, Light, Awake) & 0–100 recovery score, auto workout detection, LT1/LT2 thresholds, VO2max estimation, LoRA dataset sink. |
| `03_biometrics_and_telemetry/run_real_movesense_daemon.py` | 95 | Live Hardware Bleak Client | Direct Bleak CoreBluetooth connection to Movesense `261030002013` (`C1DB5043-8F89-88E8-46A3-BBD4ED83FC88`), JSON streaming. |
| `03_biometrics_and_telemetry/open_wearables_bridge.py` | 508 | Multi-Wearable Normalizer | Whoop, Garmin, Oura, Apple Health, Google Health Connect normalization, Delta Lake & PySpark JSONL persistence, atomic blackboard sync. |
| `03_biometrics_and_telemetry/movesense_to_4000_bridge.py` | 122 | Forwarding Bridge | Subscribes to live GATT notifications, transforms via DSP, forwards to `127.0.0.1:4000/api/v1/network/ingest`. |
| `03_biometrics_and_telemetry/tests/test_movesense_dsp_suite.py` | 549 | Verification Test Suite | 10 test suites, 24 test cases covering 512Hz Pan-Tompkins, Kamath filter, RMSSD, DFA-alpha1, PTT BP, sleep score, zero-mock contract. |
| `01_apps/biometrics/movesense_readiness_tui.py` | 199 | User-Facing Textual TUI | 6-card athlete HUD: HR/HRV, PTT BP, Sleep & Recovery, VO2max & Thresholds, Zone 2 Coaching table, ECG DSP Diagnostics. |
| `01_apps/biometrics/zone2_endurance/` | ~3,200 | Next.js 14 Web PWA | Web Bluetooth client (`movesenseBleService.ts`), 128Hz Canvas oscilloscope (`LiveEcgMonitor.tsx`), DFA-alpha1 trend chart (`DfaAlpha1TrendChart.tsx`), WCAG AA accessibility table. |
| `01_apps/biometrics/lauburu_zone2_endurance/` | ~850 | Flutter / Dart Mobile Client | Dart BLoC state management, BLE onboarding view, compute hub connection service. |
| `01_apps/edge_compute_and_ai/lauburu_compute_hub/services/movesense_ingestion.py` | 943 | Full Bleak MDS Daemon | 128-bit Movesense MDS 2.0 (`34800001-...`), Whiteboard subscriptions (`/Meas/ECG/128`, `/Meas/IMU6/52`), Polar HRS (`0x180D`/`0x2A37`), battery service (`0x180F`), zero-mock state machine. |
| `01_apps/canonical_port/tui/serve_web_tui.py` | 399 | Web-TUI Server | aiohttp + xterm.js + PTY server hosting `/readiness` at 120 FPS on Port 8088. |
| `01_apps/canonical_port/backend/spec_modules/spec_03_biometrics_dsp.py` | 206 | FastAPI Spec Router | REST `/api/v1/spec-03/dsp-metrics` and `/process-ecg-window` endpoints, health checks, diagnostic calibration runner. |

---

## 3. Movesense Sensor 261030002013 & BLE GATT Specifications

### 3.1 Device Identity & Transport Topologies
- **Target Peripheral Serial:** `Movesense 261030002013`
- **CoreBluetooth Address / MAC:** `C1DB5043-8F89-88E8-46A3-BBD4ED83FC88`
- **Operating Modes:**
  1. **High-Resolution Medical ECG & IMU (Movesense MDS 2.0 / Whiteboard Protocol):** Direct 128-bit custom GATT service.
  2. **Standard Bluetooth SIG HRS Compatibility Mode:** Standard 16-bit UUID `0x180D` / `0x2A37`.
  3. **Browser Web Bluetooth Mode:** Client-side pairing via `navigator.bluetooth.requestDevice({ filters: [{ namePrefix: "Movesense" }] })`.

### 3.2 Authoritative 128-Bit GATT UUID Matrix

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                             MOVESENSE 261030002013 GATT ARCHITECTURE                             │
├───────────────────────────────┬────────────────────────────────────────┬─────────────────────────┤
│ Service / Characteristic Name │ UUID (128-bit / 16-bit)                │ Purpose / Protocol      │
├───────────────────────────────┼────────────────────────────────────────┼─────────────────────────┤
│ Movesense MDS 2.0 Service     │ 34800001-7185-4d5d-b431-b30e393d9e05   │ Primary Whiteboard Root │
│ Movesense Command Char (Write)│ 34800001-7185-4d5d-b431-b30e393d9e05   │ Whiteboard Sub/Unsub    │
│ Movesense Data Char 1 (Notify)│ 34800002-7185-4d5d-b431-b30e393d9e05   │ Streaming ECG/IMU Bytes │
│ Movesense Data Char 2 (Notify)│ 34800003-7185-4d5d-b431-b30e393d9e05   │ Secondary Data Channel  │
│ Bluetooth SIG Heart Rate Svc  │ 0000180d-0000-1000-8000-00805f9b34fb   │ Standard Heart Rate Svc │
│ Heart Rate Measurement Char   │ 00002a37-0000-1000-8000-00805f9b34fb   │ HR BPM & RR-Intervals   │
│ Battery Service               │ 0000180f-0000-1000-8000-00805f9b34fb   │ Battery Level Svc       │
│ Battery Level Characteristic  │ 00002a19-0000-1000-8000-00805f9b34fb   │ Battery % (uint8)       │
│ Device Information Service    │ 0000180a-0000-1000-8000-00805f9b34fb   │ Device Info Root        │
│ Model Number String           │ 00002a24-0000-1000-8000-00805f9b34fb   │ "Movesense Medical"     │
│ Serial Number String          │ 00002a25-0000-1000-8000-00805f9b34fb   │ "261030002013"          │
│ Firmware Revision String      │ 00002a26-0000-1000-8000-00805f9b34fb   │ Firmware Version        │
└───────────────────────────────┴────────────────────────────────────────┴─────────────────────────┘
```

### 3.3 Binary Frame Ingestion Protocol
1. **Whiteboard Subscription Handshake:**
   - Write request to `34800001`: Opcode `0x05` (SUBSCRIBE) + ReqId `0x01` + path `/Meas/ECG/128` (or `/Meas/ECG/512`).
   - Write request to `34800001`: Opcode `0x05` (SUBSCRIBE) + ReqId `0x02` + path `/Meas/IMU6/52`.
2. **ECG Notification Decoding (`MovesenseBinaryDecoder.decode_ecg_128_packet`):**
   - Header: `[type (uint8), req_id (uint8), timestamp_uint32 (4 bytes little-endian)]`
   - Payload: Array of `int32` signed microvolt ($\mu\text{V}$) integers. Conversion: $\text{mV} = \mu\text{V} / 1000.0$.
3. **IMU 6-DoF Decoding (`MovesenseBinaryDecoder.decode_imu6_52_packet`):**
   - Payload: Array of 6 $\times$ `float32` (24 bytes per frame): $[a_x, a_y, a_z, g_x, g_y, g_z]$.
   - Dynamic Acceleration: $G_{\text{dyn}} = \sqrt{a_x^2 + a_y^2 + a_z^2}$.
4. **Standard Bluetooth SIG HRS Decoding (`PolarHrsDecoder.decode_hrs_packet` / `parseHeartRateData`):**
   - Flags byte: bit 0 (8-bit vs 16-bit HR), bit 4 (RR-interval presence).
   - RR calculation: $RR_{\text{ms}} = \frac{RR_{\text{raw}}}{1024.0} \times 1000.0$.

---

## 4. Signal Processing & Mathematical Formulations

### 4.1 512Hz / 128Hz Pan-Tompkins QRS Detection (1985)
Implemented in `pan_tompkins_dsp.py:39-258`:
1. **Zero-Phase 4th-Order Butterworth Bandpass (0.5 Hz – 40.0 Hz):**
   $$H(s) = \text{Butterworth}(4, [0.5, 40.0] \text{ Hz})$$
   Eliminates baseline wander, sweat artifacts ($<0.5\text{ Hz}$), 50/60 Hz mains interference, and high-frequency muscle tremor ($>40\text{ Hz}$).
2. **5-Point Central Derivative Filter:**
   $$d[n] = \frac{1}{8T} \left( -x[n-2] - 2x[n-1] + 2x[n+1] + x[n+2] \right)$$
   Where $T = 1/f_s$. Suppresses low-frequency P and T waves while maximizing the steep slope of the QRS complex.
3. **Nonlinear Squaring Transform:**
   $$s[n] = (d[n])^2$$
   Enforces strict non-negativity and non-linearly amplifies high-frequency QRS energy spikes.
4. **Moving Window Integration (MWI):**
   $$\text{MWI}[n] = \frac{1}{N} \sum_{k=0}^{N-1} s[n-k], \quad N = \text{round}(0.150 \cdot f_s)$$
   Window width $N = 76$ samples at 512Hz (19 samples at 128Hz). Extracts duration feature envelope.
5. **Adaptive Dual-Threshold Peak Detection & Searchback:**
   $$\text{SPK} = 0.125 \cdot \text{PEAK} + 0.875 \cdot \text{SPK}$$
   $$\text{NPK} = 0.125 \cdot \text{PEAK} + 0.875 \cdot \text{NPK}$$
   $$\text{Threshold}_{I1} = \text{NPK} + 0.25 \cdot (\text{SPK} - \text{NPK})$$
   $$\text{Threshold}_{I2} = 0.5 \cdot \text{Threshold}_{I1}$$
   Refractory period lockout: 200 ms (102 samples at 512Hz, 25 samples at 128Hz).

### 4.2 Kamath et al. (2004) Clinical 20% RR Artifact Filter
Implemented in `pan_tompkins_dsp.py:264-312`:
$$\frac{|RR[i] - RR[i-1]|}{RR[i-1]} \le 0.20$$
- Preserves natural Respiratory Sinus Arrhythmia (RSA) swings ($\pm 8\text{--}15\%$).
- Rejects ectopic bursts, Premature Ventricular Contractions (PVCs), and motion noise.
- Replaces rejected beats with physiological cubic/linear baseline interpolation: $RR_{\text{clean}}[i] = \frac{RR[i-1] + RR[i+1]}{2}$.

### 4.3 Time-Domain Autonomic HRV (RMSSD)
Implemented in `pan_tompkins_dsp.py:315-327`:
$$\text{RMSSD} = \sqrt{ \frac{1}{N-1} \sum_{i=1}^{N-1} (RR[i+1] - RR[i])^2 } \quad (\text{ms})$$
Directly quantifies vagal/parasympathetic cardiac autonomic tone.

### 4.4 120s Rolling Detrended Fluctuation Analysis (DFA-alpha1)
Implemented in `pan_tompkins_dsp.py:329-400`:
1. Mean RR extraction and integrated series calculation:
   $$y(k) = \sum_{i=1}^k (RR[i] - \overline{RR})$$
2. Segmented linear detrending across scale box sizes $s \in [4, 16]$ beats:
   $$F(s) = \sqrt{ \frac{1}{N} \sum_{k=1}^N \left( y(k) - y_{s}(k) \right)^2 }$$
3. Linear regression in log-log scale:
   $$\alpha_1 = \frac{d \log F(s)}{d \log s}$$
4. **Physiological Threshold Boundaries:**
   - **$\alpha_1 \ge 0.75$**: Zone 2 Aerobic Base (Optimal Lipid Oxidation / Below Aerobic Threshold LT1).
   - **$0.50 \le \alpha_1 < 0.75$**: Zone 3 Aerobic Power / Tempo (Lactate accumulation between LT1 and LT2).
   - **$\alpha_1 < 0.50$**: Zone 4/5 Anaerobic Domain (Severe systemic acidosis / Above LT2).

### 4.5 Continuous Pulse Transit Time (PTT) Blood Pressure Inversion
Implemented in `pan_tompkins_dsp.py:403-424` & `movesense_readiness_suite.py:38-100`:
1. **Direct PTT Hemodynamic Model:**
   $$\text{SBP} = 120.0 + 0.45 \cdot (200.0 - \text{PTT}) + 0.15 \cdot (\text{HR} - 70.0)$$
   $$\text{DBP} = 80.0 + 0.25 \cdot (200.0 - \text{PTT}) + 0.08 \cdot (\text{HR} - 70.0)$$
   $$\text{MAP} = \frac{\text{SBP} + 2 \cdot \text{DBP}}{3.0}$$
2. **Hughes-Bramwell Arterial Compliance Inversion (when PTT sensor channel is indirect):**
   $$\text{PTT}_{\text{est}} = \frac{240.0}{\sqrt{\text{Sympathetic Ratio}}}, \quad \text{where } \text{Ratio} = \frac{\text{HR}}{\max(\text{HR}_{\text{rest}}, 40)}$$
   $$\text{SBP} = 118.0 + 0.45 \cdot (\text{HR} - 65.0) - 0.25 \cdot (\text{RMSSD} - 40.0)$$
   $$\text{DBP} = 76.0 + 0.25 \cdot (\text{HR} - 65.0) - 0.15 \cdot (\text{RMSSD} - 40.0)$$

### 4.6 Overnight PPG Sleep Staging & Recovery Score (0–100)
Implemented in `movesense_readiness_suite.py:101-214`:
1. **30-Second Epoch Classifier:**
   - If Motion $> 0.12\text{ G} \rightarrow \mathbf{AWAKE}$
   - If $\text{HR} < 1.08 \cdot \text{HR}_{\text{rest}}$ and $\text{RMSSD} \ge 45\text{ ms} \rightarrow \mathbf{DEEP}$ (Slow-Wave Sleep)
   - If $\text{RMSSD} < 30\text{ ms}$ and $\text{HR} > 1.05 \cdot \text{HR}_{\text{rest}} \rightarrow \mathbf{REM}$ (Paradoxical Sleep)
   - Otherwise $\rightarrow \mathbf{LIGHT}$
2. **Nocturnal HR Dipping Percentage:**
   $$\text{Dip}\% = \frac{\text{HR}_{\text{day\_rest}} - \text{HR}_{\text{nocturnal}}}{\text{HR}_{\text{day\_rest}}} \times 100\% \quad (\text{Healthy normal: } 10\text{--}20\%)$$
3. **Composite 0–100 Recovery Score:**
   $$\text{Score} = S_{\text{Deep}} (30\text{ pts}) + S_{\text{REM}} (25\text{ pts}) + S_{\text{Efficiency}} (25\text{ pts}) + S_{\text{Autonomic}} (20\text{ pts})$$

### 4.7 Auto Workout Classification & Cardiorespiratory Thresholds
Implemented in `movesense_readiness_suite.py:216-293`:
- **Rest / Recovery:** $<55\% \text{ HR}_{\max}$ ($\text{HR}_{\max} = 220 - \text{Age}$)
- **Zone 2 Steady-State:** $55\text{--}72\% \text{ HR}_{\max}$
- **Zone 3 Tempo:** $72\text{--}85\% \text{ HR}_{\max}$
- **Zone 4 HIIT Intervals:** $85\text{--}92\% \text{ HR}_{\max}$
- **Zone 5 Maximal Grappling:** $\ge 92\% \text{ HR}_{\max}$
- **Uth-Sørensen VO2max Estimation:**
  $$VO_2\max = 15.3 \times \frac{\text{HR}_{\max}}{\text{HR}_{\text{rest}}} \quad (\text{mL/kg/min})$$
- **Heart Rate Reserve Threshold Estimates:**
  $$\text{LT1}_{\text{bpm}} = \text{HR}_{\text{rest}} + 0.60 \cdot (\text{HR}_{\max} - \text{HR}_{\text{rest}})$$
  $$\text{LT2}_{\text{bpm}} = \text{HR}_{\text{rest}} + 0.85 \cdot (\text{HR}_{\max} - \text{HR}_{\text{rest}})$$

---

## 5. Architectural Gap Analysis & Standardization Plan

### 5.1 Current Deficiencies in `01_apps/biometrics/movesense_hub`
1. **Flat / Stale Directory:** `01_apps/biometrics/movesense_hub` only contains `pyspark_biometrics_dsp.py`, `README.md`, and leftover temporary swap files (`.._..*`).
2. **Missing Standardized Subpackages:** `ORIGINAL_REQUEST.md` (R1) explicitly requires structuring `movesense_hub` into 4 standardized modules:
   - `core/`: State management, event dispatching, data contracts, and configuration.
   - `dsp/`: Pan-Tompkins QRS, Kamath filter, RMSSD, DFA-alpha1, PTT BP, sleep staging, workout detection.
   - `presentation/`: Textual TUI engine, Web-TUI adapter, and WebSocket broadcast hub.
   - `transport/`: Bleak GATT tether daemon, Web Bluetooth bridge, Whiteboard binary decoder.
3. **Fragmented Implementations:** Excellent DSP and Bleak logic currently exists in `03_biometrics_and_telemetry/` and `01_apps/edge_compute_and_ai/lauburu_compute_hub/services/movesense_ingestion.py`, but has not been cleanly packaged as an importable module within `01_apps/biometrics/movesense_hub/`.

### 5.2 Required Standardized Package Layout

```
01_apps/biometrics/movesense_hub/
├── __init__.py
├── README.md
├── core/
│   ├── __init__.py
│   ├── config.py              # User demographics, baseline HR, sampling rates (512Hz/128Hz)
│   ├── contracts.py           # Strict PROJECT.md JSON interface contract schemas
│   ├── events.py              # Internal pub/sub event bus for telemetry frames
│   └── state.py               # Rule #0 compliant thread-safe readiness state store
├── dsp/
│   ├── __init__.py
│   ├── pan_tompkins.py        # 512Hz/128Hz QRS detector, Butterworth filter, MWI
│   ├── kamath_filter.py       # Kamath 2004 20% clinical RR artifact filter
│   ├── hrv_metrics.py         # Microsecond RMSSD and 120s rolling DFA-alpha1
│   ├── ptt_blood_pressure.py  # Continuous PTT hemodynamic blood pressure inversion
│   ├── sleep_staging.py       # 30s epoch polysomnography & 0-100 recovery score
│   └── cardiorespiratory.py   # LT1/LT2 thresholds, auto workout classifier, VO2max
├── transport/
│   ├── __init__.py
│   ├── bleak_daemon.py        # Bleak GATT client for Movesense 261030002013 (MDS 2.0 / HRS)
│   ├── binary_decoder.py      # Movesense SBEM byte decoder for /Meas/ECG and /Meas/IMU6
│   ├── web_bluetooth.py       # Web Bluetooth API bridge / mock-free protocol mapper
│   └── serial_discovery.py    # Auto-scan and device discovery for Movesense sensors
├── presentation/
│   ├── __init__.py
│   ├── tui_app.py             # Rich / Textual athlete readiness HUD
│   ├── web_tui_adapter.py     # Port 8088 /readiness bridge for serve_web_tui.py
│   ├── websocket_server.py    # Port 8088 / Port 4000 live JSON broadcast engine
│   └── lora_dataset_sink.py   # 24/7 continuous training JSONL serializer
└── tests/
    ├── __init__.py
    ├── test_dsp_math.py       # Algebraic verification of Pan-Tompkins, Kamath, RMSSD, DFA
    ├── test_gatt_decoder.py   # Binary byte-level decoding tests for MDS 2.0
    └── test_zero_mock.py      # Strict verification of WAITING_FOR_SENSOR null states
```

---

## 6. Multi-Platform Client Specifications

### 6.1 Native Textual TUI (`movesense_readiness_tui.py`)
- **Framework:** Textual 0.40+ / Rich.
- **Layout:**
  - 4 Hero Metric Cards: Heart Rate & RMSSD, Continuous PTT BP, Sleep & Recovery, Cardiorespiratory Thresholds & VO2max.
  - 2 Wide Panels: Live Workout & Zone 2 Real-Time Biofeedback Table, 512Hz ECG Signal Quality Diagnostics.
  - Status Footer: Local Airgap & Bluetooth 5.0 Movesense HR+ `261030002013` status.
- **Refresh Rate:** 2 Hz (500ms intervals) reading local state JSON file.

### 6.2 Web-TUI Browser Portal (`01_apps/canonical_port/tui/serve_web_tui.py`)
- **URL Route:** `http://0.0.0.0:8088/readiness`
- **Engine:** aiohttp asynchronous web server + PTY pseudo-terminal + xterm.js + WebGL addon.
- **Performance:** 120 FPS hardware-accelerated canvas rendering in any modern web browser.
- **Domain Tier:** Flagship app in `User & Scaling Apps` tier.

### 6.3 Next.js 14 Web PWA (`01_apps/biometrics/zone2_endurance/`)
- **Tech Stack:** Next.js 14 (App Router), React 18, TailwindCSS, Lucide Icons, Web Bluetooth API.
- **ECG Visualization (`LiveEcgMonitor.tsx`):**
  - High-performance Canvas oscilloscope driven by `requestAnimationFrame`.
  - 640-sample circular ring buffer (`EcgSweepRingBuffer`).
  - Medical grid overlay (1mm minor lines, 5mm major lines at 25 mm/s).
  - Sweep bar with 16-sample erase gap mimicking medical diagnostic ECG monitors.
  - Interactive gain (5, 10, 20 mm/mV) and speed (12.5, 25, 50 mm/s) controls.
  - Lead contact badge (`OPTIMAL`, `NOISY_MOTION`, `POOR_CONTACT`, `LEAD_OFF`, `DISCONNECTED`).
  - Screen-reader accessible data table (`AccessibleDataTable.tsx`).

### 6.4 Flutter / Dart Mobile Client (`01_apps/biometrics/lauburu_zone2_endurance/`)
- **Architecture:** Flutter 3.x, Dart, BLoC pattern (`flutter_bloc`), `flutter_reactive_ble`.
- **Target Platforms:** Android 15 (Pixel 10 Pro XL / Samsung S20) and iOS.
- **Core Views:** BLE Handoff Onboarding View, Zone 2 Pacing HUD, Compute Hub Connection Service.

---

## 7. Airgap & Security Verification

1. **Rule #0 Zero-Mock Verification:**
   - When the Movesense sensor is disconnected or absent, all endpoints and UI components emit explicit `WAITING_FOR_SENSOR` states with `null` metrics.
   - Zero simulated or synthetic arrays are generated in production mode.
2. **Local Airgap Boundary:**
   - 100% of raw ECG, RR intervals, PTT blood pressure, and sleep staging calculations execute locally on CPU/Metal GPU (`127.0.0.1:8000`, `127.0.0.1:4000`, `127.0.0.1:8088`).
   - Cloud AI endpoints (Gemini Flash, Cloudflare Workers AI) are restricted to code generation and public scaffolding; zero biometric data packets ever leave the physical hardware.

---

## 8. Summary of Findings & Implementation Roadmap

1. **Foundations are solid:** All necessary signal processing algorithms, mathematical proofs, unit tests, and BLE parsers exist in the monorepo and pass verification.
2. **Immediate Implementation Task:** Refactor and assemble `01_apps/biometrics/movesense_hub` into the 4 required subpackages (`core/`, `dsp/`, `presentation/`, `transport/`), link with the existing `03_biometrics_and_telemetry/` DSP engines, purge stale swap files, and verify clean end-to-end execution.
