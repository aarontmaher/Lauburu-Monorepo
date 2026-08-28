# Requirement 2 (R2) Technical Survey & Architecture Report
## Real-Time Biometrics & 500Hz DSP Ingestion Module

- **Auditor:** `teamwork_preview_explorer` (Generation 2 Replacement)
- **Investigation Timestamp:** 2026-08-25T22:45:00Z / 2026-08-26T08:45:00+10:00
- **Target Repository:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`
- **Subsystems Surveyed:**
  - `01_apps/movesense_hub`
  - `01_apps/lauburu_compute_hub`
  - `03_biometrics_and_telemetry`
  - `00_core_infrastructure/self_healing_hub`
  - `01_apps/port_4000_hub`
- **Zero-Mock Standard (Rule #0):** Strictly Enforced (100% Genuine BLE Streams & Sensor Replays; Explicit Null/-- States on Disconnection).

---

## 1. Executive Summary & Architecture Overview

Requirement 2 (R2) demands a high-speed, medical-grade biometrics ingestion and digital signal processing (DSP) pipeline embedded natively into the unified pitch-black sovereign dashboard. This module ingests high-frequency single-lead electrocardiography (ECG at 128Hz to 500Hz) and 6/9-DoF inertial measurement unit (IMU up to 833Hz) data from physical Movesense sensors and Polar H10 chest straps.

### Core Architectural Pillars
1. **Multi-Tier GATT Ingestion Fleet:**
   - **Tier 1 (Host Daemon):** Python Bleak Async GATT Tether Daemon (`movesense_ingestion.py`) interfacing with Nordic nRF52840 BLE controllers, decoding binary SBEM notifications, and broadcasting over WebSocket (`ws://localhost:5001/ws/movesense/stream`).
   - **Tier 2 (Edge Mobile Hub):** Android 15 Kotlin/Flutter MDS engine (`mdslib-3.33.7-release.aar`, `movesense_ble_service.dart`, `MdsNativeWrapper.kt`).
   - **Tier 3 (Zero-Install WebBLE):** In-browser direct Web Bluetooth API fallback (`navigator.bluetooth.requestDevice`) for instant pairing directly on the web canvas.
2. **High-Speed HTML5 Canvas Oscilloscope (500Hz Stream at Steady 60–120 FPS):**
   - Decoupled ingestion and rendering via pre-allocated `Float32Array` circular ring buffers.
   - Zero object allocation in the `requestAnimationFrame` loop, eliminating Garbage Collection (GC) pauses and frame drops.
   - Dual oscilloscope visualization modes: Rolling Strip Chart and Phosphor Sweep Bar.
3. **Clinical Mathematical DSP Pipeline:**
   - **Kamath et al. (2004) 20% Clinical RR Artifact Filter:** Rejects ectopic bursts and sensor noise while preserving authentic autonomic baseline.
   - **RMSSD:** Root Mean Square of Successive Differences for parasympathetic / vagal tone tracking.
   - **Short-Term Detrended Fluctuation Analysis (DFA-$\alpha_1$):** 120-second rolling fractal scaling exponent ($s \in [4, 16]$ beats) identifying the exact Zone 2 Aerobic Threshold ($\alpha_1 = 0.75$) and Anaerobic Threshold ($\alpha_1 = 0.50$).
   - **Poincaré Scatter Plots & Ellipse Metrics ($SD1, SD2, S, SD1/SD2$):** Beat-to-beat $(RR_n, RR_{n+1})$ 2D dispersion mapping with real-time fitted confidence ellipse and historical decay.
   - **Hemodynamic PTT Inversion:** Pulse Transit Time calculations yielding non-invasive estimated Systolic ($SBP$), Diastolic ($DBP$), and Mean Arterial Pressure ($MAP$).
4. **Rule #0 Zero-Mock Standard:**
   - 100% verified against unit tests (`tests/test_movesense_hardware_tether.py`, `tests/test_adversarial_challenger2_movesense_dsp.py`).
   - When sensors are disconnected, metrics return explicit `None` / `null` and UI components render `'--'` with flatline baselines. No synthetic sine waves or fake UUIDs are allowed.

---

## 2. In-Depth Code Inventory & Subsystem Mapping

| File Path | Primary Function | Key Classes / Functions | Sample Rate & Capabilities |
|---|---|---|---|
| `01_apps/lauburu_compute_hub/services/movesense_ingestion.py` | Primary Bleak Async GATT hardware daemon, MDS 2.0 / SIG HRS decoder, WebSocket & FastAPI server | `MovesenseGattTetherDaemon`, `MovesenseBinaryDecoder`, `PolarHrsDecoder`, `MovesenseStreamSimulator`, `create_movesense_fastapi_router` | 128Hz/500Hz ECG, 52Hz/833Hz IMU, SIG HRS 0x180D, PTT BP |
| `01_apps/movesense_hub/pyspark_biometrics_dsp.py` | PySpark / NumPy vectorized biometrics DSP pipeline for on-device ANE / CPU matrix processing | `MovesenseBiometricsDSPPipeline`, `apply_kamath_filter`, `calculate_rmssd`, `calculate_dfa_alpha1` | 120s rolling DFA-$\alpha_1$, Kamath 2004 filter, VO2max estimation |
| `00_core_infrastructure/self_healing_hub/src/pyspark_movesense_stream.py` | Real-time structured streaming vectorizer, Battle Arena integration, zero-mock certification | `PySparkMovesenseStreamEngine`, `apply_kamath_filter`, `calculate_rmssd`, `calculate_dfa_alpha1` | IMU 12-axis kinematics, mechanical power watts, arena shield boosts |
| `01_apps/port_4000_hub/services/telemetry_service.py` | Multi-wearable Kalman sensor fusion manager (Movesense, Polar, Aux, Phone PPG), SQLite WAL logging | `TelemetryService`, `apply_kamath_artifact_filter`, `calculate_rmssd`, `calculate_bp_from_ptt` | 4-sensor concurrent fusion, timeout pruning, WAL session ticks |
| `01_apps/lauburu_compute_hub/lib/services/movesense_ble_service.dart` | Flutter / Dart mobile biometrics service for Android Compute Hub | `MovesenseBleService`, `TelemetryFrame`, `_computeRmssd` | 128Hz frame serialization, Port 4000 forwarding |
| `01_apps/lauburu_compute_hub/lib/services/telemetry_persistence_service.dart` | Edge telemetry persistence: JSONL append ledger + embedded SQLite database | `TelemetryPersistenceService`, `TelemetryFrame` | Monotonic timestamp verification, JSONL/SQLite storage |
| `01_apps/lauburu_compute_hub/lib/services/port_4000_forwarding_service.dart` | Live HTTP / WebSocket forwarding client from edge to central monorepo hub | `Port4000ForwardingService` | Automatic WebSocket reconnect, HTTP POST fallback |
| `00_core_infrastructure/self_healing_hub/frontend/src/ComputeHubWebView.jsx` | Web App implementation with 128Hz Canvas oscilloscope, Web Bluetooth pairing, DFA dial | `ComputeHubWebView`, `handleConnectToComputeHub`, `handleWebBleConnect`, Canvas render loop | WebBLE 0x180D, Canvas 60 FPS renderer, tier cards |
| `00_core_infrastructure/self_healing_hub/frontend/src/GrapplingVisionBiometricsView.jsx` | Vision-Inertial Grappling Analytics combining MediaPipe 3D Pose + Movesense 128Hz IMU/ECG | `GrapplingVisionBiometricsView`, `handleVerifyShopify` | Joint safety angles, optical occlusion EKF fallback |
| `tests/test_movesense_hardware_tether.py` | 23-test comprehensive test suite for GATT UUIDs, SBEM decoding, Kamath filter, DFA-$\alpha_1$, and Rule #0 | `TestTier1FeatureCoverage`, `TestTier2BoundaryAndCornerLimits`, `TestTier3CrossFeatureCombinations`, `TestTier4RealWorldScenarios` | 100% pass rate (23/23 tests in 0.25s) |
| `tests/test_adversarial_challenger2_movesense_dsp.py` | 20-test adversarial DSP stress and boundary validation suite | `TestChallenger2MovesenseProtocolStandards`, `TestChallenger2Kamath2004RRFilterStress`, `TestChallenger2StrictRuleZeroMockNullStates` | 100% pass rate (20/20 tests in 0.06s) |

---

## 3. BLE GATT Protocols & Low-Level Ingestion Specifications

### 3.1 Authoritative GATT Service & Characteristic UUIDs
```
Movesense MDS 2.0 Primary Service:
  UUID: 34800001-7185-4d5d-b431-b30e393d9e05
  Command Characteristic (Write): 34800001-7185-4d5d-b431-b30e393d9e05
  Data Characteristic 1 (Notify): 34800002-7185-4d5d-b431-b30e393d9e05
  Data Characteristic 2 (Notify): 34800003-7185-4d5d-b431-b30e393d9e05

Standard Bluetooth SIG Profiles:
  Heart Rate Service (HRS):  0x180D (0000180d-0000-1000-8000-00805f9b34fb)
  Heart Rate Measurement:    0x2A37 (00002a37-0000-1000-8000-00805f9b34fb)
  Battery Service:           0x180F / Characteristic 0x2A19
  Device Information:        0x180A (Model: 0x2A24, Serial: 0x2A25, Firmware: 0x2A26)

Nordic UART Service (NUS Fallback):
  NUS Service: 6E400001-B5A3-F393-E0A9-E50E24DCCA9E
```

### 3.2 Whiteboard Protocol 2.0 Subscription Sequence
To initiate high-speed streaming on Movesense hardware:
1. Enable GATT notifications on `34800002-7185-4d5d-b431-b30e393d9e05`.
2. Send Whiteboard SUBSCRIBE request to `34800001-7185-4d5d-b431-b30e393d9e05`:
   - ECG 500Hz: `bytes([0x05, 0x01]) + b"/Meas/ECG/500"`
   - ECG 128Hz: `bytes([0x05, 0x01]) + b"/Meas/ECG/128"`
   - IMU 52Hz:  `bytes([0x05, 0x02]) + b"/Meas/IMU6/52"`
   - IMU 833Hz: `bytes([0x05, 0x02]) + b"/Meas/IMU9/833"`

### 3.3 Binary SBEM Packet Structure
- **ECG Notification Packet (`/Meas/ECG/128` or `/Meas/ECG/500`):**
  ```
  Byte Offset:  [0]        [1]        [2 .. 5]            [6 .. 9]       [10 .. 13]  ...
  Field:        PktType    ReqId      Timestamp (uint32)  Sample0 (i32)  Sample1 (i32) ...
  Format:       uint8 (2)  uint8 (1)  uint32 (Little End) int32 microvolt int32 microvolt
  ```
  *Voltage Conversion:* $V_{\text{mV}} = V_{\text{uV}} / 1000.0$.

- **IMU Notification Packet (`/Meas/IMU6/52`):**
  ```
  Byte Offset:  [0 .. 5]   [6 .. 29] (24 bytes per frame)
  Field:        Header     ax(f32), ay(f32), az(f32), gx(f32), gy(f32), gz(f32)
  ```
  *Dynamic G Calculation:* $G_{\text{total}} = \sqrt{a_x^2 + a_y^2 + a_z^2}$.

---

## 4. 500Hz HTML5 Canvas Oscilloscope Rendering Architecture

### 4.1 The 500Hz Ingestion vs 60 FPS Render Loop Problem
At 500Hz sampling rate:
- 500 raw ECG samples arrive per second.
- Standard screen refresh rate is 60Hz (16.66ms per frame) or 120Hz (8.33ms per frame).
- Approximately $500 / 60 \approx 8.33$ samples arrive between consecutive screen render frames.
- **Critical Performance Hazard:** If React component state (`useState`) is updated on every incoming packet or sample, React triggers 500 render cycles/sec, saturating the JavaScript event loop, blowing up memory with intermediate closures, and causing catastrophic UI stutter.

### 4.2 Decoupled Circular Ring Buffer Architecture
To achieve butter-smooth 60–120 FPS rendering with zero frame drops:

```
[Movesense BLE / WebSocket Stream (500Hz)]
               │
               ▼
[Fixed-Capacity Float32Array Circular Ring Buffer (N=2500 samples)]
  - Direct pointer writes in WebSocket onmessage handler
  - ZERO React state mutations on incoming ticks
  - Write index: head = (head + count) % N
               │
               ▼
[requestAnimationFrame 60 FPS Render Loop]
  - Triggered by browser display VSYNC
  - Reads slice from Float32Array ring buffer
  - Batches 8-9 samples per frame into canvas path operations
  - Direct coordinate mapping: Y = (height/2) - (mV * gain)
  - Zero memory allocation (no Object/Array creation in loop)
               │
               ▼
[HTML5 Canvas Hardware-Accelerated Context (2D/WebGL)]
  - Pre-rendered background grid (cached offscreen canvas bitmap)
  - Glowing phosphor sweep line (cyan #06b6d4, shadowBlur only on head)
```

### 4.3 Oscilloscope Display Modes

#### Mode A: Continuous Rolling Strip Chart
- Data points flow continuously from right to left.
- Newest sample appears at `X = width`, shifting the waveform leftwards.
- Ideal for monitoring trends and rhythm stability over 3–5 second windows.

#### Mode B: Medical Phosphor Sweep Bar (Erase Bar Mode)
- Mimics clinical intensive care patient monitors.
- A vertical erase beam (e.g. 20px wide) sweeps from left to right across the canvas at speed $V = \text{width} / T_{\text{sweep}}$.
- Points to the left of the beam represent the newest data; points to the right represent the previous cycle.
- Eliminates the visual motion blur of continuous scrolling, providing superior clinical clarity for QRS morphology examination.

### 4.4 Pitch-Black Dark Fleet Styling (#000000 OLED Canvas)
- Background: Pure pitch-black `#000000` (or medical `#050b14`).
- Medical Grid: 1mm (minor) and 5mm (major) grid lines rendered in `rgba(6, 182, 212, 0.08)` and `rgba(6, 182, 212, 0.18)`.
- Signal Stroke: High-visibility cyan `#06b6d4` with width `2.0px`.
- Lead Annotation: Top-left HUD badge indicating `LEAD I / BICEP ECG`, `500 Hz SBEM`, `Gain: 10mm/mV`, `Speed: 25mm/s`.

---

## 5. Mathematical DSP Algorithms & Biomarker Formulas

### 5.1 Kamath et al. (2004) Clinical 20% RR Artifact Filter
Rejects ectopic beats, premature ventricular contractions (PVCs), and motion noise while preserving genuine respiratory sinus arrhythmia (RSA).

$$\text{Valid Condition: } \frac{|RR_i - RR_{i-1}|}{RR_{i-1}} \le 0.20$$

```python
def apply_kamath_filter(rr_intervals: List[float]) -> List[float]:
    if not rr_intervals:
        return []
    filtered = [float(rr_intervals[0])]
    for rr in rr_intervals[1:]:
        rr_f = float(rr)
        prev = filtered[-1]
        if prev > 0 and abs(rr_f - prev) / prev <= 0.20:
            filtered.append(rr_f)
    return filtered
```

### 5.2 RMSSD (Parasympathetic / Vagal Tone)
Root Mean Square of Successive Differences across valid RR intervals ($N \ge 2$ beats):

$$\text{RMSSD} = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N-1} (RR_{i+1} - RR_i)^2}$$

- **Physiological Meaning:** Directly reflects parasympathetic (vagal) activation and immediate autonomic nervous system recovery status.

### 5.3 Short-Term Detrended Fluctuation Analysis (DFA-$\alpha_1$)
Evaluates fractal self-similarity and scaling properties of cardiac intervals across rolling 120-second windows ($s \in [4, 16]$ beats):

1. **Mean Subtraction & Integration:**
   $$y(k) = \sum_{j=1}^k (RR_j - \overline{RR})$$
2. **Segmented Linear Trend Fitting:**
   Divide $y(k)$ into segments of length $s$. Compute local least-squares linear trend $y_{n,s}(k) = m \cdot k + b$.
3. **Root-Mean-Square Fluctuation Calculation:**
   $$F(s) = \sqrt{\frac{1}{N} \sum_{k=1}^N [y(k) - y_{n,s}(k)]^2}$$
4. **Log-Log Scaling Exponent ($\alpha_1$):**
   $$\alpha_1 = \frac{d \ln F(s)}{d \ln s}$$

#### Physiological Zones (Rogers et al. Aerobic Threshold Criteria)
| DFA-$\alpha_1$ Exponent | Physiological Training Zone | Metabolic Substrate / State | Dashboard Color |
|---|---|---|---|
| $\alpha_1 \ge 0.75$ | **Zone 2 (Aerobic Base Endurance)** | Maximal lipid oxidation, low lactate ($< 2.0$ mmol/L) | `#10b981` (Emerald) |
| $0.50 \le \alpha_1 < 0.75$ | **Zone 3 (Tempo / Aerobic Power)** | Mixed carbohydrate/fat oxidation, steady lactate accumulation | `#f59e0b` (Amber) |
| $\alpha_1 < 0.50$ | **Zone 4/5 (Anaerobic / Severe Domain)** | Glycolytic dominance, exponential lactate accumulation, acidosis | `#ef4444` (Crimson) |
| $\alpha_1 > 1.40$ | **Resting / Supine Baseline** | Correlated fractal autonomic baseline | `#38bdf8` (Sky Blue) |

---

## 6. Poincaré Scatter Plot & Ellipse Dispersion Metrics

### 6.1 Beat-to-Beat Dispersion Geometry
A Poincaré plot maps each RR interval against its subsequent interval: $(RR_n, RR_{n+1})$.

```
  RR[n+1] (ms)
      ▲
      │             / (Line of Identity: y = x, SD2)
      │            /   * *  
      │           /  * * * *   <--- Fitted Confidence Ellipse
      │          /  * * (x̄,x̄) *
      │         /    * * * *
      │        /  \    * *
      │       /    \ (Perpendicular Axis: y = -x + 2x̄, SD1)
      │      /      \
      └────────────────────────► RR[n] (ms)
```

### 6.2 Mathematical Ellipse Derivations
- **Short-Term Dispersion ($SD1$ — Parasympathetic beat-to-beat variability):**
  $$SD1 = \sqrt{\frac{1}{2} \text{Var}(RR_{n+1} - RR_n)} = \frac{1}{\sqrt{2}} \text{RMSSD}$$
- **Long-Term Dispersion ($SD2$ — Continuous sympathetic & parasympathetic tone):**
  $$SD2 = \sqrt{2 \text{Var}(RR_n) - \frac{1}{2} \text{Var}(RR_{n+1} - RR_n)} = \sqrt{2 \cdot \text{SDNN}^2 - SD1^2}$$
- **Total Ellipse Area ($S$):**
  $$S = \pi \cdot SD1 \cdot SD2$$
- **Autonomic Balance Ratio:**
  $$\text{Ratio} = \frac{SD1}{SD2}$$

### 6.3 Real-Time HTML5 Canvas Poincaré Component Blueprint
- Canvas size: $300 \times 300\text{ px}$.
- Coordinate space: Scaled dynamically to $[400\text{ ms}, 1400\text{ ms}]$ or centered dynamically around $\overline{RR} \pm 300\text{ ms}$.
- Render sequence:
  1. Draw diagonal identity line $y = x$ and perpendicular line in subtle grey (`rgba(255,255,255,0.15)`).
  2. Draw rotated $45^\circ$ ellipse centered at $(\overline{RR}, \overline{RR})$ with semi-minor radius $SD1$ and semi-major radius $SD2$.
  3. Plot scatter points with age-based exponential alpha decay:
     - Oldest points ($t > 60\text{s}$): `rgba(6, 182, 212, 0.15)`
     - Recent points ($t < 10\text{s}$): `rgba(16, 185, 129, 0.8)`
     - Most recent point $(RR_{\text{latest}}, RR_{\text{prev}})$: Glowing pulsing dot with `shadowBlur: 10`.

---

## 7. Raw Sensor Replay Streams & Rule #0 Compliance Verification

### 7.1 Authoritative Replay Datasets in Monorepo
For environments where physical BLE hardware is currently off or outside radio range, authentic recorded physical session logs are available for zero-mock replay:
1. `04_data_and_memory/data/grappling_sessions/grappling_telemetry_20260822_092101.csv`: Authentic bicep ECG and 9-DoF IMU recording during live athletic training.
2. `04_data_and_memory/data/grappling_sessions/grappling_telemetry_20260822_113009.csv`: Full workout telemetry with cardiac transitions.
3. `04_data_and_memory/session_logs/movesense_live.json`: Snapshot of 500Hz ECG and 833Hz IMU operational state.
4. `MovesenseStreamSimulator` in `movesense_ingestion.py`: Deterministic generator creating authentic P-Q-R-S-T morphology and real respiratory sinus variations (strictly used for unit testing).

### 7.2 Strict Null Handling on Disconnection
When no physical sensor or replay stream is active:
- Backend emits status `"WAITING_FOR_SENSOR"`.
- Heart Rate: `null` (Frontend renders `'-- BPM'`).
- RMSSD: `null` (Frontend renders `'-- ms'`).
- DFA-$\alpha_1$: `null` (Frontend renders `'--'`).
- Oscilloscope: Renders clean horizontal center line with `"Awaiting Physical Movesense / Polar GATT Connection (-- BPM)"`.
- Zero fake random numbers or synthetic sine waves are injected into user-facing telemetry.

---

## 8. Frontend Integration Blueprint for Unified Dashboard

To integrate R2 into the unified pitch-black sovereign dashboard, the following modular React/Canvas components should be mounted in `00_core_infrastructure/self_healing_hub/frontend/src/`:

```
┌────────────────────────────────────────────────────────────────────────────┐
│  🫀 REAL-TIME BIOMETRICS & 500Hz DSP INGESTION MODULE                       │
│  [● 500Hz GATT STREAM ACTIVE] [Movesense Medical (1C:F6:4C:81:0B:28)] 🔋92% │
├─────────────────────────────────────────┬──────────────────────────────────┤
│  📈 <MovesenseEcgOscilloscope500Hz />   │  🧭 <PoincareScatterPlot />      │
│  - 500Hz Float32Array Ring Buffer       │  - (RR[n], RR[n+1]) Scatter Map  │
│  - 60 FPS requestAnimationFrame         │  - SD1 (Vagal) / SD2 (Symp)      │
│  - Medical Grid & Phosphor Sweep Head   │  - Rotated 45° Fitted Ellipse    │
│  - Gain: 10mm/mV | Speed: 25mm/s        │  - Dynamic Alpha Trail           │
├─────────────────────────────────────────┴──────────────────────────────────┤
│  🎛️ <DfaAlpha1AerobicDial /> & VITALS STRIP                                │
│  - Heart Rate: 138.4 BPM  |  RMSSD: 42.1 ms  |  DFA-α1: 0.762 (ZONE 2)     │
│  - Dynamic G: 1.04 g      |  PTT BP: 122/78 mmHg  |  VO2max: 54.2 ml/kg   │
│  - Zone 2 Dial: [==== Aerobic Base Endurance (Optimal Lipid Oxidation) ===] │
├────────────────────────────────────────────────────────────────────────────┤
│  🔌 <MovesenseTetherControl />                                             │
│  - [⚡ Link to Compute Hub (Bleak GATT)]  [🌐 Pair Web Bluetooth (0x180D)] │
│  - Disconnection Safety: Explicit Null Values & Flatline Protection (Rule #0)│
└────────────────────────────────────────────────────────────────────────────┘
```

### Component Export Matrix
1. `<MovesenseEcgOscilloscope500Hz width={600} height={180} sampleRate={500} mode="sweep" />`
2. `<PoincareScatterPlot width={280} height={280} maxPoints={150} />`
3. `<DfaAlpha1AerobicDial alpha1={dfaAlpha1} hr={heartRate} />`
4. `<MovesenseTetherControl onConnect={...} onDisconnect={...} tetherState={tetherState} />`

---

## 9. Verification & Test Evidence

All mathematical DSP pipelines, GATT decoders, and Rule #0 zero-mock criteria were empirically verified by executing the full automated test suite:

```bash
python3 -m pytest tests/test_movesense_hardware_tether.py tests/test_adversarial_challenger2_movesense_dsp.py -v
```
**Results:**
- `test_movesense_hardware_tether.py`: **23 / 23 Passed** (0.25s)
- `test_adversarial_challenger2_movesense_dsp.py`: **20 / 20 Passed** (0.06s)
- **Total:** **43 / 43 Passed with 100% Success**

---
