# Empirical Adversarial Challenge Report — Milestone M1 DSP Suite

**Agent**: Challenger 1 (`teamwork_preview_challenger_m1_1`)  
**Target Subsystem**: `01_apps/biometrics/movesense_hub/dsp/` (`pan_tompkins.py`, `hemodynamics_bp.py`, `sleep_scoring.py`, `zone2_coaching.py`)  
**Overall Risk Assessment**: **MEDIUM-HIGH (Fixes Required for Clinical Reliability)**

---

## 1. Observation

Direct empirical observations from executing adversarial test harnesses (`tests/test_adversarial_biometrics_dsp_stress_challenger1.py`):

### Observation 1.1: Pan-Tompkins MWI Double-Accumulation Defect
- **File**: `01_apps/biometrics/movesense_hub/dsp/pan_tompkins.py:157-164`
- **Code**:
```python
157: window = self.mwi_window
158: running_sum = sum(squared_signal[: min(window, n)])
159: 
160: for i in range(n):
161:     if i >= window:
162:         running_sum += squared_signal[i] - squared_signal[i - window]
163:     elif i > 0:
164:         running_sum += squared_signal[i]
165:     mwi[i] = running_sum / float(min(i + 1, window))
```
- **Execution**: On a constant input `x = [1.0] * 200` at `fs = 512 Hz` (`window = 76`):
  - `mwi[0] = 76.0` (instead of 1.0)
  - `mwi[1] = 38.5`
  - `mwi[76] = 1.9868` (instead of 1.0)
- **Consequence**: When testing extreme tachycardia (220 BPM, 36 true peaks) at 512Hz:
  - `max_mwi = 24268.1033` (due to the false spike at index 0).
  - `min_peak_height = max_mwi * 0.05 = 1213.4052`.
  - True physiological MWI peaks are ~880, so **0 out of 36 peaks are detected** (`len(detected_peaks) == 0`).
  - When streamed through `MovesenseECGPipeline`, the pipeline retains the stale prior HR (e.g. 72.1 BPM) and emits `ACTIVE_STREAMING` with 72 BPM instead of detecting 220 BPM tachycardia.

### Observation 1.2: Kamath 20% Filter Initial Beat Lock-In
- **File**: `01_apps/biometrics/movesense_hub/dsp/pan_tompkins.py:265-287`
- **Code**:
```python
265: cleaned = [float(rr_intervals[0])]
266: artifact_count = 0
267: for i in range(1, len(rr_intervals)):
268:     prev = cleaned[-1]
269:     curr = float(rr_intervals[i])
270:     if prev > 0 and (abs(curr - prev) / prev) <= thresh:
271:         cleaned.append(curr)
...
284:         if next_val is None:
285:             next_val = prev
286:         corrected = (prev + next_val) / 2.0
287:         cleaned.append(round(corrected, 1))
```
- **Execution**: Input `rrs = [5000.0, 800.0, 805.0, 810.0, 800.0, 802.0, 798.0]`.
- **Output**: `cleaned = [5000.0, 5000.0, 5000.0, 5000.0, 5000.0, 5000.0, 5000.0]`, `artifacts_rejected = 6`.
- **Consequence**: All valid physiological beats are permanently corrupted and overwritten with the initial artifact.

### Observation 1.3: Unhandled ZeroDivisionError in Sleep Scoring
- **File**: `01_apps/biometrics/movesense_hub/dsp/sleep_scoring.py:70, 99`
- **Code**:
```python
70: daytime_base = float(daytime_hr_rest) if daytime_hr_rest is not None else (self.hr_rest_baseline * 1.15)
...
99: nocturnal_dip = round(((daytime_base - float(hr_bpm)) / daytime_base) * 100.0, 1) if hr_bpm else None
```
- **Execution**: `engine.compute_overnight_sleep_analysis(hr_bpm=60.0, rmssd_ms=40.0, epoch_stages=['LIGHT'], daytime_hr_rest=0.0)`.
- **Output**: `ZeroDivisionError: float division by zero`.

### Observation 1.4: Rule #0 Violation in Continuous Hemodynamics Model
- **File**: `01_apps/biometrics/movesense_hub/dsp/hemodynamics_bp.py:60, 96-107`
- **Code**: `if hr_bpm is None or (rmssd_ms is None and ptt_ms is None):`
- **Execution**: `model.compute_ptt_blood_pressure(hr_bpm=0.0, rmssd_ms=40.0, ptt_ms=None)`.
- **Output**: Returns `sbp_mmhg=90.0, dbp_mmhg=60.0, map_mmhg=70.0, status="NOMINAL"` for `hr=0.0` (asystole/disconnected), violating Rule #0.

### Observation 1.5: Unhandled ZeroDivisionError in Workout State Classification
- **File**: `01_apps/biometrics/movesense_hub/dsp/zone2_coaching.py:48`
- **Code**: `pct_max = (float(hr_bpm) / float(hr_max)) * 100.0`
- **Execution**: `classify_workout_state(120.0, hr_max=0)`.
- **Output**: `ZeroDivisionError: float division by zero`.

---

## 2. Logic Chain

1. **MWI Defect -> Tachycardia Blindness**:
   - `running_sum` is initialized to the full window sum `sum(squared[:window])`.
   - At iteration `i=0`, `mwi[0]` is assigned `running_sum / 1`, creating an artificial spike 76× higher than the actual signal average.
   - The adaptive threshold `min_peak_height` is derived as `0.05 * max(mwi)`.
   - Because `max(mwi)` is inflated by this initial impulse, `min_peak_height` rises above genuine QRS energy during high-frequency 512Hz tachycardia.
   - Consequently, zero peaks are identified, and `MovesenseECGPipeline` silently displays stale previous heart rate.

2. **Kamath Initial Beat Lock-In**:
   - The filter assumes `cleaned[0] = rr_intervals[0]` is a valid physiological baseline.
   - If the first sample is an artifact, the $\pm 20\%$ window is anchored around the artifact (e.g. $5000 \pm 1000\text{ ms}$).
   - Genuine physiological beats ($800\text{ ms}$) fall outside $[4000, 6000\text{ ms}]$ and are rejected.
   - The lookahead search also fails, falling back to `next_val = prev = 5000.0`.
   - Every subsequent beat is recursively replaced with $5000.0$, causing total telemetry collapse.

3. **Division by Zero & Rule #0 Invariants**:
   - `daytime_hr_rest=0.0` and `hr_max=0` bypass falsy checks (since `0.0 is not None`), causing raw division by zero crashes.
   - `ContinuousPttBloodPressureModel` checks `hr_bpm is None`, allowing non-positive heart rates (`0.0`, `-10.0`) to generate synthetic nominal blood pressure instead of emitting `STANDBY`.

---

## 3. Caveats

- **Hardware RF Noise**: Testing was conducted against mathematically rigorous synthetic ECG models with 0.1-0.3Hz baseline wander, 50Hz hum, EMG Gaussian noise, PVCs, and tachycardia/bradycardia waveforms. Physical Bluetooth radio packet drops were simulated via array truncation rather than live RF fading.
- **PTT Ground Truth**: Hughes-Bramwell arterial wave equations are clinical approximations; absolute blood pressure accuracy requires individual calibration.

---

## 4. Conclusion & Recommended Actions

The core DSP architecture is mathematically sound and adheres to zero-mock principles under nominal conditions. However, **2 high-severity algorithmic flaws** and **3 medium/low edge-case defects** must be resolved by the implementation team:

1. **Fix MWI Accumulator** (`pan_tompkins.py:157-166`):
   ```python
   # Correct sliding window integration
   mwi = [0.0] * n
   window = self.mwi_window
   running_sum = 0.0
   for i in range(n):
       running_sum += squared_signal[i]
       if i >= window:
           running_sum -= squared_signal[i - window]
       mwi[i] = running_sum / float(min(i + 1, window))
   ```

2. **Fix Kamath Initial Beat Outlier Check** (`pan_tompkins.py:253-288`):
   - Check if `rr_intervals[0]` is within physiological limits ($250\text{ ms} \le RR \le 2200\text{ ms}$).
   - If `rr_intervals[0]` is an outlier, seed `cleaned[0]` with the median of the first $K$ beats or the first beat satisfying physiological range.

3. **Fix Division-by-Zero Guards** (`sleep_scoring.py:70`, `zone2_coaching.py:48`):
   - Ensure `daytime_base = max(40.0, float(daytime_hr_rest) if ...)` and `hr_max = max(60, int(hr_max))`.

4. **Fix Rule #0 Guard in BP Model** (`hemodynamics_bp.py:60`):
   - Update guard to: `if hr_bpm is None or hr_bpm <= 0 or (rmssd_ms is None and ptt_ms is None): return STANDBY`.

---

## 5. Verification Method

To independently execute and verify all adversarial tests:

```bash
# Execute isolated adversarial test harness (35 tests)
./01_apps/canonical_port/.venv/bin/pytest tests/test_adversarial_biometrics_dsp_stress_challenger1.py -v -s
```

All 35 tests pass, confirming empirical reproduction and coverage across all 4 challenge dimensions.
