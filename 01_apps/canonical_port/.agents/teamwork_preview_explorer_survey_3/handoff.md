# Survey Report: 4-Way Debate Governance (The Devil's Lock) & Live Implementation Stream Widget

**Agent**: `teamwork_preview_explorer_survey_3`  
**Milestone**: Survey Phase — Canonical Port TUI Specialist Integration  
**Date**: 2026-08-29T03:22:30+10:00 (UTC: 2026-08-28T17:22:30Z)  
**Target Project**: `01_apps/canonical_port`  
**Working Directory**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/teamwork_preview_explorer_survey_3`  

---

## 1. Observation

### 1.1 Authoritative Requirements & Gating Invariants
Inspection of `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/ORIGINAL_REQUEST.md` (Lines 19–39) established the functional requirements:
```markdown
### R1. TUI Specialist Subagent Orchestrator
Build a backend Python daemon (or extend `tui_ux_optimizer_swarm.py`) that monitors network telemetry (`mesh_trends.json`). When UI restructuring is needed, it must spawn a sandboxed subagent using Git Worktrees (Branched Workspaces) to safely modify the code.
- Ensure `01_apps` is never directly mutated by the AI subagent; all spawned modifications occur in the isolated Git Worktree.

### R2. 4-Way Debate Governance (The Devil's Lock)
The orchestrator must strictly enforce the following gating mechanisms before spawning an agent:
1. Resource Cap: Only 1 active subagent is allowed at a time.
2. VRAM Check: Do not spawn if global VRAM headroom is under 15% (e.g. `check_vram_and_lock()` explicitly blocks execution if free VRAM < 15%).
3. Genetic ELO Mandate: It must read the `canonical_ai_leaderboard.json` and select the model with the highest domain ELO for UI tasks.

### R3. Live Implementation Stream Widget
The TUI must feature a new visible component (e.g., a Textual log panel / widget in `tui/`) that continuously tails `04_data_and_memory/tui_live_implementation_stream.json` (or relative path in project) to visually broadcast exactly what the spawned subagent is currently coding/restructuring in real-time. Appending a test string to the JSON file must successfully update the TUI live without a restart.
```

### 1.2 Existing Optimizer Swarm Implementation
Inspection of `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/tui_specialist_local_ai/tui_ux_optimizer_swarm.py` (Lines 17–49) revealed:
- `DATA_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory"`
- `TRENDS_FILE = os.path.join(DATA_DIR, "mesh_trends.json")`
- `BFS_PATH = os.path.join(DATA_DIR, "ga_optimized_path.json")`
- `ELO_PATH = os.path.join(DATA_DIR, "data", "canonical_ai_leaderboard.json")`
- `OUTPUT_REC = os.path.join(DATA_DIR, "tui_ux_recommendations.json")`
- `scout_telemetry()` polls `mesh_trends.json`, `ga_optimized_path.json`, and `canonical_ai_leaderboard.json`.
- It currently operates as an un-gated loop without subagent process locking, without VRAM headroom validation, and without Git Worktree isolation.

### 1.3 Canonical AI Leaderboard Schema & Domain ELO Structure
Inspection of `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/canonical_ai_leaderboard.json` (Lines 1–1885) and `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/canonical_ai_leaderboard.py` (Lines 75–285) revealed:
- `canonical_ai_leaderboard.json` conforms to JSON Schema v7 with root keys: `schema_version`, `last_updated_utc`, `canonical_summary`, `benchmark_pillars`, `specialist_skills_definitions`, `leaderboard`, `match_history`.
- In `leaderboard`, each model entry contains:
  - `id`: unique identifier (e.g. `kimi_tandem_titan`, `gemini_3_1_pro`, `antigravity_preview`, `claude_37_sonnet`, `genetic_moe_orchestrator`, `gemma_4_26b_vlm`, `qwen_38_vl_30b`).
  - `elo`: numerical ELO rating (e.g. 3089.0, 3145.0, 2390.0, 2360.0, 2310.0, 2275.0, 2265.0).
  - `canonical_score`: composite score (0–100).
  - `specialist_skills`: dictionary mapping skill IDs to 0.0–100.0 ratings. Key UI/UX specialist skills include:
    - `vision_vlm_truth_auditing`: VLM Visual Audit & Truth Verification (e.g. 99.7 for Kimi, 99.8 for Gemini 3.1, 99.5 for Gemma 26B).
    - `3d_ai_training_game`: 3D Spatial UI/UX & Real Project AI Training (e.g. 99.8 for Kimi, 99.6 for Antigravity, 99.4 for Genetic MoE).
    - `flutter_dart_mobile_architecture`: Reactive UI & Client Mobile Architecture (e.g. 99.0 for Antigravity, 98.8 for Claude 3.7).
    - `openclaw_utilisation`: Edge Gateway & UI Automation (e.g. 95.6 for Kimi, 94.8 for Antigravity).
    - `terminal_bench_2_1`: CLI & POSIX Terminal Mastery.

### 1.4 Existing Leaderboard Resolvers in Canonical Port
Inspection of `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/backend/agents/continuous_arena_router.py` (Lines 187–320) revealed:
- `ChampionLeaderboardResolver` implements debounced `mtime` caching against `data/canonical_ai_leaderboard.json` or `04_data_and_memory/data/canonical_ai_leaderboard.json`.
- Safely recovers from disk errors using fallback default champion `kimi_tandem_titan` (ELO 3089.0, `llama_rpc`).
- Extracts model metadata and resolves target execution engine (`llama_rpc`, `exo`, `cloudflare`, `gemini`, `julien`).

### 1.5 Hardware Telemetry & Memory/VRAM Polling Mechanisms
Inspection of `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/multi_wan/hardware_telemetry.py` (Lines 80–148, 254–332) and `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/multi_wan/agi_offload.py` (Lines 108–120) revealed:
- **macOS / Apple Silicon Unified Memory Architecture**:
  - Apple M4 Pro Mac Mini Host (24.0 GB Unified RAM / 21.6 GB AI cap).
  - VRAM is shared unified system memory (`vram_type = "Unified System Memory"`).
  - Memory telemetry is queried via `psutil.virtual_memory()`:
    - `mem.total` (total RAM in bytes)
    - `mem.available` (free/reclaimable memory in bytes)
    - `mem.percent` (used memory percentage)
    - Free memory headroom percentage = `(mem.available / mem.total) * 100.0`.
  - Non-psutil macOS fallback:
    - `sysctl -n hw.memsize` (total physical memory bytes)
    - `vm_stat` (parses `Pages free`, `Pages inactive`, `Pages speculative` multiplied by page size 4096 / 16384 bytes).
- **Linux Architecture**:
  - `/proc/meminfo` (`MemTotal`, `MemAvailable`, `MemFree`).
  - `nvidia-smi --query-gpu=memory.total,memory.free,memory.used --format=csv,noheader,nounits` (for dedicated GPU nodes).
- **Mesh / Blackboard Layer**:
  - Global Pooled Usable VRAM across 7 nodes = 82.8 GB total.
  - `blackboard_store.py` (`layer_1_hardware` and `layer_3_ai_inference`) maintains live node metrics.

### 1.6 Live Implementation Stream File State
Inspection of `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/tui_live_implementation_stream.json` revealed:
```json
{"active_agent": "Qwen 3.8 vs Gemma 4 Duel", "current_action": "Restructuring TUI Grid Layout for Network Accuracy", "progress": 25}
```
- Current format is a compact JSON object.
- The stream represents real-time execution state of background agents restructuring or coding features.

### 1.7 Textual TUI Architecture & Widget Integration
Inspection of `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/tui/canonical_tui.py` (Lines 76–150), `tui/screens/agi_coding_terminal_screen.py` (Lines 17–100), and `tui/services/blackboard_store.py` (Lines 63–120, 934–975) revealed:
- Textual 0.50+ supports asynchronous workers via `@work(exclusive=True)` and periodic reactive timers via `self.set_interval(interval_sec, callback)`.
- `BlackboardStore` utilizes POSIX atomic disk persistence (`.tmp.<pid>.<tid>` + `os.replace`) to guarantee corruption-free writes.
- TUI screens communicate via reactive message passing (`post_message`) and thread-safe data polling.

---

## 2. Logic Chain

### 2.1 The Devil's Lock: 4-Way Debate Governance Architecture

```
                                  TELEMETRY TRIGGER
                                (mesh_trends.json delta)
                                           │
                                           ▼
                       ┌───────────────────────────────────────┐
                       │  DEVIL'S LOCK GATEWAY EVALUATION      │
                       └───────────────────────────────────────┘
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         ▼                                 ▼                                 ▼
┌──────────────────┐             ┌──────────────────┐             ┌──────────────────┐
│  GATE 1: CAP     │             │  GATE 2: VRAM    │             │  GATE 3: ELO     │
│ Active Subagent  │             │ Free Headroom    │             │ Genetic Leader-  │
│ Limit == 1       │             │ >= 15.0%         │             │ board Domain Rank│
└──────────────────┘             └──────────────────┘             └──────────────────┘
         │                                 │                                 │
         │ (Subagent Active?)              │ (Free VRAM < 15%?)              │ (Select Top Model)
         ├─ YES ──> [BLOCK & LOG CAP]      ├─ YES ──> [BLOCK & LOCK VRAM]    │
         │                                 │                                 │
         └─ NO ────────────────────────────┴─ NO ────────────────────────────┘
                                           │
                                           ▼
                       ┌───────────────────────────────────────┐
                       │  ALL GATES PASSED (Devil's Lock Open) │
                       └───────────────────────────────────────┘
                                           │
                                           ▼
                       ┌───────────────────────────────────────┐
                       │  SPAWN ISOLATED GIT WORKTREE          │
                       │  path: .worktrees/tui_specialist_<id> │
                       │  (01_apps remains unmutated)          │
                       └───────────────────────────────────────┘
                                           │
                                           ▼
                       ┌───────────────────────────────────────┐
                       │  STREAM TO tui_live_stream.json       │
                       │  (Textual Tail Widget Renders Live)   │
                       └───────────────────────────────────────┘
```

#### Gate 1: Resource Cap (1 Active Subagent Limit)
1. **Concurrency Hazard**: If multiple subagents are spawned concurrently, they will compete for GPU/VRAM resources, trigger Git index lock collisions (`.git/index.lock`), cause race conditions on `mesh_trends.json` and `tui_live_implementation_stream.json`, and violate single-thread agility rules.
2. **Lock Mechanism**:
   - Primary: POSIX file lock (`fcntl.flock` on an explicit lock file `/tmp/tui_specialist_subagent.lock` or `<repo_root>/.agents/active_subagent.lock`).
   - In-Memory State: `threading.Lock` and `asyncio.Lock` inside the daemon.
   - PID & Heartbeat Tracking: Lock metadata records `{"subagent_id": str, "pid": int, "spawned_utc": str, "worktree_path": str, "last_heartbeat": float}`.
3. **Stale Lock Auto-Healing**:
   - Before blocking, the daemon inspects whether the recorded PID is actively running via `os.kill(pid, 0)`.
   - If the PID is dead, or if `now - last_heartbeat > timeout_seconds` (default 300s), the daemon automatically releases the stale lock, logs a self-healing event to `progress.md`, and safely proceeds.
4. **Context Manager Pattern**:
   - `async with SubagentResourceLock(lock_path) as lock:` guarantees that upon subagent completion, failure, or cancellation, the lock is released in a `finally:` block.

#### Gate 2: VRAM Check (`check_vram_and_lock()`)
1. **Rule #0 Zero-Mock Directive**: Telemetry must never hallucinate memory headroom or generate arbitrary mock numbers. Memory metrics must originate directly from verified OS kernel or Metal APIs.
2. **Apple Silicon Unified Memory Reality**:
   - On the host Mac Mini (M4 Pro / macOS), GPU VRAM is unified with physical RAM.
   - Memory headroom must be calculated as:
     $$\text{Free VRAM \%} = \frac{\text{Available Memory (bytes)}}{\text{Total Memory (bytes)}} \times 100.0$$
3. **Multi-Tier Zero-Mock Polling Hierarchy**:
   - **Tier 1 (psutil)**: `mem = psutil.virtual_memory()`; `free_pct = (mem.available / mem.total) * 100.0`.
   - **Tier 2 (macOS vm_stat + sysctl)**: If `psutil` is unavailable:
     - `total_bytes = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"]))`
     - Parse `vm_stat` page counts: $\text{available\_bytes} = (\text{Pages free} + \text{Pages inactive} + \text{Pages speculative}) \times \text{page\_size}$.
   - **Tier 3 (Linux /proc/meminfo or nvidia-smi)**:
     - `MemAvailable / MemTotal * 100.0` or `memory.free / memory.total * 100.0`.
   - **Tier 4 (Mesh Blackboard Telemetry)**: If host OS probes are unavailable, query `blackboard_store.get_snapshot().layer_1_hardware`.
   - **Fail-Closed Gate**: If no real metric can be extracted, DO NOT assume 50% or 100%. Fail-closed: raise `HardwareTelemetryError("Unable to verify physical VRAM headroom under Rule #0")` and block execution.
4. **The 15% Blocking Threshold**:
   - Function Signature: `def check_vram_and_lock(min_free_pct: float = 15.0) -> Tuple[bool, float, Dict[str, Any]]`
   - If $\text{free\_vram\_pct} < 15.0\%$:
     - Function returns `(False, free_vram_pct, telemetry)` or raises `VRAMLockBlockedError`.
     - Logs: `[DEVIL'S LOCK ENGAGED] Free VRAM Headroom is {free_vram_pct:.2f}% (< 15.00%). Spawning blocked.`
     - Status is broadcast to `tui_live_implementation_stream.json` (`status: "BLOCKED_VRAM_QUOTA"`).

#### Gate 3: Genetic ELO Mandate (Domain UI Model Selection)
1. **Objective**: Read `canonical_ai_leaderboard.json` and select the optimal model with the highest domain ELO for UI/UX tasks.
2. **Domain UI Score Formulation**:
   In `canonical_ai_leaderboard.json`, each candidate model possesses specific skill ratings (0–100) across 19+ pillars. For UI/UX restructuring tasks, we compute the **UI Domain Fitness Score ($S_{\text{UI}}$)**:
   $$S_{\text{UI}} = 0.35 \cdot S_{\text{vision\_vlm\_truth}} + 0.30 \cdot S_{\text{3d\_ai\_game}} + 0.20 \cdot S_{\text{flutter\_dart}} + 0.15 \cdot S_{\text{openclaw}}$$
   And the **Domain UI ELO ($R_{\text{UI}}$)**:
   $$R_{\text{UI}} = \text{Overall ELO} \times \left(\frac{S_{\text{UI}}}{100.0}\right)$$
3. **Selection Hierarchy**:
   - Rank 1: Highest $R_{\text{UI}}$ with 100% Rule #0 truth compliance.
   - Tie-breaking: Higher `overall_benchmark_score` followed by lower `params_b` (frugality scaling $\eta_{size}$).
   - Current Leaderboard Ranking for UI Tasks:
     1. `kimi_tandem_titan` (Overall ELO 3089.0 | $S_{\text{UI}} \approx 99.4$ | $R_{\text{UI}} \approx 3070.5$)
     2. `gemini_3_1_pro` (Overall ELO 3145.0 | $S_{\text{UI}} \approx 97.4$ | $R_{\text{UI}} \approx 3063.2$)
     3. `antigravity_preview` (Overall ELO 2390.0 | $S_{\text{UI}} \approx 98.6$ | $R_{\text{UI}} \approx 2356.5$)
     4. `genetic_moe_orchestrator` (Overall ELO 2310.0 | $S_{\text{UI}} \approx 98.4$ | $R_{\text{UI}} \approx 2273.0$)
     5. `gemma_4_26b_vlm` (Overall ELO 2275.0 | $S_{\text{UI}} \approx 98.2$ | $R_{\text{UI}} \approx 2234.0$)

---

### 2.2 Sandboxed Git Worktree Spawning Architecture (R1)

1. **Monorepo Invariant**: The root `01_apps/` and production source code must NEVER be directly mutated by autonomous subagents.
2. **Worktree Lifecycle Flow**:
   ```
   Main Git Worktree (/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo)
       │
       ├─ [1. Spawning Gate Passed]
       │   └── `git worktree add -b tui_patch_<id> .worktrees/tui_specialist_<id> HEAD`
       │
       ├─ [2. Subagent Execution in Sandbox]
       │   └── Subagent edits files ONLY inside `.worktrees/tui_specialist_<id>/01_apps/...`
       │   └── Subagent runs `pytest` / AST checks in isolated workspace
       │
       ├─ [3. Validation & Visual Audit Gate]
       │   └── Truth Audit / Syntax verification passes
       │
       └─ [4. Clean Teardown]
           └── `git worktree remove --force .worktrees/tui_specialist_<id>`
           └── `git branch -D tui_patch_<id>` (or merge to staging)
   ```
3. **Safety Properties**:
   - `01_apps/` on `main` branch remains 100% pristine throughout execution.
   - If subagent crashes or generates broken code, deleting the worktree completely isolates and discards the damaged workspace without repository corruption.

---

### 2.3 Live Implementation Stream Data Structure & File Watching (R3)

#### Data Structure Specification (`04_data_and_memory/tui_live_implementation_stream.json`)

```json
{
  "schema_version": "1.0.0",
  "timestamp_utc": "2026-08-29T03:22:30.123456Z",
  "epoch_ms": 1787995350123,
  "active_agent": "Kimi Tandem Titan (VL-Encoder + 72B Backbone)",
  "model_id": "kimi_tandem_titan",
  "domain_elo": 3070.5,
  "subagent_id": "tui_specialist_subagent_001",
  "worktree_path": "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.worktrees/tui_specialist_001",
  "current_action": "Restructuring TUI Grid Layout for Network Accuracy",
  "target_file": "01_apps/canonical_port/tui/widgets/live_speedtest_card.py",
  "status": "STREAMING_CODE",
  "progress": 45,
  "vram_headroom_pct": 34.2,
  "active_locks": ["resource_cap_1", "vram_headroom_ok"],
  "recent_stream_tokens": [
    "def render_dynamic_speed_gauge(self) -> Panel:",
    "    metrics = self.blackboard.get_snapshot().layer_0_networking.internet_speed",
    "    return Panel(f\"Download: {metrics.download_mbps} Mbps\", border_style=\"#00ffcc\")"
  ],
  "diff_summary": "+18 lines, -3 lines",
  "last_error": null
}
```

#### Real-Time File Change Watching Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        REAL-TIME WATCHER PIPELINE                      │
├────────────────────────────────────────────────────────────────────────┤
│ 1. WRITER SIDE (Subagent Daemon)                                       │
│    • Atomic Write: Write JSON to `tui_live_implementation_stream.json.tmp`│
│    • Atomic Swap: `os.replace(...)` to target file path                │
│    • Preserves zero partial-read corruption                            │
├────────────────────────────────────────────────────────────────────────┤
│ 2. WATCHER ENGINE (TUI Tail Service)                                   │
│    • Primary: `watchfiles.awatch()` async file system event watcher    │
│    • Fallback: Debounced `stat().st_mtime` polling loop (100ms - 250ms)│
│    • Error Recovery: Retry with 50ms exponential backoff on JSON errors│
├────────────────────────────────────────────────────────────────────────┤
│ 3. TEXTUAL REACTIVE UI COMPONENT (`LiveImplementationStreamWidget`)    │
│    • Worker: Textual `@work(exclusive=True, thread=True)` or asyncio   │
│    • Message: Dispatches `StreamUpdated(payload)` to UI thread         │
│    • Render: Rich syntax highlighted panel + animated progress bar     │
│    • Zero Restart Mandate: Live refresh on JSON append without restart │
└────────────────────────────────────────────────────────────────────────┘
```

#### Key Technical Decisions & Invariants:
1. **Atomic File Reads & Writes**:
   - Subagent daemon uses atomic file swap (`.tmp` + `os.replace`).
   - TUI reader wraps `json.loads` in `try...except (json.JSONDecodeError, OSError):` with a 50ms retry to gracefully handle transient race conditions during disk sync.
2. **Textual Non-Blocking UI Guarantee**:
   - The file watcher must NEVER execute synchronous blocking I/O on Textual's main event loop thread.
   - It runs as an asynchronous Textual worker (`@work(exclusive=True)`), posting reactive events to update the UI without dropping terminal frame rates (60 FPS).

---

## 3. Caveats

1. **Apple Silicon Unified Memory Swapping**: On macOS, when unified memory pressure rises, the OS kernel begins compressed memory swapping (`vm.swapusage`). `mem.available` in `psutil` accounts for reclaimable pages, but `check_vram_and_lock()` must strictly check `mem.available / mem.total >= 0.15` (15%) rather than pure unallocated RAM to avoid false locks from clean inactive memory caches.
2. **Git Worktree Path Depth**: Worktrees created within the repo root (e.g. `.worktrees/`) should be registered in `.gitignore` to prevent recursive Git scans or indexing bloat.
3. **No Direct Code Implementation in Survey Phase**: Under explorer rules, no production source code has been mutated in this survey turn. All designs, contracts, and test architectures are delivered as actionable specifications for implementation.

---

## 4. Conclusion

1. **4-Way Debate Governance (The Devil's Lock)** is completely specified and architecturally grounded:
   - **Resource Cap**: Enforces exactly 1 active subagent via PID-aware POSIX file locking (`/tmp/tui_specialist_subagent.lock`) with stale lock auto-healing.
   - **VRAM Check**: `check_vram_and_lock(min_free_pct=15.0)` blocks subagent spawning if free unified memory headroom falls below 15%, adhering strictly to Rule #0 Zero-Mock without simulated numbers.
   - **Genetic ELO Mandate**: Resolves `canonical_ai_leaderboard.json` using debounced `mtime` caching and selects the #1 ranked domain UI model using composite skill weighting ($S_{\text{UI}}$).
2. **Sandboxed Subagent Worktrees (R1)**:
   - Spawns isolated workspaces via `git worktree add`, ensuring `01_apps/` is never directly mutated by AI subagents.
3. **Live Implementation Stream Widget (R3)**:
   - Built on `04_data_and_memory/tui_live_implementation_stream.json` with atomic disk writes, async `watchfiles`/`mtime` watching, and a reactive Textual `LiveImplementationStreamWidget` updating live without TUI restart.

---

## 5. Verification Method

### 5.1 Test Suite & Verification Commands

```bash
# 1. Verify VRAM Headroom Check & Devil's Lock Gate
uv run pytest tests/unit/test_devils_lock_governance.py -v

# 2. Verify Genetic ELO Selection from Leaderboard
uv run pytest tests/unit/test_genetic_elo_selector.py -v

# 3. Verify Git Worktree Spawning Isolation
uv run pytest tests/unit/test_worktree_subagent_spawner.py -v

# 4. Verify Live Implementation Stream Tail Widget Live Update
uv run pytest tests/unit/test_live_stream_widget.py -v

# 5. Execute Full Integration Test Suite
uv run pytest tests/ -k "governance or stream or worktree or leaderboard" -v
```

### 5.2 Concrete Invalidation Conditions
- **Invalidation Condition 1**: If `check_vram_and_lock()` uses hardcoded constants, mock dictionaries, or random numbers instead of polling live OS kernel memory metrics (Rule #0 Violation).
- **Invalidation Condition 2**: If the daemon mutates `01_apps/` directly without creating an isolated Git Worktree.
- **Invalidation Condition 3**: If multiple subagents can run concurrently without hitting the 1-agent resource lock cap.
- **Invalidation Condition 4**: If appending a test string to `tui_live_implementation_stream.json` fails to update the TUI live without a process restart.
