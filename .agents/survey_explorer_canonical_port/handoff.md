# Handoff Report: Canonical Port Codebase Survey (`01_apps/canonical_port`)

**Agent**: survey_explorer_canonical_port  
**Role**: Canonical Port Codebase Explorer  
**Date**: 2026-08-27  
**Working Directory**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_canonical_port`  
**Target Codebase**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port`  
**Handoff Type**: Hard (Task Complete)

---

## 1. Observation

Direct observations from deep inspection of `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port`:

1. **Packaging and Dependencies**:
   - Web application is configured in `package.json` with React 18 (`react: ^18.3.1`, `react-dom: ^18.3.1`) and Vite 5 (`vite: ^5.4.2`, `@vitejs/plugin-react: ^4.3.1`).
   - TUI application dependencies are declared in `tui/requirements.txt` (`textual>=0.50.0`, `rich>=13.7.0`, `httpx>=0.27.0`).
   - No `pyproject.toml` exists in `01_apps/canonical_port` or at monorepo root.
2. **Entry Points & Execution**:
   - Web entrypoint: `index.html` -> `src/main.jsx` -> `src/App.jsx`. Builds cleanly via `npm run build` in 401ms producing `dist/assets/index-BqET5QgX.js` (233.96 kB) and `dist/assets/index-C6jswbQi.css` (4.42 kB). Dev server runs on `localhost:3000`.
   - TUI entrypoint: `tui/canonical_tui.py` (`CanonicalPortTUI(App)`). Keybindings: `g` (Governance), `n` (Network), `o` (Optimization), `t` (Training), `r` (Refresh), `q` (Quit).
   - Headless State Store entrypoint: `tui/services/network_telemetry_store.py` (`network_telemetry_store.get_raw_state_for_agi()`, `get_current_snapshot()`, `to_json()`).
3. **Current State Store Architecture**:
   - `tui/models/network_telemetry.py` defines dataclasses (`WanRoute`, `TailscalePeer`, `Tb4DmaInterconnect`, `LlamaRpcNode`, `NetworkTelemetrySnapshot`) with `.to_dict()`, `.to_json()`, `.from_dict()`.
   - `NetworkTelemetryStore` performs real TCP socket probing (`probe_socket_latency()`) against Port 50052 with a 100ms timeout and a 1.0s TTL cache.
   - Frontend state is maintained via React `useState` in `App.jsx`, polling REST endpoints (Ports 4000, 18802) via `src/hooks/useLiveTelemetry.js`, `src/hooks/useNetworkMetrics.js`, and `src/services/api.js`, falling back to `mockFallbackData.js`.
4. **Identified Architectural Gaps**:
   - **Shared Telemetry Blackboard**: Currently limited strictly to network telemetry. No unified `BlackboardState` or atomic on-disk JSON/YAML file exchange for multi-agent swarm reading/writing exists.
   - **Stability Hierarchy Navigation**: SidebarNav and TUI navigation start with Governance instead of foundational physical networking (WoL -> BLE -> KDE Connect -> TB4 DMA -> Tailscale/WAN -> Hardware -> Biometrics -> AI Inference -> Training -> Governance -> Commerce).
   - **Maximalist Metrics**: Movesense 512Hz ECG array streams (`03_biometrics_and_telemetry`), MCP server metrics (8 servers), and Agent Skills (74 skills) are currently placeholders or missing from the state store.
   - **Missing Python Models**: Governance, Training, and Optimization lack dedicated dataclasses in `tui/models/`.
5. **Test Infrastructure**:
   - Total test files: 17 files in `tests/` (7 unit test files, 4 4-tier E2E files, 3 challenger files).
   - Test execution: `python tests/run_all_tiers.py` passes 212/212 tests (100%) in 2.72s. Full pytest suite (`uv run --with rich,textual,pytest,pytest-asyncio pytest tests/ -v`) passes 255/255 tests (100%) in 48.91s.

---

## 2. Logic Chain

1. **Premise 1**: From reading `ORIGINAL_REQUEST.md`, the objective is to integrate all monorepo metrics into Canonical Port, enforce a strict ground-up stability hierarchy, provide a shared telemetry blackboard for swarm agents, and maintain strict visual/modular separation.
2. **Premise 2**: Inspection of `01_apps/canonical_port` source files reveals that while the Dual TUI and Web UI foundations are robust and 100% test-backed, the data models are currently fractured: network data is model-backed in Python, whereas governance, training, and optimization data are hardcoded presentation strings in TUI screens and JS fallbacks.
3. **Premise 3**: In the current navigation structure (`SidebarNav.jsx` and `canonical_tui.py`), Governance is placed at the top (Layer 5) rather than Networking (Layer 0: WoL -> Bluetooth -> KDE Connect -> TB4 -> Tailscale), which directly conflicts with Requirement R4 (Foundational Stability Ordering).
4. **Premise 4**: Real monorepo telemetry from `00_core_infrastructure`, `02_ai_models_and_inference`, `03_biometrics_and_telemetry`, `04_data_and_memory`, and `05_agents_and_swarms` exists across disk and live ports, but is not aggregated into a central blackboard store or exposed via YAML serialization.
5. **Inference/Conclusion**: Upgrading Canonical Port requires:
   - Defining a comprehensive `BlackboardState` Python dataclass model hierarchy in `tui/models/` and a persistent `BlackboardStore` in `tui/services/`.
   - Reordering Web UI navigation and TUI screens to strictly follow the 7-layer stability hierarchy (Layer 0 to Layer 6).
   - Integrating genuine biometrics DSP, 10-route Multi-WAN, and tooling feeds.
   - Adding a root `pyproject.toml` with YAML and async testing support.

---

## 3. Caveats

1. **Async Pytest Requirement**: Running direct pytest on `test_challenger_tui_adversarial.py` and `test_challenger_empirical_stress.py` requires `pytest-asyncio` (`uv run --with rich,textual,pytest,pytest-asyncio pytest tests/`). Running via `run_all_tiers.py` executes the 4 tiers synchronously.
2. **Socket Probing in Isolated Sandboxes**: Socket probes in `network_telemetry_store.py` timeout cleanly to authentic `None` states if external nodes (e.g. `100.101.39.98:50052`) are unreachable, preserving Rule #0 without raising unhandled exceptions.
3. **Scope of Investigation**: This survey was read-only per mission constraints. No modifications were made to `01_apps/canonical_port` source files.

---

## 4. Conclusion

The `01_apps/canonical_port` codebase is in a stable, fully passing state with clean code separation between Web UI (React/Vite) and TUI (Textual/Rich). However, to fulfill the full mandate of the monorepo-wide metric aggregation and blackboard swarm integration, the following core enhancements must be implemented in the subsequent refactor/build phase:
1. Construct the **Unified Telemetry Blackboard** (`blackboard_models.py` + `blackboard_store.py`) with atomic JSON/YAML disk sync.
2. Refactor navigation in both Web UI and TUI to enforce the **Ground-Up Stability Hierarchy** (Layers 0–6).
3. Expand **Maximalist Metric Coverage** to ingest live Movesense 512Hz ECG biometrics, 10-route Multi-WAN, MCP servers, and Agent Skills.
4. Establish standardized Python packaging with `pyproject.toml`.

---

## 5. Verification Method

To independently verify all findings and test suite execution:

1. **Verify Web Dashboard Production Build**:
   ```bash
   cd /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port
   npm run build
   ```
   *Expected result*: Build succeeds in < 1.0s, outputting bundle to `dist/`.

2. **Verify 4-Tier Test Suite Execution**:
   ```bash
   cd /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port
   uv run --with rich,textual,pytest python tests/run_all_tiers.py
   ```
   *Expected result*: 212 tests pass (100% pass rate across Unit, Tier 1, Tier 2, Tier 3, Tier 4).

3. **Verify Full Pytest Suite (including Async Challenger Tests)**:
   ```bash
   cd /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port
   uv run --with rich,textual,pytest,pytest-asyncio pytest tests/ -v
   ```
   *Expected result*: 255 tests pass (0 failures, 0 errors).

4. **Verify Headless Telemetry State Output**:
   ```bash
   cd /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/tui
   uv run --with textual,rich,httpx python3 -c "from services.network_telemetry_store import network_telemetry_store; print(network_telemetry_store.to_json())"
   ```
   *Expected result*: Valid JSON snapshot containing 7 Tailscale peers, TB4 DMA link, and 3 llama.cpp RPC nodes.

5. **Inspect Comprehensive Codebase Survey Report**:
   ```bash
   cat /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_canonical_port/canonical_port_survey.md
   ```

