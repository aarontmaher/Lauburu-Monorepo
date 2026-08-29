# Detailed Architectural Analysis: Two-Domain Application Separation & Web-TUI Portal

**Timestamp**: 2026-08-29T19:36:00+10:00  
**Subsystem**: Lauburu Monorepo Application Portfolio (`01_apps/`)  
**Integrity Mode**: Development / Zero-Mock Rule #0 Verified  

---

## 1. Executive Summary

This investigation plans the definitive architectural separation of the entire Lauburu Monorepo application portfolio into two isolated, high-cohesion domains:
1. **User & Scaling Apps (`01_apps/user_facing_and_scaling/`)**: Polished consumer, athlete, and commercial applications prioritizing user experience, zero developer clutter, responsive biometric feedback, 3D kinematics, gamification, and headless commerce.
2. **Operator & Dev Cockpits (`01_apps/operator_and_dev/`)**: Deep mission-control cockpits for multi-node mesh orchestration, 108 GB pooled RAM governance, AI debate auditing, SmolAgents code-as-action sandboxing, and continuous mathematical trend optimization.

Both domains converge through a unified, high-performance **Web-TUI Portal on Port 8088** powered by FastAPI / aiohttp asynchronous PTY multiplexing and xterm.js WebGL rendering at 120 FPS.

---

## 2. Comprehensive Subsystem Inventory & Current State Mapping

| Target Application | Current File Location(s) | Target Architectural Path | Status & Maturity |
| :--- | :--- | :--- | :--- |
| **Movesense Physiological Readiness Hub** | `01_apps/biometrics/movesense_readiness_tui.py`<br>`01_apps/biometrics/movesense_hub/pyspark_biometrics_dsp.py`<br>`03_biometrics_and_telemetry/movesense_readiness_suite.py`<br>`03_biometrics_and_telemetry/pan_tompkins_dsp.py`<br>`01_apps/biometrics/zone2_endurance/`<br>`01_apps/biometrics/lauburu_zone2_endurance/` | `01_apps/user_facing_and_scaling/movesense_readiness_hub/`<br>├── `core/`<br>├── `dsp/`<br>├── `presentation/`<br>└── `transport/` | **High**. Full 512Hz ECG, Pan-Tompkins QRS, PTT BP inversion, overnight sleep scoring, and Zone 2 coaching implemented across backend and TUI, with Next.js web and Flutter mobile scaffolds. |
| **3D Spatial Grappling Kinematics** | `01_apps/spatial_and_3d/grapplingmap_web/grappling.opml`<br>`00_core_infrastructure/self_healing_hub/src/spatial_grappling_map_engine.py`<br>`10_spatial_grappling_kinematics/opml_trees/grappling.opml`<br>`01_apps/spatial_and_3d/grapplingmap_web/` | `01_apps/user_facing_and_scaling/spatial_grappling_3d/`<br>├── `core/`<br>├── `kinematics/`<br>├── `opml_trees/`<br>└── `presentation/` | **High**. Complete 3,044-node OPML tree parsed into 3D spatial coordinates, integrated with MediaPipe 33-landmark 3D kinematic skeleton and live Movesense biofeedback. |
| **Gamified Combat Arena** | `01_apps/canonical_port/tui/tui_live_arena_dev.py`<br>`05_agents_and_swarms/red_blue_arena/compute_drain_war_arena.py`<br>`05_agents_and_swarms/red_blue_arena/smolagents_arena_engine.py` | `01_apps/user_facing_and_scaling/combat_arena/`<br>├── `core/`<br>├── `modes/`<br>└── `presentation/` | **High**. 4 selectable game modes, animated 120 FPS compute power tug-of-war bar, dual team infiltration/defense maps, 1-key battle abilities, and RAG voice TTS. |
| **Headless Shopify Storefront** | `01_apps/commerce_and_business/storefront_membership_tui.py`<br>`01_apps/commerce_and_business/lauburu-storefront/`<br>`08_business_and_commerce/shopify_saas_monetization.py`<br>`08_business_and_commerce/export_shopify_time_series.py` | `01_apps/user_facing_and_scaling/shopify_storefront/`<br>├── `core/`<br>├── `graphql/`<br>└── `presentation/` | **High**. Tiered membership models ($9 Athlete, $29 Pro, $99 Gym Team), hardware sensor bundles (512Hz Movesense chest/bicep straps), GraphQL checkout flows. |
| **Canonical Port 9-Screen NOC** | `01_apps/canonical_port/tui/canonical_tui.py`<br>`01_apps/canonical_port/tui/screens/`<br>`01_apps/canonical_port/tui/views/`<br>`01_apps/canonical_port/tui/widgets/`<br>`01_apps/canonical_port/tui/services/` | `01_apps/operator_and_dev/canonical_port/`<br>├── `screens/`<br>├── `views/`<br>├── `widgets/`<br>└── `backend/` | **Production Ready**. 9-Screen stability hierarchy, 7 physical node telemetry (108GB RAM pool), blackboard state synchronization, AI debate auditing. |
| **SmolAgents Python Duel Sandbox** | `05_agents_and_swarms/red_blue_arena/smolagents_arena_engine.py`<br>`01_apps/canonical_port/backend/agents/smolagents_ecosystem.py`<br>`05_agents_and_swarms/red_blue_arena/device_settings_sandbox.py` | `01_apps/operator_and_dev/smolagents_duel_sandbox/`<br>├── `core/`<br>├── `tools/`<br>└── `presentation/` | **High**. Code-as-action Python tool sandbox (`probe_socket`, `get_mesh_latency`, `inspect_vram_load`, `apply_kamath_filter`), live execution feedback loop. |
| **Standalone Qwen Math Trend Optimizer** | `02_ai_models_and_inference/quantum/autonomous_math_trend_optimizer.py`<br>`01_apps/canonical_port/run_network_optimizer_tui.py` | `01_apps/operator_and_dev/qwen_math_trend_optimizer/`<br>├── `core/`<br>├── `models/`<br>└── `presentation/` | **High**. Decoupled background telemetry analyzer, closed-form inverse-variance latency striping proofs, 24/7 LoRA SFT/DPO dataset serialization. |
| **Web-TUI Portal Engine** | `01_apps/canonical_port/tui/serve_web_tui.py` | `01_apps/web_tui_portal/serve_portal.py` | **High**. Multi-app async PTY server on Port 8088 rendering all 7 apps at 120 FPS with WebGL xterm.js acceleration and port auto-reclamation. |

---

## 3. Deep Domain Analysis

### 3.1 Domain 1: User & Scaling Apps (`01_apps/user_facing_and_scaling/`)

#### 1. Flagship Movesense Physiological Readiness Suite
- **Architecture Requirements**: Must be structured into 4 clean, decoupled sub-packages:
  - `core/`: State machines, readiness score aggregator (0-100), biological data models, event buses.
  - `dsp/`: Pure mathematical algorithms:
    * **Pan-Tompkins 512Hz QRS Detector**: Bandpass filtering (5-15Hz), derivative, squaring, moving window integration, adaptive dual-threshold peak detection.
    * **Continuous PTT Blood Pressure Inversion**: Hughes-Bramwell arterial pulse wave equation linking sympathetic tone and RMSSD to SBP/DBP ($SBP = 120 + 0.45(200-PTT) + 0.15(HR-70)$).
    * **DFA-alpha1 Scaling Exponent**: Detrended Fluctuation Analysis for LT1 ($\alpha_1 = 0.75$) and LT2 ($\alpha_1 = 0.50$) aerobic/anaerobic thresholds.
    * **Overnight PPG Sleep Staging**: Deep, REM, Light, Awake stage transitions and restorative sleep score.
  - `presentation/`:
    * Native Textual TUI (`movesense_readiness_tui.py`) with responsive metric cards, ECG waveform visualizer, and Zone 2 pacing advice.
    * Web-TUI browser interface served via `/readiness`.
    * Web and mobile scaffolds (`zone2_endurance` Next.js dashboard and `lauburu_zone2_endurance` Flutter mobile app).
  - `transport/`: BLE GATT subscriber for Movesense sensor (`261030002013`), authentic stream deserializer (`movesense_live_stream.json`), and WebSocket broadcast server.

#### 2. 3D Spatial Grappling Kinematics
- **Tree Topology**: 3,044 outline nodes parsed from canonical `grappling.opml` across 4 core combat quadrants:
  1. Takedowns & Wrestling (Single Leg, Double Leg, Ankle Picks, Throws)
  2. Guard & Submissions (Closed, Half, Butterfly, X-Guard, Leg Locks, Chokes)
  3. Pins & Escapes (Side Control, Mount, Back Control, North-South, Turtle)
  4. Scrambles & Dynamic Transitions (Granby Rolls, Inversions, Kimura Traps)
- **Kinematic Skeleton**: Canonical MediaPipe 33-landmark 3D biomechanical joint mapping (Head [0-10], Torso [11-12], Arms [13-22], Pelvis [23-24], Legs [25-28], Feet [29-32]).
- **Rendering Projections**: 3D spatial mat projection $(x, y, z)$ on a $10\text{m} \times 10\text{m}$ tatami coordinate grid for WebGL / Three.js and Textual Canvas terminal rendering.
- **Biofeedback Overlay**: Real-time coupling with Movesense 128Hz/512Hz heart rate and strain to highlight physiological expenditure during specific positional holds and submissions.

#### 3. Gamified Combat Arena
- **Adversarial Mechanics**: Hermes 3 + OpenClaw (Red Faction) vs LuCI OpenWrt + Sentinel (Blue Faction).
- **Game Modes**:
  1. `EDGE_ORCHESTRATOR_CLASSIC`: Rule-based network self-healing and topology defense.
  2. `SMOLAGENTS_PYTHON_DUEL`: Local AGIs generating and executing dynamic Python countermeasure tools.
  3. `MULTI_MODEL_AGI_SWARM`: Genetic MoE router selecting optimal specialist SLMs.
  4. `AIRGAP_MESH_VS_CLOUD_CHAOS`: 100% local mesh resilience against injected external cloud chaos.
- **UI Dynamics**: Animated 120 FPS compute power tug-of-war bar, live cardiac pulse gauge, dual ASCII/ANSI graphical topology maps, 1-key interactive battle abilities (`[c]` Chaos, `[h]` Heal, `[b]` BQL Burst, `[s]` Shield), and RAG voice TTS synthesis.

#### 4. Headless Shopify Storefront & Membership Tiers
- **Commercial Tiers**:
  * **Athlete Membership ($9/month)**: 512Hz ECG, Zone 2 Cardio Coaching, PTT Blood Pressure, Overnight Sleep Score.
  * **Pro Membership ($29/month)**: Full 3,044-node 3D Spatial Grappling kinematics, AI sparring analytics, priority local model inference.
  * **Gym Team Tier ($99/month)**: Multi-athlete telemetry aggregation, 7-device mesh pooling, automated coach reports.
- **Hardware Sensor Bundles**: Movesense HR+ 512Hz single-lead chest straps, bicep compression sleeves, and magnetic charging cradles.
- **Integration**: Headless Shopify Storefront GraphQL query/mutation client with Cloudflare Edge caching and zero-mock offline fallback.

---

### 3.2 Domain 2: Operator & Dev Cockpits (`01_apps/operator_and_dev/`)

#### 1. Canonical Port 9-Screen NOC
- **9-Screen Stability Hierarchy**:
  1. Screen 1 (`[c]`/`[1]`): `ChatIdeScreen` / `AgiCodingTerminalScreen` (Swarm IDE & Shell)
  2. Screen 2 (`[n]`/`[2]`): `NetworkScreen` (Layer 0 Mesh Topology & WireGuard Links)
  3. Screen 3 (`[h]`/`[3]`): `HardwareScreen` (Layer 1 NOC Cockpit — 7 Physical Nodes, 108GB RAM pool)
  4. Screen 4 (`[b]`/`[4]`): `BiometricsScreen` (Layer 2 Medical DSP Telemetry)
  5. Screen 5 (`[i]`/`[5]`): `AiInferenceScreen` (Layer 3 llama.cpp RPC & Model Mesh)
  6. Screen 6 (`[t]`/`[6]`): `TrainingScreen` (Layer 4 24/7 LoRA Distillation & Games Arena)
  7. Screen 7 (`[g]`/`[7]`): `GovernanceScreen` (Layer 5 Infinite Debate & Truth Audit)
  8. Screen 8 (`[s]`/`[8]`): `ToolingScreen` (Layer 6 Daemons, WoL & MCP Servers)
  9. Screen 9 (`[o]`/`[9]`): `OptimizationScreen` (Layer 7 61-Parameter Network Tuner)
  - Extra screens: Screen 0 (`[a]` All Tabs Grid) and Screen `[x]` (Obsidian Vault Knowledge Graph Explorer).
- **Backend Architecture**: Decoupled asynchronous daemons (`devils_lock_governor.py`, `training_telemetry_collector.py`, `tui_specialist_daemon.py`), `blackboard_state.json` / `.yaml` synchronizer.

#### 2. SmolAgents Python Duel Sandbox
- **Core Concept**: Local AGIs (Hermes 3, LuCI OpenWrt, Qwen 2.5) act as autonomous software agents writing and executing Python scripts directly within a sandboxed environment.
- **Toolbox**:
  * `probe_socket(host, port)`: Validates active RPC/TCP socket health.
  * `get_mesh_latency(source, target)`: Measures TB4 DMA (0.35ms), WireGuard (1.85ms), and Wi-Fi 7 (0.85ms) round-trip times.
  * `inspect_vram_load()`: Queries real-time VRAM allocation across Mac Mini (9.8GB), MacBook Pro (13.5GB), Linux Head (13.4GB).
  * `apply_kamath_filter(hr, threshold)`: Applies biomedical filtering to raw sensor streams.
- **Execution Lifecycle**: Real-time code synthesis -> AST safety check -> Sandboxed subprocess run -> State feedback to arena blackboard.

#### 3. Standalone Qwen Math Trend Optimizer
- **Decoupled Analytics**: Runs as an independent daemon analyzing:
  * Inverse-variance multi-path packet striping weights ($w_i = \frac{1/RTT_i^2}{\sum 1/RTT_j^2}$).
  * Dynamic Byte Queue Limits (BQL) buffer depth ($BQL^* = \text{Throughput} \times RTT$).
  * Cardiac Autonomic Coherence Index ($\text{Coherence} = 1 - \frac{|HR - 75|}{100}$).
  * Quantum QAOA 4-qubit Hamiltonian routing eigenstates.
- **Continuous Knowledge Production**: Formats statistical derivations into SFT/DPO instruction pairs written to `04_data_and_memory/lora_datasets/qwen_math_optimization_trends.jsonl` and Obsidian Vault reports.

---

## 4. Web-TUI Portal Architecture on Port 8088

### 4.1 Server Mechanics & PTY Multiplexing
- **Engine**: FastAPI / aiohttp asynchronous event loop managing virtual pseudoterminals (`pty.openpty()`).
- **Terminal Emulator**: Browser frontend powered by `xterm.js 5.3.0` + `xterm-addon-fit` + `xterm-addon-webgl` delivering true hardware-accelerated 120 FPS text rendering.
- **Bidirectional WebSocket Protocol**:
  * `input` event: Encodes keystrokes from client terminal to PTY master file descriptor.
  * `resize` event: Propagates window column/row dimension changes to PTY via `termios.TIOCSWINSZ` ioctl.
  * Binary/text streaming: Direct non-blocking PTY read (`fcntl.O_NONBLOCK`) to WebSocket frame dispatch with sub-10ms latency.

### 4.2 Unified Route Mapping

```
GET /                      -> Unified Application Portal Landing Page (Two-Domain Visual Cards)
GET /readiness             -> Movesense Physiological Readiness & Cardio Coach Web-TUI
GET /grappling             -> 3D Spatial Grappling Kinematics (3,044 OPML Tree) Web-TUI
GET /arena                 -> Gamified Combat Arena & Swarm Tug-of-War Web-TUI
GET /store                 -> Headless Shopify Storefront & Membership Tiers Web-TUI
GET /canonical             -> Canonical Port 9-Screen Command Center Web-TUI
GET /smolagents            -> SmolAgents Python Duel Sandbox Web-TUI
GET /math                  -> Standalone Qwen Math Trend Optimizer Web-TUI
GET /ws/{app_slug}         -> High-Throughput Async WebSocket PTY Stream
```

---

## 5. Directory Restructuring & Migration Plan

### 5.1 Proposed File Hierarchy

```
01_apps/
├── user_facing_and_scaling/
│   ├── movesense_readiness_hub/
│   │   ├── core/                      # Biological domain models & readiness score
│   │   ├── dsp/                       # Pan-Tompkins 512Hz, PTT BP, DFA-alpha1, Sleep
│   │   ├── presentation/              # Textual TUI & Web views
│   │   ├── transport/                 # BLE GATT subscriber & JSON stream bridge
│   │   ├── web_dashboard/             # Next.js Zone 2 web application
│   │   └── mobile_flutter/            # Flutter cross-platform mobile client
│   ├── spatial_grappling_3d/
│   │   ├── core/                      # OPML parser & coordinate graph engine
│   │   ├── kinematics/                # MediaPipe 33-landmark biomechanical model
│   │   ├── opml_trees/                # Canonical 3,044-node grappling.opml
│   │   └── presentation/              # WebGL Three.js canvas & Textual TUI
│   ├── combat_arena/
│   │   ├── core/                      # Red/Blue faction state & game modes
│   │   ├── modes/                     # Edge Classic, SmolAgents, MoE, Airgap
│   │   └── presentation/              # 120 FPS Tug-of-War TUI & RAG Voice HUD
│   └── shopify_storefront/
│       ├── core/                      # Membership tier models ($9/$29/$99) & cart
│       ├── graphql/                   # Shopify Storefront GraphQL query client
│       └── presentation/              # Terminal commerce UI & Web storefront
│
├── operator_and_dev/
│   ├── canonical_port/
│   │   ├── screens/                   # 9 stability hierarchy screens
│   │   ├── views/                     # Harmonized React/Textual view models
│   │   ├── widgets/                   # NOC gauge widgets & prompt bars
│   │   ├── services/                  # Blackboard parser & telemetry streamer
│   │   └── backend/                   # Devils lock governor & background daemons
│   ├── smolagents_duel_sandbox/
│   │   ├── core/                      # Arena engine & execution loop
│   │   ├── tools/                     # Python executable tool registry
│   │   └── presentation/              # Duel cockpit & real-time AST/code viewer
│   └── qwen_math_trend_optimizer/
│       ├── core/                      # Statistical regression & QAOA routing math
│       ├── models/                    # LoRA instruction pair generators
│       └── presentation/              # Math telemetry trend dashboard
│
├── web_tui_portal/
│   ├── serve_portal.py                # FastAPI + WebSocket 120 FPS PTY Server
│   ├── templates/                     # Portal HTML & xterm.js / WebGL client
│   └── static/                        # CSS styles, badges, icons
│
└── shared_utilities/
    ├── dsp_math/                      # Pan-Tompkins, PTT, DFA-alpha1, BQL sizing
    ├── mesh_telemetry/                # Live socket probing, RTT, VRAM inspection
    └── opml_utils/                    # XML OPML tree traversal & coordinate mapping
```

### 5.2 Shared Utilities & Decoupling Strategy
To enforce zero tight coupling:
1. **Pure Algorithmic Library**: All math/DSP functions (`dsp_math/`) must take standard Python primitives (`List[float]`, `float`, `int`) and return dataclasses or dicts with zero framework dependencies.
2. **Schema-Driven Telemetry**: Subsystems communicate via well-typed JSON schemas over file inodes or local WebSockets.
3. **Fail-Closed Fallbacks**: In the absence of live hardware, apps render clean waiting states (`--`) per Rule #0 rather than generating simulated numbers.

---

## 6. Cloud AI Scaffolding & Airgap Compliance Protocol

- **Strict Health Airgap**: 100% of live biometric ECG data, pulse wave readings, and sleep stage records remain completely local on the client device and local mesh network.
- **Free-Tier Cloud AI Usage**:
  * **Gemini 2.5 Flash Free Tier**: Automated code generation of unit test suites, TypeScript/React/Flutter UI boilerplate, and API documentation.
  * **Cloudflare Workers AI Free Tier**: Remote code analysis, semantic linting, and public documentation sync.
- **Outbound Telemetry Auditing**: Periodic automated network interface audits verify that zero packets on the Movesense BLE GATT interface (`00002A37`) or local biometrics ports are forwarded to external WAN interfaces.
