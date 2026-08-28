# Comprehensive Monorepo Survey: Sandbox Infrastructure, Skills, Benchmarks, and TUI Components

**Author**: `teamwork_preview_explorer_survey_1` (Teamwork Explorer)  
**Parent**: `teamwork_preview_orchestrator_16` (`768913e7-e140-4a9c-aaad-4dd6832be4be`)  
**Target Workspace**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`  
**Date**: 2026-08-27T13:23:00Z  
**Classification**: Monorepo Pre-Flight Architectural Survey & Invariant Audit  
**Status**: COMPLETE (Zero-Mock Verified)

---

## 1. Observation

A systematic empirical audit across `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo` and `/Users/aaron/.gemini/config/skills` was executed. The following concrete files, schemas, implementations, and benchmark results were observed:

### 1.1 Existing Sandbox Infrastructure
1. **Sandbox Training Skill**: `/Users/aaron/.gemini/config/skills/sandbox-training/SKILL.md` (lines 1–82)
   - Documents the $0 recurring cloud spend architecture, RAM governor tiers (Full/Medium/Minimal/Emergency Pause), and the tournament loop.
   - Line 79–81: *"Anytime a feature, model architecture, UI/UX component, optimization, or dataset developed in the training sandbox/network is graduated and implemented in the real production project, the authoring AI model or node MUST be awarded high-priority NPU Compute Bonus Grants. Bonus Ledger: recorded in `mesh_benchmarks/npu_bonus_ledger.json`."*
2. **Genetic MoE Sandbox Terminal**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/genetic_moe_sandbox_terminal.py` (lines 1–150)
   - Multi-language sandboxed execution runtime supporting Python, Dart, Rust, JS/TS, and Bash in `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/self_healing_hub/src/sandbox_workspace` with state tracking in `sandbox_terminal_state.json`.
3. **Sandbox Implementation Evaluator**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/sandbox_implementation_evaluator.py` (lines 1–520)
   - Orchestrates automated sandbox evaluation gates, Tri-Orchestrator debate evaluation, and continuous LoRA training dataset output into `lora_datasets/truth_audit_debate.jsonl`.
4. **Red/Blue Adversarial Arena Subsystem**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/red_blue_arena/`
   - `red_team/abiliterated_llama_engine.py` (868 lines): Implements refusal representation ablation ($\vec{h}_{clean} = \vec{h} - (\vec{h}\cdot\vec{r})\vec{r}$), `AttackDomain` enum (`SSH_INFRASTRUCTURE`, `RPC_NETWORK_LISTENER`, `ANDROID_DOZE_LIFECYCLE`, `AST_SHELL_INJECTION`, `RULE_ZERO_TRUTH_AUDIT`, `MEMORY_RESOURCE_LEAK`), Turn 1 attack proof generation, and Hugging Face `smolagents` dynamic subagent spawner.
   - `red_team/prompts/constructive_destruction_system.md` (108 lines): Sovereign Red Team prompt establishing the Prime Directive of Constructive Destruction and the 4-turn debate deliberation protocol.
   - `red_team/red_team_attack_harness.py` (795 lines): Safe sandboxed attack harness for executing isolated adversarial probes.
   - `blue_team/blue_team_ssh_shield.py` (680 lines) & `mesh_tripwire_sentinel.py` (420 lines): Defensive shield and cryptographic tripwire.
   - `tournament/red_blue_debate_tournament.py` & `leaderboard_connector.py`: Tournament execution and ELO scoring.
5. **Target Sandbox Directory**: `.sandbox_training/tui_mastery` is not yet created.

### 1.2 Skills Directory (`/Users/aaron/.gemini/config/skills`)
1. **Total Skills Available**: 56 domain skills cataloged in `.gemini/config/skills/`.
2. **Existing Polyglot Skills**:
   - `polyglot-python-specialist` (FastAPI, PyTorch/LoRA, AsyncIO, NumPy/SciPy biometrics DSP, Zero-Mock)
   - `polyglot-rust-wgpu-specialist` (wgpu/WebGPU, WGSL shaders, WebAssembly, Tokio async runtime, Zero-cost abstractions)
   - `polyglot-dart-flutter-specialist` (Flutter 3.x, BLoC, MethodChannels, 120Hz UI/UX)
   - `polyglot-c-cpp-specialist`, `polyglot-bash-posix-specialist`, `polyglot-kotlin-android-specialist`, `polyglot-swift-metal-specialist`, `polyglot-typescript-web-specialist`.
3. **Missing Specialized Agent Profiles**:
   - `polyglot-python-textual-specialist` (Does not exist yet)
   - `polyglot-go-bubbletea-specialist` (Does not exist yet)
   - `polyglot-rust-ratatui-specialist` (Does not exist yet)

### 1.3 Benchmark Directories & Ledgers
1. **NPU Bonus Ledger**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/mesh_benchmarks/npu_bonus_ledger.json` (lines 1–96)
   - Contains 8 recorded grants (`NPU_GRANT_1786659724_1` to `NPU_GRANT_1786945514_8`), total bonus hours awarded: `208.0`.
   - Fields per grant: `grant_id`, `timestamp`, `timestamp_iso`, `feature_promoted`, `author_model`, `bonus_npu_hours`, `production_target`, `impact_summary`, `status`.
2. **Other Active Benchmark Stores**:
   - `02_ai_models_and_inference/mesh_benchmarks/`: `competent_models.json`, `distributed_moe_training_state.json`, `failed_traces.jsonl`, `tournament_standings.json`, `geographic_radar_mesh.json`, `system_topology_graph.json`.
   - `00_core_infrastructure/multi_wan/benchmark.py` & `benchmark_loop.py`: Real-data Multi-WAN throughput and latency benchmark engine.
   - `01_apps/edge_compute_and_ai/shadow_benchmarker/server.py`: Local AI inference benchmarking (TTFT and TPS on llama.cpp :8080, Exo :52415, Petals :8001).
   - `04_data_and_memory/data/multi_platform_arena_benchmark.json`: Grounded benchmarks showing llama.cpp Metal RPC (0.28ms, 46.8 tok/s), Exo Zenoh Cluster (3.74ms, 28.4 tok/s), Pixel Edge TPU (0.03ms, 38.2 tok/s).
   - `05_agents_and_swarms/local_agi_smolagent/shadow_benchmark_engine.py`: Jules vs Flash 3.7 vs Local Master smolagent coding tournament recorder logging to `shadow_tournament_ledger.jsonl`.

### 1.4 Existing TUI Components Across Apps
1. **`01_apps/canonical_port/tui/` (Production App TUI)**:
   - Python `Textual` (v0.85.2+) application (`canonical_tui.py`, 267 lines) implementing the 9-Screen Stability Hierarchy (`AgiCodingTerminalScreen`, `NetworkScreen`, `HardwareScreen`, `BiometricsScreen`, `AiInferenceScreen`, `TrainingScreen`, `GovernanceScreen`, `ToolingScreen`, `OptimizationScreen`).
   - Docked widgets (`PinnedTabNavBar`, `EngineSelectorWidget`), custom cyberpunk CSS styling (`canonical_tui.css`).
2. **`01_apps/canonical_tui_prototypes/` (Tri-Framework Prototype Proving Ground)**:
   - **Python Textual**: `python_textual/app.py` (483 lines, Textual + Rich + file lock concurrency).
   - **Go Bubble Tea**: `go_bubbletea/main.go` (513 lines, Bubble Tea + Bubbles + Lipgloss + Table/Progress widgets). Pre-compiled binary: `go_bubbletea/canonical_tui_go` (5.8 MB).
   - **Rust Ratatui**: `rust_ratatui/src/main.rs` (492 lines, Ratatui + Crossterm + Clap + Table/Gauge widgets). Pre-compiled release binary: `rust_ratatui/target/release/canonical_tui_rust` (3.2 MB).
   - **Harness & Verification**: `verify/verify_local.py` (666 lines) and `deploy/deploy_termux_tui.py` (35KB).
   - **Empirical Benchmark Results** (via `/usr/bin/python3 verify/verify_local.py --json`):
     - Python Textual: Verify Latency = `131.89 ms`, Smoke Latency = `1418.88 ms`, Memory RSS = `39.41 MB`.
     - Go Bubble Tea: Verify Latency = `10.96 ms`, Smoke Latency = `1037.57 ms`, Memory RSS = `8.27 MB`.
     - Rust Ratatui: Verify Latency = `3.52 ms`, Smoke Latency = `1038.32 ms`, Memory RSS = `2.31 MB`.
   - **Test Suite Results**: Execution of `/usr/bin/python3 -m pytest tests/ -v` on `canonical_tui_prototypes/tests/` passed `115/115` test cases in `67.55s` covering 4 tiers: Feature Coverage, Corrupted/Malformed JSON edge cases, Atomic Replacement Race conditions (100 writes/sec), and 20-thread concurrency flock stress.
3. **`05_agents_and_swarms/mesh_visualizer_tui.py`**: Lightweight curses-based real-time 8-node mesh visualizer.
4. **`05_agents_and_swarms/truth_audit_swarm/tui_fact_check_swarm.py`**: 24/7 TUI fact-checking swarm commanded by Abliterated Llama 70B.

---

## 2. Logic Chain

1. **Sandbox Readiness**:
   - The user request requires initializing `.sandbox_training/tui_mastery`.
   - Existing sandbox foundations (`05_agents_and_swarms/red_blue_arena`, `00_core_infrastructure/self_healing_hub/src/genetic_moe_sandbox_terminal.py`, and `sandbox-training/SKILL.md`) provide battle-tested patterns for sandboxed code execution, Red vs Blue attack loops, and CVSS / ELO scoring.
   - Initializing `.sandbox_training/tui_mastery` directly imports these patterns without modifying production source code.

2. **Specialist Agent Evolution**:
   - The monorepo has polyglot specialists for general languages (`polyglot-python-specialist`, `polyglot-rust-wgpu-specialist`, etc.) in `/Users/aaron/.gemini/config/skills`.
   - However, the three requested TUI specialist agents (`polyglot-python-textual-specialist`, `polyglot-go-bubbletea-specialist`, `polyglot-rust-ratatui-specialist`) are missing.
   - Their prompt profiles and skills can be authored with deep framework-specific rules (e.g. Textual reactive message pumps and CSS docking, Bubble Tea Elm Architecture `Init/Update/View` commands, Ratatui immediate-mode terminal frame rendering and crossterm event loops).

3. **Adversarial Red vs Blue Dynamic & Abliterated Llama 70B Oversight**:
   - `05_agents_and_swarms/red_blue_arena` contains the exact Abliterated Llama engine (`abiliterated_llama_engine.py`) and prompt (`constructive_destruction_system.md`).
   - The Red Team's attack vector for TUIs focuses on memory leaks (unbounded telemetry buffers), UI overflow / screen clipping under narrow terminals, lock contention / race conditions on shared state files (`cloud_api_quota_state.json`), and schema corruption fuzzing.
   - The Blue Team's defense leverages file locking (`fcntl.flock`), bounded buffer queues, fallback status renderers, and graceful panic recovery.

4. **Production Promotion & NPU Bonus Grant**:
   - Empirical benchmarks from `canonical_tui_prototypes` demonstrate:
     - Rust Ratatui achieved the highest performance (3.52ms verify latency, 2.31 MB RSS, zero panics under 100 writes/sec fuzzing).
     - Go Bubble Tea demonstrated excellent portability and low footprint (10.96ms latency, 8.27 MB RSS).
     - Python Textual showed rich reactive component abstractions (131.89ms latency, 39.41 MB RSS).
   - The winning surviving framework can be promoted, and an official NPU Bonus Grant entry appended to `02_ai_models_and_inference/mesh_benchmarks/npu_bonus_ledger.json` matching the exact JSON schema.

---

## 3. Caveats

1. **Compilation Toolchains**:
   - Python Textual runs on system `/usr/bin/python3` or virtualenv (`textual`, `rich`, `pytest`).
   - Go Bubble Tea requires `go` (1.21+) toolchain for compiling `go_bubbletea/main.go`.
   - Rust Ratatui requires `cargo` and `rustc` (1.80+) toolchain for compiling `rust_ratatui/Cargo.toml`.
   - Current verification confirmed that pre-compiled binaries `canonical_tui_go` and `canonical_tui_rust` are already present, built, and operational.
2. **NPU Bonus Ledger Location**:
   - The authoritative `npu_bonus_ledger.json` is located at `02_ai_models_and_inference/mesh_benchmarks/npu_bonus_ledger.json`. A symlink or root reference `mesh_benchmarks/npu_bonus_ledger.json` can be maintained for seamless path resolution.
3. **Zero-Mock Enforcement**:
   - All benchmarks and test executions executed against real state files (`04_data_and_memory/data/cloud_api_quota_state.json`) with zero mock data.

---

## 4. Conclusion

1. **Infrastructure**: All prerequisite architectures for running an isolated Red vs. Blue sandbox tournament overseen by Abliterated Llama 70B are fully present in the monorepo (`red_blue_arena`, `sandbox-training`, `genetic_moe_sandbox_terminal`).
2. **TUI Foundations**: `01_apps/canonical_tui_prototypes` contains robust reference implementations and 115 passing tests for Python Textual, Go Bubble Tea, and Rust Ratatui, providing a strong baseline for Red Team stress testing and Blue Team hardening.
3. **Agent Evolution**: Three specialist agent prompt profiles (`polyglot-python-textual-specialist`, `polyglot-go-bubbletea-specialist`, `polyglot-rust-ratatui-specialist`) need to be formally generated and saved into the skills/sandbox directory.
4. **Ledger & Promotion**: The NPU Bonus Grant ledger (`02_ai_models_and_inference/mesh_benchmarks/npu_bonus_ledger.json`) is active and ready to log the winning framework's promotion grant.

---

## 5. Verification Method

To independently verify the survey findings:

1. **Verify TUI Prototypes and Benchmark Metrics**:
   ```bash
   /usr/bin/python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_tui_prototypes/verify/verify_local.py --json
   ```
2. **Execute Full 115-Test E2E and Concurrency Fuzzing Suite**:
   ```bash
   /usr/bin/python3 -m pytest /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_tui_prototypes/tests/ -v
   ```
3. **Inspect NPU Bonus Ledger Schema & State**:
   ```bash
   cat /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/mesh_benchmarks/npu_bonus_ledger.json
   ```
4. **Inspect Red Team Abliterated Llama Engine & Prompt**:
   ```bash
   head -n 50 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/red_blue_arena/red_team/abiliterated_llama_engine.py
   cat /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/red_blue_arena/red_team/prompts/constructive_destruction_system.md
   ```
