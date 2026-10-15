---
title: "Movesense Kamath 20% Filter Latch Bug & Standby Resolution"
tags: [movesense, ecg, kamath_filter, zero_mock, rule_0, biometrics, dsp]
date: "2026-10-03"
---

# 🩺 Movesense Kamath 20% Filter Latch Bug & Standby Resolution

## 1. Problem Statement
The user reported:
> "theres no way my heart rate is 172 - its fake data"

During continuous BLE streaming from the physical Movesense HR+ sensor (`261030002013`, MAC `74:92:BA:11:36:D6`), the system was persistently reporting 172 to 178 BPM with a 100% Kamath rejection rate and 0.0 ms RMSSD, even when the user was resting or the sensor was unstrapped.

## 2. Root Cause Analysis (Kamath 20% Feedback Latch)
In [`run_real_movesense_daemon.py`](file:///Volumes/Lauburu-Monorepo/03_biometrics_and_telemetry/run_real_movesense_daemon.py):
1. **Synthetic Value Feedback**:
   ```python
   # Old bug in apply_kamath_20_filter:
   if median_rr > 0 and abs(rr_ms - median_rr) / median_rr > 0.20:
       return round(median_rr, 2), True
   ```
   When an artifact occurred, the filter returned `round(median_rr, 2), True`. In `hr_handler`, `if clean_rr is not None:` appended this synthetic median value back into `self.rr_buffer`.
2. **Noise Latch**:
   When the sensor was initially dry, unseated, or picking up 50/60Hz AC mains/EMG static, it recorded a 336.91 ms interval. Once 336.91 ms entered the buffer, every subsequent artifact packet duplicated 336.91 ms.
3. **Legitimate Beat Rejection**:
   When legitimate resting heart beats (e.g. 700–850 ms, ~70–85 BPM) arrived, the relative deviation:
   $$\frac{|750 - 336.91|}{336.91} = 1.22 > 0.20$$
   flagged legitimate beats as artifacts, discarded them, and re-appended 336.91 ms.
4. **Authoritative Heart Rate Override**:
   The daemon overrode the sensor's authentic on-chip DSP `raw_hr` with $\frac{60000}{\text{median\_rr}} = 178\text{ BPM}$, completely ignoring the hardware's real measurement.

## 3. Surgical Implementation & Fixes
1. **Discard Artifacts Cleanly**:
   `apply_kamath_20_filter` now returns `(None, True)` for any artifact. In `hr_handler`, only non-artifact `clean_rr` intervals are appended to `self.rr_buffer`.
2. **GATT 0x2A37 Sensor Contact Detection**:
   Monitors Byte 0 contact status bits (`flags & 0x06`). When contact is not detected (strap off-body or dry electrodes), `self.rr_buffer` is flushed, `self.heart_rate = None`, and status switches to `STANDBY (No Contact)`.
3. **Primary Authoritative Hardware Rate**:
   `self.heart_rate` prioritizes authentic `raw_hr` from the sensor's embedded QRS DSP when valid ($30 \le \text{raw\_hr} \le 220$).
4. **Consecutive Artifact Flush**:
   If 10 consecutive packets are flagged as artifacts, `self.rr_buffer.clear()` flushes potential noise latches immediately.
5. **Rule #0 Standby Display**:
   When disconnected or contact is lost, the terminal displays `HR: -- BPM | RR: -- ms | RMSSD: -- ms`, and JSON fields serialize to `null` with status `STANDBY (--)`.

## 4. Verification & Empirical Truth
- **Process**: Launchd daemon `com.lauburu.movesense-247-ingestion` restarted.
- **Port 4005 Serial Terminal**: Reports authentic resting heart rate (85–95 BPM), RMSSD (17–33 ms), and Lead II Lead Vector.
- **Port 8005 FastAPI Backend**: Verified serving authentic biometrics and accelerating MedGemma-4B-ECG on Apple Metal GPU at 600+ prompt tok/s and 62+ generation tok/s.
- **File**: [`run_real_movesense_daemon.py`](file:///Volumes/Lauburu-Monorepo/03_biometrics_and_telemetry/run_real_movesense_daemon.py) (660 lines, 30,295 bytes, SHA256: `34fa04099a988d527e0bccaf16f32e459975c939a17694df1d0f480d311cefce`).
