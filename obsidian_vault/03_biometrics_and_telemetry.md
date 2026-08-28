---
title: "03_biometrics_and_telemetry — DSP Pipelines & Medical-Grade Telemetry"
updated: "2026-08-27"
tags: [biometrics, dsp, ecg, pan_tompkins, dfa_alpha1, blood_pressure, zero_mock, spec-03]
---

# 03_biometrics_and_telemetry — DSP Pipelines & Medical-Grade Telemetry

## 📋 Scope & Zero-Mock Standard (Rule #0)
Houses mathematical digital signal processing (DSP) algorithms converting raw biological sensor streams into validated physiological biomarkers.
**Strictly 0% mock or simulated data:** Telemetry originates from physical sensors or authenticated log replays, gracefully rendering clean `null`/`--` states when sensors are offline.

## 💓 Signal Processing Modules & Algorithms
1. **Movesense 512Hz ECG Acquisition:**
   - Ultra-low latency BLE GATT stream ingestion, packet loss detection, and timestamp synchronization.
2. **Pan-Tompkins QRS Complex Detection:**
   - 5-stage real-time QRS detection: Bandpass filter (5–15 Hz), 5-point derivative, squaring function, moving-window integration (150ms), and dual-threshold adaptive peak finding.
3. **Detrended Fluctuation Analysis ($\text{DFA}-\alpha_1$):**
   - Real-time short-term fractal scaling exponent calculation over 2-minute sliding RR-interval windows to identify aerobic threshold inflection points ($\alpha_1 = 0.75$).
4. **Pulse Transit Time (PTT) Blood Pressure Estimation:**
   - Dual-sensor ECG R-peak to PPG pulse wave transit time calculation for continuous cuffless BP tracking.
5. **Whoop Intelligence & Apple Health ETL:**
   - Sleep staging, recovery score ingestion, and longitudinal biomarker aggregation.

## 🤖 Assigned Subsystem Specialist AI
- **Specialist Agent:** `spec-03-biometrics-dsp`
- **Focus Areas:** Pan-Tompkins DSP, RR-interval extraction, fractal scaling DSP, BLE GATT ingestion.

## 🔗 Knowledge Graph Connections
- **Master Index:** [[Index]]
- **Whitepapers:** [[MOVESENSE_BLUETOOTH_ARCHITECTURE_DEBATE]]
- **Connected Modules:** [[01_apps]], [[04_data_and_memory]]
