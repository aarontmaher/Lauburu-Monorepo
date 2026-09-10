# 📱 Canonical Apps Overview — Lauburu Application Ecosystem

```
========================================================================================
LAUBURU ECOSYSTEM — CANONICAL APPLICATIONS & FRONTEND INTERFACE MATRIX
Version: 3.0.0-APPS-2026 | Authority: Aaron (Sovereign) | Standard: Zero-Mock UI
Port Range: 4000–18802 | Client Surfaces: Flutter, Rust Ratatui, Three.js WebGL, Termux
========================================================================================
```

---

<!-- CONTEXT_WINDOW_TIER_0_START: 4K_PORT_AND_HEALTH_INDEX -->
## 🧭 Context Window Tier 0: Port & Service Directory (~4,000 Tokens)

> **Lens AI Ingestion Target:** Fast Edge Micro-Models (`SmolLM2-135M`, `Pixel 10 Pro XL Edge TPU`, `Termux Edge Daemon`).  
> **Processing Latency:** `<15ms` | **Memory Overhead:** `<64 MB`.

### 1. Active Application Port Directory
```
┌───────┬──────────────────────────────┬────────────────────────┬─────────────────────────┬───────────────────────────┐
│ Port  │ Application Name             │ Framework / Engine     │ Host / Target Device    │ Primary Service Function  │
├───────┼──────────────────────────────┼────────────────────────┼─────────────────────────┼───────────────────────────┤
│ :4000 │ Unified Console & Portal     │ Flutter / Rust Ratatui │ L1: Mac Mini M4 Pro     │ Master System HUD & Stats │
│ :4002 │ Marimo Notebook Dashboard    │ Marimo Reactive Python │ L1: Mac Mini M4 Pro     │ Interactive DSP & Charts  │
│ :4003 │ Screen Lens MJPEG Stream     │ Python HTTP Multipart  │ L1: Mac Mini M4 Pro     │ Live 15 FPS Video Stream  │
│ :8080 │ SeaweedFS Volume Server      │ Go SeaweedFS           │ L1: Mac Mini M4 Pro     │ Raw Block Object Storage  │
│ :8081 │ llama.cpp Master RPC Server  │ C++20 GGML Metal       │ L1: Mac Mini M4 Pro     │ Local Model Inference     │
│ :8082 │ prima.cpp Ring Coordinator   │ C++20 / Python Pipelined│ Distributed (7 Nodes)  │ 85.02 GB VRAM Ring Mesh   │
│ :8083 │ Devil's Advocate Server      │ llama.cpp Abliterated  │ L1: Mac Mini M4 Pro     │ Adversarial Red-Teaming   │
│ :8888 │ SeaweedFS Filer Endpoint     │ Go SeaweedFS           │ L1: Mac Mini M4 Pro     │ POSIX File System Ingress │
│ :8890 │ Voilà Interactive Portal     │ Jupyter Voilà Python   │ L1: Mac Mini M4 Pro     │ Biometrics & Graph UI     │
│ :9333 │ SeaweedFS Master Server      │ Go SeaweedFS           │ L1: Mac Mini M4 Pro     │ DFS Cluster Coordination  │
│:18802 │ Self-Healing Hub             │ FastAPI + React SPA    │ L1: Mac Mini M4 Pro     │ Health, WoL & Watchdogs   │
│ :5555 │ Wireless ADB Server          │ Android Debug Bridge   │ L6 & L7 (Pixel / S20)   │ USB/TCP Automation Link   │
└───────┴──────────────────────────────┴────────────────────────┴─────────────────────────┴───────────────────────────┘
```

### 2. Global UI Invariants
1. **Rule #0 Zero-Mock UI:** No fake telemetry or static placeholder strings. Live biometric displays must show authentic signal waveforms or clean waiting state indicators (`--`).
2. **WCAG AAA Visual Compliance:** All text and interactive targets maintain $\ge 7:1$ (typically $\ge 14.2:1$) contrast ratios for high-speed automated computer-vision parsing.
3. **Sub-100ms Input-to-Glass Latency:** UI interactions and biometric sweeps update within 100ms across all device surfaces.
<!-- CONTEXT_WINDOW_TIER_0_END -->

---

<!-- CONTEXT_WINDOW_TIER_1_START: 16K_APP_DEEP_SPECIFICATIONS -->
## 📦 Context Window Tier 1: Application Deep Specifications (~16,000 Tokens)

> **Lens AI Ingestion Target:** Local Workhorse Models (`Qwen2.5-Coder-7B` on Port 8081, `Mistral-Nemo-Instruct` on Port 8083).  
> **Processing Latency:** `30–80ms` | **Memory Overhead:** `<380 MB`.

### 1. Port 4000 Unified Console (`01_apps/port_4000_flutter_rust/`)
- **Architecture:** Hybrid Flutter desktop frontend linked via Rust Foreign Function Interface (FFI) to a high-speed Crossterm/Ratatui immediate-mode terminal HUD.
- **Features:** 
  - Real-time 7-layer node health telemetry with per-node dynamic RAM headroom meters.
  - Tab 0: Visual Cortex & Next-Best-Action predictor showing Lens AI click coordinates.
  - Live AI conversation stream displaying Tri-Orchestrator debate consensus.
  - Integrated Movesense 512Hz ECG waveform oscilloscope.

### 2. Movesense Biometrics Hub (`01_apps/biometrics/`)
- **Architecture:** CoreBluetooth / BlueZ DBus native driver interfacing with Movesense Medical BLE sensor (`Movesense MD`).
- **Features:**
  - Ingests raw single-lead ECG data at 512Hz alongside 9-DOF IMU (accelerometer, gyroscope, magnetometer).
  - Onboard Pan-Tompkins QRS peak detection calculating instant RR-intervals (RRI) with sub-millisecond precision.
  - Computes pulse transit time (PTT) systolic/diastolic blood pressure estimates.
  - Real-time Detrended Fluctuation Analysis (DFA-$\alpha_1$) predicting aerobic vs anaerobic Zone 2 cardiovascular thresholds.

### 3. Spatial Grappling 3D Kinematics (`01_apps/spatial_grappling_3d/`)
- **Architecture:** Three.js / WebGL hardware-accelerated 3D biomechanical renderer parsing a 955-node OPML spatial martial arts taxonomy (`grappling.opml`).
- **Features:**
  - 3D tatami mat world model with interactive skeletal humanoid avatars.
  - Dynamic joint torque, angular velocity, and fulcrum vector visualization.
  - Hierarchical branching of submission counters, sweeps, escapes, and control nodes.
  - Bidirectional sync with real-time biometric strain indices during grappling sessions.

### 4. Shopify AI Commerce Engine (`01_apps/commerce_and_business/shopify_ai/`)
- **Architecture:** Headless Next.js 14 / TypeScript Storefront querying Shopify GraphQL Admin & Storefront APIs.
- **Features:**
  - Autonomous merchandise sourcing, catalog generation, and image asset auditing.
  - Dedicated product line: Custom Lauburu compression rashguards, grappling shorts, and technical training gear.
  - Recurring club membership billing tiers with automated Stripe / Shopify checkout webhooks.
  - Automated profitability calculator analyzing CAC, LTV, shipping margins, and currency conversion.

### 5. Lauburu Lens & Screen Lens (`01_apps/lauburu_lens/` & `01_apps/screen_lens/`)
- **Architecture:** Python AsyncIO daemon interfacing with Chrome DevTools Protocol (CDP), macOS Accessibility APIs, and Android ADB.
- **Features:**
  - Multimodal Vision-Language-Action (VLA) computer-use engine.
  - Live DOM tree extraction querying bounding boxes and accessibility tags (`<button>`, `<input>`, `<a>`).
  - Automated Next-Best-Action synthesis generating verified DPO training pairs.
  - Continuous 10–15 FPS multipart MJPEG screen streaming on Port 4003 (`/stream.mjpg`).

### 6. Automotive Voice Coding Hub (`01_apps/automotive/`)
- **Architecture:** Android Auto Desktop Head Unit (DHU) projection service with whisper.cpp local speech-to-text (STT) and Piper local text-to-speech (TTS).
- **Features:**
  - In-vehicle hands-free pair programming and terminal voice interaction.
  - **Region Backspace Engine:** AST-aware voice deletion removing syntax blocks without leaving broken AST nodes.
  - **Audio Priority Levels:** Voice commands duck background music at level 2; emergency vehicle navigation prompts preempt and cancel AI speech at level 1.
<!-- CONTEXT_WINDOW_TIER_1_END -->

---

<!-- CONTEXT_WINDOW_TIER_2_START: 32K_INTER_APP_PIPELINES -->
## 🌐 Context Window Tier 2: Inter-App IPC Pipelines & Multi-Surface Routing (~32,000 Tokens)

> **Lens AI Ingestion Target:** Distributed Swarm Coordinator (`prima.cpp` 80B Ring on Port 8082, Whole-Monorepo AST Evaluator).  
> **Processing Latency:** `120–250ms` | **Memory Overhead:** `<1.2 GB`.

### 1. Inter-App IPC Communication Protocols
```
┌─────────────────────────┬─────────────────────────┬──────────────────────┬──────────────────────────────────────────┐
│ Source Application      │ Target Application      │ IPC Protocol / Path  │ Data Format & Payload                    │
├─────────────────────────┼─────────────────────────┼──────────────────────┼──────────────────────────────────────────┤
│ Movesense BLE Sensor    │ Biometrics Hub          │ BLE GATT Characteristic│ Raw 512Hz 16-bit ECG + IMU Bytes       │
│ Biometrics Hub          │ Port 4000 Console       │ WebSocket (:4000/ws) │ JSON: RR-intervals, DFA-a1, HR, SpO2     │
│ Screen Lens CDP Bridge  │ Lens Rapid Maximizer    │ Unix Domain Socket   │ DOM Hierarchy, Bounding Boxes, Viewport  │
│ Lens Rapid Maximizer    │ LoRA Dataset Sink       │ POSIX Append Stream  │ JSONL: Authentic DPO Triplet Records     │
│ AI Debate Scheduler     │ Obsidian Vault          │ File I/O + MCP Pro   │ Markdown: Debate Consensus & Loop Actions│
│ Termux UI Automator     │ Self-Healing Hub        │ HTTP REST (:18802)   │ JSON: Battery, Wakelock, Memory Telemetry│
│ Automotive Voice Daemon │ Local Qwen MoE (:8081)  │ HTTP Streaming POST  │ JSON / SSE: AST Code Edit Directives     │
└─────────────────────────┴─────────────────────────┴──────────────────────┴──────────────────────────────────────────┘
```

### 2. Multi-Device Accessibility & Remote Execution Matrix
- **macOS Mac Mini (L1):** Coordinates native macOS window management via `screencapture`, AppleScript UI events, and Darwin Mach kernel RAM counters.
- **Linux Head Node (L3):** Runs containerized test runners, SeaweedFS master/volume servers, and Ray distributed computation tasks over 1GbE.
- **Samsung Galaxy S20 (L7):** Dedicated automated mobile UI runner executing Termux scripts, testing mobile web responsiveness via Chrome DevTools over Port 5555.
- **Pixel 10 Pro XL (L6):** Dedicated Edge TPU worker running on-device int4 quantization models, processing real-time video feeds from its 8K digital PTZ camera.
<!-- CONTEXT_WINDOW_TIER_2_END -->

---

<!-- CONTEXT_WINDOW_TIER_3_START: 128K_MULTI_SURFACE_ORCHESTRATION -->
## 🔮 Context Window Tier 3: Multi-Surface Autonomous Testing (~128,000+ Tokens)

> **Lens AI Ingestion Target:** Frontier Cloud Teachers (`Gemini 3.1 Pro Preview` 2M Context, `DeepSeek V4 Pro 1.6T` 1M Context).  
> **Processing Latency:** Cloud Async (`1–3s`) | **Memory Overhead:** Cloud Offloaded ($0 Cost).

### 1. The Autonomous Multi-Surface Testing Loop
The application suite runs automated cross-surface regression and fuzz testing:
- **Chrome CDP Fuzzing:** Automated headless Chrome workers navigate web interfaces, inject adversarial click coordinates, and verify zero unhandled JavaScript exceptions.
- **WCAG AAA Compliance Audits:** High-speed computer-vision filters evaluate all rendered views against 7:1 contrast ratios and touch-target bounding boxes ($\ge 48 	imes 48	ext{ px}$).
- **Biometric Stress Verification:** Telemetry streams undergo simulated packet drop, reconnect, and arrhythmia detection tests to verify DSP filter stability.
- **Automotive Audio Latency Benchmarking:** Voice commands undergo round-trip latency evaluation under ambient driving road noise profiles (Pink noise 65 dBA).
<!-- CONTEXT_WINDOW_TIER_3_END -->
