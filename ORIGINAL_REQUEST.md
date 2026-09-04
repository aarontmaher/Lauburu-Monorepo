# Original User Request

## Initial Request — 2026-09-02T11:25:33+10:00

# FULL SWARM AUDIT & PERSISTENT ZERO-MOCK EXECUTION

Deploy and verify a 100% zero-mock, real-time biometrics and 3D spatial grappling cockpit for Port 4000 and mobile Pixel 10 Pro XL.

Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust

## Requirements

### R1. Total Elimination of Mock & Fallback Data (Global Rule #0)
Purge every static array, hardcoded default (72 BPM, 48.5ms, synthetic sine waves), and mock initial state across the Rust backend, Dart UI, and HTML build. When no live sensor or camera stream is connected, the UI must render authentic waiting states (-- BPM, -- ms, flatline ECG, clean sensor probing badges).

### R2. Pure Dynamic Client-Side WebSocket & WebGL/Canvas Engine
Replace static SVG templates with dynamic client-side JavaScript that streams directly from ws://127.0.0.1:4000/ws/telemetry (512Hz biometrics) and ws://127.0.0.1:4000/ws/spatial (60 FPS 3D Tatami kinematics). The canvas and oscilloscope must only draw live incoming data packets.

### R3. Standalone Mobile Pixel Web Bluetooth Ingestion
Embed native Web Bluetooth API in the Cockpit frontend (navigator.bluetooth) with automatic GATT subscription to Movesense Heart Rate Service (0x180D/0x2A37) and raw 512Hz ECG streams. When opened in Chrome on the Pixel at the gym, one-click Bluetooth pairing connects directly to the Movesense sensor on the athlete's body.

### R4. Continuous Autonomous Execution & Verification
Deploy the updated release binary and HTML to the running Port 4000 daemon, test end-to-end over Tailscale on the Pixel 10 Pro XL (100.73.38.87), and verify 0% mock data via automated Truth Audit.

## Acceptance Criteria

### Verification & Truth Enforcement
- [x] No hardcoded numbers (72.0, 48.5, 50%, etc.) exist in the compiled index.html or backend initial state.
- [x] Initial state renders -- BPM, -- ms, and flat zero ECG lines until real sensor frames arrive.
- [x] Web Bluetooth button initiates direct CoreBluetooth / Android Bluetooth pairing on the Pixel.
- [x] Live WebSocket telemetry frames (/ws/telemetry and /ws/spatial) dynamically update the oscilloscope and 3D Tatami mat at 60+ FPS.
- [x] All 12 Rust and Dart test suites pass.
- [x] Live verification on Pixel 10 Pro XL over SSH confirms zero-mock state.
