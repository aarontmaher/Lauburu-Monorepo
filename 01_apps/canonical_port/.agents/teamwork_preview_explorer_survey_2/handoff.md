# Handoff Report: Canonical Port TUI Specialist Integration Survey (Explorer 2)

**Author**: Explorer 2 (teamwork_preview_explorer_survey_2)  
**Target Milestone**: Survey & Architectural Blueprint for TUI Specialist Integration  
**Date**: 2026-08-29T03:21:00+10:00  
**Scope**: Backend Daemon Architecture, Telemetry Ingestion (`mesh_trends.json`), Git Worktrees Sandboxing, The Devil's Lock Governance, and TUI Live Implementation Stream Widget.

---

## 1. Observation

### 1.1 Existing Telemetry & Optimization Daemon Codebase
Direct inspection of existing files across the monorepo revealed the following state:

1. **`tui_ux_optimizer_swarm.py`**:
   - **Path**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/tui_specialist_local_ai/tui_ux_optimizer_swarm.py`
   - **Lines 17–22**:
     ```python
     DATA_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory"
     TRENDS_FILE = os.path.join(DATA_DIR, "mesh_trends.json")
     BFS_PATH = os.path.join(DATA_DIR, "ga_optimized_path.json")
     ELO_PATH = os.path.join(DATA_DIR, "data", "canonical_ai_leaderboard.json")
     OUTPUT_REC = os.path.join(DATA_DIR, "tui_ux_recommendations.json")
     ```
   - **Lines 105–123**: The script currently operates on a passive 30-second polling loop (`time.sleep(30)`), writing UX recommendations to `tui_ux_recommendations.json`.
   - **Gap Identified**: It currently does *not* trigger autonomous code restructuring, does *not* invoke Git Worktree sandboxing, lacks the "Devil's Lock" resource/VRAM/ELO gating mechanisms, and does *not* publish real-time execution steps to `tui_live_implementation_stream.json`.

2. **Telemetry Source (`mesh_trends.json`)**:
   - **Path**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/mesh_trends.json`
   - **Producer**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/mesh_telemetry_crawler.py` (lines 15, 60–90) continuously polls 8 mesh nodes (`L1_Mac_Node`, `L2_MacBook_Pro`, `L3_Linux_Head`, `L4_Linux_Tablet`, `L5_MacBook_Air`, `L6_Pixel_10_Pro`, `L7_Samsung_S20`, `GW_Router`) and writes latency/status JSON atomically via `.tmp` rename.
   - **Format Observed**:
     ```json
     {
       "timestamp": 1787878597.740451,
       "nodes": {
         "L1_Mac_Node": { "ip": "100.119.199.76", "latency": 0.252, "status": "ONLINE" },
         "L2_MacBook_Pro": { "ip": "100.103.212.21", "latency": 26.892, "status": "ONLINE" },
         ...
       }
     }
     ```

3. **Canonical AI Leaderboard (`canonical_ai_leaderboard.json`)**:
   - **Path**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/canonical_ai_leaderboard.json` (and symlinked `/data/canonical_ai_leaderboard.json`)
   - **Schema & Roster**: Evaluated 15 models with composite ELOs and 30 specialist skills.
   - **Top UI/Coding Domain Performers**:
     - `kimi_tandem_titan`: Overall ELO 3089.0 | Skills: `3d_ai_training_game`: 99.8, `vision_vlm_truth_auditing`: 99.7, `flutter_dart_mobile_architecture`: 95.6, `nl2repo_synthesis`: 95.6
     - `gemini_3_1_pro`: Overall ELO 3145.0 | Skills: `3d_ai_training_game`: 99.5, `vision_vlm_truth_auditing`: 99.8
     - `antigravity_preview`: Overall ELO 2390.0 | Skills: `3d_ai_training_game`: 99.6, `flutter_dart_mobile_architecture`: 99.0, `vision_vlm_truth_auditing`: 99.0
     - `qwen2_5_vl_72b`: Overall ELO 2330.0 | Skills: `3d_ai_training_game`: 99.5, `vision_vlm_truth_auditing`: 99.5

4. **Live Stream File (`tui_live_implementation_stream.json`)**:
   - **Path**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/tui_live_implementation_stream.json`
   - **Current Content**:
     ```json
     {"active_agent": "Qwen 3.8 vs Gemma 4 Duel", "current_action": "Restructuring TUI Grid Layout for Network Accuracy", "progress": 25}
     ```

5. **Git Worktree Subsystem & Host Environment**:
   - Command `git worktree list` executed cleanly:
     - Main tree: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo [main]`
     - Git version: `git version 2.50.1 (Apple Git-155)`
   - Monorepo `.gitignore` contains only 2 lines, meaning worktrees created under `/tmp/lauburu_worktrees/` or `/tmp/canonical_port_worktrees/` remain completely outside git tracking and guarantee 0 clutter in the main monorepo.

6. **Canonical Port TUI Structure**:
   - Main Textual App: `01_apps/canonical_port/tui/canonical_tui.py`
   - Widget Directory: `01_apps/canonical_port/tui/widgets/`
   - Screens: `01_apps/canonical_port/tui/screens/` (e.g. `agi_coding_terminal_screen.py`, `optimization_screen.py`, `network_screen.py`)
   - Test Infrastructure: `tests/run_all_tiers.py` executes 4 tiers of pytest via `uv run`.

---

## 2. Logic Chain

From the direct observations, the following step-by-step reasoning informs the architecture:

1. **Safety & Zero Monorepo Mutation Invariant (R1)**:
   - *Observation*: The user explicitly requires that `01_apps` in the primary workspace is never directly mutated by autonomous subagents.
   - *Deduction*: When the daemon determines that a UI restructuring is needed (e.g., node offline, high latency on primary link requiring visual alert banner, or confidence $\ge 0.90$ from telemetry analysis), it must invoke `git worktree add -b <branch_name> <sandbox_path> HEAD`.
   - *Deduction*: The subagent executes all modifications strictly inside `<sandbox_path>/01_apps/canonical_port/`. Any compiler errors, failing tests, or malformed syntax are contained in the ephemeral branch without destabilizing the running host TUI or monorepo workspace.

2. **The Devil's Lock Gating Mechanism (R2)**:
   - *Observation*: Requirement R2 specifies three strict gates before an agent is permitted to spawn:
     1. **Resource Cap**: Exactly 1 active subagent at a time.
     2. **VRAM Check**: `check_vram_and_lock()` must block execution if free VRAM headroom $< 15\%$.
     3. **Genetic ELO Mandate**: Read `canonical_ai_leaderboard.json` and select the highest domain ELO model for UI/TUI tasks.
   - *Deduction*: A dedicated governor class (`DevilsLockGovernor`) must encapsulate these checks:
     - Mutex/Process Lock: A reentrant process lock (`threading.Lock` + filesystem PID lock) ensuring `active_subagents == 0`.
     - VRAM Formula: On macOS (Apple Silicon unified memory), free memory headroom is computed via `psutil.virtual_memory().available / psutil.virtual_memory().total * 100`. On Linux GPU nodes, `nvidia-smi` or `hardware_telemetry.py` queries dedicated VRAM. If free percentage $< 15.0\%$, `check_vram_and_lock()` returns `(False, "Free VRAM < 15.0% (Headroom: X%)")` and halts spawning.
     - ELO Selector: Query `canonical_ai_leaderboard.json` $\to$ compute weighted UI domain score (combining `overall_benchmark_score`, `elo`, `3d_ai_training_game`, `vision_vlm_truth_auditing`, `flutter_dart_mobile_architecture`, `nl2repo_synthesis`) $\to$ deterministically pick the #1 candidate (e.g., `kimi_tandem_titan` or `gemini_3_1_pro`).

3. **Live Implementation Stream Widget (R3)**:
   - *Observation*: The TUI must render the subagent's live progress by tailing `04_data_and_memory/tui_live_implementation_stream.json` without requiring app restart.
   - *Deduction*: A new Textual widget `LiveImplementationStreamWidget` (inheriting from `Static` or `Widget`) will use `set_interval(0.5, self._poll_stream)` to tail the stream file with atomic mtime checks.
   - *Deduction*: When the JSON content changes, the widget dynamically updates its Rich renderable (showing active agent badge, current action string, progress bar percentage, worktree path, and status indicator).

---

## 3. Implementation Strategy & Architecture Blueprint

### 3.1 Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                             CANONICAL PORT TUI ECOSYSTEM                                 │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  [04_data_and_memory/mesh_trends.json] ──(Live Ping Sweeps)──► [mesh_telemetry_crawler]  │
│                                │                                                         │
│                                ▼                                                         │
│     ┌──────────────────────────────────────────────────────────────────────────────┐     │
│     │               TUI Specialist Subagent Orchestrator Daemon                    │     │
│     │   (05_agents_and_swarms/.../tui_ux_optimizer_swarm.py & Backend Module)      │     │
│     ├──────────────────────────────────────────────────────────────────────────────┤     │
│     │ 1. Telemetry Monitor: Analyzes trends, computes redesign triggers            │     │
│     │ 2. The Devil's Lock Governor:                                                │     │
│     │    • Concurrency Lock (Max 1 active subagent)                                │     │
│     │    • check_vram_and_lock() (Blocks if Free VRAM < 15.0%)                     │     │
│     │    • Genetic ELO Mandate (Reads canonical_ai_leaderboard.json)               │     │
│     │ 3. Git Worktree Sandbox Manager:                                             │     │
│     │    • git worktree add -b tui-subagent-<ts> /tmp/lauburu_worktrees/...        │     │
│     │    • Zero direct mutation on 01_apps/ in main tree                           │     │
│     │    • Sandbox test verification (pytest in worktree)                          │     │
│     │    • Teardown & git worktree remove --force                                  │     │
│     │ 4. Live Stream Broadcaster:                                                  │     │
│     │    • Writes 04_data_and_memory/tui_live_implementation_stream.json           │     │
│     └──────────────────────────────────────┬───────────────────────────────────────┘     │
│                                            │                                             │
│                                            ▼ (Tails stream JSON)                         │
│     ┌──────────────────────────────────────────────────────────────────────────────┐     │
│     │                      Canonical Port Textual TUI                              │     │
│     │        (01_apps/canonical_port/tui/widgets/live_implementation_stream.py)   │     │
│     │  • Renders Live Subagent Progress, Active Agent ELO Badge, Action Text      │     │
│     │  • Reactive real-time updates without restarting the TUI                    │     │
│     └──────────────────────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Key Subsystems & File Layout

| Subsystem | File Location | Responsibility |
| :--- | :--- | :--- |
| **Telemetry Ingestion & Trigger** | `04_data_and_memory/mesh_trends.json` & `05_agents_and_swarms/tui_specialist_local_ai/tui_ux_optimizer_swarm.py` | Detects topology changes (node offline, latency $> 50\text{ms}$, routing updates) requiring UI adaptation. |
| **The Devil's Lock Governor** | `01_apps/canonical_port/backend/devils_lock_governor.py` (or shared backend) | Enforces: (1) max 1 active subagent, (2) `check_vram_and_lock()` free VRAM $\ge 15\%$, (3) Genetic ELO selection. |
| **Git Worktree Sandboxing** | `01_apps/canonical_port/backend/worktree_sandbox.py` | Manages `git worktree add -b`, execution isolation in `/tmp/lauburu_worktrees/`, pytest verification, and clean prune. |
| **Live Stream Contract** | `04_data_and_memory/tui_live_implementation_stream.json` | Atomic JSON stream recording timestamp, active agent, current action, progress (0-100), worktree path, status. |
| **TUI Stream Widget** | `01_apps/canonical_port/tui/widgets/live_implementation_stream.py` | Textual widget embedding reactive live progress bar, active model badge, and status logs into the TUI. |
| **Automated Test Suite** | `01_apps/canonical_port/tests/unit/test_tui_specialist_integration.py` | Complete unit & integration test suite covering daemon lifecycle, worktree isolation, Devil's Lock, and widget updates. |

---

## 4. Caveats

1. **Git Worktree Path Isolation**:
   - Worktrees must be placed in `/tmp/lauburu_worktrees/` or `/private/tmp/canonical_port_worktrees/` to prevent untracked file pollution in the main git repository.
   - When tearing down worktrees, always execute `git worktree remove --force <path>` followed by `git worktree prune` to avoid stale `.git/worktrees/` reference locks.
2. **Apple Silicon Unified Memory vs Discrete VRAM**:
   - On macOS ARM64 systems, VRAM is dynamically shared with system RAM. `psutil.virtual_memory()` provides the most accurate and empirical free headroom metric without requiring sudo or privileged kernel extensions.
3. **Atomic File Streaming**:
   - `tui_live_implementation_stream.json` must always be written via a temporary file + atomic rename (`os.replace`) to prevent the TUI widget from reading partial or corrupted JSON during high-frequency updates.
4. **Zero-Mock Telemetry Compliance (Rule #0)**:
   - When no subagent is actively executing, the stream and TUI widget must explicitly display an authentic waiting state (`IDLE / STANDBY`) rather than generating synthetic progress ticks.

---

## 5. Conclusion & Concrete Recommendations for Planner & Implementers

1. **Modular Architecture**: Implement the Devil's Lock, Worktree Sandbox, and Stream Broadcaster as cohesive, testable Python classes with clean interfaces so they can be invoked both by `tui_ux_optimizer_swarm.py` and directly within Canonical Port test harnesses.
2. **Devil's Lock Verification**: Ensure `check_vram_and_lock()` accepts configurable mock/test overrides (e.g. `mock_vram_pct` for testing boundary conditions under $15\%$ and above $15\%$) while defaulting strictly to live hardware telemetry.
3. **Seamless TUI Integration**: Expose `LiveImplementationStreamWidget` in `01_apps/canonical_port/tui/widgets/` and integrate it into `agi_coding_terminal_view.py` and `optimization_view.py` so operators immediately see live subagent modifications.
4. **Fast-Path Automated Testing**: Include a dedicated pytest module in `tests/unit/test_tui_specialist_integration.py` verifying:
   - Dynamic Git Worktree creation and teardown without touching `01_apps`.
   - Devil's Lock gating (blocking on concurrency $> 1$, blocking on VRAM $< 15\%$, passing on valid state).
   - ELO candidate resolution from `canonical_ai_leaderboard.json`.
   - Real-time reactivity of the `LiveImplementationStreamWidget` when test JSON payloads are appended.

---

## 6. Verification Method

To independently verify the findings and subsequent implementations:

1. **Verify Git Worktrees Isolation**:
   ```bash
   cd /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo
   git worktree list
   ```
2. **Verify Telemetry Ingestion & Leaderboard Files**:
   ```bash
   python3 -c '
   import json
   with open("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/mesh_trends.json") as f:
       print("Mesh Trends Nodes:", list(json.load(f)["nodes"].keys()))
   with open("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/canonical_ai_leaderboard.json") as f:
       print("Leaderboard Top Model:", json.load(f)["canonical_summary"]["top_sovereign_model_id"])
   '
   ```
3. **Execute Full Canonical Port Test Suite**:
   ```bash
   cd /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port
   uv run --with rich,textual,pyyaml,pytest,pytest-asyncio,httpx pytest tests/ -v
   ```
