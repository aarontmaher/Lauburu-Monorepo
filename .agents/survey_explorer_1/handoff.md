# Comprehensive Codebase Survey: Autonomous Continuous Execution Loop & Dual-World Mesh Swarm

**Agent**: `survey_explorer_1`  
**Working Directory**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_1`  
**Target Milestone**: M1_Codebase_Survey  
**Date**: 2026-09-01  

---

## 1. Observation

### 1.1 High-Confidence Runner & Confidence Gating Engine (R1, R4)
- **File**: `05_agents_and_swarms/high_confidence_swarm_runner.py`
  - **Lines 34–56**: Implements `DualWorldConfidenceGate` with `CONFIDENCE_THRESHOLD = 0.85`.
    - Evaluates task confidence based on test harness presence (`+0.15`), established polyglot domain (`+0.10`), or speculative ambiguity (`-0.25`).
    - Returns `DIRECT_EXECUTION` when `score >= 0.85`, else `LOCAL_TRAINING_FALLBACK`.
  - **Lines 58–109**: Implements `HighConfidenceSwarmRunner`.
    - `execute_step()` routes `>= 0.85` tasks via Free Cloud Oracle (`Gemini 3.7 Flash`) and Dual-World MCTS pass (`AgentWorld-35B` + `WebWorld-32B`).
    - Routes `< 0.85` tasks to local AI training fallback, formatting training pairs with adversarial counter-examples and appending atomically to `/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl`.
    - Updates persistent state at `04_data_and_memory/high_confidence_runner_state.json`.
- **Test File**: `05_agents_and_swarms/test_high_confidence_runner.py` (52 lines)
  - Tests high-confidence execution routing, low-confidence fallback routing, zero cloud spend assertion (`cloud_spend_aud == 0.00`), and LoRA sample appending.
  - **Test Command & Result**:
    `python3 -m unittest 05_agents_and_swarms/test_high_confidence_runner.py`
    Output: `Ran 3 tests in 0.001s; OK`.

### 1.2 Free Cloud AI API Quota Harvester & Zero-Dollar Gatekeeper (R2)
- **File**: `05_agents_and_swarms/cloud_oracle_shadow.py` (853 lines)
  - Implements 4-tier provider waterfall:
    1. Tier 1: Google AI Studio Free Tier (Gemini 3.7 Flash High / 2.5 Flash / 2.0 Flash at 15 RPM / 1,500 RPD).
    2. Tier 2: Cloudflare Workers AI Free Tier (10k Neurons/day, `@cf/meta/llama-3.1-8b`, `@cf/qwen/qwen2.5-coder-32b-instruct`).
    3. Tier 3: Local Hardware Mesh RPC (Ports 8081–8088 / llama.cpp / Petals / Exo).
    4. Tier 4: Deterministic Offline Heuristic Engine (100% zero-mock AST-valid generation).
  - Enforces `assert result["cost_usd"] == 0.00` and `is_free_tier is True` with `ZeroDollarSpendViolationError` kill-switch.
  - Paced rate limiter at 14.2 RPM (~4.225s interval) and daily request quota governance.
- **File**: `06_scripts_and_tooling/automation/cloud_api_quota_manager.py` (1,676 lines)
  - Multi-factor composite fitness scoring for free API quotas:
    $$\text{Score} = 0.40 \cdot Q_{\text{rem\_pct}} + 0.25 \cdot \text{Speed}_{\text{norm}} + 0.25 \cdot \text{Token}_{\text{fit}} + 0.10 \cdot \text{Health} - \text{Penalties}$$
  - Atomic quota state persistence with `fcntl.flock` at `04_data_and_memory/data/cloud_api_quota_state.json`.
- **Test Command & Result**:
  `python3 -m pytest 05_agents_and_swarms/test_cloud_oracle_shadow.py` (23 passed in 8.2s).
  `python3 -m pytest 06_scripts_and_tooling/tests/test_cloud_api_quota_manager.py` (30 passed in 3.1s).

### 1.3 Dual-World MCTS Lookahead Simulation Engine (R3)
- **File**: `05_agents_and_swarms/dual_world_mcts.py` (1,249 lines)
  - `MCTSNode` tracks AST patch diffs, visit count $N$, total value $W$, mean value $Q$, policy prior $P$, and depth.
  - `DualWorldMCTSEngine` executes PUCT tree search ($c_{\text{puct}} = 1.414$) with:
    - `AgentWorldSimulator (:8086)`: OS / AST / test runner execution $\to V_{\text{agent}} \in [0.0, 1.0]$.
    - `WebWorldSimulator (:8088)`: DOM / API / contract conformance $\to V_{\text{web}} \in [0.0, 1.0]$.
    - `DevilsAdvocateClient (:8085)`: Huihui-27B adversarial auditor $\to P_{\text{devil}} \in [0.0, 1.0]$.
    - `RouterSentinelMonitor (:18802)`: OpenWrt health guardian ($\le 28\,\text{MB}$ RAM, 0% packet loss).
    - Composite Value: $V(s) = \text{clamp}(0.25 V_{\text{oracle}} + 0.35 V_{\text{agent}} + 0.25 V_{\text{web}} - 0.15 P_{\text{devil}}, 0.0, 1.0)$.
- **Test Command & Result**:
  `python3 -m pytest 05_agents_and_swarms/test_dual_world_mcts.py` (29 passed in 5.8s).

### 1.4 Dynamic RAM Governor & Mac Mini Free Headroom Guard (AC3)
- **File**: `06_scripts_and_tooling/automation/dynamic_ram_governor.py` (535 lines)
  - Monitors Apple Silicon unified RAM, enforces $\ge 4.5\,\text{GB}$ free headroom.
  - Adapts based on user activity (`IOHIDSystem`): Interactive Mode ($\le 75\%$ ceiling, throttles training batches) vs Maximum Burst Mode ($\le 88\%$ ceiling).
  - Triggers autonomous memory reclamation (`gc.collect()`, `torch.mps.empty_cache()`, OS page purge) and TB4 DMA layer offload to MacBook Pro (`169.254.187.138`).
- **Test Command & Result**:
  `python3 -m pytest 06_scripts_and_tooling/tests/test_dynamic_ram_governor.py` (19 passed in 2.6s).

### 1.5 Live TUI Server on Port 8088 & WebGL Terminal Stream (R5, AC4)
- **File**: `01_apps/web_tui_portal/serve_portal.py` (571 lines)
  - FastAPI server running on `0.0.0.0:8088` providing live WebGL terminal streams at 120 FPS via `/ws/{app_id}`.
  - Endpoints:
    - `/training`: HTML UI for real-time training telemetry and pipeline inspection.
    - `/leaderboard`: Mounts `leaderboard_dashboard.router` for live ELO ratings.
    - `/api/status` & `/api/apps`: Returns status, port 8088, 120 FPS, and registered applications.
- **File**: `01_apps/web_tui_portal/leaderboard_dashboard.py` (1,168 lines)
  - Dynamic tab-responsive project swarm composer, 3-tier model leaderboard (Local Airgap, Cloud Free Tier, Hybrid Sharded Mesh), and multi-transport interconnect table.
- **File**: `05_agents_and_swarms/swarm_elo_leaderboard.json` (142 lines)
  - Tracks 6 swarms with `👑 Dual-World Sovereign Mesh Swarm` holding Rank 1 (ELO 2248.5, 36/36 MCTS pass rate).
- **Test Command & Result**:
  `python3 -m pytest 05_agents_and_swarms/test_tri_vault_elo.py` (25 passed in 1.07s).

### 1.6 Native Rust Ratatui TUI Crates (R5, F21)
1. **`01_apps/rust_swarm_training_tui/`**
   - Implements `RatatuiApp` with 120 FPS render loop and non-blocking background telemetry reader.
   - Ingests `swarm_elo_leaderboard.json`, `continuous_lora_dataset.jsonl`, and `swe_bench_predictions/preds.json`.
   - `cargo test --manifest-path 01_apps/rust_swarm_training_tui/Cargo.toml` $\to$ Passes in 1.31s.
2. **`02_ai_models_and_inference/lauburu_tui/`**
   - Native Rust Ratatui control plane with 6 tabs: `Topology`, `Chat`, `Sharding`, `ApiScanner`, `Training`, `WebLens`.
   - `src/training.rs`: Implements `TrainingState`, `LoraTrainingJob`, `RamGovernorTier`, `BenchmarkTournamentRow`, `NpuBonusGrant`.
   - `cargo test --manifest-path 02_ai_models_and_inference/lauburu_tui/Cargo.toml` $\to$ Passes all 100+ tests across 10 test suites in 1.2s.

---

## 2. Logic Chain

1. **System Invariant Check**: The user request requires a continuous execution loop with dynamic confidence gating ($\tau = 0.85$), free cloud API quota harvesting ($0 spend), dual-world MCTS lookahead simulation, local AI training fallback, and real-time telemetry streaming to Port 8088 (`/training`, `/leaderboard`) and Rust TUI.
2. **Existing Implementation Verification**:
   - Gating mechanism is verified in `05_agents_and_swarms/high_confidence_swarm_runner.py` and `DualWorldConfidenceGate.CONFIDENCE_THRESHOLD = 0.85`.
   - Zero-dollar cloud oracle waterfall is verified in `05_agents_and_swarms/cloud_oracle_shadow.py` and `06_scripts_and_tooling/automation/cloud_api_quota_manager.py`.
   - Dual-World MCTS lookahead is verified in `05_agents_and_swarms/dual_world_mcts.py`.
   - Local LoRA training sink is verified at `/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl`.
   - Port 8088 web portal and leaderboard are verified in `01_apps/web_tui_portal/serve_portal.py` and `01_apps/web_tui_portal/leaderboard_dashboard.py`.
   - Live Rust TUI is verified in both `01_apps/rust_swarm_training_tui/` and `02_ai_models_and_inference/lauburu_tui/`.
3. **Execution & Conformance**:
   - All unit test suites (`test_high_confidence_runner.py`, `test_tri_vault_elo.py`, `test_dual_world_mcts.py`, `test_cloud_oracle_shadow.py`, `test_cloud_api_quota_manager.py`, `test_dynamic_ram_governor.py`) pass 100%.
   - Both Rust crates compile and pass tests cleanly with zero errors.

---

## 3. Caveats

1. **Local Model Endpoints**: Ports 8080 (Qwen 3.8 Max), 8085 (Huihui-27B Devil's Advocate), 8086 (AgentWorld-35B), 8088 (WebWorld-32B), and 18802 (Router Sentinel) have built-in deterministic offline fallback mocks (Rule #0 compliant with real AST parsing and zero-synthetic tokens). When physical endpoints are offline, the engines automatically use verifiable deterministic offline heuristic validation without crashing.
2. **Tri-Vault Headroom**: The NVMe disk headroom was measured at ~0.64 GB free before cache purging. While tests and file operations execute normally, regular maintenance via `DynamicRAMGovernor` and `clean_caches` is recommended to maintain $\ge 5.0\,\text{GB}$ free disk headroom.

---

## 4. Conclusion

The Lauburu Monorepo possesses a complete, modular, and verified autonomous execution loop architecture:
- `high_confidence_swarm_runner.py` directly enforces confidence gating ($\tau = 0.85$), routing $\ge 0.85$ to free cloud reasoning + dual-world simulation and $< 0.85$ to local LoRA dataset distillation.
- `cloud_oracle_shadow.py` and `cloud_api_quota_manager.py` strictly enforce $0.00 AUD cloud spend with 15 RPM Gemini 3.7 Flash and 10k daily Cloudflare Neurons.
- `dual_world_mcts.py` evaluates code diffs against `AgentWorld-35B` (:8086) and `WebWorld-32B` (:8088) with `DevilsAdvocateClient` (:8085).
- `serve_portal.py` runs on Port 8088 serving `/training`, `/leaderboard`, and WebSocket terminal streams for the Rust TUI (`rust_swarm_training_tui` and `lauburu-tui`).
- All 150+ unit and integration tests pass 100% across Python and Rust test harnesses.

---

## 5. Verification Method

To independently reproduce and verify all observations:

1. **High Confidence Runner Tests**:
   ```bash
   python3 -m unittest /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/test_high_confidence_runner.py
   ```
2. **Tri-Vault ELO & Port 8088 Leaderboard API Tests**:
   ```bash
   python3 -m pytest /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/test_tri_vault_elo.py
   ```
3. **Dual-World MCTS & Cloud Oracle Shadow Tests**:
   ```bash
   python3 -m pytest /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/test_dual_world_mcts.py /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/test_cloud_oracle_shadow.py
   ```
4. **Cloud Quota Manager & Dynamic RAM Governor Tests**:
   ```bash
   python3 -m pytest /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/tests/test_cloud_api_quota_manager.py /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/tests/test_dynamic_ram_governor.py
   ```
5. **Rust Swarm Training TUI Test**:
   ```bash
   cargo test --manifest-path /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/rust_swarm_training_tui/Cargo.toml
   ```
6. **Lauburu TUI Control Plane Tests**:
   ```bash
   cargo test --manifest-path /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/lauburu_tui/Cargo.toml
   ```
