# Comprehensive Codebase & Architecture Survey: Canonical Port (`01_apps/canonical_port`)

**Surveyor**: Canonical Port Codebase Explorer  
**Date**: 2026-08-27  
**Target Codebase**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port`  
**Monorepo Root**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`  
**Scope**: Codebase Structure, Packaging, Entry Points, TUI/Web UI Architecture, State Management, Architectural Gaps (R1–R5), and Test Infrastructure.

---

## 1. Executive Summary

The `01_apps/canonical_port` application is the unified command center for the **Lauburu Mesh Ecosystem**, designed to provide dual interfaces:
1. A cyberpunk aerospace Web Dashboard powered by React 18 and Vite 5.
2. A keyboard-driven headless Terminal UI (TUI) powered by Python Textual and Rich.
3. A headless Python telemetry store providing raw structured data for Master AGI models (Kimi 88B Tandem, Qwen 3.8 Max, Gemini 3.1 Pro).

While the application successfully implements core governance, 4 optimization mounting shells, local AI training/games benchmarking, and a dedicated network metrics dashboard with 100% test coverage across a 4-tier test suite (212 unit/E2E tests + 26 challenger tests), significant architectural gaps exist relative to the latest **ORIGINAL_REQUEST.md** directives:
- **Shared Telemetry Blackboard**: State is currently split between isolated Python in-memory dataclasses (`network_telemetry.py`) and Web UI React state/fallbacks (`mockFallbackData.js`). There is no persistent, atomic on-disk JSON/YAML blackboard feed for multi-agent swarm cross-pollination.
- **Foundational Stability Hierarchy Navigation**: Current navigation orders Governance -> Optimization -> Training -> Network, violating the mandatory ground-up stability ordering (Layer 0 Networking: WoL -> Bluetooth PAN/BLE -> KDE Connect -> TB4 DMA -> Tailscale/WAN -> Hardware -> Biometrics -> AI Inference -> Training -> Governance -> Commerce).
- **Maximalist Metric Coverage**: Deep monorepo telemetry (Movesense 512Hz ECG array streams, 10-route Multi-WAN matrix, 8 MCP servers, 74 Agent Skills, and Obsidian knowledge graph synchronization) is only partially integrated or represented as UI placeholders.

---

## 2. Directory Layout & Package Architecture

### 2.1 File Tree Structure
```
01_apps/canonical_port/
├── ORIGINAL_REQUEST.md              # Requirement specification
├── PROJECT.md                       # Project plan, interface contracts, feature inventory
├── README.md                        # User documentation & quickstart
├── TEST_READY.md                    # Test execution certification report
├── index.html                       # HTML5 entrypoint for Vite Web Dashboard
├── package.json                     # Node.js dependencies & scripts
├── package-lock.json                # npm lockfile
├── vite.config.js                   # Vite 5 React configuration
├── dist/                            # Production Web build bundle
│   ├── index.html
│   └── assets/ (index-*.js, index-*.css)
├── src/                             # React 18 Web UI source code
│   ├── main.jsx                     # ReactDOM root render
│   ├── App.jsx                      # Master layout router & state coordinator
│   ├── types/
│   │   └── networkTelemetry.ts      # TypeScript interfaces for network state
│   ├── styles/
│   │   ├── index.css                # Global CSS resets & variables
│   │   └── canonical_theme.css      # Aerospace dark cyber theme
│   ├── components/
│   │   ├── layout/
│   │   │   ├── ShellLayout.jsx      # Top header + collapsible sidebar wrapper
│   │   │   ├── SidebarNav.jsx       # Left navigation menu
│   │   │   └── HeaderStatusBar.jsx  # Top bar with VRAM meter, connectivity, WoL
│   │   ├── governance/
│   │   │   ├── MasterAGIGovernanceView.jsx
│   │   │   ├── AGIModelRosterCard.jsx
│   │   │   ├── ClusterVRAMGauge.jsx
│   │   │   ├── TriOrchestratorDebatePanel.jsx
│   │   │   ├── StagnationEscalationModal.jsx
│   │   │   └── SwarmActionDispatcherBar.jsx
│   │   ├── network/
│   │   │   ├── NetworkMetricsView.jsx
│   │   │   ├── WANFailoverCard.jsx
│   │   │   ├── TB4DmaBridgeCard.jsx
│   │   │   ├── TailscaleMeshCard.jsx
│   │   │   └── LlamaRpcLatencyCard.jsx
│   │   ├── optimization/
│   │   │   ├── OptimizationHubShell.jsx
│   │   │   ├── HardwareOptimizationView.jsx
│   │   │   ├── SoftwareOptimizationView.jsx
│   │   │   ├── InternetOptimizationView.jsx
│   │   │   └── StorageOptimizationView.jsx
│   │   ├── training/
│   │   │   ├── TrainingMultiTabView.jsx
│   │   │   ├── LoRADistillationMonitorTab.jsx
│   │   │   ├── ImplementedGamesArenaTab.jsx
│   │   │   ├── StructuralMetricsTab.jsx
│   │   │   └── ExecutionTracesTab.jsx
│   │   └── leaderboard/
│   │       └── CanonicalLeaderboardView.jsx
│   ├── hooks/
│   │   ├── useLiveTelemetry.js      # Polling hook for Port 18802/4000 VRAM state
│   │   ├── useNetworkMetrics.js     # Polling hook for Port 18802 network telemetry
│   │   └── useSwarmDebate.js        # Multi-turn debate state machine
│   └── services/
│       ├── api.js                   # CanonicalApiService REST client
│       └── mockFallbackData.js      # Rule #0 compliant fallback constants
├── tui/                             # Python Textual / Rich Terminal UI
│   ├── requirements.txt             # Python dependencies (textual, rich, httpx)
│   ├── canonical_tui.py             # Master Textual App entrypoint
│   ├── models/
│   │   ├── __init__.py
│   │   ├── network_telemetry.py     # Dataclasses (WanRoute, TailscalePeer, TB4, RPC)
│   │   └── network_state.py         # Model aliases
│   ├── screens/
│   │   ├── governance_screen.py     # AGI Roster & 82.8GB VRAM sharding screen
│   │   ├── network_screen.py        # Dedicated 4-table network metrics screen
│   │   ├── optimization_screen.py   # 4-tab optimization aggregation screen
│   │   └── training_screen.py       # 4-tab training & games arena screen
│   └── services/
│       ├── __init__.py
│       └── network_telemetry_store.py # Headless state store with live socket probing
└── tests/                           # Multi-Tier Opaque-Box & Unit Test Suite
    ├── conftest.py                  # Pytest configuration and path injection
    ├── run_tests.sh                 # Bash master test runner
    ├── run_all_tiers.py             # Python programmatic 4-tier runner
    ├── unit/
    │   ├── test_tui_components.py
    │   ├── test_network_headless_store.py
    │   ├── test_navigation_routing.py
    │   ├── test_react_components_ast.py
    │   ├── test_training_multitab.py
    │   ├── test_optimization_mounts.py
    │   └── test_governance_contracts.py
    └── e2e/
        ├── test_tier1_category_partition.py
        ├── test_tier2_boundary_values.py
        ├── test_tier3_pairwise_combinations.py
        ├── test_tier4_real_world_scenarios.py
        ├── test_challenger_react_web_adversarial.py
        ├── test_challenger_tui_adversarial.py
        └── test_challenger_empirical_stress.py
```

### 2.2 Dependencies & Packaging
| Ecosystem | File | Key Dependencies | Notes |
| :--- | :--- | :--- | :--- |
| **Node.js (Web)** | `package.json` | `react: ^18.3.1`, `react-dom: ^18.3.1`, `vite: ^5.4.2`, `@vitejs/plugin-react: ^4.3.1` | Clean zero-dependency runtime (pure CSS/JS). No bloated UI libraries. |
| **Python (TUI)** | `tui/requirements.txt` | `textual>=0.50.0`, `rich>=13.7.0`, `httpx>=0.27.0` | Packaged as standalone scripts. Invoked via `uv run --with ...`. |
| **Python Project** | *(None)* | Missing `pyproject.toml` | No unified `pyproject.toml` currently exists at `canonical_port/` root. |

---

## 3. Entry Points & Execution Lifecycle

### 3.1 Web Dashboard (Vite / React 18)
- **Development**: `npm run dev` (Spawns Vite local server on `http://localhost:3000`).
- **Production Build**: `npm run build` (Outputs optimized production bundle to `dist/` in ~400ms).
- **Execution Flow**: `index.html` mounts `src/main.jsx` -> renders `src/App.jsx` inside `ShellLayout.jsx`.
- **API Connectivity**: `CanonicalApiService` (`src/services/api.js`) attempts connections to:
  - Port 4000 (`/api/agi/models`, `/api/swarm/debate`)
  - Port 18802 (`/api/mesh/vram`, `/api/mesh/telemetry`, `/api/action`)
  - Port 50052 (`llama.cpp` RPC sharding sockets)

### 3.2 Terminal UI (Python Textual)
- **Invocation**: `uv run --with textual,rich,httpx python3 tui/canonical_tui.py`
- **Application Class**: `CanonicalPortTUI(App)` in `tui/canonical_tui.py`
- **Navigation Keybindings**:
  - `g`: Switch to `GovernanceScreen`
  - `n`: Switch to `NetworkScreen`
  - `o`: Switch to `OptimizationScreen`
  - `t`: Switch to `TrainingScreen`
  - `r`: Refresh live telemetry across all 7 nodes
  - `q`: Clean application termination
- **Screen Rendering**: Rich tables and panels rendered inside Textual `ScrollableContainer` or `TabbedContent`.

### 3.3 Headless Python Telemetry API
- **Module**: `tui.services.network_telemetry_store.network_telemetry_store`
- **Methods**:
  - `network_telemetry_store.get_current_snapshot()` -> Returns `NetworkTelemetrySnapshot`
  - `network_telemetry_store.get_raw_state_for_agi()` -> Returns pure Python `dict`
  - `network_telemetry_store.to_json(indent=2)` -> Returns formatted JSON string
  - `network_telemetry_store.probe_socket_latency(host, port)` -> Live TCP connect probe

---

## 4. Current Dual-Interface Architectures

### 4.1 Web UI Architecture
```
App.jsx (Master State & Active Route)
 ├── ShellLayout.jsx (HeaderStatusBar + SidebarNav)
 ├── MasterAGIGovernanceView.jsx
 │    ├── AGIModelRosterCard.jsx
 │    ├── ClusterVRAMGauge.jsx (82.8 GB Pooled VRAM)
 │    ├── TriOrchestratorDebatePanel.jsx (>0.98 Accord)
 │    ├── StagnationEscalationModal.jsx
 │    └── SwarmActionDispatcherBar.jsx (/audit, /duel, /cron, /storage, /ping, /revive)
 ├── NetworkMetricsView.jsx
 │    ├── WANFailoverCard.jsx (10-Route EWMA Circuit Breaker)
 │    ├── TB4DmaBridgeCard.jsx (10Gbps PCIe DMA Bridge)
 │    ├── TailscaleMeshCard.jsx (7-Node WireGuard Mesh)
 │    └── LlamaRpcLatencyCard.jsx (Port 50052 -ts 28,28,24 Sharding Split)
 ├── OptimizationHubShell.jsx (Sub-navigation for 4 optimization modules)
 │    ├── HardwareOptimizationView.jsx (LiveDeviceSentinelHUD + Biometrics DSP)
 │    ├── SoftwareOptimizationView.jsx (MetaTrainingGame AST + Clang ASan Sandbox)
 │    ├── InternetOptimizationView.jsx (FutureNetworkSimulationHub)
 │    └── StorageOptimizationView.jsx (StorageAnalysisHub + Tri-Vault Sync)
 ├── TrainingMultiTabView.jsx (4 Sub-tabs)
 │    ├── LoRADistillationMonitorTab.jsx (24/7 SFTTrainer + Truth Gate)
 │    ├── ImplementedGamesArenaTab.jsx (13-Model FFA Championship)
 │    ├── StructuralMetricsTab.jsx (PySpark AST Monorepo Index: 10.2k files, 3.29M LOC)
 │    └── ExecutionTracesTab.jsx (Swarm Action Ledger)
 └── CanonicalLeaderboardView.jsx (ELO Leaderboard)
```

### 4.2 TUI Architecture
```
CanonicalPortTUI (Textual App)
 ├── Screen 1: GovernanceScreen
 │    ├── Header(show_clock=True)
 │    ├── #agi-roster-view (Rich Table: Kimi 88B, Qwen 3.8 Max, Gemini Flash, Genetic MoE)
 │    ├── #cluster-vram-view (Rich Table: 7 physical nodes, AI VRAM caps, dynamic ceilings)
 │    ├── #debate-feed-view (Rich Panel: 3-turn live consensus feed)
 │    ├── Action Buttons Horizontal Bar (/audit, /duel, /cron, /storage, /ping, Stagnation)
 │    └── Footer()
 ├── Screen 2: NetworkScreen
 │    ├── #wan-status-view (Rich Table: WAN routes, EWMA RTT, drop rate, circuit state)
 │    ├── #tb4-dma-view (Rich Table: 10Gbps TB4 DMA Bridge interconnect metrics)
 │    ├── #tailscale-mesh-view (Rich Table: 7-Node WireGuard overlay status)
 │    ├── #rpc-latency-view (Rich Table: Port 50052 llama.cpp RPC nodes)
 │    └── Action Buttons (Ping TB4, Probe RPC, Refresh, WoL)
 ├── Screen 3: OptimizationScreen
 │    └── TabbedContent (Hardware, Software, Internet, Storage)
 └── Screen 4: TrainingScreen
      └── TabbedContent (LoRA Distillation, Games Arena, AST Metrics, Action Traces)
```

---

## 5. State Store & Management Analysis

### 5.1 Python Headless State Store
- **Models** (`tui/models/network_telemetry.py`): Strongly typed Python dataclasses:
  - `WanRoute`: Represents WAN interface, status, EWMA RTT, drop rate, circuit breaker state, bandwidth.
  - `TailscalePeer`: 7 nodes with name, Tailscale IP, status, relay type, layer (L1–L7), OS.
  - `Tb4DmaInterconnect`: 10Gbps TB4 bridge link, status, 0.277ms nominal RTT, 38.4 Gbps throughput.
  - `LlamaRpcNode`: Port 50052 sharding nodes (`-ts 28,28,24` layer allocations, VRAM used, RTT).
  - `NetworkTelemetrySnapshot`: Root aggregation container with `.to_dict()`, `.to_json()`, and `.from_dict()`.
- **Probing Engine** (`tui/services/network_telemetry_store.py`):
  - Performs live TCP connect probes (`probe_socket_latency()`) against endpoints with a 100ms timeout.
  - Implements a 1.0-second TTL cache (`_cache_ttl_seconds = 1.0`) to protect against high-frequency query exhaustion.
  - Generates authentic waiting states (`None` / `--`) rather than fabricated mock jitter (Rule #0).

### 5.2 React Web State Store
- **State Holders**: Local React state variables inside `src/App.jsx` (`models`, `trainingState`, `gamesState`, `structuralMetrics`, `executionTraces`, `leaderboard`).
- **Hooks**:
  - `useLiveTelemetry(2500)`: Periodically polls `http://127.0.0.1:18802/api/mesh/vram`.
  - `useNetworkMetrics(2500)`: Periodically polls `http://127.0.0.1:18802/api/mesh/telemetry`.
  - `useSwarmDebate()`: Maintains 4-turn debate state with consensus accord calculation and stagnation handling.
- **Fallbacks** (`src/services/mockFallbackData.js`): Provides static initial fallback structures reflecting the canonical 7-node hardware matrix (108 GB RAM, 82.8 GB AI VRAM) when backend daemons are unreachable.

---

## 6. Detailed Architectural Gap Analysis (Requirements R1–R5)

### 🚨 Gap 1: Shared Telemetry Blackboard Pattern (R2)
* **Current Situation**: Telemetry state is siloed. The Python TUI state store (`NetworkTelemetryStore`) only stores network data; other screens have their metrics hardcoded into presentation tables. The Web UI relies on disparate API calls and in-memory JS state.
* **Requirement**: All specialist agents and system components must read from and write to a single centralized telemetry feed (Blackboard Pattern).
* **Missing Architecture**:
  1. No unified `BlackboardState` schema aggregating fleet hardware, multi-WAN, open ports/daemons, training/games, biometrics DSP, tooling metrics, and knowledge vault sync.
  2. No persistent on-disk state file (e.g. `blackboard_state.json` / `blackboard_state.yaml`) with file locking or REST/WebSocket broadcast enabling bi-directional reads/writes by the swarm.

### 🚨 Gap 2: Foundational Stability Hierarchy Navigation (R4)
* **Current Situation**:
  - Web UI Sidebar: `GOVERNANCE & AGI` -> `OPTIMIZATION MODULES` -> `LOCAL AI TRAINING & BENCH`.
  - TUI Navigation: `1` Governance -> `2` Optimization -> `3` Training -> `n` Network.
* **Requirement**: Navigation and visual layout must strictly build from the ground up based on foundational physical stability:
  1. **Layer 0 — Foundation & Bare-Metal Networking**: WoL (Power) -> Bluetooth PAN / BLE Proximity -> KDE Connect LAN -> Thunderbolt 4 DMA -> Tailscale / WAN Overlays.
  2. **Layer 1 — Hardware & Node Infrastructure**: 7 Physical Nodes, 108GB RAM / 82.8GB VRAM pools, Storage Tri-Vault (Obsidian, PySpark Lake, Git), Daemons/Open Ports.
  3. **Layer 2 — Biometrics & Edge DSP**: Movesense 512Hz ECG, Pan-Tompkins QRS, PTT Blood Pressure, DFA-alpha1, Zone 2 endurance.
  4. **Layer 3 — Local AI Inference & Mesh Sharding**: llama.cpp GGML-RPC (Port 50052), Petals DHT, Exo P2P.
  5. **Layer 4 — Local AI Training & Games Arena**: SFTTrainer 24/7 LoRA, Truth Gate verification, 13-Model FFA Arena, PySpark AST metrics.
  6. **Layer 5 — Master AGI Governance & Debate Council**: Tri-Orchestrator (>0.98 Accord), Stagnation Failsafe, Action Dispatcher, ELO Leaderboard.
  7. **Layer 6 — Tooling, Commerce & Swarm Extensions**: Shopify Storefront GraphQL, MCP Server status, Agent Skills catalog, CLI fleet.

### 🚨 Gap 3: Maximalist Metric Integration (R1, R5)
* **Missing Monorepo Feeds in `canonical_port`**:
  - **Biometrics DSP**: `03_biometrics_and_telemetry` contains active Movesense BLE 512Hz ECG streams and optical PPG DSP, but `canonical_port` currently displays only a static placeholder box.
  - **Tooling Metrics**: Monorepo has 8 active MCP servers, 74 Agent Skills, and key CLIs (`agy`, `uv`, `gh`, `adb`, `docker`), none of which are surfaced in the headless state or UI.
  - **Full 10-Route Multi-WAN**: `NetworkScreen` only shows 3 routes (`en0`, `en6`, `utun1`) instead of the full 10-route matrix (Speedify, TB4 10GbE, Bluetooth PAN, Wi-Fi Direct AWDL, Mobile Hotspot, Tailscale DERP).
  - **YAML State Serialization**: Current state store only exports JSON; YAML serialization is required for headless agent ingestion.

### 🚨 Gap 4: Modular Separation & Headless Python Model Completeness (R3, R5)
* **Current Situation**: Only `network_telemetry.py` exists as a structured dataclass model in `tui/models/`. Governance, Training, and Optimization data are defined as inline string tables in screen classes.
* **Requirement**: All modules must have corresponding headless Python dataclasses in `tui/models/` (e.g., `hardware_models.py`, `biometrics_models.py`, `governance_models.py`, `training_models.py`, `tooling_models.py`, `blackboard_models.py`).

---

## 7. Existing Test Infrastructure & Quality Assurance

### 7.1 Test Suite Structure
The test suite in `tests/` contains **17 test files**:
- **Unit & AST Tests (7 files)**:
  - `test_tui_components.py`: TUI lifecycle, keyboard shortcuts, screen switching.
  - `test_network_headless_store.py`: Model serialization, round-trip deserialization, socket probe resilience.
  - `test_navigation_routing.py`: Route transitions and deep linking.
  - `test_react_components_ast.py`: Physical JSX/CSS verification and exports.
  - `test_training_multitab.py`: Training state, loss curves, sample stream.
  - `test_optimization_mounts.py`: 4 optimization module mounting contracts.
  - `test_governance_contracts.py`: Master AGI specs and VRAM allocations.
- **4-Tier Opaque-Box E2E Tests (4 files)**:
  - `test_tier1_category_partition.py`: 75 tests covering all 15 features across nominal partitions.
  - `test_tier2_boundary_values.py`: 75 boundary tests (e.g. 0 loss, extreme latency, 0 free disk, NaN loss).
  - `test_tier3_pairwise_combinations.py`: 16 pairwise combinatorial interaction tests.
  - `test_tier4_real_world_scenarios.py`: 5 real-world swarm workload scenarios.
- **Challenger Adversarial Stress Tests (3 files)**:
  - `test_challenger_react_web_adversarial.py`: Web AST, null guards, division-by-zero protection.
  - `test_challenger_tui_adversarial.py`: Rapid keypress bursts, malformed snapshots, viewport resizing.
  - `test_challenger_empirical_stress.py`: Real Textual pilot lifecycle, API fallback, telemetry bounds.

### 7.2 Test Execution Commands & Verified Results
| Test Runner | Command | Status | Time |
| :--- | :--- | :--- | :--- |
| **Vite Web Build** | `npm run build` | 🟢 PASS | 0.40s |
| **4-Tier E2E Master** | `uv run --with rich,textual,pytest python tests/run_all_tiers.py` | 🟢 212/212 PASS | 2.72s |
| **Challenger Adversarial** | `uv run --with rich,textual,pytest,pytest-asyncio pytest tests/e2e/test_challenger_*.py` | 🟢 26/26 PASS | 46.36s |
| **Full Pytest Suite** | `uv run --with rich,textual,pytest,pytest-asyncio pytest tests/ -v` | 🟢 255/255 PASS | 48.91s |

*Note: The async challenger tests (`test_challenger_tui_adversarial.py` and `test_challenger_empirical_stress.py`) require `pytest-asyncio` when run directly through pytest.*

---

## 8. Actionable Architectural Recommendations

To address all identified gaps and satisfy requirements R1–R5, the following engineering steps are recommended:

1. **Implement Unified Telemetry Blackboard (`tui/models/blackboard_models.py` & `tui/services/blackboard_store.py`)**:
   - Aggregate all monorepo domains: Network, Hardware, Biometrics, Local AI Inference, Training & Benchmarks, Governance, and Tooling.
   - Support bidirectional disk persistence (`blackboard_state.json` / `blackboard_state.yaml`) with file locking.
2. **Restructure Navigation to Foundational Stability Hierarchy (Ground-Up)**:
   - Reorder Web UI `SidebarNav.jsx` and TUI `canonical_tui.py` to follow Layers 0 -> 6 (Networking -> Hardware/Storage -> Biometrics -> AI Inference -> Training -> Governance -> Tooling/Commerce).
3. **Expand Headless Models & Serializers**:
   - Create Python dataclasses for `HardwareFleetState`, `BiometricsDspState`, `AiInferenceState`, `TrainingBenchState`, `GovernanceState`, `ToolingState`.
   - Add native PyYAML serialization (`.to_yaml()`) alongside `.to_json()`.
4. **Integrate Live Biometrics & Tooling Feeds**:
   - Wire up live Movesense 512Hz ECG DSP and PPG telemetry cards.
   - Wire up MCP server status cards (8 servers) and Agent Skills metrics (74 skills).
5. **Add Root `pyproject.toml`**:
   - Standardize Python project metadata, dependencies (`textual`, `rich`, `httpx`, `pyyaml`, `pytest`, `pytest-asyncio`), and console entrypoints (`canonical-tui`).

