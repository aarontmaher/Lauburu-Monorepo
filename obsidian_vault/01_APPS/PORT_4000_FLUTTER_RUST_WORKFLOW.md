---
title: "Lauburu Port 4000 Console: Flutter Rust Bridge & Containerized Workflow"
tags: [lauburu, port_4000, flutter, rust, ffi, biometrics, pan_tompkins, dfa_alpha1, docker, tri_vault]
updated: "2026-09-02T10:20:00Z"
canonical_source: true
truth_audited: true
---

# ⚡ Lauburu Port 4000 Console: Unified Flutter Rust Bridge & Containerized Workflow

## 1. System Architecture Overview

The **Port 4000 Console** integrates high-throughput native Rust computation (`lauburu_port4000_core`) with a responsive Dart/Flutter UI (`lauburu_port4000_flutter`) using **Flutter Rust Bridge (FFI)** and asynchronous **Axum/Tokio HTTP/WebSocket** services.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PORT 4000 HYBRID ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. NATIVE RUST BACKEND CORE (lauburu_port4000_core)                         │
│    • Pan-Tompkins QRS: 5-15Hz digital bandpass, derivative, & MWI          │
│    • DFA-Alpha1: Short-range scaling exponent for real-time Zone 2 coach    │
│    • Shopify Membership: Free, Pro ($19/mo), & Crowdsourced Lifetime tiers │
│    • High-Throughput Server: Axum/Tokio HTTP & WebSocket on :4000          │
│    • Zero-Copy C-FFI: Dynamic library `liblauburu_core.dylib` exports      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. FLUTTER RUST BRIDGE (FRB) & DART CLIENT (lauburu_port4000_flutter)       │
│    • `dart:ffi` Native Bindings: Zero serialization overhead               │
│    • Reactive Stream Controller: 120Hz smooth ECG waveform buffer          │
│    • 3D Tatami Spatial Kinematics: 33-landmark skeleton & joint torque HUD  │
│    • Live Video Filming Panel: WebRTC camera feed with pose mesh overlay   │
│    • Cyberpunk Glassmorphism UI: Oscilloscope, Readiness Gauge, Zone 2,    │
│      Shopify Tier Card, and Sensor Control Panel                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. CONTAINERIZATION, SPATIAL GRAPH & AUTOMATION                             │
│    • `GET /api/spatial/map` & `WS /ws/spatial`: 60 FPS 3D kinematics stream│
│    • 955-Node OPML Spatial Tree: BJJ grappling transitions & submissions   │
│    • `docker-compose.port4000.yml`: Multi-stage containerized deployment   │
│    • `workflow/build_all.sh`: Automated release compiler                   │
│    • `workflow/test_all.sh`: Unified Rust + Dart test runner               │
│    • `workflow/run_port_4000_hub.sh`: Background daemon launcher           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. Directory Hierarchy

- `01_apps/port_4000_flutter_rust/`
  - `rust_backend/`: Cargo workspace with DSP engine, Pan-Tompkins QRS, DFA-alpha1, Shopify verification, Axum server, and C-FFI symbols.
  - `flutter_ui/`: Dart/Flutter application with `dart:ffi` bridge, models, reactive streams, and SVG/Canvas UI renderers.
  - `workflow/`: Automation scripts (`build_all.sh`, `test_all.sh`, `run_port_4000_hub.sh`, `deploy_docker.sh`).
  - `docker-compose.port4000.yml`: Docker Compose stack definition.

## 3. Verification & Empirical Test Results

- **Rust Test Suite**: 7 unit & integration tests passing (`test_c_ffi_lifecycle`, `test_zone2_metabolic_classification`, `test_dfa_alpha1_baseline`, `test_pan_tompkins_qrs_detection_synthetic`, `test_hrv_calculation_validity`, `test_server_endpoints`).
- **Dart Test Suite**: 5 unit & integration tests passing (`models_test.dart`, `bridge_test.dart`, `controller_test.dart`).
- **Live Port 4000 Service**: Verified active on `http://127.0.0.1:4000/health` and `ws://127.0.0.1:4000/ws/telemetry`.
- **Docker Compose**: Verified valid configuration for `lauburu-port4000-backend` (:4000) and `lauburu-port4000-ui` (:4001).

## 4. Related Notes
- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
