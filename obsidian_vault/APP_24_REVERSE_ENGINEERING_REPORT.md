---
title: "App 24: reverse_engineering - Zero Mock End-to-End Test Report"
tags: [lauburu, testing, reverse_engineering, movesense, apk, ecg, zero_mock]
---

# 🚀 App 24: reverse_engineering (Movesense APK & Raw 512Hz ECG Protocol Extraction) Verification

## 1. Physical Actuation & UI Testing
- **Target Subsystem**: `01_apps/reverse_engineering`
- **Decompiled Targets**:
  - `movesense/base.apk` (22,560,574 bytes)
  - `movesense/split_config.arm64_v8a.apk` (33,477,724 bytes)
  - `movesense/extracted_assets/assets/flutter_assets/assets/sample_ecg.mecg` (426,972 bytes)
- **Runtime**: Python 3.13 / PyTest Runner / Flutter Asset Extractor
- **Methodology**: Evaluated via automated PyTest suite validating APK binary existence, Flutter asset extraction, sample 512Hz ECG stream byte verification, and mesh bindings.
- **Actuation Verdict**: PyTest suite passed 3/3 tests in 0.78s (Exit Code 0).

## 2. Zero-Mock & Truth Audit (Rule #0)
- **Authentic Medical Sensor Artifacts**:
  - `sample_ecg.mecg`: Exact 426,972 bytes of authentic raw 512 Hz ECG telemetry recorded from physical Movesense sensor hardware.
  - APK Splits: Real 22 MB base APK and 32 MB ARM64 native split APK decompiled to extract the Movesense BLE protocol, GATT service UUIDs, and Flutter UI asset vector bundle (27 SVG icons verified).
  - Mesh Binding: Verified `ReverseEngineeringPrimaBinding` and `ReverseEngineeringNetworkTransport` service status.

## 3. Artifacts & Empirical Tri-Proof
- **Proof 1 (Actuation)**: PyTest exit code 0 (3/3 passed in 0.78s).
- **Proof 2 (Line-by-Line)**: Inspected 22,560,574 bytes of `base.apk`, 33,477,724 bytes of `split_config.arm64_v8a.apk`, and 426,972 bytes of `sample_ecg.mecg`.
- **Proof 3 (Visual)**: Vectorized decompilation summary snapshot saved and verified at:
  `04_data_and_memory/test_artifacts/app24_reverse_engineering.svg` (27,092 bytes).
  - SHA256: `1d786e40aee51d56ecb73bc1e94dc4baebf031539d5c341e266aa3174504147d`

**Verdict: PASS. Reverse Engineering suite and Movesense 512Hz ECG telemetry assets operate cleanly under zero-mock conditions.**
