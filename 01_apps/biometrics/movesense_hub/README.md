# 💓 Movesense Physiological Readiness & Biometrics Hub

**Subsystem:** `01_apps/biometrics/movesense_hub`  
**Version:** `1.0.0-CANONICAL`  
**Security:** 100% Strict Local Airgap Protected (0% Biometrics Cloud Egress)  
**Rule #0 Guarantee:** Strictly zero-mock and zero-simulated data. Disconnected states emit `WAITING_FOR_SENSOR` with null metrics.

---

## 🏛️ 1. Architecture Overview

The Movesense Hub is structured into 4 decoupled, commercial-grade subpackages:

```
01_apps/biometrics/movesense_hub/
├── __init__.py                # Package root exports, versioning, convenience factory
├── README.md                  # Comprehensive subsystem documentation
├── pyspark_biometrics_dsp.py  # PySpark MLlib large-scale telemetry analytics
├── core/                      # Configuration, state management, interface contracts
│   ├── __init__.py
│   ├── config.py              # MovesenseHubConfig (device serial 261030002013, 512Hz/128Hz)
│   └── models.py              # Dataclasses & BiometricsStateStore (Rule #0 compliant)
├── dsp/                       # Medical-grade digital signal processing & physiological math
│   ├── __init__.py
│   ├── pan_tompkins.py        # 512Hz/128Hz 4th-order Butterworth, derivative, squaring, 150ms MWI, dual-threshold QRS
│   ├── hemodynamics_bp.py     # Continuous PTT Blood Pressure (SBP/DBP/MAP) inversion
│   ├── sleep_scoring.py       # 30s epoch sleep staging (Deep/REM/Light/Awake) & 0-100 recovery score
│   └── zone2_coaching.py      # DFA-alpha1 aerobic mapping, auto workout detection, VO2max, LT1/LT2
├── transport/                 # Hardware communication & protocol decoders
│   ├── __init__.py
│   ├── bleak_daemon.py        # Bleak GATT daemon (Movesense MDS 2.0 & SIG HRS 0x2A37)
│   └── web_ble_bridge.py      # Web Bluetooth API & WebSocket client bridge
└── presentation/              # Multi-platform visualization & Web-TUI adapters
    ├── __init__.py
    ├── tui.py                 # Native Textual TUI dashboard HUD
    └── web_adapter.py         # Web-TUI Port 8088 /readiness launcher & Next.js Canvas Oscilloscope PWA connector
```

---

## 🔬 2. Mathematical Models & Digital Signal Processing

### 2.1 Pan-Tompkins (1985) QRS Detection
- **Bandpass Filter:** 4th-order zero-phase Butterworth ($0.5\,\text{Hz} - 40.0\,\text{Hz}$).
- **5-Point Central Derivative:**
  $$d[n] = \frac{1}{8T}(-x[n-2] - 2x[n-1] + 2x[n+1] + x[n+2])$$
- **Nonlinear Squaring Transform:**
  $$s[n] = (d[n])^2$$
- **Moving Window Integration (MWI):** $N = 150\,\text{ms}$ window.
- **Adaptive Dual Thresholds:**
  $$\text{Threshold}_{I1} = \text{NPK} + 0.25 \times (\text{SPK} - \text{NPK}), \quad \text{Threshold}_{I2} = 0.5 \times \text{Threshold}_{I1}$$
- **Refractory Lockout:** $200\,\text{ms}$ physiological lockout.

### 2.2 Kamath et al. (2004) Clinical Artifact Filter
- Filters out ectopic bursts and premature ventricular contractions (PVCs):
  $$\frac{|RR[i] - RR[i-1]|}{RR[i-1]} \le 0.20$$

### 2.3 Short-Term HRV RMSSD
- Microsecond-precision Root Mean Square of Successive Differences:
  $$\text{RMSSD} = \sqrt{\frac{1}{N-1}\sum_{i=1}^{N-1} (RR[i+1] - RR[i])^2}$$

### 2.4 Detrended Fluctuation Analysis (DFA-alpha1)
- Vectorized short-term scaling exponent over rolling RR history ($s \in [4, 16]$ beats).
- Aerobic Domain Thresholds:
  - $\alpha_1 \ge 0.75$: Zone 2 (Aerobic Base Endurance / FatMax)
  - $0.50 \le \alpha_1 < 0.75$: Zone 3 (Tempo / Aerobic Power)
  - $\alpha_1 < 0.50$: Zone 4/5 (Anaerobic / Severe Acidosis)

### 2.5 Pulse Transit Time (PTT) Blood Pressure Inversion
- Hughes-Bramwell arterial wave propagation inversion:
  $$\text{SBP} = 120.0 + 0.45 \times (200.0 - \text{PTT}) + 0.15 \times (\text{HR} - 70.0)$$
  $$\text{DBP} = 80.0 + 0.25 \times (200.0 - \text{PTT}) + 0.08 \times (\text{HR} - 70.0)$$
  $$\text{MAP} = \frac{\text{SBP} + 2 \times \text{DBP}}{3.0}$$

### 2.6 Overnight PPG Sleep Staging & Recovery Scoring
- 30s epoch classification: `AWAKE`, `DEEP` (Slow Wave Sleep), `REM`, `LIGHT`.
- Nocturnal Heart Rate Dipping:
  $$\text{Dip}\% = \frac{\text{HR}_{\text{day}} - \text{HR}_{\text{night}}}{\text{HR}_{\text{day}}} \times 100\%$$
- Composite Recovery Score (0–100): Deep Sleep (30%), REM (25%), Sleep Efficiency (25%), Autonomic Balance (20%).

### 2.7 Cardiorespiratory Capacity & HRR Thresholds
- **Uth-Sørensen VO2max:**
  $$\text{VO}_2\text{max} = 15.3 \times \frac{\text{HR}_{\max}}{\text{HR}_{\text{rest}}}$$
- **Heart Rate Reserve (HRR) Thresholds:**
  $$\text{LT1} = \text{HR}_{\text{rest}} + 0.60 \times (\text{HR}_{\max} - \text{HR}_{\text{rest}})$$
  $$\text{LT2} = \text{HR}_{\text{rest}} + 0.85 \times (\text{HR}_{\max} - \text{HR}_{\text{rest}})$$

---

## 📡 3. Hardware & Protocol Specifications

- **Target Peripheral:** Movesense Medical HR+ (Serial `261030002013`, MAC `C1DB5043-8F89-88E8-46A3-BBD4ED83FC88`).
- **GATT Services:**
  - Movesense MDS 2.0 Whiteboard: `34800001-7185-4d5d-b431-b30e393d9e05`
  - Bluetooth SIG HRS: `0000180d-0000-1000-8000-00805f9b34fb` (`0x2A37`)
  - Battery Service: `0000180f-0000-1000-8000-00805f9b34fb` (`0x2A19`)

---

## 💻 4. Python Usage & Code Examples

```python
import importlib
mhb = importlib.import_module("01_apps.biometrics.movesense_hub")

# 1. Initialize Hub
state_store, pipeline, bridge = mhb.create_hub()

# 2. Process Raw 512Hz ECG window
result = mhb.process_raw_ecg([0.0, 1.2, 3.8, -1.0, 0.0] * 100, sample_rate_hz=512, ptt_ms=195.0)
print(result["status"], result["heart_rate_bpm"], result["ptt_blood_pressure"])

# 3. Retrieve Interface Contract for UI / PWA
contract = state_store.get_interface_contract()
print("UI Contract Payload:", contract)
```

---

## 🧪 5. Verification & Test Execution

Run the complete biometrics DSP and hub test suites:

```bash
# Run standalone DSP test suite
python3 -m pytest 03_biometrics_and_telemetry/tests/test_movesense_dsp_suite.py -v

# Run modular hub test suite
python3 -m pytest 03_biometrics_and_telemetry/tests/test_movesense_hub_modular_suite.py -v

# Verify modular import
python3 -c "import importlib; mhb = importlib.import_module('01_apps.biometrics.movesense_hub'); print('Movesense Hub Version:', mhb.__version__)"
```
