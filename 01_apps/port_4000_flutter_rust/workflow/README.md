# ⚡ Lauburu Port 4000 Console: Unified Flutter Rust Bridge Workflow

## 1. System Architecture Overview

The **Lauburu Port 4000 Console** integrates high-throughput native Rust compute with a reactive Dart/Flutter UI across desktop, mobile, and web targets.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PORT 4000 HYBRID ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. NATIVE RUST BACKEND CORE (lauburu_port4000_core)                         │
│    • Pan-Tompkins QRS Algorithm: Real-time 5-15Hz Bandpass & MWI Integrator │
│    • DFA-Alpha1 Engine: Short-range scaling exponent for Zone 2 coaching    │
│    • Shopify Membership Engine: Free, Pro ($19/mo), & Crowdsourced Lifetime │
│    • Axum / Tokio Asynchronous HTTP REST & WebSocket Server (:4000)         │
│    • C-FFI Bridge: Exports `liblauburu_core.dylib` with zero-copy bindings  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. FLUTTER RUST BRIDGE (FRB) & DART CLIENT (lauburu_port4000_flutter)       │
│    • `dart:ffi` Native Interop: Direct in-memory C function dispatch        │
│    • Reactive Stream Controller: 120Hz smooth ECG rendering buffer          │
│    • Dark Cyberpunk Glassmorphism UI: Live Oscilloscope, Readiness Gauge,   │
│      Zone 2 LT1/LT2 Coach, Shopify Tier Card, and Sensor Control Panel     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. DOCKER CONTAINERIZATION & WORKFLOW SCRIPTS                               │
│    • `docker-compose.port4000.yml`: Multi-container backend & UI stack     │
│    • `workflow/build_all.sh`: Automated multi-stage compiler                │
│    • `workflow/test_all.sh`: Unified Rust and Dart test runner              │
│    • `workflow/run_port_4000_hub.sh`: Background daemon launcher            │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. Fast-Path CLI Commands

```bash
# 1. Run full unified test suite (Rust + Dart)
bash 01_apps/port_4000_flutter_rust/workflow/test_all.sh

# 2. Build release dynamic library and UI assets
bash 01_apps/port_4000_flutter_rust/workflow/build_all.sh

# 3. Start Port 4000 daemon
bash 01_apps/port_4000_flutter_rust/workflow/run_port_4000_hub.sh

# 4. Deploy containerized stack via Docker
bash 01_apps/port_4000_flutter_rust/workflow/deploy_docker.sh
```

## 3. Endpoints & Protocol Matrix

| Protocol | Endpoint | Description |
|---|---|---|
| HTTP GET | `http://localhost:4000/health` | System health, uptime, and sensor status |
| HTTP GET | `http://localhost:4000/api/biometrics/readiness` | Readiness score, HRV RMSSD, and Zone 2 status |
| HTTP GET | `http://localhost:4000/api/biometrics/snapshot` | Full JSON telemetry snapshot |
| HTTP POST | `http://localhost:4000/api/shopify/verify` | Validates customer token against Shopify tiers |
| WebSocket | `ws://localhost:4000/ws/telemetry` | High-frequency 512Hz raw biometric stream |
| Web UI | `http://localhost:4001` | Containerized Console Web Dashboard |
