# Comprehensive Architectural & Codebase Survey Report
**Project**: Distributed Resource & Compute Pooling Manager Application
**Agent**: Survey Explorer 1 (`survey_explorer_1`)
**Date**: 2026-08-24
**Target Workspace**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/teamwork_projects/compute_pooling_app` (symlinked `/Volumes/aaronmaher/Lauburu-Monorepo/teamwork_projects/compute_pooling_app`)

---

## 1. Executive Summary
The Lauburu Monorepo represents a 1.701 TB distributed unified ecosystem spanning a heterogeneous 7-device hardware mesh with 82.8 GB total pooled AI VRAM. The system is designed to orchestrate local edge AI inference, real-time medical-grade biometrics DSP, multi-WAN network bonding/failover, and automated self-healing.

This survey establishes the complete baseline for building the **Distributed Resource & Compute Pooling Manager** application, fulfilling requirements **R1** (Standalone App & Deep Analytics/Dark Mode/Multi-WAN), **R2** (Auto-Adaptive Compute Pooling & User Opt-In), **R3** (Cloud AI Synergy with Gemini Pro 3.1 High & Opus 4.6), and **R4** (Mac Mini 24GB Dynamic Governor & Workload Offloading).

---

## 2. 7-Node Hardware Mesh Topology & Specifications

| Layer | Node Identifier | Hardware Platform | Core Roles | Primary IPs & Ports | VRAM / RAM Allocation |
|---|---|---|---|---|---|
| **Layer 1** | `Mac_Node` | Apple Mac Mini M4 / M4 Host | Swarm Orchestrator, Memory Governor, ADB Master | `127.0.0.1`, `100.119.199.76`, `192.168.8.230` | 32 GB Unified RAM (38 TOPS ANE) |
| **Layer 2** | `MacBook_Pro` | Apple MacBook Pro M1 Max | Storage Vault, Metal GPU RPC Worker, 285GB SSD Vault | `100.103.212.21`, `192.168.8.127`, `169.254.122.166` (TB4) | 32-64 GB Unified RAM (Metal GPU) |
| **Layer 3** | `Linux_Head_Node` | AMD Ryzen 7 5700U / Linux Head | SeaweedFS Master/Filer, Ray Head, Gateway & Ingress | `100.101.39.98`, `192.168.8.224` (SSH: 22, RPC: 50052) | 64 GB DDR4 RAM (100 TOPS GPU eq.) |
| **Layer 4** | `Linux_Tablet` | Debian Linux Tablet | Mobile Linux Compute HUD, Secondary Petals Worker | `100.81.92.125`, `192.168.8.173` (SSH: 22, RPC: 50052) | 8-16 GB RAM |
| **Layer 5** | `Mac_Mini` | Apple Mac Mini (24GB Unified RAM) | High-Speed Metal Worker, MPS Sharding, LoRA Fine-Tuning | `100.93.158.96`, `192.168.8.222` (SSH: 22, RPC: 50052) | 24 GB Unified RAM (Primary Target R4) |
| **Layer 6** | `Pixel_10_Pro_XL` | Google Tensor G5 (Android 15/17) | Edge TPU Worker, Petals DHT Swarm (`31330`), 8K PTZ | `100.73.38.87:5555` (SSH: 8022, RPC: 50052, DHT: 31330) | 16 GB LPDDR5X (45 TOPS NPU) |
| **Layer 7** | `Samsung_S20` | Samsung Galaxy S20+ (Exynos/Snap) | Dedicated UI Tester, USB Tether Gateway, Edge Sensor | `100.84.40.95:5555`, `100.99.123.58` (SSH: 8022) | 12 GB RAM (15 TOPS NPU) |

*Source Verification*: `00_core_infrastructure/self_healing_hub/src/devices.json` (lines 1-116), `README.md` (lines 6-14).

---

## 3. Subsystem Breakdown & Reusable Assets

### 3.1 `00_core_infrastructure` (Mesh Networking & Telemetry)
- **Multi-WAN Engine (`00_core_infrastructure/multi_wan/`)**:
  - `gateway_fallback.py`: EWMA RTT latency tracking (`EWMA_t = alpha * RTT_t + (1-alpha) * EWMA_{t-1}`), sliding window drop detection, sub-50ms predictive circuit breaking (lines 17-220).
  - `multiwan_bond.py`: Chunked multi-transport bonding transfer protocol with SHA-256 validation (lines 1-160).
  - `compute_offloader.py`: Node scoring formula:
    $$\text{Score} = (\text{RAM}_{\text{free\_GB}} \times 0.4) + (\text{NPU}_{\text{TOPS}} \times 0.4) + ((100 - \text{CPU}_{\text{load\_pct}}) \times 0.2)$$
    Supports dynamic weights for `inference` (0.3 RAM / 0.5 NPU / 0.2 CPU) and `code_exec` (0.5 RAM / 0.2 NPU / 0.3 CPU) (lines 137-160).
  - `hardware_telemetry.py`: Non-mock system calls (`psutil`, `sysctl`, `system_profiler`, ADB, SSH) querying CPU, RAM, GPU, NPU, Storage, and consolidated Tailscale/Ethernet/Wi-Fi adapters (lines 1-551).
- **Self-Healing Hub (`00_core_infrastructure/self_healing_hub/src/`)**:
  - `adaptive_device_hardware_governor.py`: Context-aware resource limits (`HUMAN_INTERACTIVE_MODE` with 58% RAM / 45% CPU cap vs `AUTONOMOUS_MAX_SURGE_MODE` with 94% RAM / 92% CPU / 100% NPU) using macOS `IOHIDSystem` / `HIDIdleTime` detection (lines 27-152).
  - `api_server.py`: Flask/CORS API exposing 30+ endpoints for telemetry, device statuses, and remote actuation.

### 3.2 `01_apps` (Application Ecosystem & Frontends)
- `port_4000_hub/`: Production telemetry dashboard, membership manager, and live readiness monitor.
- `movesense_hub/`: 128Hz single-lead ECG and 9-DoF IMU medical-grade Bluetooth ingestion daemon.
- `zone2_endurance/`: Real-time DFA-alpha1 aerobic threshold (LT1/LT2) calculations.
- `termux_edge_daemon/`: Headless background daemon on Android edge nodes managing network health and RPC bridging.

### 3.3 `02_ai_models_and_inference` (Distributed Inference Engines)
- `llama.cpp RPC Sharding`: Metal GPU / Vulkan / CPU tensor distribution listening on Port `50052`.
- `Petals DHT Swarm`: Decentralized pipeline parallel sharding across edge devices (Pixel 10, Samsung S20, Linux Tablet) on Port `31330`.
- `Exo Cluster`: Peer-to-peer layer splitting on Port `52415`.

### 3.4 `03_biometrics_and_telemetry` (DSP & Sensor Pipelines)
- `movesense_ecg_128hz`: Pan-Tompkins QRS detector, R-R interval extraction, HRV RMSSD/SDNN.
- `dfa_alpha1_thresholds`: Dynamic correlation coefficients determining aerobic threshold (0.75) and anaerobic threshold (0.50).
- Live state verified at `data/telemetry_state.json`.

### 3.5 `05_agents_and_swarms` (Swarm Intelligence & Routing)
- Tri-Orchestrator architecture: Cloud Orchestrator (Gemini 3.7 / 3.1 Pro / Opus 4.6), Local AI Orchestrator (DeepSeek-R1 / Qwen on Mesh), Genetic AI Orchestrator.
- Waterfall routing heuristics in `teamwork_projects/lauburu_compute_hub/src/router/complexity_detector.py` classifying queries into `LOW`, `MEDIUM`, `HIGH`, `EXTREME` complexity envelopes.

### 3.6 `06_scripts_and_tooling` (Daemons, Dark Mode & Automation)
- **Dark Mode Fleet Controller (`06_scripts_and_tooling/dark_mode/`)**:
  - `dark_mode_device_controller.py`: Universal dark mode across macOS (AppleScript `set dark mode to true`), Linux GNOME (`gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'`), and Android (`adb shell cmd uimode night yes`) (lines 1-242).
  - `dark_mode_orchestrator.py`: REST API (Port 18801) and socket broadcast (Port 18800) for synchronized theme toggling.
- **Compute Supervisor & Mesh Orchestrator (`06_scripts_and_tooling/mesh/`)**:
  - `ai_compute_supervisor.py`: Audits, pins, and auto-restarts llama.cpp RPC, Exo, and Petals (lines 1-145).
  - `master_mesh_daemon.py`: Supervises WoL API (Port 18802), AI Supervisor, and Night Scheduler.
- **Network Self-Healing (`06_scripts_and_tooling/network/`)**:
  - `multiwan_bond_manager.py`: Probes Ethernet, Wi-Fi 6E/7, Hotspots; calculates fitness score (0-100); records LoRA decision traces (lines 1-325).
  - `nomad_courier_self_healer.py`: 8-point autonomous loop restoring Web UIs (Port 3000/4000), skills, and MCP configurations.

---

## 4. Multi-WAN Network Matrix & Failover Topologies

| Transport Link | Physical Interface / SSID | Typical Latency (RTT) | Theoretical Bandwidth | Failover Priority | Target Use Case |
|---|---|---|---|---|---|
| **Thunderbolt 4 DMA** | Direct TB4 Cable (`169.254.x.x`) | 0.28 ms | 10,000 Mbps (10 Gbps) | Tier 1 (Ultra-Low Latency) | Raw llama.cpp tensor weight transfers & KV cache sync |
| **10GbE / Gigabit Ethernet** | `eth0` / `en0` (`192.168.8.x`) | 0.8 - 2.5 ms | 1,000 - 10,000 Mbps | Tier 2 (Wired Primary) | Core DFS storage traffic & Ray worker cluster communication |
| **Wi-Fi 7 / 6E MLO** | `GL-MT3600BE-a0f-MLO` | 4.0 - 12.0 ms | 1,200 - 2,400 Mbps | Tier 3 (Wireless Primary) | High-speed mobile compute offloading & UI streaming |
| **Tailscale WireGuard Mesh** | `utunX` overlay (`100.x.x.x`) | 12.0 - 45.0 ms | 100 - 500 Mbps | Tier 4 (Encrypted Global Mesh) | Out-of-band management, remote SSH, cloud-to-edge tunnels |
| **Mobile 5G Hotspot / USB Tether** | `en6` / Android ADB (`100.73.38.87`) | 25.0 - 80.0 ms | 150 - 600 Mbps | Tier 5 (Nomad Failover) | Automatic fallback when primary ISP/LAN links drop |

---

## 5. Architectural Alignment with Project Requirements

### Requirement R1: Standalone Application Features & Auto-Optimization
- **Deep Device Analytics**: Aggregate real-time CPU, RAM, GPU, NPU, disk I/O, battery %, thermal status, and per-adapter network metrics across all 7 nodes via `HardwareTelemetryMonitor`.
- **Auto-Optimization**: Continuously tune background process limits based on `AdaptiveDeviceHardwareGovernor` to maintain 60 FPS interactive UI fluidity.
- **System Integrations**: Bidirectional synchronized Dark Mode controller bridging macOS, Linux GNOME, Android ADB, and Web CSS tokens (`#0A0A0C` background, `#121216` elevated, WCAG AAA compliant 18.73:1 contrast ratio).
- **Network Resilience**: Sub-50ms predictive circuit breaking via `LatencyAwareGatewayFallback` with zero compute disruption.

### Requirement R2: Auto-Adaptive Compute Pooling & User Opt-In
- **Dynamic Task Throttling**: Active user input detection (`IOHIDSystem` / `HIDIdleTime` < 180s) automatically throttles or migrates heavy background tasks from host node to utility nodes within <100ms.
- **Opt-In Tiers**:
  - **Light**: 20% max AI RAM cap, 25% CPU, strict battery threshold (>80% required), pauses immediately on any user activity.
  - **Moderate**: 50% max AI RAM cap, 50% CPU, NPU prioritized, throttles to 20% on user activity.
  - **Maximum / Autonomous Surge**: 90-95% RAM cap, 95% CPU, 100% NPU, full headless/idle pooling.

### Requirement R3: Cloud AI Synergy (Gemini Pro 3.1 High & Opus 4.6)
- **Runtime Escalation**: Escalates complex network partition triage, multi-hop routing, or compute pooling deadlocks to Gemini 3.1 Pro / Opus 4.6 when heuristic complexity is `EXTREME`.
- **Deep Telemetry Analytics**: Batches 10-minute hardware metric windows (CPU, thermal spikes, packet drops, battery degradation) and submits structured prompts to Cloud AI for long-term anomaly detection and predictive maintenance.

### Requirement R4: Mesh Adaptation (Mac Mini 24GB RAM)
- **Workload Governor**: Mac Mini (Layer 5, 24GB Unified RAM) acts as the high-throughput worker while protecting local interactive workflows. When local interactive load spikes, the governor offloads tasks to Linux Head Node (Layer 3, 64GB RAM) or MacBook Pro Vault (Layer 2).

---

## 6. Recommended Architecture for the Compute Pooling App

The standalone Compute Pooling Manager application in `teamwork_projects/compute_pooling_app` should be structured as follows:

```
teamwork_projects/compute_pooling_app/
├── src/
│   ├── __init__.py
│   ├── app.py                      # FastAPI + WebSocket backend service
│   ├── config.py                   # Mesh topology, ports, opt-in defaults
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── hardware_collector.py   # Live psutil/SSH/ADB telemetry engine
│   │   ├── anomaly_detector.py     # Local statistical anomaly detection
│   │   └── cloud_synergy.py        # Gemini 3.1 Pro & Opus 4.6 batch evaluator
│   ├── governor/
│   │   ├── __init__.py
│   │   ├── activity_sensor.py      # IOHIDSystem & input activity detector
│   │   ├── adaptive_pool.py        # Light/Moderate/Maximum Opt-in governor
│   │   └── workload_offloader.py   # Dynamic task migration across 7 nodes
│   ├── network/
│   │   ├── __init__.py
│   │   ├── multiwan_monitor.py     # TB4 / Ethernet / Wi-Fi / Tailscale tracker
│   │   └── failover_circuit.py     # Sub-50ms EWMA circuit breaker & failover
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── dark_mode_sync.py       # macOS, Linux, Android dark mode syncer
│   │   └── thermal_power_guard.py  # Battery & thermal threshold watchdog
│   └── ui/
│       ├── index.html              # Reactive standalone dashboard UI
│       ├── app.js                  # 60fps analytics, dark mode toggle, opt-in controls
│       └── styles.css              # Canonical Lauburu dark mode design system
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_tier1_analytics_and_darkmode.py
│   ├── test_tier2_adaptive_throttling.py
│   ├── test_tier3_multiwan_failover.py
│   └── test_tier4_cloud_ai_synergy.py
├── pyproject.toml
└── README.md
```

---

## 7. Verification Standards & Zero-Mock Compliance
1. **Zero Mock Policy**: Telemetry must query live hardware interfaces (`psutil`, `sysctl`, `socket`, `subprocess` calls to local OS / SSH / ADB). In unit test environments, deterministic network sockets and real system calls with simulated activity controllers (like `SimulationController`) must be used without inventing artificial fake numbers.
2. **Automated Test Coverage**: 4-Tier test suite verifying:
   - Tier 1: Deep analytics retrieval and cross-platform Dark Mode toggle.
   - Tier 2: Real-time throttling/offload on simulated user input event within <100ms.
   - Tier 3: Simulated WAN drop triggering seamless automatic failover without dropped compute tasks.
   - Tier 4: Telemetry batch formatting and dispatch to Gemini Pro 3.1 / Opus 4.6 runtime evaluators.
